#!/usr/bin/env python3
"""统计 yolo / actionmixed 两类数据集中各类样本数量。

yolo 侧的产物路径来自 yolo/train.yaml,split 从各组 data.yaml 现读(数据集自己
声明布局);actionmixed 侧暂沿用固定布局。
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yolo import manifest

ROOT = Path(__file__).resolve().parent.parent   # common/ 的上一级 = pipeline 根


def parse_names(yaml_path):
    """从 data.yaml 解析 {id: name}。"""
    names = {}
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d+):\s*(\S+)", line)
        if m:
            names[int(m.group(1))] = m.group(2)
    return names


def parse_splits(yaml_path):
    """从 data.yaml 解析声明了哪些 split(形如 `train: images/train`)。"""
    splits = []
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\w+):\s*images/(\S+)\s*$", line)
        if m:
            splits.append(m.group(1))
    return splits


def count_bbox(label_dir, names):
    """YOLO bbox 标签：每行 class_id ... → 每类实例数 + 标签文件数。"""
    counts = defaultdict(int)
    nfiles = 0
    for f in sorted(label_dir.glob("*.txt")):
        nfiles += 1
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if parts and parts[0].lstrip("-").isdigit():
                counts[int(parts[0])] += 1
    return counts, nfiles


def count_action_frames(label_dir):
    """动作标签：每行 frame_id action_id → 每类帧数 + 标签文件数。"""
    counts = defaultdict(int)
    nfiles = 0
    for f in sorted(label_dir.glob("*.txt")):
        nfiles += 1
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
                counts[int(parts[1])] += 1
    return counts, nfiles


def count_images(img_dir):
    return len(list(img_dir.glob("*.jpg")))


def pct(c, total):
    return f"{c / total * 100:.1f}%" if total else "0.0%"


def report(title, names, counts, unit="实例", nfiles=None):
    print(f"\n{'=' * 56}\n{title}\n{'=' * 56}")
    total = sum(counts.values())
    rows = []
    for cid in sorted(names):
        c = counts.get(cid, 0)
        rows.append((cid, names[cid], c, pct(c, total)))
    # 缺失类（出现在统计但不在 names）
    for cid in sorted(counts):
        if cid not in names:
            rows.append((cid, f"(未定义#{cid})", counts[cid], pct(counts[cid], total)))
    print(f"{'class_id':<10}{'类别':<24}{unit:<10}{'占比':<8}")
    print("-" * 56)
    for cid, name, c, p in rows:
        print(f"{cid:<10}{name:<24}{c:<10}{p:<8}")
    extra = f"  | 标签文件 {nfiles}" if nfiles is not None else ""
    print(f"合计: {total} {unit}{extra}")
    return rows


# ============ 1. YOLO 数据集 ============
yolo_root = manifest.out_root(manifest.load(manifest.TRAIN_MANIFEST))
print("\n" + "#" * 56)
print(f"# 1. YOLO 数据集 ({yolo_root.name}/) — 目标检测 bbox 实例")
print("#" * 56)
if not yolo_root.is_dir():
    print(f"  {yolo_root} 不存在,先跑 yolo/build.py")
for grp in sorted(d.name for d in yolo_root.iterdir() if d.is_dir()) if yolo_root.is_dir() else []:
    gdir = yolo_root / grp
    yaml = gdir / "data.yaml"
    if not yaml.exists():
        continue
    names = parse_names(yaml)
    agg = defaultdict(int)
    nfiles = 0
    per_split = {}
    for split in parse_splits(yaml):
        c, nf = count_bbox(gdir / "labels" / split, names)
        per_split[split] = sum(c.values())
        for k, v in c.items():
            agg[k] += v
        nfiles += nf
    report(f"[YOLO/{grp}]  ({len(names)} 类)", names, agg, "bbox", nfiles)
    print("  逐 split: " + "  ".join(f"{s}={n}" for s, n in per_split.items()))


# ============ 2. actionmixed 数据集 ============
print("\n" + "#" * 56)
print("# 2. actionmixed 数据集 (datasets_actionmixed/)")
print("#" * 56)
am = ROOT / "datasets_actionmixed"

# 2a. frames/ 目标检测
fnames = parse_names(am / "frames" / "data.yaml")
agg = defaultdict(int)
nfiles = 0
for split in ("train", "val", "test"):
    c, nf = count_bbox(am / "frames" / split, fnames)
    for k, v in c.items():
        agg[k] += v
    nfiles += nf
report("[actionmixed/frames] 目标检测 bbox", fnames, agg, "bbox", nfiles)

# 2b. labels/ 动作分类
anames = parse_names(am / "labels" / "data.yaml")
agg = defaultdict(int)
nfiles = 0
for split in ("train", "val", "test"):
    c, nf = count_action_frames(am / "labels" / split)
    for k, v in c.items():
        agg[k] += v
    nfiles += nf
report("[actionmixed/labels] 动作分类 (逐帧)", anames, agg, "帧", nfiles)
