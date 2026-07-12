#!/usr/bin/env python3
"""
LS 导出 JSON + 视频 -> YOLO 目标检测数据集（group1_large / group2_small）。

输出结构：
  datasets/<group>/
    images/{train,val,test}/*.jpg
    labels/{train,val,test}/*.txt
    data.yaml

每个 LS 任务的所有帧完整保留在同一 split 内，杜绝时间相邻帧泄漏。
对稀有类别（框数 < rare_threshold）在正常 stride 之外额外密集采样相邻帧，
以自然方式增加样本量，避免旋转/缩放等人工增强带来的失真。

用法（在 cleansight-yolo-pipeline/ 下执行）：
    python3 02_build_dataset.py
    python3 02_build_dataset.py --auto-assign
"""
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from utils.common import ROOT, load_config, is_whitelisted
from utils import lsexport, split as splitmod, stats

OUT_ROOT = ROOT / "datasets"


def prepare_dirs(groups):
    """创建目录结构（不清除已有文件，支持增量构建）。"""
    for g in groups:
        for s in ("train", "val", "test"):
            (OUT_ROOT / g / "images" / s).mkdir(parents=True, exist_ok=True)
            (OUT_ROOT / g / "labels" / s).mkdir(parents=True, exist_ok=True)


def write_data_yamls(groups):
    for g, labels in groups.items():
        names = "\n".join(f"  {i}: {lab}" for i, lab in enumerate(labels))
        (OUT_ROOT / g / "data.yaml").write_text(
            f"path: .\n"
            f"train: images/train\nval: images/val\ntest: images/test\n"
            f"nc: {len(labels)}\nnames:\n{names}\n",
            encoding="utf-8",
        )


def _write_frame(frame_array, lines, group, split, base, jpg_q):
    out_img = OUT_ROOT / group / "images" / split / f"{base}.jpg"
    Image.fromarray(frame_array[:, :, ::-1]).save(str(out_img), quality=jpg_q)
    (OUT_ROOT / group / "labels" / split / f"{base}.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def compute_rare_classes(tasks, label2group, only, threshold):
    """统计所有确认任务中各 label 的 keyframe 总数，返回 {label: True if rare}。"""
    kf_counts = defaultdict(int)
    for task in tasks:
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        for r in lsexport.iter_results(task, "videorectangle"):
            labs = r.get("value", {}).get("labels", [])
            if not labs or labs[0] not in label2group:
                continue
            seq = r.get("value", {}).get("sequence", [])
            kf_counts[labs[0]] += len(seq)
    return {lab: cnt < threshold for lab, cnt in kf_counts.items()}


def main():
    auto_assign = "--auto-assign" in sys.argv[1:]
    force = "--force" in sys.argv[1:]
    cfg = load_config()
    groups = cfg["groups"]
    only = cfg.get("only_videos") or []
    label2group = lsexport.build_label_index(groups)
    stride = cfg.get("stride", 4)
    jpg_q = cfg.get("jpg_quality", 90)
    dense_enabled = cfg.get("rare_dense_sampling", True)
    rare_threshold = cfg.get("rare_threshold", 200)

    json_path = lsexport.latest_export()
    tasks = lsexport.load_tasks(json_path)
    sp = splitmod.load()

    # ---- 增量：加载已完成任务列表 ----
    completed_path = ROOT / "completed_tasks.json"
    completed = {}
    if completed_path.exists():
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
    if force:
        print("[--force] 全量重建，清除已完成记录")
        completed = {}

    print(f"Export: {json_path.name}  {len(tasks)} tasks"
          f"  (已完成: {len(completed)})")

    # Compute rare classes
    rare_labels = compute_rare_classes(tasks, label2group, only, rare_threshold)
    # Convert to cid-based lookup per group
    rare_cids = {}  # group -> set(cid)
    for lab, is_rare in rare_labels.items():
        if is_rare and lab in label2group:
            g, cid = label2group[lab]
            rare_cids.setdefault(g, set()).add(cid)
    if dense_enabled:
        print(f"Dense sampling enabled (threshold < {rare_threshold} keyframes):")
        for lab, is_rare in sorted(rare_labels.items()):
            if is_rare:
                print(f"  {lab}: RARE")
    else:
        print("Dense sampling disabled")

    # ---- Determine splits ----
    pending = []
    unassigned = []
    for ti, task in enumerate(tasks):
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        if not lsexport.collect_tracks(task, label2group):
            continue
        tid = task["id"]
        stem = splitmod.stem_of(name)
        s = splitmod.get_split(stem, sp)

        # 增量跳过：已处理且导出文件和stride未变
        task_key = str(tid)
        if not force and task_key in completed:
            prev = completed[task_key]
            if prev.get("export") == json_path.name and prev.get("stride") == stride:
                print(f"  [skip] task#{tid} {name} (已完成，未变化)")
                continue
            else:
                # 导出变了或stride变了 → 清除旧文件
                print(f"  [reprocess] task#{tid} {name} (配置已变)")
                for g in groups:
                    for sp_n in ("train", "val", "test"):
                        stem12 = Path(name).stem[:12]
                        for pat in [f"{ti:02d}_{stem12}_*", f"{ti:02d}_{stem12}_*_dense"]:
                            for f in (OUT_ROOT / g / "images" / sp_n).glob(f"{pat}.jpg"):
                                f.unlink()
                            for f in (OUT_ROOT / g / "labels" / sp_n).glob(f"{pat}.txt"):
                                f.unlink()

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
            print("ERROR: unassigned videos, use --auto-assign")
            for stem, *_ in unassigned:
                print(f"    {stem}")
            sys.exit(2)

    prepare_dirs(groups)

    emitted = 0
    task_stats = []

    for ti, task, name, split in pending:
        tid = task["id"]
        if split not in splitmod.DATASET_SPLITS:
            print(f"  [hold] task#{tid} {name} split={split}")
            continue
        vpath = lsexport.VIDEO_DIR / name
        if not vpath.exists():
            print(f"  [warn] task#{tid} video missing: {name}")
            continue

        tracks = lsexport.collect_tracks(task, label2group)
        task_phases = lsexport.collect_task_phases(task)
        det_labels = lsexport.collect_det_labels(task)
        stem12 = vpath.stem[:12]

        cap = cv2.VideoCapture(str(vpath))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        real_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fc, dur = lsexport.clip_meta(task)
        scale, ls_fps = lsexport.fps_scale(real_fps, fc, dur)
        print(f"  task#{tid} [{split}] {name}  real={total}@{real_fps:.1f}fps  "
              f"tracks={len(tracks)}  stride={stride}")

        group_frame_counts = defaultdict(int)
        dense_frames_to_sample = set()  # frame indices for dense pass

        # ---- Pass 1: normal stride sampling ----
        frame_idx = 0
        max_sampled_real = 0
        while True:
            if not cap.grab():
                break
            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue
            ls_frame = frame_idx * scale

            lines_by_group = defaultdict(list)
            has_rare = defaultdict(bool)
            for g, cid, segs in tracks:
                box = lsexport.box_at(segs, ls_frame)
                if box is None:
                    continue
                cx, cy, w, h = lsexport.to_yolo(*box)
                if w <= 0 or h <= 0:
                    continue
                lines_by_group[g].append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                if dense_enabled and cid in rare_cids.get(g, set()):
                    has_rare[g] = True

            if not lines_by_group:
                continue

            ok, frame = cap.retrieve()
            if not ok:
                continue
            max_sampled_real = frame_idx
            base = f"{ti:02d}_{stem12}_{frame_idx:06d}"

            for g, lines in lines_by_group.items():
                _write_frame(frame, lines, g, split, base, jpg_q)
                emitted += 1
                group_frame_counts[g] += 1

            # Mark neighbor frames for dense sampling if rare classes present
            if dense_enabled and any(has_rare.values()):
                half = stride - 1
                for n in range(frame_idx - half, frame_idx + half + 1):
                    if n >= 1 and n != frame_idx and (n - 1) % stride != 0:
                        dense_frames_to_sample.add(n)

        cap.release()

        # ---- Pass 2: dense sampling for rare neighbors ----
        dense_count = 0
        if dense_enabled and dense_frames_to_sample:
            cap2 = cv2.VideoCapture(str(vpath))
            for df_idx in sorted(dense_frames_to_sample):
                if df_idx > total:
                    continue
                cap2.set(cv2.CAP_PROP_POS_FRAMES, df_idx - 1)  # 0-based seek
                ok, frame = cap2.read()
                if not ok:
                    continue
                ls_frame = df_idx * scale

                lines_by_group = defaultdict(list)
                for g, cid, segs in tracks:
                    box = lsexport.box_at(segs, ls_frame)
                    if box is None:
                        continue
                    cx, cy, w, h = lsexport.to_yolo(*box)
                    if w <= 0 or h <= 0:
                        continue
                    lines_by_group[g].append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

                if not lines_by_group:
                    continue

                base = f"{ti:02d}_{stem12}_{df_idx:06d}_dense"
                for g, lines in lines_by_group.items():
                    _write_frame(frame, lines, g, split, base, jpg_q)
                    emitted += 1
                    group_frame_counts[g] += 1
                    dense_count += 1
            cap2.release()

        cover = (max_sampled_real / total * 100) if total else 0
        print(f"        stride frames: {sum(group_frame_counts.values()) - dense_count}  "
              f"dense frames: {dense_count}  "
              f"coverage: 1..{max_sampled_real}/{total} ({cover:.0f}%)")
        for g in sorted(group_frame_counts):
            print(f"          {g}: {group_frame_counts[g]} frames")

        task_stats.append({
            "id": tid, "stem": splitmod.stem_of(name), "name": name,
            "split": split, "phases": task_phases, "det_labels": det_labels,
            "total_frames": total,
            "group_frame_counts": dict(group_frame_counts),
            "confirmed": True,
        })

    # ---- 保存已完成任务 ----
    for s in task_stats:
        completed[str(s["id"])] = {
            "export": json_path.name,
            "stride": stride,
            "stem": s["stem"],
            "split": s["split"],
            "completed_at": datetime.now().isoformat(),
        }
    completed_path.write_text(json.dumps(completed, indent=2, ensure_ascii=False), encoding="utf-8")

    write_data_yamls(groups)

    for g, class_names in groups.items():
        gdir = OUT_ROOT / g
        if gdir.exists():
            stats.print_distribution(g, class_names, gdir)

    print(f"\nTotal images: {emitted}")

    write_tracking_table(tasks, task_stats, groups, only, json_path)
    print("tracking.md generated. Next: 03_train.py / 04_validate.py")


# ----- tracking.md -----
def write_tracking_table(all_tasks, task_stats, groups, only_videos, json_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_by_id = {s["id"]: s for s in task_stats}
    label2group = lsexport.build_label_index(groups)

    lines = [
        "# CleanSight Dataset Status", "",
        f"**Generated**: {now}", f"**Export**: {json_path.name}", "",
        "## Task Status", "",
        "| LS Task ID | Video | Confirmed | Split | Phases | Det Labels | Sampled Frames |",
        "|-----------|------|-----------|-------|--------|------------|----------------|",
    ]
    for task in all_tasks:
        tid = task["id"]
        name = lsexport.task_video_name(task)
        if not name:
            continue
        st = stats_by_id.get(tid)
        if st:
            sp = st["split"]
            phases_str = ", ".join(st["phases"]) or "—"
            det = len(st["det_labels"])
            tf = sum(st["group_frame_counts"].values())
            lines.append(f"| {tid} | {name.rsplit('.',1)[0][:35]} | [OK] | {sp} | {phases_str} | {det} | {tf} |")
        else:
            phases_str = ", ".join(lsexport.collect_task_phases(task)) or "—"
            det = len(lsexport.collect_det_labels(task))
            lines.append(f"| {tid} | {name.rsplit('.',1)[0][:35]} | [NO] | — | {phases_str} | {det} | — |")

    lines.extend(["", "## Group Summary", "",
                   "| Group | Split | Images | Boxes |",
                   "|-------|-------|--------|-------|"])
    for g in groups:
        gdir = OUT_ROOT / g
        if not gdir.exists():
            continue
        for sp in ("train", "val", "test"):
            imgs = len(list((gdir / "images" / sp).glob("*.jpg"))) if (gdir / "images" / sp).exists() else 0
            boxes = 0
            lbl_dir = gdir / "labels" / sp
            if lbl_dir.exists():
                for txt in lbl_dir.glob("*.txt"):
                    boxes += len([l for l in txt.read_text(encoding="utf-8").splitlines() if l.strip()])
            if imgs:
                lines.append(f"| {g} | {sp} | {imgs} | {boxes} |")

    lines.extend(["", "## Split Assignment", "",
                   "| Split | Tasks |",
                   "|-------|-------|"])
    for sp in ("train", "val", "test"):
        tids = [str(s["id"]) for s in task_stats if s["split"] == sp]
        lines.append(f"| {sp} | {', '.join(tids) or '—'} |")

    lines.extend(["", "> Each LS task's frames stay entirely in one split.",
                   "> Rotated bboxes auto-converted to AABB.",
                   "> Rare classes (< 200 keyframes) have dense neighbor-frame sampling."])

    (ROOT / "tracking.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
