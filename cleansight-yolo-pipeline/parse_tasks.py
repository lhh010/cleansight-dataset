#!/usr/bin/env python3
"""解析 Label Studio 导出，建立 task -> 视频 -> 动作/检测类 映射，定位稀缺类来源。"""
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
EXP = ROOT / "raw" / "exports" / "project-10-at-2026-07-12-02-49-086781a3.json"
VID_DIR = ROOT / "raw" / "videos"

DET_NAMES = {0: "hand", 1: "scope_control_body", 2: "scope_mid_section",
             3: "scope_distal_end", 4: "syringe", 5: "air_gun",
             6: "short_brush", 7: "brush_tip_out"}
ACT_NAMES = {0: "idle", 1: "air_injection", 2: "flush", 3: "long_brush_insert",
             4: "long_brush_withdraw", 5: "short_brush_cleaning"}
SCARCE_DET = {"air_gun", "brush_tip_out", "short_brush"}
SCARCE_ACT = {"air_injection"}

exp = json.load(open(EXP, encoding="utf-8"))

def stem_of(video_path):
    return Path(video_path).name.rsplit(".", 1)[0]

rows = []
for t in exp:
    tid = t["id"]
    video = t["data"].get("video", "")
    stem = stem_of(video)
    acts, dets = set(), set()
    nframes = None
    annotated = False
    for ann in t.get("annotations", []):
        res = ann.get("result", [])
        if res:
            annotated = True
        for r in res:
            typ = r.get("type")
            labels = r.get("value", {}).get("labels") or r.get("value", {}).get("timelinelabels")
            if typ == "videorectangle":
                nframes = r.get("value", {}).get("framesCount", nframes)
            if labels:
                for lab in labels:
                    if lab in ACT_NAMES.values():
                        acts.add(lab)
                    elif lab in DET_NAMES.values():
                        dets.add(lab)
    exists = (VID_DIR / f"{stem}.mp4").exists()
    rows.append({
        "tid": tid, "stem": stem, "annotated": annotated,
        "acts": acts, "dets": dets, "nframes": nframes,
        "video_on_disk": exists,
    })

rows.sort(key=lambda r: r["tid"])

print(f"{'task':<6}{'video_stem':<48}{'annot':<7}{'disk':<6}{'actions / scarce-dets'}")
print("-" * 110)
for r in rows:
    scar = SCARCE_DET & r["dets"]
    scar_a = SCARCE_ACT & r["acts"]
    mark = ("★稀缺:" + ",".join(sorted(scar | scar_a))) if (scar or scar_a) else ""
    print(f"{r['tid']:<6}{r['stem'][:46]:<48}{str(r['annotated']):<7}{str(r['video_on_disk']):<6}"
          f"{','.join(sorted(r['acts'])) or '-'}  [{','.join(sorted(r['dets'])) or '-'}] {mark}")

# 未标注任务
print("\n=== 未标注任务（annotation 结果为空）===")
for r in rows:
    if not r["annotated"]:
        print(f"  task#{r['tid']}  {r['stem']}  disk={r['video_on_disk']}")

# 磁盘上有但导出里没有 task 的视频
exp_stems = {r["stem"] for r in rows}
disk_stems = {p.stem for p in VID_DIR.glob("*.mp4")}
print("\n=== 磁盘有视频但 Label Studio 里无对应 task（完全没建任务）===")
for s in sorted(disk_stems - exp_stems):
    print(f"  {s}.mp4")

# 稀缺类来源汇总
print("\n=== 稀缺检测类来源（已标注任务）===")
for cls in sorted(SCARCE_DET):
    src = [f"task#{r['tid']}({r['stem'][:8]})" for r in rows if r["annotated"] and cls in r["dets"]]
    print(f"  {cls}: {src or '（无）'}")
print("\n=== 稀缺动作类来源（已标注任务）===")
for cls in sorted(SCARCE_ACT):
    src = [f"task#{r['tid']}({r['stem'][:8]})" for r in rows if r["annotated"] and cls in r["acts"]]
    print(f"  {cls}: {src or '（无）'}")
