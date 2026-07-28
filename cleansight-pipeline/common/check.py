#!/usr/bin/env python3
"""
推送前数据集校验卡口 —— CLI 入口（核心逻辑见 utils/check.py）。

判据按轨传入，不是一套逻辑套所有 split：
  - 训练轨（train/val）：关心**数据量与分布** —— train:val 比例、每类 val 必须有样本
    （否则该类无法评估，判 error）。比例取自 yolo/train.yaml 的 assign.ratios。
  - benchmark（test）：是**策展**的，按比例查它没有意义，所以不参与比例检查；
    每类覆盖只 warn。它的达标口径（覆盖率？每桶最少样本？）尚未定稿。

用法:
    python3 common/check.py                          # 校验所有已构建的数据集
    python3 common/check.py --group group1_large     # 只校验指定 group
    python3 common/check.py --json                   # JSON 格式输出（供 CI 消费）
    python3 common/check.py --no-images              # 跳过图像解码抽查（加速）
    python3 common/check.py --strict                 # 警告也按失败处理

供 upload 脚本集成:
    from utils.check import check_dataset, CheckResult
    from common.check import yolo_criteria
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# --- 从子目录运行时也能 import 顶层 utils/ ---
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.check import check_dataset, print_result, CheckResult
from yolo import manifest

PKG_ROOT = Path(__file__).resolve().parent.parent


def yolo_criteria() -> dict:
    """yolo 数据集的校验判据（喂给 utils.check.check_dataset 的 kwargs）。

    比例期望只覆盖训练轨的 split：分母是 train+val，test 完全不参与 —— 它是
    策展出来的 benchmark，帧数多少由等价类覆盖决定，不该被比例约束。
    """
    m = manifest.load(manifest.TRAIN_MANIFEST)
    ratios = dict((m.get("assign") or {}).get("ratios") or {})
    train_splits = ("train", "val")
    named = {s: float(ratios.get(s, 0)) for s in train_splits[1:]}
    named[train_splits[0]] = max(0.0, 1.0 - sum(named.values()))
    return {"ratio_expectations": named, "required_splits": {"val"}}


def datasets_root() -> Path:
    return manifest.out_root(manifest.load(manifest.TRAIN_MANIFEST))


def _discover(datasets: Path) -> list[tuple[Path, str]]:
    """自动发现数据集根下所有含 data.yaml 的子目录。"""
    items: list[tuple[Path, str]] = []
    if datasets.is_dir():
        for d in sorted(datasets.iterdir()):
            if d.is_dir() and (d / "data.yaml").exists():
                items.append((d, f"Group/{d.name}"))
    return items


def main(argv: Optional[list[str]] = None) -> dict[str, CheckResult]:
    parser = argparse.ArgumentParser(
        description="推送前数据集校验卡口（纯数据级，不依赖训练权重）"
    )
    parser.add_argument("--group", metavar="NAME", help="只校验 datasets/ 下的指定 group")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--no-images", action="store_true", help="跳过图像解码抽查")
    parser.add_argument("--strict", action="store_true", help="严格模式：warnings 升级为 errors")
    parser.add_argument("--quiet", action="store_true", help="PASS 的仅显示结论")
    args = parser.parse_args(argv)

    # 收集待校验项
    datasets = datasets_root()
    check_items: list[tuple[Path, str]] = []
    if args.group:
        d = datasets / args.group
        check_items.append((d, f"Group/{args.group}"))
    else:
        check_items = _discover(datasets)

    if not check_items:
        print(f"未找到可校验的数据集（{datasets} 下含 data.yaml 的子目录）。")
        print("先跑: python3 yolo/build.py [--auto-assign] 和 python3 yolo/build_test.py")
        sys.exit(1)

    # 执行
    criteria = yolo_criteria()
    results: dict[str, CheckResult] = {}
    for dataset_dir, name in check_items:
        r = check_dataset(dataset_dir, name, check_images_flag=not args.no_images,
                          **criteria)
        if args.strict and r.warnings:
            r.errors.extend(r.warnings)
            r.warnings.clear()
        results[name] = r

    # 输出
    if args.json:
        output = {}
        for name, r in results.items():
            output[name] = {"passed": r.passed, "errors": r.errors, "warnings": r.warnings}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        any_fail = False
        for name, r in results.items():
            if not print_result(r, verbose=not args.quiet):
                any_fail = True
        print(f"\n{'=' * 60}")
        if any_fail:
            print("  结论: FAIL ❌ — 请修复上述问题后再推送")
            print(f"{'=' * 60}\n")
            sys.exit(2)
        else:
            print("  结论: 全部通过 ✅ — 可以推送至 ModelScope")
            print(f"{'=' * 60}\n")

    return results


if __name__ == "__main__":
    main()
