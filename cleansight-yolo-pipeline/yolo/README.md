# yolo · 目标检测数据集(cleansight-yolo)

从 LS `videorectangle` bbox 构建**分组 YOLO 检测集**,含训练与验收。所有命令在上级 `cleansight-yolo-pipeline/` 下执行。

## 脚本
| 脚本 | 作用 |
|------|------|
| `02_build.py` | 导出+视频 → `datasets/<组>/`,按 `../splits.yaml` 整段路由;`--auto-assign` `--force` |
| `02b_augment.py` | 稀有类别旋转/缩放增强(仅 train,备用);`--threshold` `--copies` `--dry-run` |
| `03_train.py` | 各组训练 → `../runs/<组>/weights/best.pt`;可传组名只训一组 |
| `04_validate.py` | val 指标 + 验收判定 → `../runs/<组>/acceptance_report.md`;任一组 FAIL 退出码非零 |
| `upload.py` | SDK 上传 → `cleansight-yolo`(上传前自动校验;`--skip-check` 跳过) |

## State(入库)
- `completed_tasks.json` — 增量完成清单(`02_build.py` 读写)
- `tracking.md` — `02_build.py` 生成的追踪表

## 关键点
- 分组、白名单、抽帧、超参、验收阈值全在上级 `config.yaml`。
- 切分用 `../splits.yaml`(视频级整段路由)。
- 产物 `datasets/`、`runs/` 落在 pipeline 根(gitignored)。
