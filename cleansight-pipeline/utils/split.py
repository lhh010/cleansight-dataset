#!/usr/bin/env python3
"""
确定性切分的**纯函数** —— 只提供"给定键算出稳定的桶",不知道 split 叫什么名字。

原先本模块还兼管 splits.yaml 的读写(视频 stem -> split)。yolo 与 actionmixed 的
数据源分离后,per-video 清单下沉到了各数据集自己的配置里(yolo 见 yolo/manifest.py),
共享的只剩下面两个纯函数,split 名称一律由各自的 yaml 决定。

稳定切分的性质(不可退化):
  - 同一个键永远同一个桶,可复现。
  - 新增条目不打乱已有分配(增量友好)。
  - 人工可覆盖 —— 清单里写死的值永不被自动重排。
"""
import hashlib
from pathlib import Path


def stem_of(name: str) -> str:
    """视频文件名 -> 去扩展名的 stem。"""
    return Path(name).stem


def deterministic_bucket(key: str, seed) -> int:
    """hash(seed:key) -> 0..99 的确定性桶。切点与 split 名由调用方按配置决定。"""
    h = hashlib.sha1(f"{seed}:{key}".encode("utf-8")).hexdigest()
    return int(h, 16) % 100


def deterministic_split(key: str, seed, val_ratio: float, test_ratio: float = 0.0) -> str:
    """三路切分的便捷封装(test/val/train),供仍用固定 split 名的调用方使用。"""
    bucket = deterministic_bucket(key, seed)
    test_cutoff = round(test_ratio * 100)
    val_cutoff = test_cutoff + round(val_ratio * 100)
    if bucket < test_cutoff:
        return "test"
    if bucket < val_cutoff:
        return "val"
    return "train"
