#!/usr/bin/env python3
"""
稀缺类补采/补标清单:对比"已标注 vs 已构建",定位待构建与待标注的 task。

数据源全部走训练轨清单(yolo/train.yaml)——导出项目、在册 task 与 split 都从那里读,
不再硬编码某一份导出文件名。检测类名取自 yolo/classes.yaml。

用法(在 cleansight-pipeline/ 下执行):
    python3 common/scarce_checklist.py
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from utils import labelstudio          # noqa: E402
from yolo import manifest              # noqa: E402

# 动作类只用于给行加上下文(动作数据集是 actionmixed 的事,这里不做判断)
ACT_NAMES = {"idle", "air_injection", "flush", "long_brush_insert",
             "long_brush_withdraw", "short_brush_cleaning"}
# 关注的稀缺项(依 archive/DATASET_BALANCE_REVIEW.md 的实例数偏低类)
SCARCE = {"air_gun", "brush_tip_out", "short_brush", "air_injection"}


def main():
    m = manifest.load(manifest.TRAIN_MANIFEST)
    groups = manifest.load_classes()
    det_names = {lab for labs in groups.values() for lab in labs}
    video_dir = manifest.video_dir(m)

    tasks, exports = manifest.load_tasks(m)
    completed_path = manifest.completed_path(m)
    built = set(json.loads(completed_path.read_text(encoding="utf-8"))) \
        if completed_path.exists() else set()
    registered = m.get("tasks") or {}

    print(f"导出: {', '.join(exports)}   在册 {len(registered)} / 已构建 {len(built)}")

    rows = []
    for t in sorted(tasks, key=lambda x: x["id"]):
        tid = int(t["id"])
        name = labelstudio.task_video_name(t)
        acts, dets = set(), set()
        annotated = False
        nframes = None
        for ann in t.get("annotations", []):
            if ann.get("result"):
                annotated = True
            for r in ann.get("result", []):
                if r.get("type") == "videorectangle":
                    nframes = r.get("value", {}).get("framesCount", nframes)
                v = r.get("value", {})
                for lab in (v.get("labels") or v.get("timelinelabels") or []):
                    if lab in ACT_NAMES:
                        acts.add(lab)
                    elif lab in det_names:
                        dets.add(lab)
        rows.append({
            "tid": tid, "name": name, "annotated": annotated,
            "acts": acts, "dets": dets, "nframes": nframes,
            "disk": (video_dir / name).exists() if name else False,
            "split": registered.get(tid, "（未登记）"),
            "built": str(tid) in built,
        })

    def fmt(r):
        scar = SCARCE & (r["acts"] | r["dets"])
        mark = ("★" + ",".join(sorted(scar))) if scar else ""
        return (f"task#{r['tid']:<5} {r['name'][:24]:<26} split={str(r['split']):<12} "
                f"disk={'Y' if r['disk'] else 'N'}  frames={r['nframes']}  "
                f"acts=[{','.join(sorted(r['acts']))}] {mark}")

    print("\n###### A. 已标注但【未构建进数据集】(零标注成本,最高 ROI) ######")
    for r in rows:
        if r["annotated"] and not r["built"]:
            print("  " + fmt(r))

    print("\n###### B. 未标注(需先在 Label Studio 标注) ######")
    for r in rows:
        if not r["annotated"]:
            print("  " + fmt(r))

    print("\n###### C. 已标注但视频【不在磁盘】(需先跑 common/pull.py) ######")
    for r in rows:
        if r["annotated"] and not r["disk"]:
            print("  " + fmt(r))

    print("\n###### D. 已构建(基线,供参考) ######")
    for r in rows:
        if r["built"]:
            print("  " + fmt(r))

    print("\n###### 稀缺类在【已构建】task 里的 split 覆盖 ######")
    splits_seen = sorted({str(r["split"]) for r in rows if r["built"]})
    for cls in sorted(SCARCE):
        cov = {}
        for r in rows:
            if r["built"] and (cls in r["acts"] or cls in r["dets"]):
                cov.setdefault(str(r["split"]), []).append(f"#{r['tid']}")
        missing = [s for s in splits_seen if s not in cov]
        print(f"  {cls:<22} " + "  ".join(f"{s}:{cov.get(s, [])}" for s in splits_seen)
              + (f"   ⚠缺 {missing}" if missing else "   ✓全覆盖"))


if __name__ == "__main__":
    main()
