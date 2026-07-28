#!/usr/bin/env python3
"""
产物落盘布局 —— yolo 两轨(build.py / build_test.py)共享。

输出结构(路径与 split 名全部来自 yaml,本模块不含字面量):
  <out_root>/<组>/
    images/<split>/*.jpg
    labels/<split>/*.txt
    data.yaml

帧名 `t{task_id}_{frame:06d}`:身份键是 LS task id(全局唯一、重传视频也不变),
不含视频名和导出下标 —— 后者会随导出增删而重排,前者会随 LS 重传而变。
task id 全局唯一也意味着两轨天然不会撞名,不需要额外的轨前缀。
"""
from pathlib import Path

from PIL import Image

# YOLO 数据集的 split 布局 —— 结构约定,不是可调项,所以不进 yaml。
# data.yaml 声明全部三个(否则 validate 指不到 test);各轨实际产出哪一部分
# 是**轨的定义**(训练轨 train/val、benchmark 轨 test),由各入口脚本传入。
SPLITS = ("train", "val", "test")


def frame_base(tid, frame_idx, suffix="") -> str:
    """帧的落盘基名(不含扩展名)。suffix 用于区分密采帧等变体。"""
    return f"t{tid}_{frame_idx:06d}{suffix}"


def task_glob(tid) -> str:
    """匹配某 task 全部产物的 glob(重建前清理用)。"""
    return f"t{tid}_*"


def prepare_dirs(out_root, groups):
    """建全部 split 的目录(不清除已有文件,支持增量构建)。"""
    for g in groups:
        for s in SPLITS:
            (Path(out_root) / g / "images" / s).mkdir(parents=True, exist_ok=True)
            (Path(out_root) / g / "labels" / s).mkdir(parents=True, exist_ok=True)


def write_data_yaml(out_root, groups):
    """写各组的 data.yaml。

    声明**完整**的 split 布局而非本轨产出的那部分 —— 否则训练轨先跑就会写出一份
    没有 test: 的 data.yaml,validate 指不到 benchmark。两轨写出的内容因此完全一致,
    谁先跑谁写,幂等。
    """
    for g, labels in groups.items():
        names = "\n".join(f"  {i}: {lab}" for i, lab in enumerate(labels))
        paths = "\n".join(f"{s}: images/{s}" for s in SPLITS)
        (Path(out_root) / g / "data.yaml").write_text(
            f"path: .\n{paths}\nnc: {len(labels)}\nnames:\n{names}\n",
            encoding="utf-8",
        )


def write_frame(out_root, group, split, base, frame_bgr, lines, jpg_quality):
    """落一帧的图 + 标签。lines 为空时写空标签文件(空帧负样本)。"""
    out_root = Path(out_root)
    Image.fromarray(frame_bgr[:, :, ::-1]).save(
        str(out_root / group / "images" / split / f"{base}.jpg"), quality=jpg_quality)
    (out_root / group / "labels" / split / f"{base}.txt").write_text(
        ("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


def clear_task(out_root, groups, tid) -> int:
    """删掉某 task 在所有组/所有 split 下的产物,返回删除文件数。"""
    out_root = Path(out_root)
    pat = task_glob(tid)
    n = 0
    for g in groups:
        for s in SPLITS:
            for sub, ext in (("images", "jpg"), ("labels", "txt")):
                d = out_root / g / sub / s
                if not d.is_dir():
                    continue
                for f in d.glob(f"{pat}.{ext}"):
                    f.unlink()
                    n += 1
    return n


def count_split(out_root, group, split):
    """(图片数, 框数) —— tracking 表用。"""
    gdir = Path(out_root) / group
    img_dir, lbl_dir = gdir / "images" / split, gdir / "labels" / split
    imgs = len(list(img_dir.glob("*.jpg"))) if img_dir.is_dir() else 0
    boxes = 0
    if lbl_dir.is_dir():
        for txt in lbl_dir.glob("*.txt"):
            boxes += sum(1 for l in txt.read_text(encoding="utf-8").splitlines() if l.strip())
    return imgs, boxes
