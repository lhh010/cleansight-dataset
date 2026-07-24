# actionseq · 动作阶段数据集(cleansight-ActionSequence)

按 LS `timelinelabels` 把帧切进各**动作阶段**子集,每个 phase 是一个独立 YOLO 子数据集(统一 8 类)。所有命令在上级 `cleansight-yolo-pipeline/` 下执行。

## 脚本
| 脚本 | 作用 |
|------|------|
| `02_build.py` | 导出+视频 → `datasets_actionseq/<phase>/`,只保留落在 phase 区间内的帧;`--auto-assign` `--force` |
| `upload.py` | SDK 上传 → `cleansight-ActionSequence`(上传前自动校验;`--skip-check` 跳过) |

## State(入库)
- `completed_tasks_actionseq.json` — 增量完成清单

## 关键点
- 切分用共享 `../splits.yaml`(与 yolo 同源,确保同视频不跨 split)。
- `README.md` / `data_records.md` 由 `02_build.py` 生成在产物目录 `datasets_actionseq/` 内(gitignored),与本说明不同。
- 抽帧/稀有类密集采样参数在上级 `config.yaml`。
