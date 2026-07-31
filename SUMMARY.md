# CleanSight 数据集与模型设计总结

> [lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)
> https://github.com/lhh010/cleansight-dataset

## 一、数据来源

```
Label Studio (yolo-train 项目, 原 Project #10, 内镜清洗操作视频)
  ├── 33 个视频任务 (id=50~91)
  ├── 标注类型: videorectangle (目标检测 bbox) + timelinelabels (动作阶段)
  └── 导出 JSON → cleansight-pipeline 流水线处理
```

## 二、数据集设计

### 2.1 管线结构（yolo 两轨分离）

```
cleansight-pipeline/yolo/
├── train.yaml          ← 训练轨：配置 + 16 task 清单（一体）
├── test.yaml           ← benchmark 轨：独立 LS 项目，策展清单（待构建）
├── classes.yaml        ← 两轨共享的 class id 映射（单点真源）
├── build.py            ← 训练轨入口 → datasets/<组>/images/{train,val}/
├── build_test.py       ← benchmark 入口 → datasets/<组>/images/test/
└── builder.py          ← 两轨共享引擎
```

**设计原则**：训练轨（train/val）和 benchmark 轨（test）完全解耦，各自独立 LS 项目、独立清单、独立生命周期。两轨唯一的共享配置是 `classes.yaml`（class id 映射必须一致，否则训出的权重无法在 benchmark 上评测）。

### 2.2 输出结构

```
cleansight-pipeline/datasets/
├── group1_large/                 # 大目标检测组
│   ├── data.yaml
│   ├── images/{train,val,test}/*.jpg
│   └── labels/{train,val,test}/*.txt
└── group2_small/                 # 小目标检测组
    ├── data.yaml
    ├── images/{train,val,test}/*.jpg
    └── labels/{train,val,test}/*.txt
```

### 2.3 检测类别（8 类，分两组）

| class_id | 标签 | 组 | 说明 |
|----------|------|-----|------|
| 0 | `hand` | group1_large | 操作者手部 |
| 1 | `scope_control_body` | group1_large | 内镜操控部 |
| 2 | `scope_mid_section` | group1_large | 内镜中部 |
| 0 | `syringe` | group2_small | 注射器 |
| 1 | `air_gun` | group2_small | 气枪 |
| 2 | `scope_distal_end` | group2_small | 内镜头端 |
| 3 | `short_brush` | group2_small | 短毛刷 |
| 4 | `brush_tip_out` | group2_small | 刷头外露 |

> 每组 class_id 从 0 开始。类别只能追加到列表末尾，不可插入中间。

### 2.4 Split 划分

```
train (15 task): 50, 51, 52, 53, 54, 55, 59, 60, 62, 68, 69, 77, 78, 84, 85
val   ( 1 task): 61
test  ( 0 task): —（benchmark 轨独立策展，由 yolo/build_test.py 从 yolo-test 项目构建）
```

**核心约束**：按 LS 任务整段切分 —— 同一视频的所有帧永远在同一 split，杜绝时间相邻帧泄漏。task 身份键使用 LS task id（全局唯一，重传视频不变）。

### 2.5 数据版本管理

```
本地:
  DATASET_STATUS.md                     ← 项目根目录
  cleansight-pipeline/yolo/tracking_train.md  ← 构建自动生成
  cleansight-pipeline/yolo/completed_train.json ← 增量构建记录

ModelScope:
  lhh010/cleansight-yolo/
      ├── tracking_train.md
      ├── group1_large/   (images + labels + data.yaml)
      └── group2_small/   (images + labels + data.yaml)
```

## 三、流水线设计

```
common/reconcile.py     对账：导出/磁盘/清单三方对齐
common/pull.py          拉取原始视频
yolo/build.py           训练轨构建：抽帧 → YOLO 格式输出 → train/val
yolo/build_test.py      benchmark 构建：独立 LS 项目 → test
yolo/upload.py          上传到 ModelScope（含校验卡口）
```

## 四、关键设计决策

| 决策 | 说明 |
|------|------|
| **两轨分离** | 训练轨 (train.yaml) 和 benchmark 轨 (test.yaml) 独立 LS 项目、独立清单、独立生命周期 |
| **task id 做主键** | 清单按 LS task id 登记（非视频文件名），重传视频不变、天然跨轨唯一 |
| **classes.yaml 共享** | class id 映射单点真源，两轨逐字一致，避免权重-评测对不上 |
| **整段路由防泄漏** | 同一视频不进多个 split，验证/测试指标可复现 |
| **确定性切分** | `hash(seed:tid)` 分配 split，增量新增不打乱已有分配 |
| **清单即意图** | 人工登记的 yaml + 注释 = 决策依据；自动生成的 completed json = 机器状态；两者分离 |
| **旋转框处理** | LS 标注中的旋转矩形取 AABB（外接轴对齐矩形），兼容 YOLO 的 axis-aligned bbox 格式 |
| **稀有类密采** | keyframe < 200 的类别在 stride 外额外密集采样相邻帧（当前：air_gun, brush_tip_out, short_brush） |

## 五、模型设计

```
模型: YOLO11 nano (yolo11n.pt)
输入: 640×640
策略: 每组独立训练一个模型

group1_large/  →  runs/group1_large/weights/best.pt
group2_small/  →  runs/group2_small/weights/best.pt
```

## 六、当前数据覆盖矩阵

| 组 | Train 帧 | Val 帧 | Test 帧 | Train 框 | Val 框 | 合计帧 |
|----|---------|--------|---------|---------|--------|--------|
| group1_large | 10,410 | 1,244 | 0 | 35,090 | 4,722 | 11,654 |
| group2_small | 7,557 | 1,122 | 0 | 10,901 | 1,350 | 8,679 |
| **合计** | **17,967** | **2,366** | **0** | **45,991** | **6,072** | **20,333** |

### 逐类分布

| 类别 | Train 帧 | Val 帧 | Train 框 | Val 框 |
|------|---------|--------|---------|--------|
| hand | 10,041 | 1,239 | 18,640 | 2,354 |
| scope_control_body | 8,411 | 1,184 | 8,411 | 1,184 |
| scope_mid_section | 8,039 | 1,184 | 8,039 | 1,184 |
| syringe | 3,627 | 367 | 3,627 | 367 |
| air_gun | 837 | 0 | 837 | 0 |
| scope_distal_end | 5,104 | 755 | 5,104 | 755 |
| short_brush | 1,165 | 0 | 1,165 | 0 |
| brush_tip_out | 168 | 228 | 168 | 228 |

**待改进**：

- 无 test 集（待 yolo-test LS 项目标注 + benchmark 策展）
- `air_gun` 和 `short_brush` 在 val 中无样本（val 仅 task#61，这两类在其采样帧中未出现）—— 后续增量补 task 到 val
- 异内镜型号 / 异操作者泛化：暂无数据源

## 七、Links

- YOLO 数据集：[lhh010/cleansight-yolo](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)
- 原始数据：[lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)
- 项目仓库：[lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)
- Benchmark 设计：[docs/BENCHMARK_DETECTION.md](docs/BENCHMARK_DETECTION.md)
