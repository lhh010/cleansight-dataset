#!/usr/bin/env python3
"""生成稀缺类补采/补标清单：对比 已标注任务 vs 已构建任务，定位待构建与待标注任务。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXP = ROOT / "raw" / "exports" / "project-10-at-2026-07-12-02-49-086781a3.json"
VID_DIR = ROOT / "raw" / "videos"
COMPLETED = ROOT / "completed_tasks.json"
SPLITS = ROOT / "splits.yaml"

DET = {0:"hand",1:"scope_control_body",2:"scope_mid_section",3:"scope_distal_end",
       4:"syringe",5:"air_gun",6:"short_brush",7:"brush_tip_out"}
ACT = {0:"idle",1:"air_injection",2:"flush",3:"long_brush_insert",4:"long_brush_withdraw",5:"short_brush_cleaning"}
SCARCE = {"air_gun","brush_tip_out","short_brush","air_injection"}

exp = json.load(open(EXP, encoding="utf-8"))
built = set(json.load(open(COMPLETED, encoding="utf-8")).keys())

# 读 splits.yaml 的人工分配
splits = {}
for line in SPLITS.read_text(encoding="utf-8").splitlines():
    line = line.split("#")[0].strip()
    if ":" in line and not line.endswith(":"):
        k, v = line.split(":", 1)
        k = k.strip()
        if "-clip_" in k:
            splits[k.strip()] = v.strip()

def parse_task(t):
    stem = Path(t["data"].get("video","")).stem
    acts, dets, nframes = set(), set(), None
    annotated = False
    for ann in t.get("annotations", []):
        if ann.get("result"):
            annotated = True
        for r in ann.get("result", []):
            labs = r.get("value",{}).get("labels") or r.get("value",{}).get("timelinelabels") or []
            if r.get("type")=="videorectangle":
                nframes = r.get("value",{}).get("framesCount", nframes)
            for l in labs:
                if l in ACT.values(): acts.add(l)
                elif l in DET.values(): dets.add(l)
    return {"tid":str(t["id"]),"stem":stem,"annotated":annotated,"acts":acts,"dets":dets,
            "nframes":nframes,"disk":VID_DIR.exists() and (VID_DIR/f"{stem}.mp4").exists(),
            "split":splits.get(stem,"（未分配）")}

rows = [parse_task(t) for t in sorted(exp, key=lambda x:x["id"])]

def fmt(r):
    scar = SCARCE & (r["acts"]|r["dets"])
    sm = ("★"+",".join(sorted(scar))) if scar else ""
    return (f"task#{r['tid']:<3} {r['stem'][:8]}  split={r['split']:<6} "
            f"disk={'Y' if r['disk'] else 'N'}  frames={r['nframes']}  "
            f"acts=[{','.join(sorted(r['acts']))}] scarce {sm}")

print("###### A. 已标注但【未构建进数据集】（零标注成本，最高 ROI）######")
for r in rows:
    if r["annotated"] and r["tid"] not in built:
        print(" ", fmt(r))

print("\n###### B. 未标注（需先在 Label Studio 标注）######")
for r in rows:
    if not r["annotated"]:
        print(" ", fmt(r))

print("\n###### C. 已标注且视频【不在磁盘】（需先从 Label Studio 重新下载视频）######")
for r in rows:
    if r["annotated"] and not r["disk"]:
        print(" ", fmt(r))

print("\n###### D. 已构建（基线，供参考）######")
for r in rows:
    if r["tid"] in built:
        print(" ", fmt(r))

# 稀缺类 split 覆盖现状（仅已构建任务）
print("\n###### 稀缺类在【已构建】任务里的 split 覆盖 ######")
built_rows = [r for r in rows if r["tid"] in built]
for cls in sorted(SCARCE):
    cov = {}
    for r in built_rows:
        if cls in r["acts"] or cls in r["dets"]:
            cov.setdefault(r["split"], []).append(f"#{r['tid']}")
    missing = [s for s in ("train","val","test") if s not in cov]
    print(f"  {cls:<22} " + "  ".join(f"{s}:{cov.get(s,[])}" for s in ("train","val","test"))
          + (f"   ⚠缺 {missing}" if missing else "   ✓全覆盖"))
