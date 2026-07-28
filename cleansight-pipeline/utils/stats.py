#!/usr/bin/env python3
"""
数据集生成后的样本分布统计(训练帧粒度)。

纯扫描落盘的 label 文件(<组>/labels/<split>/*.txt),不解码视频、不需 torch,
因此统计是"生成完毕的数据集"的纯函数:可信、可随时独立重算(不必重建)。

  - 帧数 = label 文件数(一帧一文件);框数 = 所有文件的行数之和;class_id = 每行首列。
  - 逐类给出各 split 的帧数/框数,并对空 split、某类某 split 无样本给出提示。

split 名与目录位置由调用方传入(来自各数据集的 yaml),本模块不含字面量。
"""
from collections import defaultdict


def scan_group(group_dir, splits):
    """扫描一个组的 labels/,返回 {split: {frames, boxes, cls_frames, cls_boxes}}。"""
    out = {}
    for split in splits:
        d = group_dir / "labels" / split
        frames = boxes = 0
        cls_frames = defaultdict(int)
        cls_boxes = defaultdict(int)
        for txt in sorted(d.glob("*.txt")) if d.exists() else []:
            frames += 1
            seen = set()
            for line in txt.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                cid = int(line.split()[0])
                boxes += 1
                cls_boxes[cid] += 1
                seen.add(cid)
            for cid in seen:
                cls_frames[cid] += 1
        out[split] = {"frames": frames, "boxes": boxes,
                      "cls_frames": cls_frames, "cls_boxes": cls_boxes}
    return out


def print_distribution(group, class_names, group_dir, splits):
    """打印一个组逐类 × 逐 split 的帧/框分布 + 提示。返回扫描结果 dict。"""
    st = scan_group(group_dir, splits)

    head = "".join(f"{s + '帧':>9}" for s in splits) + "".join(f"{s + '框':>9}" for s in splits)
    width = 24 + 18 * len(splits)
    print(f"\n=== 样本分布 · {group}  (训练帧粒度,扫描 {group_dir}/labels) ===")
    print(f"{'类别':<22}{head}")
    print("-" * width)
    for cid, name in enumerate(class_names):
        cells = "".join(f"{st[s]['cls_frames'].get(cid, 0):>9}" for s in splits)
        cells += "".join(f"{st[s]['cls_boxes'].get(cid, 0):>9}" for s in splits)
        print(f"{name:<22}{cells}")
    print("-" * width)
    totals = "".join(f"{st[s]['frames']:>9}" for s in splits)
    totals += "".join(f"{st[s]['boxes']:>9}" for s in splits)
    print(f"{'合计(帧/框)':<22}{totals}")

    warns = []
    for s in splits:
        if st[s]["frames"] == 0:
            warns.append(f"{s} 为空")
    for cid, name in enumerate(class_names):
        per = {s: st[s]["cls_frames"].get(cid, 0) for s in splits}
        if sum(per.values()) == 0:
            warns.append(f"类别 {name} 在所有 split 都无样本")
        else:
            for s in splits:
                if per[s] == 0:
                    warns.append(f"类别 {name} 在 {s} 无样本")
    for w in warns:
        print(f"  [WARN] {w}")
    return st
