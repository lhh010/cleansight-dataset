#!/usr/bin/env python3
"""
解码抽帧 —— yolo 两轨(build.py / build_test.py)共享的核心循环。

刻意放在 yolo/ 而不是 utils/:它服务的是"检测数据集怎么抽帧",不是通用的 LS 解析。
actionmixed 的抽帧口径(段级、带 idle padding)与此不同,两边各自实现,不强行抽象。

两轨的差异全部由参数表达,不在这里写 if 分支:
  - 训练轨: keep_empty=False(空帧丢弃,避免负样本稀释)
  - benchmark 轨: keep_empty=True + empty_stride(空帧作负样本,再稀释)
"""
import cv2

from utils import labelstudio


def boxes_at(tracks, ls_frame):
    """某个 LS 帧号上所有可见目标框,按组归并。

    tracks: [(group, class_id, segments), ...](labelstudio.collect_tracks 的产物)
    返回 {group: [(class_id, cx, cy, w, h), ...]},均为归一化坐标;无框时返回空 dict。
    """
    out = {}
    for g, cid, segs in tracks:
        box = labelstudio.box_at(segs, ls_frame)
        if box is None:
            continue
        cx, cy, w, h = labelstudio.to_yolo(*box)
        if w <= 0 or h <= 0:
            continue
        out.setdefault(g, []).append((cid, cx, cy, w, h))
    return out


def fmt_lines(boxes):
    """[(cid, cx, cy, w, h), ...] -> YOLO 标签行(每行 `cid cx cy w h`,归一化)。"""
    return [f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cid, cx, cy, w, h in boxes]


def iter_stride(vpath, tracks, scale, stride, *, keep_empty=False, empty_stride=1):
    """按 stride 顺序遍历视频,yield (frame_idx, frame_bgr, boxes_by_group)。

    frame_idx 是 1 起的**真实**帧号;查框用的 LS 帧号由 scale 换算
    (LS 帧号按标注端 fps 计,与真实 fps 常不同,见 utils/labelstudio.fps_scale)。

    keep_empty=False: 无框帧直接跳过,且**不解码**(只 grab 不 retrieve),省大量时间。
    keep_empty=True:  无框帧每 empty_stride 个留 1 个,boxes_by_group 为空 dict。
    """
    cap = cv2.VideoCapture(str(vpath))
    try:
        frame_idx = 0
        empty_seen = 0
        while True:
            if not cap.grab():
                break
            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue

            boxes = boxes_at(tracks, frame_idx * scale)
            if not boxes:
                if not keep_empty:
                    continue
                empty_seen += 1
                if empty_stride > 1 and (empty_seen - 1) % empty_stride != 0:
                    continue

            ok, frame = cap.retrieve()
            if not ok:
                continue
            yield frame_idx, frame, boxes
    finally:
        cap.release()


def read_at(vpath, frame_indices, tracks, scale):
    """随机定位读取指定真实帧号(稀有类密采用),yield (frame_idx, frame_bgr, boxes)。

    与 iter_stride 分开是因为它靠 seek 而非顺序解码 —— 只对少量帧划算。
    无框的帧不产出(密采的目的就是补框,空帧没有意义)。
    """
    cap = cv2.VideoCapture(str(vpath))
    try:
        for idx in sorted(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx - 1)   # LS/本模块 1 起,cv2 0 起
            ok, frame = cap.read()
            if not ok:
                continue
            boxes = boxes_at(tracks, idx * scale)
            if not boxes:
                continue
            yield idx, frame, boxes
    finally:
        cap.release()


def video_meta(vpath):
    """(总帧数, 真实 fps)。"""
    cap = cv2.VideoCapture(str(vpath))
    try:
        return int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0, cap.get(cv2.CAP_PROP_FPS) or 0.0
    finally:
        cap.release()
