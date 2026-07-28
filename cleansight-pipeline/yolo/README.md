# yolo · 目标检测数据集(cleansight-yolo)

从 LS `videorectangle` bbox 构建**分组 YOLO 检测集**。所有命令在上级 `cleansight-pipeline/` 下执行。

> **本仓库只做数据**:模型训练、评测、验收门槛、权重与报告都不在这里。产物止于
> `datasets/<组>/`(含 `data.yaml`)与追踪表,训练侧拿走自行开跑。

## 两条轨(核心)

检测轨在 Label Studio 侧就是两个独立项目,流水线这边也是两条独立管道,除类别外零共享:

| | 训练轨 | benchmark 轨 |
|---|---|---|
| LS 项目 | `yolo-train` | `yolo-test` |
| 配置+清单 | `train.yaml` | `test.yaml` |
| 入口 | `build.py` | `build_test.py` |
| 产出 split | `train` / `val` | `test` |
| 生命周期 | 滚动补量(评测驱动) | **策展 + 冻结**,定版后只增不改 |
| 空帧 | 丢弃(避免负样本稀释) | **保留**作负样本(DET §2 Group C) |
| 稀有类密采 | 开 | 关(人为加密会扭曲评测集分布) |
| 自动回填 split | `--auto-assign` 可 | **不可**(选哪条片当评测集是人工策展决策) |

`test` **不是**从训练池随机 hold-out 的 —— 它来自独立项目、整条源不进 train/val。
两份清单的 task id 零交集由 `manifest.assert_disjoint()` 强制。

> ⚠️ benchmark 的**等价类**(`ec_tags`、几何桶)与数据侧的**覆盖判据**尚未落地,
> 待 `yolo-test` 产出首批标注、口径定稿后单独设计。

## 脚本

| 脚本 | 作用 |
|------|------|
| `build.py` | 训练轨 → `<out_root>/<组>/{train,val}`;`--auto-assign` `--force` |
| `build_test.py` | benchmark 轨 → `<out_root>/<组>/test`;`--force` |
| `builder.py` | 两轨共用的构建引擎(不单独运行) |
| `manifest.py` | 清单读写 / split 回填 / 两表互斥断言(不单独运行) |
| `frames.py` · `dataset.py` | 抽帧循环 / 产物落盘布局(不单独运行) |
| `augment.py` | 稀有类增强,**仅 train**(合成图不进 val/test);`--threshold=` `--copies=` `--dry-run` |
| `upload.py` | SDK 上传 → `cleansight-yolo`(上传前自动校验;`--skip-check` 跳过) |

## 配置(三份 yaml)

| 文件 | 管什么 |
|------|--------|
| `classes.yaml` | 类别分组与 class id 映射 —— **两轨唯一的共享配置**(必须逐字一致,否则权重在 benchmark 上 class id 对不上) |
| `train.yaml` | 训练轨:数据源项目 / 产物路径 / 抽帧参数 / 回填比例 / **在册 task+split**(文件名里的 `train` 指 split,不是模型训练) |
| `test.yaml` | benchmark 轨:同上各项独立一份 + `version` / `frozen_at` / **在册 task** |

**yaml 只放真会变的**。`train`/`val`/`test` 这类 YOLO 结构约定、state 文件命名规则都在代码里
(`dataset.py` 的 `SPLITS`、`manifest.py` 的 `completed_path()`),不是可调项。

## 清单的身份键是 LS task id

清单**不存视频文件名** —— 视频在 LS 重传会换 uuid 前缀,文件名跟着变,而 task id 是
数据库主键、全局递增、跨项目唯一。视频名 build 时从导出 json 的 `task.data.video` 现查。

同理帧名是 `t{task_id}_{frame:06d}`(如 `t59_000004.jpg`):不含视频名(会变),
也不含导出下标(增删 task 就重排)。task id 全局唯一,两轨也就天然不会撞名。

在册 = 已人工质检 + 已定归属。不在册的 task 一律跳过。

## State(入库)与增量

`build.py` / `build_test.py` 各写各的,文件名从清单名派生:

- `completed_{train,test}.json` — 增量完成清单(**机器状态**)
- `tracking_{train,test}.md` — 追踪表,随数据集上传

清单 = 人工意图(手改、入库);`completed_*.json` = 机器状态。分开,免得人工编辑时误改状态。

增量粒度是 **LS task**,靠 `completed_*.json` 里的**重建签名**判断:

```
annotations  该 task 标注内容的 sha1 —— 只有它自己的标注改了才重建它
sampling     全部抽帧/编码参数的指纹
rare         稀有类集合(全部在册 task 共同决定,跨阈值会让旧密采帧过时)
split        归属,手工改清单里的 split 时帧要真的搬过去
```

签名**不含导出文件名** —— LS 导出文件名带时间戳,拿它当签名会让"放一份新导出"退化成
全量重建。实测:换导出文件名而标注未变 → 16 个 task 全 `[skip]`;只改一个 task 的
关键帧 → 只有那一个 `[reprocess]`。

`--force` 清空状态全量重建。**已知缺口**:从清单删掉 task 不会自动清理其已落盘的帧。

## 常规流程

```bash
# 导出 JSON 按 LS 项目放进 raw/exports/{yolo-train,yolo-test}/
python3 common/pull.py            # 下视频(两个项目取并集)
python3 common/reconcile.py       # 双轨对账:未登记 / 遗失 / 孤儿
python3 common/reconcile.py --assign   # 训练轨未登记 task 确定性回填(benchmark 不回填)
python3 yolo/build.py             # 训练轨 → train/val
python3 yolo/build_test.py        # benchmark 轨 → test
python3 common/check.py --strict   # 推送前校验
python3 yolo/upload.py            # 发布 → ModelScope
```
