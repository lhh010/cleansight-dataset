#!/usr/bin/env python3
"""
训练轨 build:LS 项目 yolo-train 的导出 + 视频 -> YOLO 检测集的 train/val。

配置与清单全在 yolo/train.yaml(数据源、产物路径、抽帧参数、在册 task 及其 split),
类别在 yolo/classes.yaml。构建逻辑见 yolo/builder.py —— 两轨共用引擎。

在册 = 已人工质检 + 已定 split。不在册的 task 一律跳过。登记以 **LS task id** 为键
(视频文件名会随 LS 重传而变,task id 不会)。

benchmark 的 test 由 yolo/build_test.py 从独立的 yolo-test 项目构建,与本脚本零交集。

用法(在 cleansight-pipeline/ 下执行):
    python3 yolo/build.py
    python3 yolo/build.py --auto-assign   # 未登记 task 当场确定性回填并写回 train.yaml
    python3 yolo/build.py --force         # 全量重建
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yolo import builder, manifest   # noqa: E402

if __name__ == "__main__":
    builder.run(manifest.TRAIN_MANIFEST, sys.argv[1:],
                splits=("train", "val"), allow_assign=True, title="训练轨(train/val)")
