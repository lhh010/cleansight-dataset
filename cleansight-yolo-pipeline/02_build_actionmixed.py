#!/usr/bin/env python3
"""
LS export JSON + videos -> ActionMixed dataset (action recognition, mixed phases).

Output structure:
  datasets_actionmixed/
    images/{train,val,test}/{video_id}-{frame_id:06d}.jpg     # sampled frames
    frames/{train,val,test}/{video_id}-{frame_id:06d}.txt     # YOLO bbox per frame
    frames/data.yaml                                           # detection class mapping
    labels/{train,val,test}/{video_id}.txt                     # action labels per video
    labels/data.yaml                                           # action class mapping

Each action segment from Label Studio timelinelabels is extended with idle frames
before and after (up to half the segment length, constrained by video bounds and
adjacent-segment midpoints). All sampled frames in extended ranges are included.

Usage:
    python3 02_build_actionmixed.py
    python3 02_build_actionmixed.py --auto-assign
    python3 02_build_actionmixed.py --force
"""
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image

from utils.common import ROOT, load_config, is_whitelisted
from utils import lsexport, split as splitmod

OUT_ROOT = ROOT / "datasets_actionmixed"

# Split management for ActionMixed — segment-level (no per-video splits file needed)
COMPLETED_PATH = ROOT / "completed_tasks_actionmixed.json"

# Unified detection classes (same across all datasets)
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

# When total task count <= this, skip val; assign train+test only
SMALL_DATA_THRESHOLD = 5

# Output subdirectories
OUT_SUBDIRS = ("images", "frames", "labels")


# ---------------------------------------------------------------------------
# Directory & data.yaml helpers
# ---------------------------------------------------------------------------

def prepare_dirs():
    """Create output directory structure (incremental-friendly)."""
    for sub in OUT_SUBDIRS:
        for s in ("train", "val", "test"):
            (OUT_ROOT / sub / s).mkdir(parents=True, exist_ok=True)


def write_detection_data_yaml():
    names = "\n".join(f"  {i}: {lab}" for i, lab in enumerate(UNIFIED_CLASSES))
    (OUT_ROOT / "frames" / "data.yaml").write_text(
        f"nc: {len(UNIFIED_CLASSES)}\nnames:\n{names}\n",
        encoding="utf-8",
    )


def write_action_data_yaml(action_names):
    """action_names: list like ['idle', 'short_brush_cleaning', ...]."""
    names = "\n".join(f"  {i}: {lab}" for i, lab in enumerate(action_names))
    (OUT_ROOT / "labels" / "data.yaml").write_text(
        f"nc: {len(action_names)}\nnames:\n{names}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Segment extension algorithm
# ---------------------------------------------------------------------------

def compute_extended_segments(phase_ranges, total_frames):
    """Given sorted LS phase ranges (in real-frame space), compute extended segments.

    Args:
        phase_ranges: [(real_start, real_end, phase_name), ...] sorted by start.
        total_frames: total real video frame count.

    Returns:
        [(new_start, new_end, phase_name, action_start, action_end), ...]
        where [action_start, action_end] is the original action range.
    """
    segments = []
    for i, (start, end, phase) in enumerate(phase_ranges):
        L = end - start + 1
        max_ext = max(1, L // 2)  # half the segment length, at least 1

        # ---- forward boundary ----
        prev_boundary = 0
        if i > 0:
            prev_end = phase_ranges[i - 1][1]
            midpoint = (prev_end + start) // 2
            prev_boundary = midpoint
        new_start = max(prev_boundary, start - max_ext, 0)

        # ---- backward boundary ----
        next_boundary = total_frames
        if i < len(phase_ranges) - 1:
            next_start = phase_ranges[i + 1][0]
            midpoint = (end + next_start) // 2
            next_boundary = midpoint
        new_end = min(next_boundary, end + max_ext, total_frames)

        # Clamp: new_start ≤ start, new_end ≥ end
        new_start = min(new_start, start)
        new_end = max(new_end, end)

        segments.append((new_start, new_end, phase, start, end))

    return segments


# ---------------------------------------------------------------------------
# Assign action labels to frames
# ---------------------------------------------------------------------------

def get_action_for_frame(segments, real_frame):
    """Return (action_name, is_action_core) for a real frame index.
    is_action_core=True means the frame falls within the original LS action range.
    """
    for new_start, new_end, phase, action_start, action_end in segments:
        if new_start <= real_frame <= new_end:
            if action_start <= real_frame <= action_end:
                return phase, True
            else:
                return "idle", False
    return None, False



# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def write_frame_output(name, split, frame_idx, bbox_lines, frame_bgr, jpg_q):
    """Write image + bbox label for a single sampled frame."""
    base = f"{name}-{frame_idx:06d}"

    # Save JPEG image
    img_path = OUT_ROOT / "images" / split / f"{base}.jpg"
    Image.fromarray(frame_bgr[:, :, ::-1]).save(str(img_path), quality=jpg_q)

    # Save bbox label
    lbl_path = OUT_ROOT / "frames" / split / f"{base}.txt"
    lbl_path.write_text(
        "\n".join(bbox_lines) + "\n" if bbox_lines else "",
        encoding="utf-8",
    )


def clean_task_output(name):
    """Remove all output files for a task before reprocessing."""
    for sub in OUT_SUBDIRS:
        for sp_n in ("train", "val", "test"):
            subdir = OUT_ROOT / sub / sp_n
            if not subdir.is_dir():
                continue
            if sub in ("images", "frames"):
                # Per-frame files: {name}-{frame:06d}.{jpg,txt} + _dense variants
                for f in list(subdir.glob(f"{name}-*.jpg")) + list(subdir.glob(f"{name}-*.txt")):
                    f.unlink()
            elif sub == "labels":
                # Consolidated per-video file
                lbl_file = subdir / f"{name}.txt"
                if lbl_file.exists():
                    lbl_file.unlink()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    force = "--force" in sys.argv[1:]
    cfg = load_config()
    only = cfg.get("only_videos") or []
    stride = cfg.get("stride", 4)
    jpg_q = cfg.get("jpg_quality", 90)
    dense_enabled = cfg.get("rare_dense_sampling", True)
    rare_threshold = cfg.get("rare_threshold", 200)

    # Detection class mapping
    det_label2cid = {lab: i for i, lab in enumerate(UNIFIED_CLASSES)}

    json_path = lsexport.latest_export()
    tasks = lsexport.load_tasks(json_path)

    # ---- Load completed tasks for incremental processing ----
    completed = {}
    if COMPLETED_PATH.exists():
        completed = json.loads(COMPLETED_PATH.read_text(encoding="utf-8"))
    if force:
        print("[--force] full rebuild")
        completed = {}

    print(f"Export: {json_path.name}  {len(tasks)} tasks  (completed: {len(completed)})")

    # ---- Discover action classes across all confirmed tasks ----
    all_phases = set()
    for task in tasks:
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        for _, _, phase in lsexport.iter_phase_ranges(task):
            all_phases.add(phase)

    # Build action class list: 0 = idle, then sorted discovered phases
    action_names = ["idle"] + sorted(all_phases)
    phase2action_id = {ph: i for i, ph in enumerate(action_names)}
    print(f"Action classes: {action_names}")

    # ---- Compute rare detection classes ----
    kf_counts = defaultdict(int)
    for task in tasks:
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        for r in lsexport.iter_results(task, "videorectangle"):
            labs = r.get("value", {}).get("labels", [])
            if not labs or labs[0] not in det_label2cid:
                continue
            kf_counts[labs[0]] += len(r.get("value", {}).get("sequence", []))
    rare_cids = {det_label2cid[lab] for lab, cnt in kf_counts.items()
                 if cnt < rare_threshold and lab in det_label2cid}
    if dense_enabled:
        rare_names = [UNIFIED_CLASSES[c] for c in sorted(rare_cids)]
        print(f"Dense sampling (threshold < {rare_threshold} kf): "
              f"{rare_names if rare_names else 'none'}")

    # ---- Collect pending tasks ----
    # For ActionMixed, splits are at the SEGMENT level — same video can
    # contribute frames to different splits.  No per-video splits.yaml needed.
    pending_tasks = []

    for ti, task in enumerate(tasks):
        name = lsexport.task_video_name(task)
        if not name or not is_whitelisted(name, only):
            continue
        phases = list(lsexport.iter_phase_ranges(task))
        if not phases:
            continue

        tid = task["id"]
        task_key = str(tid)

        # Incremental skip
        if not force and task_key in completed:
            prev = completed[task_key]
            if prev.get("export") == json_path.name and prev.get("stride") == stride:
                print(f"  [skip] task#{tid} {name}")
                continue
            else:
                print(f"  [reprocess] task#{tid} {name}")
                clean_task_output(name)

        pending_tasks.append((ti, task, name))

    prepare_dirs()
    write_detection_data_yaml()
    write_action_data_yaml(action_names)

    # ---- Segment-level split assignment ----
    # Each segment gets an independent split via deterministic hash on
    # (stem + segment_index), targeting 6:2:2 ratio (or train+test for small data).
    # Count total segments first to decide small/large mode.
    all_segments_pre = []  # (ti, task, name, seg_idx, seg_info)
    for ti, task, name in pending_tasks:
        vpath = lsexport.VIDEO_DIR / name
        if not vpath.exists():
            continue
        cap = cv2.VideoCapture(str(vpath))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        cap.release()
        phase_ranges_ls = list(lsexport.iter_phase_ranges(task))
        fc, dur = lsexport.clip_meta(task)
        real_fps_tmp = 30.0  # placeholder, will be read properly in processing
        scale_tmp, _ = lsexport.fps_scale(real_fps_tmp, fc, dur)
        phase_ranges_real = []
        for start_ls, end_ls, phase in phase_ranges_ls:
            start_real = max(1, int(round(start_ls / scale_tmp)))
            end_real = min(total, int(round(end_ls / scale_tmp)))
            phase_ranges_real.append((start_real, end_real, phase))
        phase_ranges_real.sort(key=lambda x: x[0])
        segments = compute_extended_segments(phase_ranges_real, total)
        for seg_idx, seg in enumerate(segments):
            all_segments_pre.append((ti, task, name, seg_idx, seg))

    total_segments = len(all_segments_pre)
    use_small_mode = total_segments <= SMALL_DATA_THRESHOLD
    seed = cfg.get("seed", 1337)
    if use_small_mode:
        print(f"Small-data mode: {total_segments} segments → train + test only")
    else:
        print(f"Large-data mode: {total_segments} segments → train:val:test = 6:2:2")

    # Assign split to each segment
    segment_splits = {}  # (name, seg_idx) -> split
    for ti, task, name, seg_idx, seg in all_segments_pre:
        stem = splitmod.stem_of(name)
        if use_small_mode:
            sp = splitmod.deterministic_split(
                f"{stem}:seg{seg_idx}", seed, val_ratio=0.0, test_ratio=0.2)
        else:
            sp = splitmod.deterministic_split(
                f"{stem}:seg{seg_idx}", seed, val_ratio=0.2, test_ratio=0.2)
        segment_splits[(name, seg_idx)] = sp

    # Print summary of segment assignments per task
    for ti, task, name in pending_tasks:
        tid = task["id"]
        task_seg_splits = {}
        for (n, si), sp in segment_splits.items():
            if n == name:
                task_seg_splits.setdefault(sp, 0)
                task_seg_splits[sp] += 1
        sp_summary = ", ".join(f"{sp}:{cnt}" for sp, cnt in sorted(task_seg_splits.items()))
        print(f"  task#{tid} {name}  segment-splits: {sp_summary}")

    # ---- Main processing loop ----
    emitted_frames = 0
    task_stats = []

    for ti, task, name in pending_tasks:
        tid = task["id"]

        vpath = lsexport.VIDEO_DIR / name
        if not vpath.exists():
            print(f"  [warn] task#{tid} video missing: {name}")
            continue

        tracks = lsexport.collect_tracks_unified(task, det_label2cid)
        phase_ranges_ls = list(lsexport.iter_phase_ranges(task))

        cap = cv2.VideoCapture(str(vpath))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        real_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fc, dur = lsexport.clip_meta(task)
        scale, ls_fps = lsexport.fps_scale(real_fps, fc, dur)

        # Convert LS phase ranges to real-frame space
        phase_ranges_real = []
        for start_ls, end_ls, phase in phase_ranges_ls:
            start_real = max(1, int(round(start_ls / scale)))
            end_real = min(total, int(round(end_ls / scale)))
            phase_ranges_real.append((start_real, end_real, phase))
        phase_ranges_real.sort(key=lambda x: x[0])

        # Compute extended segments with idle padding
        segments = compute_extended_segments(phase_ranges_real, total)

        task_phases = sorted(set(ph for _, _, ph in phase_ranges_ls))
        det_labels = lsexport.collect_det_labels(task)

        seg_desc = ", ".join(
            f"{ph}[{ns}-{ne}]" for ns, ne, ph, _, _ in segments
        )
        print(f"  task#{tid} {name}  total={total}@{real_fps:.1f}fps  "
              f"LS={fc}@{ls_fps:.1f}fps  scale={scale:.3f}  "
              f"phases={task_phases}  tracks={len(tracks)}")
        print(f"        segments: {seg_desc}")

        # ---- Collect frame data: frame_idx -> (seg_idx, action_id, bbox_lines) ----
        frame_data = {}        # frame_idx -> (seg_idx, action_id, bbox_lines, frame_bgr)
        dense_frames_to_sample = set()
        phase_frame_counts = defaultdict(int)
        seg_frame_counts = defaultdict(int)

        # Build a quick lookup: real_frame -> seg_index
        frame_to_seg = {}
        for seg_idx, (new_start, new_end, phase, action_start, action_end) in enumerate(segments):
            for f in range(new_start, new_end + 1):
                frame_to_seg[f] = seg_idx

        # ---- Pass 1: stride sampling ----
        frame_idx = 0
        while True:
            if not cap.grab():
                break
            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue

            seg_idx = frame_to_seg.get(frame_idx)
            if seg_idx is None:
                continue

            new_start, new_end, phase, action_start, action_end = segments[seg_idx]
            action_name, is_core = get_action_for_frame(segments, frame_idx)
            if action_name is None:
                continue

            ls_frame = frame_idx * scale

            # Get detection bboxes
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

            ok, frame_bgr = cap.retrieve()
            if not ok:
                continue

            action_id = phase2action_id[action_name]
            frame_data[frame_idx] = (seg_idx, action_id, lines, frame_bgr)
            phase_frame_counts[action_name] += 1
            seg_frame_counts[seg_idx] += 1

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
                seg_idx = frame_to_seg.get(df_idx)
                if seg_idx is None:
                    continue
                action_name, is_core = get_action_for_frame(segments, df_idx)
                if action_name is None:
                    continue

                cap2.set(cv2.CAP_PROP_POS_FRAMES, df_idx - 1)
                ok, frame_bgr = cap2.read()
                if not ok:
                    continue

                ls_frame = df_idx * scale
                lines = []
                for cid, segs in tracks:
                    box = lsexport.box_at(segs, ls_frame)
                    if box is None:
                        continue
                    cx, cy, w, h = lsexport.to_yolo(*box)
                    if w <= 0 or h <= 0:
                        continue
                    lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

                action_id = phase2action_id[action_name]
                frame_data[df_idx] = (seg_idx, action_id, lines, frame_bgr)
                phase_frame_counts[action_name] += 1
                seg_frame_counts[seg_idx] += 1
                dense_count += 1
            cap2.release()

        # ---- Write output files, grouped by (split, seg_idx) ----
        sorted_frames = sorted(frame_data.items())

        # Group frames by split (segment-level assignment)
        split_frames = defaultdict(list)  # split -> [(frame_idx, seg_idx, action_id, lines, frame_bgr)]
        for frame_idx, (seg_idx, action_id, lines, frame_bgr) in sorted_frames:
            sp = segment_splits.get((name, seg_idx), "train")
            split_frames[sp].append((frame_idx, seg_idx, action_id, lines, frame_bgr))

        # Write per-frame images + bbox files
        for sp, frames in split_frames.items():
            for frame_idx, seg_idx, action_id, bbox_lines, frame_bgr in frames:
                write_frame_output(name, sp, frame_idx, bbox_lines, frame_bgr, jpg_q)
                emitted_frames += 1

            # Consolidated action label file per (video, split)
            label_path = OUT_ROOT / "labels" / sp / f"{name}.txt"
            label_content = "\n".join(
                f"{frame_idx} {action_id}"
                for frame_idx, _, action_id, _, _ in frames
            ) + "\n"
            label_path.write_text(label_content, encoding="utf-8")

        # Coverage stats
        max_frame = max(frame_data.keys()) if frame_data else 0
        cover = (max_frame / total * 100) if total else 0
        print(f"        frames: {len(sorted_frames) - dense_count} (stride) + "
              f"{dense_count} (dense) = {len(sorted_frames)}  "
              f"coverage: 1..{max_frame}/{total} ({cover:.0f}%)")
        for ph in sorted(phase_frame_counts):
            print(f"          {ph}: {phase_frame_counts[ph]} frames")
        seg_detail = ", ".join(
            f"seg{i}[{ns}-{ne}]->{segment_splits.get((name, i), '?')}({seg_frame_counts.get(i,0)}f)"
            for i, (ns, ne, ph, _, _) in enumerate(segments)
        )
        print(f"        seg splits: {seg_detail}")

        # Build segment info for tracking
        seg_infos = []
        for i, (ns, ne, ph, ast, aed) in enumerate(segments):
            seg_infos.append({
                "index": i,
                "new_start": ns, "new_end": ne,
                "phase": ph,
                "action_start": ast, "action_end": aed,
                "split": segment_splits.get((name, i), "train"),
                "frame_count": seg_frame_counts.get(i, 0),
            })

        task_stats.append({
            "id": tid,
            "stem": splitmod.stem_of(name),
            "name": name,
            "phases": task_phases,
            "det_labels": det_labels,
            "total_frames": total,
            "segments": seg_infos,
            "frame_counts": dict(phase_frame_counts),
            "split_summary": {
                sp: sum(s["frame_count"] for s in seg_infos if s["split"] == sp)
                for sp in splitmod.DATASET_SPLITS
            },
        })

    # ---- Save completed tasks (segment-level) ----
    for s in task_stats:
        completed[str(s["id"])] = {
            "export": json_path.name,
            "stride": stride,
            "stem": s["stem"],
            "segments": [
                {"index": seg["index"], "split": seg["split"],
                 "phase": seg["phase"], "frames": seg["frame_count"]}
                for seg in s["segments"]
            ],
            "completed_at": datetime.now().isoformat(),
        }
    COMPLETED_PATH.write_text(
        json.dumps(completed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nTotal images + frame files written: {emitted_frames}")

    # ---- Generate tracking documentation ----
    generate_tracking(task_stats, tasks, json_path, only, action_names)


# ---------------------------------------------------------------------------
# Tracking / documentation
# ---------------------------------------------------------------------------

def generate_tracking(task_stats, all_tasks, json_path, only_videos, action_names):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_by_id = {s["id"]: s for s in task_stats}

    lines = [
        "# CleanSight ActionMixed — Processing Record",
        "",
        f"**Generated**: {now}",
        f"**Export**: {json_path.name}",
        "",
        "## Dataset Overview",
        "",
        "Action recognition dataset combining detection bboxes with action labels.",
        "Each action segment is extended with idle frames (up to half segment length,",
        "constrained by adjacent-segment midpoints and video bounds).",
        "**Splits are at segment level** — different segments from the same video",
        "may belong to different splits (train/val/test).",
        "",
        "## Directory Structure",
        "",
        "```",
        "datasets_actionmixed/",
        "├── images/{train,val,test}/{video_id}-{frame_id:06d}.jpg",
        "├── frames/{train,val,test}/{video_id}-{frame_id:06d}.txt   (YOLO bbox)",
        "│   └── data.yaml                                             (detection classes)",
        "└── labels/{train,val,test}/{video_id}.txt                    (action labels)",
        "    └── data.yaml                                             (action classes)",
        "```",
        "",
        "## Task Processing Status",
        "",
        "| LS Task ID | Video | Total Frames | Phases | Segments (split:frames) |",
        "|-----------|------|-------------|--------|------------------------|",
    ]

    for task in all_tasks:
        tid = task["id"]
        name = lsexport.task_video_name(task)
        if not name:
            continue
        if only_videos and not is_whitelisted(name, only_videos):
            continue
        st = stats_by_id.get(tid)
        if st:
            phases_str = ", ".join(st["phases"]) or "—"
            seg_str = ", ".join(
                f"{s['phase']}[{s['action_start']}-{s['action_end']}]→{s['split']}({s['frame_count']})"
                for s in st["segments"]
            )
            tf = sum(s["frame_count"] for s in st["segments"])
            lines.append(
                f"| {tid} | {name.rsplit('.', 1)[0][:30]} | "
                f"{st['total_frames']} | {phases_str} | {seg_str} |"
            )
        else:
            phases = sorted(set(
                ph for _, _, ph in lsexport.iter_phase_ranges(task)
            ))
            lines.append(
                f"| {tid} | {name.rsplit('.', 1)[0][:30]} | "
                f"— | {', '.join(phases) or '—'} | — |"
            )

    # Split summary
    lines.extend([
        "",
        "## Split Summary (by segment-level assignment)",
        "",
        "| Split | Segments | Frames |",
        "|-------|----------|--------|",
    ])
    for sp in ("train", "val", "test"):
        sp_segments = 0
        sp_frames = 0
        for s in task_stats:
            for seg in s["segments"]:
                if seg["split"] == sp:
                    sp_segments += 1
                    sp_frames += seg["frame_count"]
        lines.append(f"| {sp} | {sp_segments} | {sp_frames} |")

    # Per-task split breakdown
    lines.extend([
        "",
        "## Per-Task Split Breakdown",
        "",
        "| Task ID | Train | Val | Test |",
        "|---------|-------|-----|------|",
    ])
    for s in task_stats:
        tr = sum(seg["frame_count"] for seg in s["segments"] if seg["split"] == "train")
        va = sum(seg["frame_count"] for seg in s["segments"] if seg["split"] == "val")
        te = sum(seg["frame_count"] for seg in s["segments"] if seg["split"] == "test")
        lines.append(f"| {s['id']} | {tr} | {va} | {te} |")

    # Action classes
    lines.extend([
        "",
        "## Action Classes",
        "",
        "| ID | Name |",
        "|---|------|",
    ])
    for i, name in enumerate(action_names):
        lines.append(f"| {i} | {name} |")

    # Detection classes
    lines.extend([
        "",
        "## Detection Classes",
        "",
        "| ID | Name |",
        "|---|------|",
    ])
    for i, name in enumerate(UNIFIED_CLASSES):
        lines.append(f"| {i} | {name} |")

    lines.extend([
        "",
        "> Splits are assigned per-segment (not per-video). Same video may span multiple splits.",
        "> Action segments extended with idle padding: half-length + midpoint rule.",
        "> Rotated bboxes auto-converted to AABB (YOLO compatible).",
    ])

    (ROOT / "tracking_actionmixed.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )
    print("tracking_actionmixed.md generated.")


if __name__ == "__main__":
    main()
