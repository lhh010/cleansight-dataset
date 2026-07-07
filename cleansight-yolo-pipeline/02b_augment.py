#!/usr/bin/env python3
"""
稀有类别数据增强 —— 对样本量不足的类别做随机仿射变换，生成增强副本。

增强策略（仅针对包含稀有类别的帧）：
  - 随机旋转 [-15°, +15°]，变换后 bbox 取 AABB（保持 YOLO 兼容）
  - 随机缩放 [0.85, 1.15]
  - 随机水平翻转（可选，默认关闭——内镜场景左右有意义）
  - 每帧默认生成 3 个增强副本（可配置）

用法（在 cleansight-yolo-pipeline/ 下执行）：
    python3 02b_augment.py
    python3 02b_augment.py --dry-run        # 只统计，不生成
    python3 02b_augment.py --threshold 30   # 自定义稀有阈值（默认 50 框）
    python3 02b_augment.py --copies 5       # 每帧增强副本数（默认 3）
"""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from utils.common import ROOT, load_config

OUT_ROOT = ROOT / "datasets"

# 可配置的稀有阈值：某类总框数 < RARE_THRESHOLD 即触发增强
RARE_THRESHOLD = 50
# 每个稀有帧生成的增强副本数
AUG_COPIES = 3


def scan_dataset(group_dir, class_names, rare_threshold=RARE_THRESHOLD):
    """扫描一个 group，返回 {
        'total_boxes_per_class': {cid: count},
        'rare_classes': set(cid),
        'frames': [(split, img_path, label_path, rare_cids_in_this_frame)]
    }.
    """
    total_boxes = defaultdict(int)
    frame_records = []  # (split, img_path, label_path)

    for split in ("train", "val", "test"):
        img_dir = group_dir / "images" / split
        lbl_dir = group_dir / "labels" / split
        if not img_dir.exists():
            continue
        for img_path in sorted(img_dir.glob("*.jpg")):
            # 跳过已增强的文件
            if "_aug" in img_path.stem:
                continue
            txt_path = lbl_dir / f"{img_path.stem}.txt"
            if not txt_path.exists():
                continue
            lines = [
                l.strip() for l in txt_path.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
            for line in lines:
                cid = int(line.split()[0])
                total_boxes[cid] += 1
            frame_records.append((split, img_path, txt_path, lines))

    rare_classes = {cid for cid, cnt in total_boxes.items() if cnt < rare_threshold}
    return {
        "total_boxes_per_class": dict(total_boxes),
        "rare_classes": rare_classes,
        "frames": frame_records,
    }


def parse_yolo_line(line):
    """'cid cx cy w h' -> (cid, cx, cy, w, h)."""
    parts = line.strip().split()
    return int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])


def format_yolo_line(cid, cx, cy, w, h):
    return f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def yolo_corners(cx, cy, w, h):
    """归一化中心点 -> 四个角点 (归一化坐标)。"""
    hw, hh = w / 2, h / 2
    return np.array([
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
    ], dtype=np.float32)


def corners_to_yolo(corners):
    """四个角点 (归一化坐标) -> (cx, cy, w, h) 即 AABB。"""
    x_min, y_min = corners.min(axis=0)
    x_max, y_max = corners.max(axis=0)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w = x_max - x_min
    h = y_max - y_min
    return cx, cy, w, h


def augment_one(image, bgr=True):
    """对一张图像做一次随机增强，返回 (augmented_image, M_inv)。

    M_inv 是 2×3 矩阵，把原始归一化坐标映射到增强后图像的归一化坐标。
    实际做法：在像素空间做变换，然后反向计算坐标映射。

    具体:
      1. 构建变换 M (像素空间): 旋转 + 缩放 + 平移
      2. 对图像做 warpAffine
      3. 返回 M 用于 bbox 坐标映射
    """
    h, w = image.shape[:2]

    # 随机参数
    angle = random.uniform(-15, 15)
    scale = random.uniform(0.85, 1.15)

    # 旋转+缩放的变换矩阵（绕图像中心）
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, scale)

    # warp
    augmented = cv2.warpAffine(image, M, (w, h),
                               flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REFLECT_101)

    return augmented, M


def transform_bbox(cx, cy, bw, bh, M, img_w, img_h):
    """计算增强后的 AABB。

    M: 2×3 像素空间变换矩阵 (从原始→增强)。
    步骤: 归一化 → 像素 → 变换 → 归一化 → AABB。
    """
    # 归一化 → 像素
    corners_norm = yolo_corners(cx, cy, bw, bh)  # shape (4,2), 归一化
    corners_pix = corners_norm * np.array([img_w, img_h], dtype=np.float32)  # (4,2), 像素

    # 变换
    ones = np.ones((4, 1), dtype=np.float32)
    corners_pix_h = np.hstack([corners_pix, ones])  # (4,3)
    transformed = corners_pix_h @ M.T  # (4,2), 增强后像素坐标

    # 像素 → 归一化
    transformed_norm = transformed / np.array([img_w, img_h], dtype=np.float32)

    # 裁剪到 [0,1]
    transformed_norm = np.clip(transformed_norm, 0.0, 1.0)

    # 取 AABB
    new_cx, new_cy, new_w, new_h = corners_to_yolo(transformed_norm)

    # 过滤退化框
    if new_w < 0.002 or new_h < 0.002:
        return None
    return new_cx, new_cy, new_w, new_h


def main():
    cfg = load_config()
    groups = cfg["groups"]

    threshold = RARE_THRESHOLD
    copies = AUG_COPIES
    dry_run = "--dry-run" in sys.argv
    jpg_q = cfg.get("jpg_quality", 90)

    # 解析命令行参数
    for arg in sys.argv[1:]:
        if arg.startswith("--threshold="):
            threshold = int(arg.split("=")[1])
        elif arg.startswith("--copies="):
            copies = int(arg.split("=")[1])

    print(f"稀有阈值: < {threshold} 框  每帧增强副本: {copies}")
    if dry_run:
        print("[dry-run] 只统计，不生成文件")

    total_augmented = 0

    for g, class_names in groups.items():
        group_dir = OUT_ROOT / g
        if not group_dir.exists():
            print(f"\n[skip] {g}: 数据集目录不存在")
            continue

        info = scan_dataset(group_dir, class_names, rare_threshold=threshold)
        rare = info["rare_classes"]
        total_per_class = info["total_boxes_per_class"]

        print(f"\n=== {g} ===")
        for cid, name in enumerate(class_names):
            cnt = total_per_class.get(cid, 0)
            marker = " <-- RARE" if cid in rare else ""
            print(f"  {name}: {cnt} 框{marker}")

        if not rare:
            print("  无稀有类别，跳过")
            continue

        rare_names = [class_names[c] for c in sorted(rare)]
        print(f"  稀有类别: {', '.join(rare_names)}")

        # 筛选包含稀有类别的帧
        rare_frames = []
        for split, img_path, txt_path, lines in info["frames"]:
            rare_in_frame = set()
            all_bboxes = []
            for line in lines:
                cid, cx, cy, w, h = parse_yolo_line(line)
                all_bboxes.append((cid, cx, cy, w, h))
                if cid in rare:
                    rare_in_frame.add(cid)
            if rare_in_frame:
                rare_frames.append((split, img_path, txt_path, all_bboxes, rare_in_frame))

        print(f"  含稀有类别的帧: {len(rare_frames)}")

        if dry_run:
            continue

        # 生成增强副本
        aug_count = 0
        random.seed(42)  # 可复现

        for split, img_path, txt_path, all_bboxes, rare_in_frame in rare_frames:
            # cv2.imread 不支持中文路径，用 imdecode 绕过
            raw = np.fromfile(str(img_path), dtype=np.uint8)
            image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            if image is None:
                continue
            img_h, img_w = image.shape[:2]

            for aug_i in range(copies):
                aug_img, M = augment_one(image)

                # 变换所有 bbox（不只是稀有类别——保持标注完整性）
                new_lines = []
                valid = True
                for cid, cx, cy, bw, bh in all_bboxes:
                    result = transform_bbox(cx, cy, bw, bh, M, img_w, img_h)
                    if result is None:
                        continue
                    new_cx, new_cy, new_w, new_h = result
                    new_lines.append(format_yolo_line(cid, new_cx, new_cy, new_w, new_h))

                if not new_lines:
                    continue  # 增强后所有框退化

                # 保存
                stem = img_path.stem
                aug_stem = f"{stem}_aug{aug_i}"
                out_img = group_dir / "images" / split / f"{aug_stem}.jpg"
                out_lbl = group_dir / "labels" / split / f"{aug_stem}.txt"

                ok, buf = cv2.imencode(".jpg", aug_img, [cv2.IMWRITE_JPEG_QUALITY, jpg_q])
                if ok:
                    buf.tofile(str(out_img))
                out_lbl.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                aug_count += 1

        print(f"  生成增强副本: {aug_count}")
        total_augmented += aug_count

    if not dry_run:
        print(f"\n总共生成 {total_augmented} 张增强图像。")
        print("下一步:03_train.py / 04_validate.py")


if __name__ == "__main__":
    main()
