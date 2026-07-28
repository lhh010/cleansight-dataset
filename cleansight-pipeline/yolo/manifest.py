#!/usr/bin/env python3
"""
yolo 两轨清单(train.yaml / test.yaml)的读写与解析 —— 只做机制,不含业务知识。

设计约束(整套改造的地基):
  - 本模块里**不出现**任何具体 split 名、类别名、目录名。它们全在 yaml 里,
    这里只负责把 yaml 说的话变成可用的数据结构。
  - 身份键是 **LS task id**(数据库主键,全局递增、跨项目唯一),不是视频文件名 ——
    视频在 LS 重传会换 uuid 前缀,文件名跟着变,task id 不变。
    因此清单不存视频名,build 时从导出 json 的 task.data.video 现查。
  - 清单 = **人工意图**(入库、手改);build 状态在各自的 completed_*.json。
    两者分开,免得人工编辑时误改状态。

清单的 tasks 有两种等价形态,load() 统一归一化成 {task_id: split_or_None}:
  - 映射(train.yaml):  {59: train, 61: val}   —— 逐条指定 split
  - 列表(test.yaml):   [101, 102]             —— 恒为本轨唯一的 split,值为 None,
                                                 由 builder 用轨的 split 填上
"""
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent        # yolo/
ROOT = HERE.parent                            # cleansight-pipeline/

sys.path.insert(0, str(ROOT))
from utils import labelstudio, split as splitmod  # noqa: E402

TRAIN_MANIFEST = HERE / "train.yaml"      # 训练轨清单(train/val)
TEST_MANIFEST = HERE / "test.yaml"        # benchmark 清单(test)
CLASSES_PATH = HERE / "classes.yaml"      # 两轨共享的 class id 映射


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

def load(path=TRAIN_MANIFEST) -> dict:
    """读清单 yaml。tasks 归一化成 {int task_id: split};原始形态记在 _tasks_form。"""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["_path"] = path

    raw = data.get("tasks")
    if isinstance(raw, dict):
        data["tasks"] = {int(k): str(v) for k, v in raw.items()}
        data["_tasks_form"] = "map"
    else:
        # 列表(含 None / 空列表):split 恒为本轨唯一的那个,留 None 由 builder 填
        data["tasks"] = {int(t): None for t in (raw or [])}
        data["_tasks_form"] = "list"
    return data


def load_classes(path=CLASSES_PATH) -> dict:
    """{组名: [类名,...]} —— 两轨唯一的共享配置(class id 映射必须一致)。"""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not data.get("groups"):
        raise SystemExit(f"{path} 缺少 groups")
    return data["groups"]


# ---- yaml 字段访问器(避免各脚本各写一遍 .get 链) ----

def _resolve(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def out_root(m) -> Path:
    return _resolve((m.get("output") or {}).get("root", "datasets"))


def export_root(m) -> Path:
    return _resolve((m.get("source") or {}).get("export_root", "raw/exports"))


def video_dir(m) -> Path:
    return _resolve((m.get("source") or {}).get("video_dir", "raw/videos"))


def projects(m) -> list:
    return list((m.get("source") or {}).get("projects") or [])


def sampling(m) -> dict:
    return dict(m.get("sampling") or {})


def completed_path(m) -> Path:
    """增量完成清单(build 写的**机器状态**,与人工维护的清单分开)。

    文件名从清单文件名派生(train.yaml -> completed_train.json),不进 yaml ——
    它是固定的命名约定,不是可调项。
    """
    p = Path(m["_path"])
    return p.parent / f"completed_{p.stem}.json"


def tracking_path(m) -> Path:
    """build 生成的追踪表(train.yaml -> tracking_train.md)。"""
    p = Path(m["_path"])
    return p.parent / f"tracking_{p.stem}.md"


def load_tasks(m):
    """按 source.projects 读取导出,返回 (tasks, 导出文件名列表)。"""
    return labelstudio.load_projects(export_root(m), projects(m))


# ---------------------------------------------------------------------------
# 解析:清单 × 导出
# ---------------------------------------------------------------------------

def resolve(m, tasks):
    """用清单过滤导出的 task 列表。

    返回 (registered, unregistered):
      registered   = [(tid, task, video_name, split), ...]  —— 在册且导出里有
      unregistered = [(tid, video_name), ...]               —— 导出里有但未在册

    在册但导出里没有的 task 由调用方通过 missing() 单独查(通常是导出没更新)。
    """
    manifest_tasks = m.get("tasks") or {}
    registered, unregistered = [], []
    for task in tasks:
        tid = int(task["id"])
        name = labelstudio.task_video_name(task)
        if tid in manifest_tasks:
            registered.append((tid, task, name, manifest_tasks[tid]))
        else:
            unregistered.append((tid, name))
    return registered, unregistered


def missing(m, tasks) -> list:
    """在册但导出里查无此 task 的 id(导出过期或 task 被删)。"""
    seen = {int(t["id"]) for t in tasks}
    return sorted(tid for tid in (m.get("tasks") or {}) if tid not in seen)


# ---------------------------------------------------------------------------
# 回填:给未在册 task 确定性分配 split
# ---------------------------------------------------------------------------

def assign(m, tids, splits) -> list:
    """给 tids 算 split,返回 [(tid, split), ...]。纯函数,不写盘。

    splits 是**本轨**的 split 元组(轨的定义,由调用方给);比例与盐来自 yaml 的
    assign 段(那才是可调的)。splits 的第一项是余额桶,其余各项按 assign.ratios
    的比例累积切分 hash(seed:tid) 落到的 0..99 桶。
    """
    sp = list(splits)
    if not sp:
        raise SystemExit("splits 为空,无法分配")
    cfg = m.get("assign") or {}
    seed = cfg.get("seed", 0)
    ratios = cfg.get("ratios") or {}

    # 累积切点:[(cutoff, split_name), ...],按 splits[1:] 顺序
    cutoffs, acc = [], 0
    for name in sp[1:]:
        acc += round(float(ratios.get(name, 0)) * 100)
        cutoffs.append((acc, name))

    out = []
    for tid in tids:
        bucket = splitmod.deterministic_bucket(str(tid), seed)
        chosen = sp[0]
        for cutoff, name in cutoffs:
            if bucket < cutoff:
                chosen = name
                break
        out.append((int(tid), chosen))
    return out


# ---------------------------------------------------------------------------
# 写回:文本级追加(保住逐条注释)
# ---------------------------------------------------------------------------

def append_tasks(m, additions) -> int:
    """把新条目**追加**到 tasks 块末尾,其余行字节不动。

    刻意不用 yaml.dump 重写整个文件:清单里的逐条注释(如"原 test,回收"、
    "稀有: air_gun")是人工留下的判断依据,重写会全部抹掉。而 assign 的语义本就是
    "只加不改已有",所以文本级追加既够用又无损。

    additions: [(tid, split), ...];list 形态的清单忽略 split(它恒为 splits[0])。
    返回实际追加条数。
    """
    path = Path(m["_path"])
    existing = m.get("tasks") or {}
    new = [(int(t), s) for t, s in additions if int(t) not in existing]
    if not new:
        return 0

    lines = path.read_text(encoding="utf-8").splitlines()

    # 定位 tasks: 所在行(顶格)
    idx = next((i for i, l in enumerate(lines) if l.startswith("tasks:")), None)
    if idx is None:
        raise SystemExit(f"{path} 找不到顶格的 tasks: 块")

    is_list = m.get("_tasks_form") == "list"
    fmt = (lambda t, s: f"  - {t}") if is_list else (lambda t, s: f"  {t}: {s}")

    # 空的行内形态(tasks: [] / tasks: {})要先展开成块形态
    head = lines[idx].split("#", 1)[0].strip()
    if head not in ("tasks:",):
        lines[idx] = "tasks:"

    # 块的结尾:下一个顶格的非空非注释行
    end = len(lines)
    for i in range(idx + 1, len(lines)):
        s = lines[i]
        if s.strip() and not s.startswith((" ", "\t", "#")):
            end = i
            break

    # 回退掉块尾的空行/注释行,保证追加紧贴最后一个条目
    while end > idx + 1 and not lines[end - 1].strip():
        end -= 1

    lines[end:end] = [fmt(t, s) for t, s in sorted(new)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(new)


# ---------------------------------------------------------------------------
# 断言
# ---------------------------------------------------------------------------

def assert_disjoint(train_m=None, test_m=None) -> None:
    """两轨清单的 task id 必须零交集(源级隔离)。

    源头就是两个独立 LS 项目、两份清单,本就不该重叠 —— 这是个便宜的断言,
    不是重型泄漏检测。
    """
    train_m = train_m if train_m is not None else load(TRAIN_MANIFEST)
    test_m = test_m if test_m is not None else load(TEST_MANIFEST)
    overlap = sorted(set(train_m.get("tasks") or {}) & set(test_m.get("tasks") or {}))
    if overlap:
        raise SystemExit(
            "源级隔离被破坏:以下 task 同时在训练轨与 benchmark 轨清单中 —— "
            + ", ".join(f"task#{t}" for t in overlap)
        )


def assert_not_frozen(m, changed_tids=()) -> None:
    """frozen_at 非空时,只许追加新 task,不许改动已有条目。"""
    frozen = m.get("frozen_at")
    if not frozen:
        return
    existing = set(m.get("tasks") or {})
    touched = sorted(set(int(t) for t in changed_tids) & existing)
    if touched:
        raise SystemExit(
            f"{m.get('_path')} 已于 {frozen} 冻结(version={m.get('version')}),"
            "只增不改。被改动的: " + ", ".join(f"task#{t}" for t in touched)
        )
