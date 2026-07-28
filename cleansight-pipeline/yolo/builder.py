#!/usr/bin/env python3
"""
构建引擎 —— 两轨(build.py 训练 / build_test.py benchmark)共用。

两轨的差异不写成 if 训练轨 / if benchmark 的分支,而是分成两类来源:

  可调的  -> yaml          数据源项目、产物路径、抽帧参数、在册 task 及其 split
  轨定义  -> 入口脚本传参   产出哪些 split、是否允许 --auto-assign

  差异             训练轨          benchmark 轨     来自
  --------------   -------------   --------------   ------------------------------
  数据源            yolo-train      yolo-test        yaml: source.projects
  空帧              丢弃            保留作负样本      yaml: sampling.keep_empty_frames
  稀有类密采         开              关               yaml: sampling.rare_dense_sampling
  产出 split        train / val     test             入口传参 splits=
  自动回填 split     允许            不允许            入口传参 allow_assign=

benchmark 不允许 --auto-assign,是因为选哪条片当评测集是**人工策展决策**,
不该被确定性回填代劳。
"""
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime

from utils import labelstudio, stats
from yolo import dataset as ds, frames, manifest


def _rare_labels(registered, label2group, threshold):
    """在册 task 里各类的 keyframe 总数 < threshold 即视为稀有类。"""
    counts = defaultdict(int)
    for _tid, task, _name, _split in registered:
        for r in labelstudio.iter_results(task, "videorectangle"):
            labs = r.get("value", {}).get("labels", [])
            if labs and labs[0] in label2group:
                counts[labs[0]] += len(r.get("value", {}).get("sequence", []))
    return {lab for lab, cnt in counts.items() if cnt < threshold}


def _fingerprint(obj) -> str:
    return hashlib.sha1(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


def _task_sig(task, split, samp_fp, rare) -> dict:
    """某个 task 的重建签名 —— 变了就重建,没变就跳过。

    刻意**不含导出文件名**:LS 每次导出的文件名都带时间戳,拿它当签名会让
    "放一份新导出"退化成全量重建 —— 增量在最常用的那个场景里恰好失效。
    改用该 task **自己标注内容**的指纹:纯 JSON 计算、不解码视频,
    只有这条 task 的标注真的改了才重建它。

    四个组成部分,少一个都会静默产出与配置不符的数据集:
      annotations — 标注本身
      sampling    — 全部抽帧/编码参数(stride、jpg_quality、空帧、密采阈值……)
      rare        — 稀有类集合。它由**全部在册 task 共同**决定,某类跨过阈值后,
                    已建好的 task 里那些密采帧就过时了,必须跟着重建
      split       — 归属。手工把清单里的 val 改成 train 时,帧要真的搬过去
    """
    return {
        "annotations": _fingerprint(task.get("annotations", [])),
        "sampling": samp_fp,
        "rare": sorted(rare),
        "split": split,
    }


def run(manifest_path, argv=(), *, splits, allow_assign=False, title=""):
    """构建一条轨。splits 是本轨产出的 split 元组(轨的定义,不是配置)。"""
    auto_assign = allow_assign and "--auto-assign" in argv
    force = "--force" in argv

    m = manifest.load(manifest_path)
    groups = manifest.load_classes()
    my_splits = list(splits)
    out_root = manifest.out_root(m)
    video_dir = manifest.video_dir(m)

    samp = manifest.sampling(m)
    stride = samp.get("stride", 4)
    jpg_q = samp.get("jpg_quality", 90)
    keep_empty = bool(samp.get("keep_empty_frames", False))
    empty_stride = int(samp.get("empty_frame_stride", 1))
    dense_enabled = bool(samp.get("rare_dense_sampling", False))
    rare_threshold = samp.get("rare_threshold", 0)

    completed_path = manifest.completed_path(m)
    tracking_path = manifest.tracking_path(m)

    manifest.assert_disjoint()

    print(f"=== {title} ===")
    if m.get("frozen_at"):
        print(f"[冻结] version={m.get('version')} frozen_at={m['frozen_at']} —— 清单只增不改")

    if not m.get("tasks"):
        print(f"清单 {manifest_path.name} 为空 —— 无在册 task,不构建任何产物。")
        print("在 LS 项目 " + ", ".join(manifest.projects(m))
              + " 完成标注与质检后,把 task id 登记进该清单。")
        return

    label2group = labelstudio.build_label_index(groups)
    tasks, export_names = manifest.load_tasks(m)
    registered, unregistered = manifest.resolve(m, tasks)

    print(f"项目: {', '.join(manifest.projects(m))}   导出: {', '.join(export_names)}")
    print(f"task: 导出 {len(tasks)} / 在册 {len(registered)} / 未登记 {len(unregistered)}"
          f"   产出 split: {', '.join(my_splits)}")

    if unregistered:
        if auto_assign:
            added = manifest.assign(m, [tid for tid, _ in unregistered], my_splits)
            n = manifest.append_tasks(m, added)
            print(f"[--auto-assign] 回填 {n} 条到 {manifest_path.name}: "
                  + ", ".join(f"task#{t}->{s}" for t, s in added))
            print("请 review 并提交该 yaml 的改动。")
            m = manifest.load(manifest_path)
            registered, unregistered = manifest.resolve(m, tasks)
        else:
            hint = ",或跑 --auto-assign 确定性回填" if allow_assign else ""
            print(f"\n[未登记] {len(unregistered)} 条 —— 质检后登记进 {manifest_path.name}{hint}:")
            for tid, name in unregistered:
                print(f"    task#{tid}  {name}")

    absent = manifest.missing(m, tasks)
    if absent:
        print("\n[在册但导出里没有] " + ", ".join(f"task#{t}" for t in absent)
              + " —— 导出过期,或 task 已在 LS 删除")

    # ---- 增量 ----
    completed = {}
    if force:
        print("[--force] 全量重建,清除已完成记录")
    elif completed_path.exists():
        completed = json.loads(completed_path.read_text(encoding="utf-8"))

    # 稀有类由**全部在册 task** 共同决定,所以必须先于增量判断算出来 ——
    # 它是每个 task 签名的一部分(见 _task_sig)。
    rare = _rare_labels(registered, label2group, rare_threshold) if dense_enabled else set()
    rare_cids = defaultdict(set)
    for lab in rare:
        g, cid = label2group[lab]
        rare_cids[g].add(cid)
    if dense_enabled:
        print(f"稀有类密采(< {rare_threshold} keyframes): {', '.join(sorted(rare)) or '无'}")
    if keep_empty:
        print(f"保留空帧作负样本(每 {empty_stride} 个候选留 1 个)")

    samp_fp = _fingerprint(samp)
    sigs = {}
    pending = []
    resolved = []
    for tid, task, name, split in registered:
        # 列表形态的清单不带 split(如 benchmark 轨恒为 test),用本轨唯一的那个填上
        split = split or my_splits[0]
        resolved.append((tid, task, name, split))
        if split not in my_splits:
            print(f"  [hold] task#{tid} {name}  split={split} 不在本轨产出范围")
            continue
        sig = _task_sig(task, split, samp_fp, rare)
        sigs[tid] = sig
        prev = completed.get(str(tid))
        if prev and all(prev.get(k) == v for k, v in sig.items()):
            print(f"  [skip] task#{tid} {name}(未变化)")
            continue
        if prev:
            changed = [k for k, v in sig.items() if prev.get(k) != v] or ["首次记录格式"]
            n = ds.clear_task(out_root, groups, tid)
            print(f"  [reprocess] task#{tid} {name}"
                  f"({'/'.join(changed)} 已变,清除旧产物 {n} 个文件)")
        pending.append((tid, task, name, split))
    registered = resolved

    ds.prepare_dirs(out_root, groups)
    ds.write_data_yaml(out_root, groups)

    emitted = 0
    task_stats = []

    for tid, task, name, split in pending:
        vpath = video_dir / name
        if not vpath.exists():
            print(f"  [warn] task#{tid} 视频不在磁盘: {name}")
            continue
        tracks = labelstudio.collect_tracks(task, label2group)
        if not tracks:
            print(f"  [warn] task#{tid} {name} 无可用检测框,跳过")
            continue

        total, real_fps = frames.video_meta(vpath)
        fc, dur = labelstudio.clip_meta(task)
        scale, _ls_fps = labelstudio.fps_scale(real_fps, fc, dur)
        print(f"  task#{tid} [{split}] {name}  {total}帧@{real_fps:.1f}fps  "
              f"tracks={len(tracks)}  stride={stride}")

        counts = defaultdict(int)
        empty_frames = 0
        dense_wanted = set()
        max_sampled = 0

        for fidx, frame, boxes in frames.iter_stride(
                vpath, tracks, scale, stride,
                keep_empty=keep_empty, empty_stride=empty_stride):
            max_sampled = fidx
            base = ds.frame_base(tid, fidx)
            if not boxes:
                empty_frames += 1
            # 空帧对每个组各落一份空标签(负样本);有框帧只落有该组框的组
            targets = boxes if boxes else {gname: [] for gname in groups}
            for g, bs in targets.items():
                ds.write_frame(out_root, g, split, base, frame, frames.fmt_lines(bs), jpg_q)
                emitted += 1
                counts[g] += 1
            if dense_enabled and any(
                    any(cid in rare_cids[g] for cid, *_ in bs) for g, bs in boxes.items()):
                half = stride - 1
                dense_wanted.update(
                    n for n in range(fidx - half, fidx + half + 1)
                    if n >= 1 and n != fidx and (n - 1) % stride != 0)

        dense_count = 0
        if dense_wanted:
            for fidx, frame, boxes in frames.read_at(
                    vpath, {n for n in dense_wanted if n <= total}, tracks, scale):
                base = ds.frame_base(tid, fidx, suffix="_dense")
                for g, bs in boxes.items():
                    ds.write_frame(out_root, g, split, base, frame,
                                   frames.fmt_lines(bs), jpg_q)
                    emitted += 1
                    counts[g] += 1
                    dense_count += 1

        cover = (max_sampled / total * 100) if total else 0
        extra = f"  空帧 {empty_frames}" if keep_empty else ""
        print(f"        stride 帧 {sum(counts.values()) - dense_count}  密采帧 {dense_count}"
              f"{extra}  覆盖 1..{max_sampled}/{total} ({cover:.0f}%)")
        if cover < 80:
            print(f"        [warn] 尾部覆盖仅 {cover:.0f}% —— 检查 fps 对齐"
                  f"(见 utils/labelstudio.py 的 fps_scale)")
        for g in sorted(counts):
            print(f"          {g}: {counts[g]} 帧")

        task_stats.append({
            "id": tid, "name": name, "split": split,
            "phases": labelstudio.collect_task_phases(task),
            "det_labels": labelstudio.collect_det_labels(task),
            "total_frames": total, "empty_frames": empty_frames,
            "counts": dict(counts),
        })

    for s in task_stats:
        completed[str(s["id"])] = dict(sigs[s["id"]], video=s["name"],
                                       export=export_names,
                                       completed_at=datetime.now().isoformat())
    completed_path.write_text(json.dumps(completed, indent=2, ensure_ascii=False),
                              encoding="utf-8")

    for g, class_names in groups.items():
        if (out_root / g).exists():
            stats.print_distribution(g, class_names, out_root / g, my_splits)

    print(f"\n本次落盘 {emitted} 张图。")
    _write_tracking(m, manifest_path, registered, task_stats, groups, my_splits,
                    out_root, export_names, tracking_path, title)
    print(f"{tracking_path.name} 已生成。")


def _write_tracking(m, manifest_path, registered, task_stats, groups, my_splits,
                    out_root, export_names, tracking_path, title):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    by_id = {s["id"]: s for s in task_stats}

    lines = [f"# CleanSight YOLO · {title}", "",
             f"**生成**: {now}",
             f"**清单**: {manifest_path.name}",
             f"**项目**: {', '.join(manifest.projects(m))}",
             f"**导出**: {', '.join(export_names)}"]
    if m.get("version"):
        lines.append(f"**版本**: {m['version']}"
                     + (f"(冻结于 {m['frozen_at']})" if m.get("frozen_at") else "(未冻结)"))
    lines += ["", "## 在册 task", "",
              "| LS Task | 视频 | Split | 本次构建 | 动作段 | 检测类 | 落盘帧 |",
              "|---------|------|-------|---------|--------|--------|--------|"]
    for tid, task, name, split in registered:
        st = by_id.get(tid)
        stem = name.rsplit(".", 1)[0][:35]
        if st:
            lines.append(f"| {tid} | {stem} | {split} | 是 | "
                         f"{', '.join(st['phases']) or '—'} | {len(st['det_labels'])} | "
                         f"{sum(st['counts'].values())} |")
        else:
            phases = ", ".join(labelstudio.collect_task_phases(task)) or "—"
            lines.append(f"| {tid} | {stem} | {split} | 否(增量跳过) | {phases} | "
                         f"{len(labelstudio.collect_det_labels(task))} | — |")

    lines += ["", "## 各组产出", "", "| 组 | Split | 图片 | 框 |", "|----|-------|------|-----|"]
    for g in groups:
        for sp in my_splits:
            imgs, boxes = ds.count_split(out_root, g, sp)
            if imgs:
                lines.append(f"| {g} | {sp} | {imgs} | {boxes} |")

    lines += ["", "## Split 分配", "", "| Split | Task |", "|-------|------|"]
    for sp in my_splits:
        tids = [str(tid) for tid, _t, _n, s in registered if s == sp]
        lines.append(f"| {sp} | {', '.join(tids) or '—'} |")

    lines += ["", "> 一个 task 的所有帧只进它的 split,杜绝时间相邻泄漏。",
              "> 帧名 `t{task_id}_{frame:06d}` —— 身份键是 LS task id,不随视频重传而变。",
              "> 旋转框自动转 AABB。"]
    tracking_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
