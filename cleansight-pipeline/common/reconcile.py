#!/usr/bin/env python3
"""
对账 / 增量前置:把三方来源对齐,告诉你每次该做什么。

三方(原先是四方:导出/磁盘/splits/白名单。yolo 两轨改造后,"已质检"与"已定 split"
合并成了清单里的一条登记记录,所以四方变三方):
  - LS 导出 JSON(raw/exports/<项目>/ 各取最新)—— 标注侧"应该有"的 task
  - raw/videos/ ——                              实际下载到磁盘的视频
  - yolo/{train,test}.yaml 的 tasks ——           已质检 + 已定归属的在册 task

分类:
  未下载   导出引用了但磁盘没有            -> 跑 pull.py
  未登记   已下载但不在清单                -> 人工质检后登记进对应清单(train 轨可 --assign)
  遗失     在册但视频不在磁盘              -> 重下,或从清单删(不自动删)
  导出缺失 在册但导出里查无此 task         -> 导出过期,或 task 已在 LS 删除
  孤儿     磁盘有但任何导出都没引用        -> 陈旧下载,可清理

注意:本脚本目前只服务 yolo 两轨(actionmixed 是段级切分,没有 per-video 归属问题)。
校验/对账的整体口径待重新明确,这里维持既有分类不扩展。

用法(在 cleansight-pipeline/ 下执行):
  python3 common/reconcile.py            # 只读,打印状态
  python3 common/reconcile.py --assign   # 给训练轨"未登记"的 task 确定性回填并写回 train.yaml
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from utils import labelstudio                      # noqa: E402
from yolo import manifest                          # noqa: E402

# 轨定义:(展示名, 清单路径, 本轨产出的 split, 是否允许 --assign 回填)
TRACKS = [
    ("训练轨", manifest.TRAIN_MANIFEST, ("train", "val"), True),
    ("benchmark", manifest.TEST_MANIFEST, ("test",), False),
]


def gather():
    groups = manifest.load_classes()
    label2group = labelstudio.build_label_index(groups)
    on_disk = {f.name for f in labelstudio.VIDEO_DIR.glob("*.mp4")} \
        if labelstudio.VIDEO_DIR.is_dir() else set()

    tracks, referenced = [], set()
    for label, path, splits, can_assign in TRACKS:
        m = manifest.load(path)
        rows, exports = [], []
        try:
            tasks, exports = manifest.load_tasks(m)
        except SystemExit as e:
            tasks = []
            print(f"[{label}] 读取导出失败: {e}")
        mtasks = m.get("tasks") or {}
        for t in tasks:
            tid = int(t["id"])
            name = labelstudio.task_video_name(t)
            referenced.add(name)
            registered = tid in mtasks
            rows.append({
                "tid": tid, "name": name,
                "on_disk": name in on_disk,
                # 列表形态的清单不带 split(benchmark 恒为 test),用本轨唯一的那个显示
                "split": (mtasks.get(tid) or splits[0]) if registered else None,
                "registered": registered,
                "has_det": bool(labelstudio.collect_tracks(t, label2group)),
            })
        tracks.append({
            "label": label, "manifest": m, "path": path, "splits": splits,
            "can_assign": can_assign, "rows": rows, "exports": exports,
            "absent": manifest.missing(m, tasks),
        })
    orphans = sorted(on_disk - referenced)
    return tracks, orphans


def print_track(tr):
    print(f"\n=== {tr['label']}  ({tr['path'].name}"
          f"{'  导出: ' + ', '.join(tr['exports']) if tr['exports'] else ''}) ===")
    if not tr["rows"]:
        print("  导出里没有 task。")
    else:
        print(f"  {'task':<8} {'视频':<50} {'磁盘':<5} {'检测':<5} {'登记/split'}")
        print("  " + "-" * 85)
        for r in sorted(tr["rows"], key=lambda x: x["tid"]):
            yn = lambda b: "[Y]" if b else "[ ]"   # noqa: E731
            reg = r["split"] if r["registered"] else "--"
            print(f"  {r['tid']:<8} {r['name'][:50]:<50} "
                  f"{yn(r['on_disk']):<5} {yn(r['has_det']):<5} {reg}")

    todo = {
        "未登记": [r for r in tr["rows"] if not r["registered"]],
        "遗失/未下载": [r for r in tr["rows"] if r["registered"] and not r["on_disk"]],
    }
    hints = {
        "未登记": ("人工质检后登记进 " + tr["path"].name
                 + (",或跑 --assign 确定性回填" if tr["can_assign"]
                    else "(benchmark 入册是人工策展决策,不自动回填)")),
        "遗失/未下载": "跑 common/pull.py 补下;确已作废则从清单删(不自动删)",
    }
    for cat, items in todo.items():
        if items:
            print(f"\n  [{cat}] {len(items)} 个 —— {hints[cat]}")
            for r in items:
                print(f"      task#{r['tid']}  {r['name']}")
    if tr["absent"]:
        print(f"\n  [导出缺失] {len(tr['absent'])} 个 —— 导出过期,或 task 已在 LS 删除")
        print("      " + ", ".join(f"task#{t}" for t in tr["absent"]))
    if not any(todo.values()) and not tr["absent"]:
        print("\n  一切就绪,无待办。")


def main():
    do_assign = "--assign" in sys.argv[1:]
    print(f"视频目录: {labelstudio.VIDEO_DIR}")
    manifest.assert_disjoint()

    tracks, orphans = gather()
    for tr in tracks:
        print_track(tr)

    if orphans:
        print(f"\n=== 孤儿 {len(orphans)} 个 —— 磁盘有但任何导出都没引用,可清理 ===")
        for n in orphans:
            print(f"    {n}")

    if do_assign:
        for tr in tracks:
            if not tr["can_assign"]:
                continue
            pending = [r["tid"] for r in tr["rows"] if not r["registered"]]
            if not pending:
                print(f"\n=== --assign [{tr['label']}]:没有需要回填的 task ===")
                continue
            added = manifest.assign(tr["manifest"], pending, tr["splits"])
            n = manifest.append_tasks(tr["manifest"], added)
            print(f"\n=== --assign [{tr['label']}] 回填 {n} 个"
                  f"(已写回 {tr['path'].name})===")
            for tid, s in added:
                print(f"    task#{tid} -> {s}")
            print("请 review 并提交该 yaml 的改动。")


if __name__ == "__main__":
    main()
