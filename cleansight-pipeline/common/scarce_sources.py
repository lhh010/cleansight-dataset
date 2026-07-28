#!/usr/bin/env python3
"""
解析 LS 导出,建立 task -> 视频 -> 动作/检测类 映射,定位稀缺类的来源片段。

与 scarce_checklist.py 的分工:那个按"已标注 / 已构建 / split 覆盖"给行动清单,
这个只给**来源汇总**(哪几条片子有稀缺类),用于选片补采。
"孤儿视频"的对账已归 common/reconcile.py,这里不再重复。

数据源走训练轨清单(yolo/train.yaml)的 projects,检测类名取自 yolo/classes.yaml。

用法(在 cleansight-pipeline/ 下执行):
    python3 common/scarce_sources.py
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from utils import labelstudio          # noqa: E402
from yolo import manifest              # noqa: E402

ACT_NAMES = {"idle", "air_injection", "flush", "long_brush_insert",
             "long_brush_withdraw", "short_brush_cleaning"}
SCARCE_DET = {"air_gun", "brush_tip_out", "short_brush"}
SCARCE_ACT = {"air_injection"}


def main():
    m = manifest.load(manifest.TRAIN_MANIFEST)
    groups = manifest.load_classes()
    det_names = {lab for labs in groups.values() for lab in labs}
    video_dir = manifest.video_dir(m)

    tasks, exports = manifest.load_tasks(m)
    print(f"导出: {', '.join(exports)}")

    rows = []
    for t in sorted(tasks, key=lambda x: x["id"]):
        name = labelstudio.task_video_name(t)
        acts, dets = set(), set()
        annotated, nframes = False, None
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
        rows.append({"tid": int(t["id"]), "stem": pathlib.Path(name).stem,
                     "annotated": annotated, "acts": acts, "dets": dets,
                     "nframes": nframes,
                     "on_disk": (video_dir / name).exists() if name else False})

    print(f"\n{'task':<6}{'video_stem':<48}{'annot':<7}{'disk':<6}{'actions / dets'}")
    print("-" * 110)
    for r in rows:
        scar = (SCARCE_DET & r["dets"]) | (SCARCE_ACT & r["acts"])
        mark = ("★稀缺:" + ",".join(sorted(scar))) if scar else ""
        print(f"{r['tid']:<6}{r['stem'][:46]:<48}{str(r['annotated']):<7}"
              f"{str(r['on_disk']):<6}{','.join(sorted(r['acts'])) or '-'}  "
              f"[{','.join(sorted(r['dets'])) or '-'}] {mark}")

    print("\n=== 未标注 task(annotation 结果为空)===")
    for r in rows:
        if not r["annotated"]:
            print(f"  task#{r['tid']}  {r['stem']}  disk={r['on_disk']}")

    print("\n=== 稀缺检测类来源(已标注 task)===")
    for cls in sorted(SCARCE_DET):
        src = [f"task#{r['tid']}({r['stem'][:8]})" for r in rows
               if r["annotated"] and cls in r["dets"]]
        print(f"  {cls}: {src or '(无)'}")

    print("\n=== 稀缺动作类来源(已标注 task)===")
    for cls in sorted(SCARCE_ACT):
        src = [f"task#{r['tid']}({r['stem'][:8]})" for r in rows
               if r["annotated"] and cls in r["acts"]]
        print(f"  {cls}: {src or '(无)'}")


if __name__ == "__main__":
    main()
