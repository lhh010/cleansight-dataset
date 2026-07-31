# CleanSight YOLO Dataset

内镜清洗巡检目标检测数据集，由 Label Studio 标注平台（yolo-train 项目）原始标注数据经标准化流水线处理后生成的标准 YOLO 格式数据集。

## 数据集概述

| 项目 | 说明 |
|------|------|
| 数据来源 | Label Studio 标注平台，yolo-train 项目（内镜清洗操作视频） |
| 标注类型 | 目标检测（VideoRectangle bounding box） |
| 数据格式 | Ultralytics YOLO（归一化中心点坐标） |
| 视频任务数 | 16 个（在册，已质检） |
| 总样本数 | 20,333 张图像（stride=4 抽帧 + 稀有类密集采样） |
| 划分方式 | 按 Label Studio 任务整段切分（train: 15 task / val: 1 task） |
| 管线版本 | yolo 两轨分离（train.yaml + test.yaml），配置与清单下沉至 yolo/ |

## 处理流程

原始标注数据经过 **cleansight-pipeline** 标准化流水线的以下步骤处理：

### 1. 数据拉取（common/pull.py）
- 从 Label Studio 服务器下载导出 JSON 中引用的原始视频到本地 `raw/videos/`
- 对每个视频做完整性校验（ffprobe 读时长/帧数）

### 2. 对账与切分（common/reconcile.py + train.yaml）
- 对齐"导出 JSON / 本地视频 / 清单"三方数据
- **按 Label Studio 任务粒度**分配 train/val（`train.yaml` 的 `tasks` 段为唯一真源）
- **关键约束**：同一 LS 任务的所有帧全部进入同一 split，绝不跨 split，杜绝时间相邻帧泄漏
- task 身份键使用 **LS task id**（全局唯一，重传视频不变）

### 3. 转 YOLO 格式（yolo/build.py）
- **关键帧对齐**：LS 标注帧号按标注端 fps 计算，通过 `scale = ls_fps/real_fps` 映射到真实帧号，消除漂移
- **线性插值**：LS 只存关键帧 bbox，中间帧由相邻关键帧线性插值得到；`enabled=False` 表示目标离场
- **抽帧采样**：`stride=4`（30fps 下约 7.5 张/秒），仅保留含分组内目标的帧（空帧丢弃）
- **稀有类密集采样**：keyframe < 200 的类别（air_gun, brush_tip_out, short_brush）在正常 stride 外额外采集相邻帧
- **坐标转换**：LS 左上角百分比 → YOLO 归一化中心点 `(cx, cy, w, h)`，裁剪到 [0,1]
- **类别过滤**：仅保留分组内类别；未列入任一组的类别自动忽略

### 4. 稳定切分契约

```
train.yaml tasks（入库，唯一真源）
    ↓
yolo/build.py 读取每个 task 的 split
    ↓
同一 task 所有帧 → 全部进入该 split
    ↓
产出 datasets/<组>/images/{train,val}/ + labels/{train,val}/
```

- 已分配 task 的 split **永不被自动重排**，人工可改
- 新增 task 由 `--auto-assign` 按 `hash(seed:tid)` 确定性回填，不打乱已有分配
- 增量更新天然安全：已有 task split 不变，只回填新 task

---

## 数据集划分

| Split | 任务数 | Task ID |
|-------|--------|---------|
| **train** | 15 | 50, 51, 52, 53, 54, 55, 59, 60, 62, 68, 69, 77, 78, 84, 85 |
| **val** | 1 | 61 |
| **test** | 0 | —（benchmark 轨独立策展，由 `yolo/build_test.py` 从 yolo-test 项目构建） |

> ⚠️ **重要**：每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏，确保验证/测试指标的可靠性和可复现性。

---

## 数据集结构

```
lhh010/cleansight-yolo/
├── README.md
├── tracking_train.md               # 训练轨构建追踪表
├── group1_large/                   # 大目标检测组
│   ├── data.yaml                   # YOLO 数据配置（含 train/val/test 路径）
│   ├── images/
│   │   ├── train/                  # 10,410 张
│   │   ├── val/                    # 1,244 张
│   │   └── test/                   # 0 张（benchmark 待策展）
│   └── labels/
│       ├── train/                  # 10,410 个 .txt
│       ├── val/                    # 1,244 个 .txt
│       └── test/                   # 0 个 .txt
└── group2_small/                   # 小目标检测组
    ├── data.yaml
    ├── images/
    │   ├── train/                  # 7,557 张
    │   ├── val/                    # 1,122 张
    │   └── test/                   # 0 张
    └── labels/
        ├── train/                  # 7,557 个 .txt
        ├── val/                    # 1,122 个 .txt
        └── test/                   # 0 个 .txt
```

### 图片命名规范
```
t{task_id}_{frame:06d}[_dense].jpg
例: t59_000042.jpg        → task#59 的 stride 帧
    t59_000045_dense.jpg  → task#59 的稀有类密采帧
```

### 标注格式（YOLO 归一化）
```
class_id cx cy w h    # 全部为归一化 [0,1] 浮点数
例: 0 0.453125 0.687500 0.164062 0.183333
```

---

## 类别定义

### group1_large — 大目标
| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `hand` | 手 |
| 1 | `scope_control_body` | 内镜操控部 |
| 2 | `scope_mid_section` | 内镜中部 |

### group2_small — 小目标
| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `syringe` | 注射器 |
| 1 | `air_gun` | 气枪 |
| 2 | `scope_distal_end` | 内镜头端 |
| 3 | `short_brush` | 短毛刷 |
| 4 | `brush_tip_out` | 刷头外露 |

> **注意**：类别列表只能追加到末尾，不可插入中间 —— 否则打乱已训权重的 class_id 映射。

---

## 样本分布统计

### group1_large

| 类别 | train帧 | val帧 | train框 | val框 |
|------|---------|-------|---------|-------|
| hand | 10,041 | 1,239 | 18,640 | 2,354 |
| scope_control_body | 8,411 | 1,184 | 8,411 | 1,184 |
| scope_mid_section | 8,039 | 1,184 | 8,039 | 1,184 |
| **合计** | **10,410** | **1,244** | **35,090** | **4,722** |

### group2_small

| 类别 | train帧 | val帧 | train框 | val框 |
|------|---------|-------|---------|-------|
| syringe | 3,627 | 367 | 3,627 | 367 |
| air_gun | 837 | 0 | 837 | 0 |
| scope_distal_end | 5,104 | 755 | 5,104 | 755 |
| short_brush | 1,165 | 0 | 1,165 | 0 |
| brush_tip_out | 168 | 228 | 168 | 228 |
| **合计** | **7,557** | **1,122** | **10,901** | **1,350** |

> ⚠️ `air_gun` 和 `short_brush` 在 val 中无样本 —— val 仅 task#61，这两类在其采样帧中未出现。后续增量补 task 到 val 可解决。

---

## 下载数据集

### 方式一：ModelScope SDK（推荐）

```bash
pip install modelscope
```

```python
from modelscope.msdatasets import MsDataset

# 下载整个数据集
ds = MsDataset.load("lhh010/cleansight-yolo", split="master")
```

### 方式二：Git LFS

```bash
# 安装 git-lfs
apt install git-lfs     # Linux
brew install git-lfs    # macOS

# 克隆数据集
git lfs install
git clone https://www.modelscope.cn/datasets/lhh010/cleansight-yolo.git
```

### 方式三：浏览器下载

访问 [数据集主页](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)，点击「下载」按钮。

### 加载到 YOLO 训练

下载后，直接使用各组的 `data.yaml` 进行训练：

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
model.train(data="path/to/group1_large/data.yaml", epochs=100, imgsz=640)
```

---

## 更新/重新生成数据集

数据集通过 `cleansight-pipeline` 流水线生成，完整工具链见项目仓库。

### 环境准备

```bash
cd cleansight-pipeline
pip install opencv-python-headless numpy pyyaml pillow ultralytics modelscope
```

### 完整流程

```bash
# 1. 将 LS 导出 JSON 放入 raw/exports/yolo-train/
# 2. 下载视频
export LS_HOST=http://<LS地址>:8080 LS_TOKEN=<AccessToken>
python common/pull.py

# 3. 对账 & 分配 split
python common/reconcile.py             # 查看状态
python common/reconcile.py --assign    # 确定性回填 split（写入 train.yaml）

# 4. 生成 YOLO 数据集
python yolo/build.py                   # 增量构建
python yolo/build.py --force           # 全量重建

# 5. 上传到 ModelScope
python yolo/upload.py                  # 含校验卡口
python yolo/upload.py --skip-check     # 跳过校验直接上传
```

### 增量更新

```bash
# 新导出 JSON 放入 raw/exports/yolo-train/
python common/reconcile.py             # 看差异
python common/pull.py                  # 补下新视频
# 质检新 task 后登记进 yolo/train.yaml
python common/reconcile.py --assign    # 仅回填新 task
python yolo/build.py                   # 增量重建（已处理 task 秒级跳过）
python yolo/upload.py                  # 增量上传（ModelScope SDK 自动去重）
```

---

## 相关链接

- 数据集：[lhh010/cleansight-yolo](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)
- 原始数据：[lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)
- 项目仓库：[lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)
- 标注平台：Label Studio (yolo-train 项目)
- Benchmark 设计：[BENCHMARK_DETECTION.md](https://github.com/lhh010/cleansight-dataset/blob/main/docs/BENCHMARK_DETECTION.md)
