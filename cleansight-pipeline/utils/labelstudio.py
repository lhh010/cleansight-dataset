#!/usr/bin/env python3
"""
Label Studio 视频导出解析 —— 共享核心逻辑,供各脚本复用。

已验证正确、**不可退化**的几处:
  - fps 对齐:LS 标注帧号按标注端 fps(常 24)计,真实视频 fps 可能不同,
    用 scale = ls_fps/real_fps 把真实解码帧号映射回 LS 帧号,消除漂移/尾部丢失。
  - 关键帧线性插值:sequence 只存关键帧,中间帧插值;enabled=False = 目标离场。
  - 坐标转换:LS 左上角百分比 -> YOLO 归一化中心点 (cx,cy,w,h),裁剪到 [0,1]。

只依赖标准库(路径/JSON)。cv2 由调用方使用,这里不导入,便于纯解析场景。
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # yolo_pipeline/(自包含)
EXPORT_DIR = ROOT / "raw" / "exports"
VIDEO_DIR = ROOT / "raw" / "videos"


def latest_export(export_dir: Path = EXPORT_DIR) -> Path:
    """取 raw/exports/ 下文件名排序最后一个 JSON。"""
    files = sorted(export_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"raw/exports/ 下没有导出 JSON: {export_dir}")
    return files[-1]


def load_tasks(json_path: Path):
    return json.load(open(json_path, encoding="utf-8"))


def task_video_name(task) -> str:
    """task 引用的视频文件名(不含目录)。"""
    rel = task.get("data", {}).get("video", "") or ""
    return Path(rel).name


def iter_results(task, rtype=None):
    """遍历 task 所有 annotation 的 result;rtype 非空时只出该 type。"""
    for ann in task.get("annotations", []):
        for r in ann.get("result", []):
            if rtype is None or r.get("type") == rtype:
                yield r


def clip_meta(task):
    """从第一个 videorectangle 读 (framesCount, duration);取不到返回 (None, None)。"""
    for r in iter_results(task, "videorectangle"):
        v = r["value"]
        return v.get("framesCount"), v.get("duration")
    return None, None


def build_label_index(groups: dict):
    """LS 类别名 -> (组名, class_id) 的反查表。

    当同一个 label 出现在多个 group 时取第一个匹配（class_id 在各 group 中
    应保持一致；若不一致会有警告但不会报错）。
    """
    label2group = {}
    for g, labels in groups.items():
        for cid, lab in enumerate(labels):
            if lab not in label2group:
                label2group[lab] = (g, cid)
    return label2group


def build_unified_class_map(groups: dict):
    """构建统一的 label -> class_id 映射（跨所有 phase 共享）。

    返回 (label2cid, cid2label)。class_id 由第一个出现的 group 的 class
    列表顺序决定；所有 group 应使用相同的 class 列表。
    """
    label2cid = {}
    cid2label = {}
    for g, labels in groups.items():
        for cid, lab in enumerate(labels):
            if lab not in label2cid:
                label2cid[lab] = cid
                cid2label[cid] = lab
    return label2cid, cid2label


def collect_tracks_unified(task, label2cid):
    """收集 task 内所有目标轨迹: [(class_id, segments), ...]。

    与 collect_tracks 不同，返回的是统一 class_id（跨所有 phase 共享），
    不绑定到特定 group。仅包含在 label2cid 中的类别。
    """
    tracks = []
    for r in iter_results(task, "videorectangle"):
        v = r["value"]
        labs = v.get("labels") or []
        if not labs or labs[0] not in label2cid:
            continue
        cid = label2cid[labs[0]]
        segs = build_segments(v.get("sequence", []))
        if segs:
            tracks.append((cid, segs))
    return tracks


def build_segments(seq):
    """把关键帧序列拆成可见插值区间 [(f0, box0, f1, box1), ...]。"""
    seq = sorted(seq, key=lambda s: s["frame"])
    segs = []
    for a, b in zip(seq, seq[1:]):
        if a.get("enabled", True):
            segs.append((a["frame"], a, b["frame"], b))
    if seq and seq[-1].get("enabled", True):  # 末关键帧若在场,补单帧区间
        last = seq[-1]
        segs.append((last["frame"], last, last["frame"], last))
    return segs


def aabb_of_rotated_rect(x, y, w, h, rotation):
    """Compute axis-aligned bounding box of a rotated rectangle.

    LS bbox is (x, y, w, h) in percentage units (0-100), with rotation
    ``rotation`` in radians counter-clockwise around the centre.

    Returns (aabb_x, aabb_y, aabb_w, aabb_h) — still LS percentage units.
    For zero rotation this is identical to the input.
    """
    if abs(rotation) < 1e-9:
        return (x, y, w, h)

    cx = x + w / 2.0
    cy = y + h / 2.0
    hw = w / 2.0
    hh = h / 2.0

    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)

    # Four rotated corner offsets relative to centre
    corners = [
        (-hw * cos_r - (-hh) * sin_r,  -hw * sin_r + (-hh) * cos_r),
        ( hw * cos_r - (-hh) * sin_r,   hw * sin_r + (-hh) * cos_r),
        ( hw * cos_r -   hh  * sin_r,   hw * sin_r +   hh  * cos_r),
        (-hw * cos_r -   hh  * sin_r,  -hw * sin_r +   hh  * cos_r),
    ]

    xs = [cx + dx for dx, _ in corners]
    ys = [cy + dy for _, dy in corners]

    x_min = min(xs)
    y_min = min(ys)
    return (x_min, y_min, max(xs) - x_min, max(ys) - y_min)


def box_at(segs, frame):
    """Interpolated axis-aligned bounding box at ``frame``.

    Handles rotated keyframes by computing the AABB of the interpolated
    rotated rectangle so that the result is always axis-aligned (YOLO
    compatible).

    Returns (x, y, w, h) as LS percentages, or None when not visible.
    """
    for f0, b0, f1, b1 in segs:
        if f0 <= frame <= f1:
            t = 0.0 if f1 == f0 else (frame - f0) / (f1 - f0)
            x = b0["x"] + (b1["x"] - b0["x"]) * t
            y = b0["y"] + (b1["y"] - b0["y"]) * t
            w = b0["width"] + (b1["width"] - b0["width"]) * t
            h = b0["height"] + (b1["height"] - b0["height"]) * t
            r0 = b0.get("rotation", 0.0)
            r1 = b1.get("rotation", 0.0)
            rotation = r0 + (r1 - r0) * t

            if abs(rotation) < 1e-9:
                return (x, y, w, h)

            return aabb_of_rotated_rect(x, y, w, h, rotation)
    return None


def to_yolo(x, y, w, h):
    """LS 左上角百分比 -> YOLO 归一化中心点,裁剪到 [0,1]。"""
    cx = (x + w / 2) / 100.0
    cy = (y + h / 2) / 100.0
    nw = w / 100.0
    nh = h / 100.0
    clamp = lambda v: max(0.0, min(1.0, v))
    return clamp(cx), clamp(cy), clamp(nw), clamp(nh)


def collect_tracks(task, label2group):
    """收集 task 内所有目标轨迹: [(group, class_id, segments), ...](仅分组内类别)。"""
    tracks = []
    for r in iter_results(task, "videorectangle"):
        v = r["value"]
        labs = v.get("labels") or []
        if not labs or labs[0] not in label2group:
            continue
        g, cid = label2group[labs[0]]
        segs = build_segments(v.get("sequence", []))
        if segs:
            tracks.append((g, cid, segs))
    return tracks


def fps_scale(cap_fps, framesCount, duration):
    """真实帧号 -> LS 帧号 的比例 scale = ls_fps / real_fps。"""
    ls_fps = (framesCount / duration) if (framesCount and duration) else cap_fps
    return (ls_fps / cap_fps) if cap_fps else 1.0, ls_fps


# ---------------------------------------------------------------------------
#  Phase (timelinelabels) helpers
# ---------------------------------------------------------------------------

def iter_phase_ranges(task):
    """Yield (start_frame, end_frame, phase_name) for every timeline range.

    Frame numbers are in LS annotation frame space (same as keyframe
    ``frame`` values).
    """
    for r in iter_results(task, "timelinelabels"):
        v = r.get("value", {})
        ranges = v.get("ranges", [])
        labels = v.get("timelinelabels", [])
        if len(ranges) == len(labels):
            for rng, phase in zip(ranges, labels):
                yield rng["start"], rng["end"], phase
        else:
            # defensive: assign all ranges to each label
            for rng in ranges:
                for phase in labels:
                    yield rng["start"], rng["end"], phase


def build_phase_map(task):
    """Build mapping: LS frame number → phase name.

    Frames not covered by any phase range are absent from the dict.
    Ranges may overlap — later ranges overwrite earlier ones.
    """
    phase_map = {}
    for start, end, phase in iter_phase_ranges(task):
        for f in range(int(start), int(end) + 1):
            phase_map[f] = phase
    return phase_map


def get_phase_for_frame(phase_map, ls_frame):
    """Return the phase name an LS frame belongs to, or None."""
    return phase_map.get(int(round(ls_frame)))


def collect_task_phases(task):
    """Return sorted set of unique phase names appearing in *task*."""
    phases = set()
    for _, _, phase in iter_phase_ranges(task):
        phases.add(phase)
    return sorted(phases)


def collect_det_labels(task):
    """Return sorted set of unique detection (videorectangle) label names."""
    labels = set()
    for r in iter_results(task, "videorectangle"):
        for lab in r.get("value", {}).get("labels", []):
            labels.add(lab)
    return sorted(labels)
