#!/usr/bin/env python3
"""
benchmark 轨 build:LS 项目 yolo-test 的导出 + 视频 -> YOLO 检测集的 test。

配置与清单全在 yolo/test.yaml。构建逻辑见 yolo/builder.py —— 与训练轨共用引擎,
差异全部由 yaml 表达(保留空帧作负样本、不做稀有类密采、split 恒为 test)。

与训练轨的本质区别:这是**策展**的评测集,不是从训练池随机 hold-out。
  - 源级隔离:在册 task 的整条源不进 train/val(assert_disjoint 断言两表零交集;
    源头就是两个独立 LS 项目)。
  - 冻结:test.yaml 的 frozen_at 非空后只增不改。
  - **没有 --auto-assign**:选哪条片当评测集是人工策展决策,不能被确定性回填代劳。

用法(在 cleansight-pipeline/ 下执行):
    python3 yolo/build_test.py
    python3 yolo/build_test.py --force
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yolo import builder, manifest   # noqa: E402

if __name__ == "__main__":
    builder.run(manifest.TEST_MANIFEST, sys.argv[1:],
                splits=("test",), allow_assign=False, title="benchmark 轨(test)")
