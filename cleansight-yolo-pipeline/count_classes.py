#!/usr/bin/env python3
"""统计 yolo / actionmixed / actionseq 三类数据集中各类样本数量。"""
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent


def parse_names(yaml_path):
    """从 data.yaml 解析 {id: name}。"""
    names = {}
    text = yaml_path.read_text(encoding="utf-8")
    cur = None
    for line in text.splitlines():
        m = re.match(r"\s*(\d+):\s*(\S+)", line)
        if m:
            names[int(m.group(1))] = m.group(2)
    return names


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
print("\n" + "#" * 56)
print("# 1. YOLO 数据集 (datasets/) — 目标检测 bbox 实例")
print("#" * 56)
yolo_root = ROOT / "datasets"
for grp in sorted(d.name for d in yolo_root.iterdir() if d.is_dir()):
    gdir = yolo_root / grp
    yaml = gdir / "data.yaml"
    if not yaml.exists():
        continue
    names = parse_names(yaml)
    agg = defaultdict(int)
    nfiles = 0
    for split in ("train", "val", "test"):
        c, nf = count_bbox(gdir / "labels" / split, names)
        for k, v in c.items():
            agg[k] += v
        nfiles += nf
    report(f"[YOLO/{grp}]  ({len(names)} 类)", names, agg, "bbox", nfiles)


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

# ============ 3. actionseq 数据集 ============
print("\n" + "#" * 56)
print("# 3. actionseq 数据集 (datasets_actionseq/) — 每动作一目录")
print("#" * 56)
asq = ROOT / "datasets_actionseq"

# 3a. 每个动作目录的图像/样本数
print(f"\n--- [actionseq] 各动作类样本数(图像数, train+val+test) ---")
print(f"{'动作类别':<26}{'train':<10}{'val':<10}{'test':<10}{'合计':<10}")
print("-" * 56)
action_totals = []
for act in sorted(d.name for d in asq.iterdir() if d.is_dir()):
    adir = asq / act
    if not (adir / "data.yaml").exists():
        continue
    per = {}
    for split in ("train", "val", "test"):
        per[split] = count_images(adir / "images" / split)
    tot = sum(per.values())
    action_totals.append((act, per, tot))
    print(f"{act:<26}{per['train']:<10}{per['val']:<10}{per['test']:<10}{tot:<10}")
gtot = sum(t for _, _, t in action_totals)
print("-" * 56)
print(f"{'合计':<26}{'':<30}{gtot:<10}")

# 3b. 每个动作目录内的目标检测 bbox 分布
names8 = parse_names(asq / "short_brush_cleaning" / "data.yaml")
for act, per, tot in action_totals:
    adir = asq / act
    agg = defaultdict(int)
    nfiles = 0
    for split in ("train", "val", "test"):
        c, nf = count_bbox(adir / "labels" / split, names8)
        for k, v in c.items():
            agg[k] += v
        nfiles += nf
    report(f"[actionseq/{act}] bbox (图像 {tot})", names8, agg, "bbox", nfiles)
