#!/usr/bin/env python3
"""
推送前数据集校验卡口 —— CLI 入口（核心逻辑见 utils/check.py）。

用法:
    python3 05_check.py                          # 校验所有已构建的数据集
    python3 05_check.py --group group1_large     # 只校验指定 group
    python3 05_check.py --phase long_brush_insert # 只校验指定 phase
    python3 05_check.py --json                   # JSON 格式输出（供 CI 消费）
    python3 05_check.py --no-images              # 跳过图像解码抽查（加速）
    python3 05_check.py --strict                 # 警告也按失败处理

供 upload 脚本集成:
    from utils.check import check_dataset, CheckResult
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from utils.check import check_dataset, print_result, CheckResult

PKG_ROOT = Path(__file__).resolve().parent
DATASETS = PKG_ROOT / "datasets"
DATASETS_ACTIONSEQ = PKG_ROOT / "datasets_actionseq"


def _discover() -> list[tuple[Path, str]]:
    """自动发现 datasets/ 和 datasets_actionseq/ 下所有含 data.yaml 的子目录。"""
    items: list[tuple[Path, str]] = []
    for base, prefix in [(DATASETS, "Group"), (DATASETS_ACTIONSEQ, "ActionSequence")]:
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "data.yaml").exists():
                items.append((d, f"{prefix}/{d.name}"))
    return items


def main(argv: Optional[list[str]] = None) -> dict[str, CheckResult]:
    parser = argparse.ArgumentParser(
        description="推送前数据集校验卡口（纯数据级，不依赖训练权重）"
    )
    parser.add_argument("--group", metavar="NAME", help="只校验 datasets/ 下的指定 group")
    parser.add_argument("--phase", metavar="NAME", help="只校验 datasets_actionseq/ 下的指定 phase")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--no-images", action="store_true", help="跳过图像解码抽查")
    parser.add_argument("--strict", action="store_true", help="严格模式：warnings 升级为 errors")
    parser.add_argument("--quiet", action="store_true", help="PASS 的仅显示结论")
    args = parser.parse_args(argv)

    # 收集待校验项
    check_items: list[tuple[Path, str]] = []
    if args.phase:
        d = DATASETS_ACTIONSEQ / args.phase
        check_items.append((d, f"ActionSequence/{args.phase}"))
    elif args.group:
        d = DATASETS / args.group
        check_items.append((d, f"Group/{args.group}"))
    else:
        check_items = _discover()

    if not check_items:
        print("未找到可校验的数据集（含 data.yaml 的子目录）。")
        print("先跑: python3 02_build_dataset.py [--auto-assign]")
        print(" 或:  python3 02_build_actionseq.py [--auto-assign]")
        sys.exit(1)

    # 执行
    results: dict[str, CheckResult] = {}
    for dataset_dir, name in check_items:
        r = check_dataset(dataset_dir, name, check_images_flag=not args.no_images,
                          pkg_root=PKG_ROOT)
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
