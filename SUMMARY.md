# CleanSight 数据集与模型设计总结

> [lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)
> https://github.com/lhh010/cleansight-dataset

## 一、数据来源

```
Label Studio (Project #10, 内镜清洗操作视频)
  ├── 17 个视频任务 (id=50~75)
  ├── 标注类型: videorectangle (目标检测 bbox) + timelinelabels (动作阶段)
  └── 导出 JSON → cleansight-yolo-pipeline 流水线处理
```

## 二、数据集设计

### 2.1 分层结构

```
cleansight-yolo-pipeline/datasets/
├── long_brush_insert/       # 长刷插入阶段
│   ├── images/{train,val,test}/*.jpg
│   ├── labels/{train,val,test}/*.txt
│   └── data.yaml
├── long_brush_withdraw/     # 长刷撤回阶段
│   ├── ...
├── air_injection/           # 气枪吹气阶段
│   ├── ...
└── flush/                   # 冲水冲洗阶段
    ├── ...
```

**设计原则**：按动作阶段（action phase）作为数据集的第一层维度，每个阶段是一个独立的 YOLO 子数据集，可单独用于训练特定阶段的检测模型。

### 2.2 检测类别（8 类，所有阶段共享）

| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `hand` | 操作者手部 |
| 1 | `scope_control_body` | 内镜操控部 |
| 2 | `scope_mid_section` | 内镜中部 |
| 3 | `scope_distal_end` | 内镜头端 |
| 4 | `syringe` | 注射器 |
| 5 | `air_gun` | 气枪 |
| 6 | `short_brush` | 短毛刷 |
| 7 | `brush_tip_out` | 刷头外露 |

### 2.3 Split 划分

```
train (627 帧):  task#59 (4807dbbe-clip) + task#68 (63a848d5-clip)
val   (191 帧):  task#61 (65d70028-clip)
test  (  0 帧):  (目前暂无，待更多确认任务)
```

**核心约束**：按 LS 任务整段切分 —— 同一视频的所有帧永远在同一 split，杜绝时间相邻帧泄漏。

### 2.4 数据版本管理

```
本地:
  DATASET_STATUS.md                ← 项目根目录
  cleansight-yolo-pipeline/tracking.md  ← 流水线自动生成

ModelScope:
  lhh010/cleansight-raw/           ← 原始 LS 导出 JSON + DATASET_STATUS.md
  lhh010/cleansight-yolo/          ← 处理后 YOLO 数据集 + tracking.md
      ├── long_brush_insert/
      ├── long_brush_withdraw/
      ├── air_injection/
      └── flush/
```

## 三、流水线设计

```
00_status.py         对账：导出/磁盘/白名单/split 四方对齐
01_pull_data.py      拉取原始视频
02_build_dataset.py  核心：旋转框 AABB 修正 → 阶段分割 → 抽帧 → YOLO 格式输出
03_train.py          YOLO 训练（每阶段独立模型）
04_validate.py       验收评估（PASS/FAIL 门禁）
```

## 四、关键设计决策

| 决策 | 说明 |
|------|------|
| **阶段分割优先** | 动作阶段作为数据集第一维度，因为不同阶段的目标分布和行为模式差异大，分开训练更精准 |
| **旋转框处理** | LS 标注中的旋转矩形取 AABB（外接轴对齐矩形），兼容 YOLO 的 axis-aligned bbox 格式 |
| **整段路由防泄漏** | 同一视频不进多个 split，验证/测试指标可复现，不会被时间相邻帧"作弊" |
| **确定性切分** | `hash(seed:stem)` 分配 split，增量新增视频不打乱已有分配 |
| **白名单机制** | `config.yaml` 的 `only_videos` 控制哪些任务进数据集，只有人工确认标注完成的任务才放行 |

## 五、模型设计

```
模型: YOLO11 nano (yolo11n.pt)
输入: 640×640
策略: 每阶段独立训练一个模型

long_brush_insert/   →  runs/long_brush_insert/weights/best.pt
long_brush_withdraw/ →  runs/long_brush_withdraw/weights/best.pt
air_injection/       →  runs/air_injection/weights/best.pt
flush/               →  runs/flush/weights/best.pt
```

## 六、当前数据覆盖矩阵

| 阶段 | Train | Val | Test | 合计 | 确认任务 |
|------|-------|-----|------|------|----------|
| long_brush_insert | 217 | 42 | 0 | 259 | 59, 61, 68 |
| long_brush_withdraw | 123 | 38 | 0 | 161 | 59, 61, 68 |
| air_injection | 30 | 0 | 0 | 30 | 59 (仅有) |
| flush | 257 | 111 | 0 | 368 | 61, 68 |
| **合计** | **627** | **191** | **0** | **818** | **3 个任务** |

**待改进**：

- 无 test 集（需更多确认任务）
- `air_injection` 无 val（只出现在 train 任务中）
- `syringe`、`short_brush`、`air_gun`、`brush_tip_out` 等类别样本稀少

## 七、Links

- Raw 数据集：[lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)
- YOLO 数据集：[lhh010/cleansight-yolo](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)
