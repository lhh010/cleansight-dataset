# actionmixed · 动作识别数据集(cleansight-ActionMixed)

**bbox + 动作标签同存**:每帧带 YOLO 检测框(`frames/`),每视频带动作标签(`labels/`),动作段前后各扩展 idle 帧。所有命令在上级 `cleansight-yolo-pipeline/` 下执行。

## 脚本
| 脚本 | 作用 |
|------|------|
| `02_build.py` | 导出+视频 → `datasets_actionmixed/{images,frames,labels}`;`--force` 全量重建 |
| `upload.py` | SDK 上传 → `cleansight-ActionMixed` |

## State(入库)
- `completed_tasks_actionmixed.json` — 增量完成清单
- `tracking_actionmixed.md` — `02_build.py` 生成的追踪表

## 关键点
- **不使用 `../splits.yaml`**:按**段级内存哈希**(seeded by `config.seed`)在内存分 train/val/test,不落 per-video 清单。
- 抽帧/稀有类参数在上级 `config.yaml`;检测类沿用统一 8 类,动作类从导出动态发现。
