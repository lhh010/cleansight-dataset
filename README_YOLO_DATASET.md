# CleanSight YOLO Dataset

内镜清洗巡检目标检测数据集，由 [lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw) 原始标注数据经标准化流水线处理后生成的标准 YOLO 格式数据集。

## 数据集概述

| 项目 | 说明 |
|------|------|
| 数据来源 | Label Studio 标注平台 Project #10，内镜清洗操作视频 |
| 原始数据集 | [lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw) |
| 标注类型 | 目标检测（VideoRectangle bounding box） |
| 数据格式 | Ultralytics YOLO（归一化中心点坐标） |
| 视频任务数 | 10 个 |
| 总样本数 | 1696 张图像（stride=12 抽帧，仅保留有标注帧） |
| 划分方式 | 按 Label Studio 任务整段切分（train/val/test = 6:2:2） |

## 处理流程

原始标注数据经过 **cleansight-yolo-pipeline** 标准化流水线的以下步骤处理：

### 1. 数据拉取（01_pull_data.py）
- 从 Label Studio 服务器下载导出 JSON 中引用的原始视频到本地 `raw/videos/`
- 对每个视频做完整性校验（ffprobe 读时长/帧数）

### 2. 对账与切分（00_status.py + splits.yaml）
- 对齐"导出 JSON / 本地视频 / 白名单 / 切分清单"四方数据
- **按 Label Studio 任务粒度**分配 train/val/test（`splits.yaml` 为唯一真源）
- **关键约束**：同一 LS 任务的所有帧全部进入同一 split，绝不跨 split，杜绝时间相邻帧泄漏

### 3. 转 YOLO 格式（02_build_dataset.py）
- **关键帧对齐**：LS 标注帧号按标注端 fps 计算，通过 `scale = ls_fps/real_fps` 映射到真实帧号，消除漂移
- **线性插值**：LS 只存关键帧 bbox，中间帧由相邻关键帧线性插值得到；`enabled=False` 表示目标离场
- **抽帧采样**：`stride=12`（30fps 下约 2.5 张/秒），仅保留含分组内目标的帧（空帧丢弃）
- **坐标转换**：LS 左上角百分比 → YOLO 归一化中心点 `(cx, cy, w, h)`，裁剪到 [0,1]
- **类别过滤**：仅保留分组内类别（`short_brush`、`brush_tip_out` 未列入任何组，自动忽略）

### 4. 稳定切分契约

```
splits.yaml（入库，唯一真源）
    ↓
02_build_dataset.py 读取每个视频的 split
    ↓
同一视频所有帧 → 全部进入该 split
    ↓
产出 datasets/<组>/images/{train,val,test}/ + labels/{train,val,test}/
```

- 已分配视频的 split **永不被自动重排**，人工可改
- 新增视频由 `--assign` 按 `hash(seed:stem)` 确定性回填，不打乱已有分配
- 增量更新天然安全：已有视频 split 不变，只回填新视频

---

## 数据集划分

| Split | 任务数 | 占比 | 视频任务 |
|-------|--------|------|----------|
| **train** | 6 | 60% | 05ba4406-clip, 218f9117-clip, 4807dbbe-clip, 7e8f5b4f-clip, af0e7803-clip, ed1f1353-clip |
| **val** | 2 | 20% | 687e3c78-clip, 65d70028-clip |
| **test** | 2 | 20% | b004acff-clip, 9f93cf16-clip |

> ⚠️ **重要**：每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏，确保验证/测试指标的可靠性和可复现性。

---

## 数据集结构

```
lhh010/cleansight-yolo/
├── README.md
├── group1_large/                  # 大目标检测组
│   ├── data.yaml                  # YOLO 数据配置（含 train/val/test 路径）
│   ├── images/
│   │   ├── train/                 # 568 张
│   │   ├── val/                   # 549 张
│   │   └── test/                  # 40 张
│   └── labels/
│       ├── train/                 # 568 个 .txt
│       ├── val/                   # 549 个 .txt
│       └── test/                  # 40 个 .txt
└── group2_small/                  # 小目标检测组
    ├── data.yaml
    ├── images/
    │   ├── train/                 # 37 张
    │   ├── val/                   # 500 张
    │   └── test/                  # 2 张
    └── labels/
        ├── train/                 # 37 个 .txt
        ├── val/                   # 500 个 .txt
        └── test/                  # 2 个 .txt
```

### 图片命名规范
```
{task序号:02d}_{视频名前12位}_{真实帧号:06d}.jpg
例: 06_687e3c78-cli_002329.jpg
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

> **注意**：原始标注中的 `short_brush`（短毛刷）和 `brush_tip_out`（刷头外露）未列入上述任一组，在当前数据集中被自动排除。如需加入，在 `config.yaml` 对应组末尾追加即可（**只能追加，不可插入中间**，否则打乱已训权重的 class_id 映射）。

---

## 样本分布统计

### group1_large

| 类别 | train帧 | val帧 | test帧 | train框 | val框 | test框 |
|------|---------|-------|--------|---------|-------|--------|
| hand | 565 | 492 | 20 | 1077 | 915 | 40 |
| scope_control_body | 494 | 492 | 36 | 494 | 492 | 36 |
| scope_mid_section | 422 | 496 | 25 | 422 | 496 | 25 |
| **合计** | **568** | **549** | **40** | **1993** | **1903** | **101** |

### group2_small

| 类别 | train帧 | val帧 | test帧 | train框 | val框 | test框 |
|------|---------|-------|--------|---------|-------|--------|
| syringe | 0 | 254 | 0 | 0 | 254 | 0 |
| air_gun | 33 | 46 | 0 | 33 | 46 | 0 |
| scope_distal_end | 4 | 301 | 2 | 4 | 301 | 2 |
| **合计** | **37** | **500** | **2** | **37** | **601** | **2** |

> ⚠️ `syringe` 和 `air_gun` 在 test 中无样本 — 当前 10 个视频数据量有限，这两类仅出现在 val 视频中。增量数据后可改善 test 覆盖。

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

或直接访问子目录：

```python
from modelscope.hub.api import HubApi

api = HubApi()
# 下载指定文件
api.download_file(
    repo_id="lhh010/cleansight-yolo",
    file_path="group1_large/data.yaml",
    output_dir="./my_dataset/group1_large/"
)
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

数据集通过 `cleansight-yolo-pipeline` 流水线生成，完整工具链见项目仓库。

### 环境准备

```bash
cd cleansight-yolo-pipeline
python -m venv .venv
.venv/bin/pip install opencv-python-headless numpy pyyaml pillow ultralytics
```

### 完整流程

```bash
# 1. 将 LS 导出 JSON 放入 raw/exports/
# 2. 下载视频
export LS_HOST=http://<LS地址>:8080 LS_TOKEN=<AccessToken>
python 01_pull_data.py

# 3. 对账 & 分配 split
python 00_status.py               # 查看状态
python 00_status.py --assign      # 确定性回填 split（写入 splits.yaml）
# 必要时手工调整 splits.yaml

# 4. 生成 YOLO 数据集
python 02_build_dataset.py

# 5. 训练 & 验证（可选）
python 03_train.py
python 04_validate.py
```

### 上传到 ModelScope

```bash
# 在项目根目录执行
python upload_yolo_to_modelscope.py
```

上传脚本将 `cleansight-yolo-pipeline/datasets/` 下的各组分目录上传到 `lhh010/cleansight-yolo`。

### 增量更新

```bash
# 新导出 JSON 放入 raw/exports/
python 00_status.py               # 看差异
python 01_pull_data.py            # 补下新视频
# 质检新视频后追加到 config.yaml 的 only_videos
python 00_status.py --assign      # 仅回填新视频，已有 split 不变
python 02_build_dataset.py        # 重建数据集
python upload_yolo_to_modelscope.py  # 更新 ModelScope
```

---

## 相关链接

- 原始数据集：[lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)
- 处理流水线：`cleansight-yolo-pipeline/`（项目仓库内）
- 标注平台：Label Studio (Project #10)
