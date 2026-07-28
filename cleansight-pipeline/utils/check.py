#!/usr/bin/env python3
"""
数据集校验核心逻辑 —— 纯数据级，不依赖训练权重 / GPU。

供 check.py (CLI) 和 upload 脚本导入使用。

校验项:
  1. 结构完整性 — data.yaml、images/labels 一一对应、0 字节文件
  2. 标注合法性 — class_id 范围、归一化坐标、列数格式
  3. Split 合理性 — 非空 split、比例偏差、每类覆盖
  4. 图像完整性 — PIL 解码抽查
  5. 时序一致性 — 同一 task 的帧不跨 split

split 名从 data.yaml 现读(数据集自己声明布局),本模块不含 split 字面量。
比例期望与"哪些 split 必须每类有样本"由调用方传入 —— 因为不同轨的判据不同:
训练轨按比例切分、val 每类必须有样本;benchmark 是**策展**的,按比例查它没有意义。

  ⚠️ benchmark(test)的达标口径尚未定稿(覆盖率?每桶最少样本?还是只出报告不判
     PASS/FAIL?),所以这里对 test 只给 warn,不判 FAIL。定下来后再单独设计。
"""

from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml
from PIL import Image

# ---------------------------------------------------------------------------
# 结果容器
# ---------------------------------------------------------------------------

class CheckResult:
    """单次校验的完整结果。"""

    def __init__(self, name: str):
        self.name = name
        self.errors: list[str] = []    # 硬错误 —— 必须修
        self.warnings: list[str] = []  # 软警告 —— 建议关注

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# ===================================================================
# 1. 结构完整性
# ===================================================================

def _splits_from_data_yaml(cfg: dict) -> list:
    """data.yaml 里声明了哪些 split(键值形如 `train: images/train`)。"""
    reserved = {"path", "nc", "names", "download"}
    return [k for k, v in cfg.items() if k not in reserved and isinstance(v, str)]


def _check_structure(dataset_dir: Path, result: CheckResult) -> Optional[dict]:
    """data.yaml 可解析、images/ 与 labels/ 一一对应、无 0 字节文件。"""
    data_yaml = dataset_dir / "data.yaml"
    if not data_yaml.exists():
        result.error(f"缺少 data.yaml: {data_yaml}")
        return None

    try:
        cfg = yaml.safe_load(data_yaml.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        result.error(f"data.yaml 解析失败: {exc}")
        return None

    splits = _splits_from_data_yaml(cfg)
    if not splits:
        result.error("data.yaml 未声明任何 split")
        return None

    nc = cfg.get("nc")
    names = cfg.get("names", [])
    if nc is None:
        result.error("data.yaml 缺少 nc 字段")
        return None
    if not isinstance(names, (list, dict)):
        result.error("data.yaml 缺少 names 字段或格式非法")
        return None

    name_count = len(names) if isinstance(names, list) else len(names)
    if nc != name_count:
        result.error(f"data.yaml: nc={nc} 但 names 包含 {name_count} 个条目，不一致")

    total_images = 0
    empty_label_count = 0

    for split in splits:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.is_dir():
            continue
        if not lbl_dir.is_dir():
            continue

        imgs = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png"))
        lbl_stems = {p.stem for p in lbl_dir.glob("*.txt")}

        for img in imgs:
            total_images += 1
            if img.stat().st_size == 0:
                result.error(f"0 字节图像: {img.relative_to(dataset_dir)}")
            if img.stem not in lbl_stems:
                result.error(f"图像无对应标注: {img.relative_to(dataset_dir)}")

        for lbl in sorted(lbl_dir.glob("*.txt")):
            if lbl.stat().st_size == 0:
                empty_label_count += 1
            has_img = (
                (img_dir / f"{lbl.stem}.jpg").exists()
                or (img_dir / f"{lbl.stem}.png").exists()
            )
            if not has_img:
                result.error(f"标注无对应图像: {lbl.relative_to(dataset_dir)}")

        if len(imgs) == 0:
            result.warn(f"images/{split}/ 为空")

    if empty_label_count > 0:
        result.warn(f"{empty_label_count} 个标注文件为空（空帧负样本，benchmark 侧属正常）")
    if total_images == 0:
        result.error("数据集没有任何图像文件")

    return {
        "nc": nc,
        "names": list(names.values()) if isinstance(names, dict) else list(names),
        "total_images": total_images,
        "splits": splits,
    }


# ===================================================================
# 2. 标注合法性
# ===================================================================

def _check_labels(dataset_dir: Path, meta: Optional[dict], result: CheckResult) -> None:
    """逐行检查 class_id 范围、归一化坐标范围、列数格式。"""
    if meta is None:
        return

    nc = meta["nc"]
    bad_format = 0
    bad_cid: dict[int, int] = defaultdict(int)
    oob = 0
    zero_wh = 0

    for split in meta["splits"]:
        lbl_dir = dataset_dir / "labels" / split
        if not lbl_dir.is_dir():
            continue
        for txt in sorted(lbl_dir.glob("*.txt")):
            rel = str(txt.relative_to(dataset_dir))
            for li, line in enumerate(txt.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()

                if len(parts) != 5:
                    bad_format += 1
                    if bad_format <= 3:
                        result.error(
                            f"列数异常（期望 5，实际 {len(parts)}）: {rel} 行 {li}: {line[:60]}"
                        )
                    continue

                try:
                    cid = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:5])
                except ValueError:
                    bad_format += 1
                    if bad_format <= 3:
                        result.error(f"数值解析失败: {rel} 行 {li}: {line[:60]}")
                    continue

                if cid < 0 or cid >= nc:
                    bad_cid[cid] += 1

                for vn, v in [("cx", cx), ("cy", cy), ("w", w), ("h", h)]:
                    if v < -0.001 or v > 1.001:
                        oob += 1
                        if oob <= 3:
                            result.error(f"坐标越界 ({vn}={v:.4f}): {rel} 行 {li}")
                        break

                if w <= 0 or h <= 0:
                    zero_wh += 1
                    if zero_wh <= 3:
                        result.error(f"宽高非法 (w={w}, h={h}): {rel} 行 {li}")

    for cid, cnt in sorted(bad_cid.items()):
        result.error(f"非法 class_id={cid}（有效范围 0~{nc - 1}）: 出现 {cnt} 次")
    if bad_format > 3:
        result.error(f"……还有 {bad_format - 3} 处格式错误（已截断显示）")
    if oob > 3:
        result.error(f"……还有 {oob - 3} 处坐标越界（已截断显示）")
    if zero_wh > 3:
        result.error(f"……还有 {zero_wh - 3} 处宽高非法（已截断显示）")


# ===================================================================
# 3. Split 合理性
# ===================================================================

def _check_splits(
    dataset_dir: Path, meta: Optional[dict], result: CheckResult,
    ratio_expectations: Optional[dict], required_splits,
) -> None:
    """检查 split 比例偏差、每类覆盖。

    ratio_expectations: {split: 期望占比},**分母只算这些 split** —— 策展的
        benchmark 不该参与比例约束,所以它不出现在这个字典里。None = 跳过比例检查。
    required_splits: 这些 split 里某类无样本判 error(如训练轨的 val:该类无法评估);
        其余 split 只 warn。
    """
    if meta is None:
        return

    nc = meta["nc"]
    names = meta["names"]
    splits = meta["splits"]

    split_frames: dict[str, int] = {}
    cls_split_frames: dict[str, dict[int, int]] = {
        split: defaultdict(int) for split in splits
    }

    for split in splits:
        lbl_dir = dataset_dir / "labels" / split
        if not lbl_dir.is_dir():
            split_frames[split] = 0
            continue
        txts = sorted(lbl_dir.glob("*.txt"))
        split_frames[split] = len(txts)

        for txt in txts:
            seen: set[int] = set()
            for line in txt.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    cid = int(line.split()[0])
                except (ValueError, IndexError):
                    continue
                if 0 <= cid < nc:
                    seen.add(cid)
            for cid in seen:
                cls_split_frames[split][cid] += 1

    if sum(split_frames.values()) == 0:
        return

    # 比例检查:分母只算参与比例切分的 split(策展的 benchmark 不在其中)
    if ratio_expectations:
        base = sum(split_frames.get(s, 0) for s in ratio_expectations)
        if base:
            for split, exp in ratio_expectations.items():
                actual = split_frames.get(split, 0) / base
                dev = abs(actual - exp)
                if dev > 0.15:
                    result.warn(
                        f"images/{split} 在 {'+'.join(ratio_expectations)} 中占比 "
                        f"{actual:.1%}，与预期 {exp:.1%} 偏差 {dev:.1%}"
                        f"（样本少时常见，增多后应收敛）"
                    )

    required = set(required_splits or ())
    for cid in range(nc):
        name = names[cid] if cid < len(names) else f"class_{cid}"
        per = {s: cls_split_frames[s].get(cid, 0) for s in splits}
        if sum(per.values()) == 0:
            result.warn(f"类别 '{name}' (id={cid}) 在所有 split 中均无样本")
            continue
        for s in splits:
            if per[s] > 0:
                continue
            elsewhere = sum(v for k, v in per.items() if k != s)
            if s in required:
                result.error(f"类别 '{name}' (id={cid}) 在 {s} 无样本"
                             f"（其余 split 共 {elsewhere} 帧）—— 该类无法评估")
            else:
                result.warn(f"类别 '{name}' (id={cid}) 在 {s} 无样本 —— 覆盖不足")


# ===================================================================
# 4. 图像完整性
# ===================================================================

def _check_images(dataset_dir: Path, result: CheckResult, splits) -> None:
    """等距抽样检查 jpg/png 可被 PIL 解码。确定性的，不依赖随机。"""
    all_imgs: list[Path] = []
    for split in splits:
        img_dir = dataset_dir / "images" / split
        if img_dir.is_dir():
            all_imgs.extend(sorted(img_dir.glob("*.jpg")))
            all_imgs.extend(sorted(img_dir.glob("*.png")))

    if not all_imgs:
        return

    n_total = len(all_imgs)
    n_check = max(min(n_total, 200), min(n_total, 10))
    step = max(1, n_total // n_check) if n_check > 0 else 1
    sample = all_imgs[::step][:n_check]

    corrupted = 0
    for img in sample:
        try:
            with Image.open(img) as im:
                im.verify()
        except Exception as exc:
            corrupted += 1
            if corrupted <= 5:
                result.error(f"图像损坏/无法解码: {img.relative_to(dataset_dir)} — {exc}")

    if corrupted > 5:
        result.error(f"……还有 {corrupted - 5} 张损坏图像（已截断显示）")


# ===================================================================
# 5. 时序一致性（同视频帧不跨 split）
# ===================================================================

def _check_temporal_consistency(dataset_dir: Path, result: CheckResult, splits) -> None:
    """同一 task 的帧不得跨 split（时间相邻泄漏）。

    帧名 `t{task_id}_{frame:06d}[_变体]`，首段即 task 身份。LS task id 全局唯一，
    所以这一条同时覆盖了训练轨与 benchmark 轨之间的源级隔离。
    """
    task_split: dict[str, str] = {}

    for split in splits:
        img_dir = dataset_dir / "images" / split
        if not img_dir.is_dir():
            continue
        for img in sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png")):
            task_key = img.stem.split("_")[0]

            prev = task_split.get(task_key)
            if prev is not None and prev != split:
                result.error(
                    f"泄漏: task '{task_key}' 的帧同时出现在 "
                    f"'{prev}' 和 '{split}' 中（例: {img.name}）"
                )
            elif prev is None:
                task_split[task_key] = split


# ===================================================================
# 对外入口
# ===================================================================

def check_dataset(
    dataset_dir: Path,
    name: str = "",
    check_images_flag: bool = True,
    ratio_expectations: Optional[dict] = None,
    required_splits=(),
) -> CheckResult:
    """对单个数据集目录执行全部校验。

    Args:
        dataset_dir: 数据集根目录（包含 data.yaml、images/、labels/）
        name: 显示名称（为空则用目录名）
        check_images_flag: False 跳过图像解码抽查
        ratio_expectations: {split: 期望占比}，分母只算这些 split。None 跳过比例检查
        required_splits: 这些 split 里某类无样本判 error，其余只 warn

    split 名从 data.yaml 现读，本函数不预设有哪些 split。

    Returns:
        CheckResult — .passed / .errors / .warnings
    """
    if not name:
        name = dataset_dir.name
    result = CheckResult(name)

    if not dataset_dir.is_dir():
        result.error(f"数据集目录不存在: {dataset_dir}")
        return result

    meta = _check_structure(dataset_dir, result)
    _check_labels(dataset_dir, meta, result)
    _check_splits(dataset_dir, meta, result, ratio_expectations, required_splits)
    splits = meta["splits"] if meta else []
    if check_images_flag:
        _check_images(dataset_dir, result, splits)
    _check_temporal_consistency(dataset_dir, result, splits)

    return result


def print_result(result: CheckResult, verbose: bool = True) -> bool:
    """终端友好的结果输出。返回是否通过。"""
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"  {result.name}: {status}")
    print(f"{'=' * 60}")

    if result.errors:
        print(f"\n  [ERROR] {len(result.errors)} 项必须修复:")
        for e in result.errors:
            print(f"    X {e}")

    if result.warnings and verbose:
        print(f"\n  [WARN]  {len(result.warnings)} 项建议关注:")
        for w in result.warnings:
            print(f"    ! {w}")

    if result.passed and not result.warnings:
        print(f"\n  全部校验通过，可以推送。")

    return result.passed
