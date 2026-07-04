# CleanSight Raw Dataset

内窥镜清洗过程视频标注数据集，包含目标检测（bounding box）和动作时序（timeline）两
类标注。

## 数据集概览

| 项目 | 说明 |
|------|------|
| 标注平台 | [Label Studio](http://49.234.120.241:8080) |
| 数据集主页 | [ModelScope: lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw) |
| 原始视频 | 内窥镜清洗操作录像 |

### 标注类别

**目标检测（Bounding Box）：**

| 标签 | 含义 |
|------|------|
| `hand` | 手 |
| `short_brush` | 短毛刷 |
| `syringe` | 注射器 |
| `air_gun` | 气枪 |
| `scope_control_body` | 内镜操控部 |
| `scope_mid_section` | 内镜中部 |
| `scope_distal_end` | 内镜头端 |
| `brush_tip_out` | 刷头外露 |

**动作时序（Timeline）：**

| 标签 | 含义 |
|------|------|
| `short_brush_cleaning` | 短毛刷清洗 |
| `flush` | 冲洗 |
| `air_injection` | 注气 |
| `long_brush_insert` | 长毛刷插入 |
| `long_brush_withdraw` | 长毛刷退出 |

### 标注数量

- 已标注任务：10 个
- 目标检测（VideoRectangle）：56 个标注实例
- 动作时序（TimelineLabels）：22 个标注实例

---

## 数据说明

### 标注数据格式

每条任务的 JSON 结构如下：

```json
{
  "id": 123,
  "data": {
    "video": "/data/upload/10/xxx.mp4"
  },
  "annotations": [{
    "completed_by": { "id": 3, "email": "..." },
    "result": [
      {
        "type": "videorectangle",
        "value": {
          "framesCount": 510,
          "duration": 21.23,
          "labels": ["hand"],
          "sequence": [
            { "frame": 1, "x": 33.98, "y": 71.04, "width": 12.5, "height": 8.3, "enabled": true }
          ]
        }
      },
      {
        "type": "timelinelabels",
        "value": {
          "start": 100,
          "end": 500,
          "timelinelabels": ["flush"]
        }
      }
    ]
  }]
}
```

### 重要提示

1. **标注是非连续的（关键帧插值）**：VideoRectangle 使用关键帧标注方式 — 只在关键
   帧上标记位置，中间帧由标注工具线性插值。因此 `sequence` 数组长度 < 视频总帧数。
   例如：510 帧视频中只有 127 个关键帧。

2. **不包含视频文件**：数据集中仅包含标注 JSON，**不包含原始视频**。`data.video` 字
   段为 Label Studio 服务器内部路径（`/data/upload/...`），外部无法直接访问。

3. **跨帧关联**：同一个标注目标的 `sequence` 数组中各帧通过连续性关联；需按 `frame`
   字段重建完整的时间序列。

---

## 下载数据集

### 方式一：ModelScope SDK

```bash
pip install modelscope
```

```python
from modelscope.msdatasets import MsDataset

# 下载整个数据集
ds = MsDataset.load("lhh010/cleansight-raw", subset_name="default", split="master")
print(len(ds))
```

### 方式二：Git LFS

```bash
# 安装 git-lfs
apt install git-lfs    # Linux
brew install git-lfs   # macOS

# 克隆数据集
git lfs install
git clone https://www.modelscope.cn/datasets/lhh010/cleansight-raw.git
```

### 方式三：浏览器下载

直接访问 [数据集主页](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)，
点击「下载」按钮。

---

## 上传数据集

### 前提条件

```bash
pip install modelscope
```

将 `config.example.py` 复制为 `config.py`，并填入真实值：

```bash
cp config.example.py config.py
```

编辑 `config.py`：

```python
MS_ACCESS_TOKEN = "ms-xxxxxxxx"       # https://modelscope.cn/my/myaccesstoken
MS_REPO_ID = "lhh010/cleansight-raw"  # 数据集仓库
```

### 方式一：上传本地文件夹

```bash
python upload_to_modelscope.py
```

将 `config.py` 中 `UPLOAD_FOLDER_PATH` 指向的文件夹整体上传。

### 方式二：从 Label Studio 导出并上传

```bash
python export_mix_label.py
```

该脚本执行三个步骤：
1. 从 Label Studio API 导出指定项目的标注数据
2. 过滤掉没有实际标注内容的任务
3. 上传到 ModelScope

---

## 文件结构

```
dataset/
├── config.example.py         # 配置模板（可提交 git）
├── config.py                 # 真实配置（已在 .gitignore 排除，含 Token）
├── upload_to_modelscope.py   # 上传本地文件夹到 ModelScope
├── export_mix_label.py       # 导出 Label Studio 标注 + 上传
├── .gitignore                # 忽略 config.py、exports/ 等
└── README.md                 # 本文件
```

---

## 环境依赖

```
modelscope>=1.37.0
requests
```
