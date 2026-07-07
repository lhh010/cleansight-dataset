#!/usr/bin/env python3
"""
LS export JSON + videos -> ActionSequence YOLO dataset (phase-segmented).

Output structure:
  datasets_actionseq/<phase>/
    images/{train,val,test}/*.jpg
    labels/{train,val,test}/*.txt
    data.yaml

Only frames falling within timeline-label phase ranges are included.
All 8 detection classes are shared across phases (unified class-id mapping).
Each LS task's frames stay in the same split (no cross-split leakage).
Rotated bboxes are automatically converted to AABB.

Usage:
    python3 02_build_actionseq.py
    python3 02_build_actionseq.py --auto-assign
"""
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime

import cv2
from PIL import Image

from utils.common import ROOT, load_config, is_whitelisted
from utils import lsexport, split as splitmod, stats

OUT_ROOT = ROOT / "datasets_actionseq"

# Unified 8-class list (same class-id across all phases)
UNIFIED_CLASSES = [
    "hand",
    "scope_control_body",
    "scope_mid_section",
    "scope_distal_end",
    "syringe",
    "air_gun",
    "short_brush",
    "brush_tip_out",
]

# All 5 phases (even if some have no confirmed data yet)
ALL_PHASES = [
    "short_brush_cleaning",
    "long_brush_insert",
    "long_brush_withdraw",
    "air_injection",
    "flush",
]


def prepare_dirs():
    """创建目录结构（不清除已有文件，支持增量构建）。"""
    for phase in ALL_PHASES:
        for s in ("train", "val", "test"):
            (OUT_ROOT / phase / "images" / s).mkdir(parents=True, exist_ok=True)
            (OUT_ROOT / phase / "labels" / s).mkdir(parents=True, exist_ok=True)


def write_data_yamls():
    names = "\n".join(f"  {i}: {lab}" for i, lab in enumerate(UNIFIED_CLASSES))
    for phase in ALL_PHASES:
        (OUT_ROOT / phase / "data.yaml").write_text(
            f"path: {(OUT_ROOT / phase).resolve()}\n"
            f"train: images/train\nval: images/val\ntest: images/test\n"
            f"nc: {len(UNIFIED_CLASSES)}\nnames:\n{names}\n",
            encoding="utf-8",
        )


def _write_frame(frame_array, lines, phase, split, base_name, jpg_q):
    out_img = OUT_ROOT / phase / "images" / split / f"{base_name}.jpg"
    Image.fromarray(frame_array[:, :, ::-1]).save(str(out_img), quality=jpg_q)
    (OUT_ROOT / phase / "labels" / split / f"{base_name}.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def main():
    auto_assign = "--auto-assign" in sys.argv[1:]
    force = "--force" in sys.argv[1:]
    cfg = load_config()
    only = cfg.get("only_videos") or []
    stride = cfg.get("stride", 4)
    jpg_q = cfg.get("jpg_quality", 90)
    dense_enabled = cfg.get("rare_dense_sampling", True)
    rare_threshold = cfg.get("rare_threshold", 200)

    # Build unified class-id mapping
    label2cid = {lab: i for i, lab in enumerate(UNIFIED_CLASSES)}

    json_path = lsexport.latest_export()
    tasks = lsexport.load_tasks(json_path)
    sp = splitmod.load()

    # ---- 增量 ----
    completed_path = ROOT / "completed_tasks_actionseq.json"
    completed = {}
    if completed_path.exists():
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
    if force:
        print("[--force] 全量重建")
        completed = {}
    print(f"Export: {json_path.name}  {len(tasks)} tasks  (completed: {len(completed)})")

    # Compute rare classes
    kf_counts = defaultdict(int)
    for task in tasks:
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        for r in lsexport.iter_results(task, "videorectangle"):
            labs = r.get("value", {}).get("labels", [])
            if not labs or labs[0] not in label2cid:
                continue
            kf_counts[labs[0]] += len(r.get("value", {}).get("sequence", []))
    rare_cids = {label2cid[lab] for lab, cnt in kf_counts.items()
                 if cnt < rare_threshold and lab in label2cid}
    if dense_enabled:
        rare_names = [UNIFIED_CLASSES[c] for c in sorted(rare_cids)]
        print(f"Dense sampling (threshold < {rare_threshold} kf): {rare_names if rare_names else 'none'}")
    else:
        print("Dense sampling disabled")
    print(f"Export: {json_path.name}  {len(tasks)} tasks")

    # ---- Determine splits ----
    pending = []
    unassigned = []
    for ti, task in enumerate(tasks):
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        tracks = lsexport.collect_tracks_unified(task, label2cid)
        if not tracks:
            continue
        tid = task["id"]
        stem = splitmod.stem_of(name)

        # 增量跳过
        task_key = str(tid)
        if not force and task_key in completed:
            prev = completed[task_key]
            if prev.get("export") == json_path.name and prev.get("stride") == stride:
                print(f"  [skip] task#{tid} {name}")
                continue
            else:
                print(f"  [reprocess] task#{tid} {name}")
                for ph in ALL_PHASES:
                    for sp_n in ("train", "val", "test"):
                        stem12 = Path(name).stem[:12]
                        for pat in [f"{ti:02d}_{stem12}_*", f"{ti:02d}_{stem12}_*_dense"]:
                            for f in (OUT_ROOT / ph / "images" / sp_n).glob(f"{pat}.jpg"):
                                f.unlink()
                            for f in (OUT_ROOT / ph / "labels" / sp_n).glob(f"{pat}.txt"):
                                f.unlink()

        s = splitmod.get_split(stem, sp)
        if s is None:
            unassigned.append((stem, ti, task, name))
        else:
            pending.append((ti, task, name, s))

    if unassigned:
        stems = [u[0] for u in unassigned]
        if auto_assign:
            added = splitmod.assign(stems, sp)
            splitmod.save(sp)
            print(f"[auto-assign] backfilled {len(added)} to splits.yaml: "
                  + ", ".join(f"{k}->{v}" for k, v in added))
            for stem, ti, task, name in unassigned:
                pending.append((ti, task, name, splitmod.get_split(stem, sp)))
        else:
            print("ERROR: unassigned videos. Run --auto-assign or 00_status.py --assign")
            for stem, *_ in unassigned:
                print(f"    {stem}")
            sys.exit(2)

    prepare_dirs()

    emitted = 0
    task_stats = []

    for ti, task, name, split in pending:
        tid = task["id"]
        if split not in splitmod.DATASET_SPLITS:
            print(f"  [hold] task#{tid} {name} split={split}, skipping")
            continue
        vpath = lsexport.VIDEO_DIR / name
        if not vpath.exists():
            print(f"  [warn] task#{tid} video missing: {name}")
            continue

        tracks = lsexport.collect_tracks_unified(task, label2cid)
        phase_map = lsexport.build_phase_map(task)
        task_phases = lsexport.collect_task_phases(task)
        det_labels = lsexport.collect_det_labels(task)

        cap = cv2.VideoCapture(str(vpath))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        real_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fc, dur = lsexport.clip_meta(task)
        scale, ls_fps = lsexport.fps_scale(real_fps, fc, dur)
        stem12 = vpath.stem[:12]
        print(f"  task#{tid} [{split}] {name}  real_frames={total}@{real_fps:.1f}  "
              f"LS={fc}@{ls_fps:.1f}  tracks={len(tracks)}  phases={task_phases}")

        phase_frame_counts = defaultdict(int)
        dense_frames_to_sample = set()

        frame_idx = 0
        max_sampled_real = 0
        while True:
            if not cap.grab():
                break
            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue
            ls_frame = frame_idx * scale

            phase = lsexport.get_phase_for_frame(phase_map, ls_frame)
            if phase is None or phase not in ALL_PHASES:
                continue

            lines = []
            has_rare = False
            for cid, segs in tracks:
                box = lsexport.box_at(segs, ls_frame)
                if box is None:
                    continue
                cx, cy, w, h = lsexport.to_yolo(*box)
                if w <= 0 or h <= 0:
                    continue
                lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                if dense_enabled and cid in rare_cids:
                    has_rare = True

            if not lines:
                continue

            ok, frame = cap.retrieve()
            if not ok:
                continue
            max_sampled_real = frame_idx
            base = f"{ti:02d}_{stem12}_{frame_idx:06d}"

            _write_frame(frame, lines, phase, split, base, jpg_q)
            emitted += 1
            phase_frame_counts[phase] += 1

            if dense_enabled and has_rare:
                half = stride - 1
                for n in range(frame_idx - half, frame_idx + half + 1):
                    if n >= 1 and n != frame_idx and (n - 1) % stride != 0:
                        dense_frames_to_sample.add(n)

        cap.release()

        # ---- Pass 2: dense sampling ----
        dense_count = 0
        if dense_enabled and dense_frames_to_sample:
            cap2 = cv2.VideoCapture(str(vpath))
            for df_idx in sorted(dense_frames_to_sample):
                if df_idx > total:
                    continue
                cap2.set(cv2.CAP_PROP_POS_FRAMES, df_idx - 1)
                ok, frame = cap2.read()
                if not ok:
                    continue
                ls_frame = df_idx * scale

                phase = lsexport.get_phase_for_frame(phase_map, ls_frame)
                if phase is None or phase not in ALL_PHASES:
                    continue

                lines = []
                for cid, segs in tracks:
                    box = lsexport.box_at(segs, ls_frame)
                    if box is None:
                        continue
                    cx, cy, w, h = lsexport.to_yolo(*box)
                    if w <= 0 or h <= 0:
                        continue
                    lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

                if not lines:
                    continue

                base = f"{ti:02d}_{stem12}_{df_idx:06d}_dense"
                _write_frame(frame, lines, phase, split, base, jpg_q)
                emitted += 1
                phase_frame_counts[phase] += 1
                dense_count += 1
            cap2.release()

        cover = (max_sampled_real / total * 100) if total else 0
        print(f"        stride: {sum(phase_frame_counts.values()) - dense_count}  "
              f"dense: {dense_count}  "
              f"coverage: 1..{max_sampled_real}/{total} ({cover:.0f}%)")
        for ph in sorted(phase_frame_counts):
            print(f"          {ph}: {phase_frame_counts[ph]} frames")

        task_stats.append({
            "id": tid,
            "stem": splitmod.stem_of(name),
            "name": name,
            "split": split,
            "phases": task_phases,
            "det_labels": det_labels,
            "total_frames": total,
            "phase_frame_counts": dict(phase_frame_counts),
        })

    write_data_yamls()

    # ---- Stats ----
    for phase in ALL_PHASES:
        gdir = OUT_ROOT / phase
        if gdir.exists() and any(gdir.rglob("*.txt")):
            stats.print_distribution(phase, UNIFIED_CLASSES, gdir)

    print(f"\nTotal images written: {emitted}")

    # ---- Save completed tasks ----
    for s in task_stats:
        completed[str(s["id"])] = {
            "export": json_path.name, "stride": stride,
            "stem": s["stem"], "split": s["split"],
            "completed_at": datetime.now().isoformat(),
        }
    completed_path.write_text(json.dumps(completed, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- Generate README + data_records ----
    generate_readme(task_stats, json_path)
    generate_data_records(task_stats)
    print("README.md + data_records.md generated.")


# ---------------------------------------------------------------------------
def generate_readme(task_stats, json_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_imgs = sum(
        len(list((OUT_ROOT / ph / "images").rglob("*.jpg")))
        for ph in ALL_PHASES if (OUT_ROOT / ph).exists()
    )

    lines = [
        "# CleanSight ActionSequence Dataset",
        "",
        "内镜清洗操作视频的**动作阶段切分**目标检测数据集。",
        "按 Label Studio 中标注的动作时序阶段 (timelinelabels) 将视频"
        "帧划分到对应的阶段子数据集中，每个阶段是一个独立的 YOLO 子数据集。",
        "",
        "## 数据集概述",
        "",
        "| 项目 | 说明 |",
        "|------|------|",
        "| 数据来源 | Label Studio Project #10，内镜清洗操作视频 |",
        "| 原始数据集 | [lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw) |",
        "| 标注类型 | 目标检测 (videorectangle) + 动作阶段 (timelinelabels) |",
        "| 数据格式 | Ultralytics YOLO (归一化中心点坐标) |",
        f"| 确认任务数 | {len(task_stats)} 个 |",
        f"| 总样本数 | {total_imgs} 张图像 (stride=4, ~7.5 fps) |",
        "| 划分方式 | 按 LS 任务整段切分 (train/val/test) |",
        "",
        "## 动作阶段",
        "",
        "| 阶段 | 说明 | 有数据 | 来源任务 |",
        "|------|------|--------|---------|",
    ]

    phase_has_data = {}
    for ph in ALL_PHASES:
        tasks_in = [s for s in task_stats if ph in s["phases"]]
        phase_has_data[ph] = len(tasks_in) > 0
        task_ids = ", ".join(str(s["id"]) for s in tasks_in) or "—"
        marker = "✅" if tasks_in else "❌ (暂无确认数据)"
        desc = {
            "short_brush_cleaning": "短刷清洁",
            "long_brush_insert": "长刷插入",
            "long_brush_withdraw": "长刷撤回",
            "air_injection": "气枪吹气",
            "flush": "冲水冲洗",
        }.get(ph, ph)
        lines.append(f"| {ph} | {desc} | {marker} | {task_ids} |")

    lines.extend([
        "",
        "## 检测类别 (8 类，所有阶段共享)",
        "",
        "| class_id | 标签 | 说明 |",
        "|----------|------|------|",
        "| 0 | `hand` | 操作者手部 |",
        "| 1 | `scope_control_body` | 内镜操控部 |",
        "| 2 | `scope_mid_section` | 内镜中部 |",
        "| 3 | `scope_distal_end` | 内镜头端 |",
        "| 4 | `syringe` | 注射器 |",
        "| 5 | `air_gun` | 气枪 |",
        "| 6 | `short_brush` | 短毛刷 |",
        "| 7 | `brush_tip_out` | 刷头外露 |",
        "",
        "> 注意：class_id 在所有阶段中保持一致，便于跨阶段模型对比和集成。",
        "",
        "## Split 划分",
        "",
        "| Split | 任务 | 视频 |",
        "|-------|------|------|",
    ])
    for sp in ("train", "val", "test"):
        tasks_in = [s for s in task_stats if s["split"] == sp]
        if not tasks_in:
            lines.append(f"| {sp} | — | — |")
        for s in tasks_in:
            lines.append(f"| {sp} | {s['id']} | {s['stem']} |")

    lines.extend([
        "",
        "> ⚠️ 每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏。",
        "> 旋转标注框已自动转换为外接轴对齐矩形 (AABB)，兼容 YOLO。",
        "",
        "## 数据集结构",
        "",
        "```",
        "lhh010/cleansight-ActionSequence/",
        "├── README.md",
        "├── data_records.md",
    ])
    for ph in ALL_PHASES:
        lines.append(f"├── {ph}/")
        lines.append(f"│   ├── data.yaml")
        lines.append(f"│   ├── images/{{train,val,test}}/*.jpg")
        lines.append(f"│   └── labels/{{train,val,test}}/*.txt")
    lines.append("```")

    lines.extend([
        "",
        "## 快速使用",
        "",
        "### 下载",
        "```python",
        "from modelscope.msdatasets import MsDataset",
        "ds = MsDataset.load('lhh010/cleansight-ActionSequence', split='master')",
        "```",
        "",
        "### 训练",
        "```python",
        "from ultralytics import YOLO",
        "# 训练长刷插入阶段的检测模型",
        "model = YOLO('yolo11n.pt')",
        "model.train(data='long_brush_insert/data.yaml', epochs=100, imgsz=640)",
        "```",
        "",
        "## 图片命名规范",
        "```",
        "{task序号:02d}_{视频名前12位}_{真实帧号:06d}.jpg",
        "例: 08_4807dbbe-cli_001045.jpg",
        "```",
        "",
        "## 标注格式 (YOLO 归一化)",
        "```",
        "class_id cx cy w h    # 归一化 [0,1] 浮点数",
        "例: 0 0.453125 0.687500 0.164062 0.183333",
        "```",
        "",
        "## 处理流水线",
        "",
        "1. Label Studio 导出 JSON → `raw/exports/`",
        "2. `02_build_actionseq.py` — 旋转框 AABB 修正 → 阶段过滤 → 抽帧 → YOLO 输出",
        "3. 上传至 ModelScope",
        "",
        "## 相关链接",
        "",
        "- 原始数据集: [lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)",
        "- Group 数据集: [lhh010/cleansight-yolo](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)",
        f"- 生成时间: {now}",
        f"- 导出文件: {json_path.name}",
    ])

    (OUT_ROOT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_data_records(task_stats):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# CleanSight ActionSequence — Data Records",
        "",
        f"**生成时间**: {now}",
        "",
        "## 任务级别统计",
        "",
        "| Task ID | Video | Split | 总帧数(视频) | 动作阶段 | 各阶段采样帧数 |",
        "|---------|-------|-------|-------------|---------|---------------|",
    ]

    for s in task_stats:
        phase_detail = ", ".join(
            f"{ph}({s['phase_frame_counts'].get(ph, 0)})"
            for ph in s["phases"]
        )
        lines.append(
            f"| {s['id']} | {s['stem'][:30]} | {s['split']} | {s['total_frames']} | "
            f"{', '.join(s['phases'])} | {phase_detail} |"
        )

    # Per-phase per-class statistics
    lines.extend([
        "",
        "## 逐阶段逐类别统计",
        "",
    ])

    for phase in ALL_PHASES:
        gdir = OUT_ROOT / phase
        if not gdir.exists() or not any(gdir.rglob("*.txt")):
            lines.extend([
                f"### {phase}",
                "",
                "> ⚠️ 暂无数据（缺少确认标注的包含此阶段的任务）",
                "",
            ])
            continue

        lines.extend([
            f"### {phase}",
            "",
            "| 类别 | Train 帧 | Val 帧 | Test 帧 | Train 框 | Val 框 | Test 框 |",
            "|------|---------|--------|---------|---------|--------|---------|",
        ])

        st = stats.scan_group(gdir)
        for cid, name in enumerate(UNIFIED_CLASSES):
            tr = st.get("train", {})
            va = st.get("val", {})
            te = st.get("test", {})
            tf = tr.get("cls_frames", {}).get(cid, 0)
            vf = va.get("cls_frames", {}).get(cid, 0)
            tef = te.get("cls_frames", {}).get(cid, 0)
            tb = tr.get("cls_boxes", {}).get(cid, 0)
            vb = va.get("cls_boxes", {}).get(cid, 0)
            teb = te.get("cls_boxes", {}).get(cid, 0)
            lines.append(f"| {name} | {tf} | {vf} | {tef} | {tb} | {vb} | {teb} |")

        tr_f = tr.get("frames", 0)
        va_f = va.get("frames", 0)
        te_f = te.get("frames", 0)
        tr_b = tr.get("boxes", 0)
        va_b = va.get("boxes", 0)
        te_b = te.get("boxes", 0)
        lines.append(f"| **合计** | **{tr_f}** | **{va_f}** | **{te_f}** | **{tr_b}** | **{va_b}** | **{te_b}** |")
        lines.append("")

    # Summary matrix
    lines.extend([
        "## 总览矩阵",
        "",
        "| 阶段 | Train | Val | Test | 合计 |",
        "|------|-------|-----|------|------|",
    ])
    for phase in ALL_PHASES:
        gdir = OUT_ROOT / phase
        if not gdir.exists():
            lines.append(f"| {phase} | — | — | — | 0 |")
            continue
        st = stats.scan_group(gdir)
        tr_f = st.get("train", {}).get("frames", 0)
        va_f = st.get("val", {}).get("frames", 0)
        te_f = st.get("test", {}).get("frames", 0)
        lines.append(f"| {phase} | {tr_f} | {va_f} | {te_f} | {tr_f + va_f + te_f} |")

    (OUT_ROOT / "data_records.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
