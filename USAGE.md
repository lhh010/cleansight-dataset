# CleanSight Dataset — 使用说明

内镜清洗操作视频的目标检测数据集构建与版本管理工具。

> GitHub: [lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)

## 目录

- [一、项目结构](#一项目结构)
- [二、环境准备](#二环境准备)
- [三、数据集概览](#三数据集概览)
- [四、快速开始](#四快速开始)
- [五、添加新标注任务](#五添加新标注任务)
- [六、日常维护](#六日常维护)
- [七、配置参考](#七配置参考)
- [八、脚本速查](#八脚本速查)
- [九、版本管理](#九版本管理)

---

## 一、项目结构

```
dataset/
├── config.py          # ModelScope / Label Studio 密钥（不入 git）
├── config.example.py  # 密钥模板
├── DATASET_STATUS.md  # 数据集状态追踪表
├── SUMMARY.md         # 数据集与模型设计总结
│
└── cleansight-pipeline/  # ← 所有操作在此目录下执行
    ├── config.yaml       # 中央配置（groups, only_videos, stride...）
    ├── splits.yaml       # Split 分配唯一真源
    ├── requirements.txt  # 依赖清单
    │
    ├── common/                  # 共享编排脚本
    │   ├── reconcile.py         # 对账：导出/磁盘/白名单/split 四方对齐
    │   ├── pull.py              # 下载 LS 视频到 raw/videos/
    │   ├── check.py             # 数据集校验
    │   ├── count_classes.py     # 类别计数
    │   ├── scarce_sources.py    # 解析任务
    │   ├── scarce_checklist.py  # 生成检查清单
    │   └── upload_git.py        # 统一 git 上传
    │
    ├── yolo/                     # YOLO 检测数据集
    │   ├── build.py              # 构建 group1_large / group2_small YOLO 数据集
    │   ├── augment.py            # 稀有类别数据增强（备用）
    │   ├── train.py              # YOLO 训练
    │   ├── validate.py           # 验收评估
    │   ├── upload.py             # 上传 group 数据集 → cleansight-yolo
    │   ├── completed_tasks.json  # 增量构建记录（自动生成）
    │   └── tracking.md           # 追踪表（自动生成）
    │
    ├── actionmixed/                          # ActionMixed 混合数据集
    │   ├── build.py                          # 构建 ActionMixed 数据集
    │   ├── upload.py                         # 上传混合数据集
    │   ├── completed_tasks_actionmixed.json  # 增量构建记录（自动生成）
    │   └── tracking_actionmixed.md           # 追踪表（自动生成）
    │
    ├── utils/              # 共享库
    │   ├── labelstudio.py  # LS 导出 JSON 解析（旋转AABB、阶段提取）
    │   ├── split.py        # 确定性切分
    │   ├── stats.py        # 样本分布统计
    │   └── common.py       # 公共工具
    │
    ├── raw/
    │   ├── exports/           # LS 导出 JSON
    │   └── videos/            # 下载的视频
    ├── datasets/              # group 数据集输出
    └── datasets_actionmixed/  # 混合数据集输出

（原根目录的 upload_to_modelscope.py 上传 raw 数据脚本已归档至 archive/scripts/）
```

---

## 二、环境准备

```bash
cd cleansight-pipeline
pip install opencv-python-headless numpy pyyaml pillow ultralytics modelscope

# 如果训练/验证，还需 ultralytics（自动安装 PyTorch）
```

**Label Studio 连接**：确保 `config.py` 中配置了正确的 `LS_BASE_URL` 和 `LS_API_TOKEN`。

---

## 三、数据集概览

| 数据集                           | ModelScope                                                                | 组织方式                        | 类别    |
| ----------------------------- | ------------------------------------------------------------------------- | --------------------------- | ----- |
| **cleansight-raw**            | [链接](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)            | 原始 LS 导出 JSON               | —     |
| **cleansight-yolo**           | [链接](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)           | group1_large + group2_small | 见下    |

### group1_large

| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `hand` | 操作者手部 |
| 1 | `scope_control_body` | 内镜操控部 |
| 2 | `scope_mid_section` | 内镜中部 |

### group2_small

| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `syringe` | 注射器 |
| 1 | `air_gun` | 气枪 |
| 2 | `scope_distal_end` | 内镜头端 |
| 3 | `short_brush` | 短毛刷 |
| 4 | `brush_tip_out` | 刷头外露 |

> **cleansight-ActionSequence** 已弃用,脚本归档至 `archive/actionseq/`,不再构建;段级动作请以 cleansight-ActionMixed 为准。

---

## 四、快速开始

### 从零构建

```bash
cd cleansight-pipeline

# 1. 下载 LS 导出 JSON → raw/exports/
#    或从 LS 服务器拉取：
export LS_HOST=http://<LS地址>:8080  LS_TOKEN=<AccessToken>
python common/pull.py

# 2. 对账 & 分配 split
python common/reconcile.py        # 查看状态
python common/reconcile.py --assign  # 确定性回填 split

# 3. 构建数据集
python yolo/build.py           # group 数据集 → datasets/

# 4. 上传
python yolo/upload.py             # cleansight-yolo
# raw 上传脚本已归档至 archive/scripts/upload_to_modelscope.py
```

---

## 五、添加新标注任务

当 Label Studio 上有新的确认标注完成的任务需要加入数据集：

### 步骤 1：重新导出 LS 数据

在 LS 网页端重新导出 Project #10 的 JSON，放入：
- `cleansight-pipeline/raw/exports/`
- `raw-from Label Studio/`

### 步骤 2：加入白名单

编辑 `cleansight-pipeline/config.yaml`，在 `only_videos` 末尾追加：

```yaml
only_videos:
  - 4807dbbe-clip      # task#59
  - 65d70028-clip      # task#61
  - 63a848d5-clip      # task#68
  - xxxxxxxx-clip      # task#新ID  ← 新增
```

### 步骤 3：下载视频 & 分配 split

```bash
cd cleansight-pipeline

# 下载新视频
export LS_HOST=... LS_TOKEN=...
python common/pull.py

# 分配 split
python common/reconcile.py --assign
```

### 步骤 4：增量构建

```bash
# 增量模式：只处理新任务，已有任务秒级跳过
python yolo/build.py
```

> 如需全量重建：`python yolo/build.py --force`

### 步骤 5：增量上传

```bash
python yolo/upload.py
```

> ModelScope SDK 自带的 `.ms_upload_cache` 会自动只上传新增/变化的文件，已上传的秒级跳过。

---

## 六、日常维护

### 查看数据集状态

```bash
cd cleansight-pipeline
python common/reconcile.py
```

### 查看样本分布

```bash
python -c "from utils import stats; stats.main()"
```

### 同步 LS 最新数据

```bash
# 手动从 LS 网页下载 JSON，放入 raw/exports/
# （原 export_mix_label.py 已归档至 archive/scripts/）
```

### 调整采样密度

编辑 `config.yaml` 的 `stride` 值，然后 `--force` 重建：
```bash
python yolo/build.py --force
```

### 调整稀有类别阈值

编辑 `config.yaml` 的 `rare_threshold`，然后 `--force` 重建。

---

## 七、配置参考

### config.yaml

```yaml
groups:
  group1_large: [hand, scope_control_body, scope_mid_section]
  group2_small: [syringe, air_gun, scope_distal_end, short_brush, brush_tip_out]

only_videos:              # 只有这里列出的任务进数据集
  - 4807dbbe-clip
  - 65d70028-clip
  - 63a848d5-clip

stride: 4                 # 抽帧间隔（30fps 下 ≈7.5 fps）
jpg_quality: 90

rare_dense_sampling: true # 稀有类别密集采样
rare_threshold: 200       # keyframe 数低于此值触发密集采样

train:
  model: yolo11n.pt
  epochs: 100
  imgsz: 640
  batch: 16
  patience: 20
```

### splits.yaml

```yaml
assignments:
  4807dbbe-clip_1781659328328_1781659467929: train
  65d70028-clip_1781661552468_1781661702909: val
  63a848d5-clip_1782695363948_1782695590302: train
```

- 已分配的视频 split 永不自动重排，人工可改
- 新增视频由 `--assign` 按 `hash(seed:stem)` 确定性分配

---

## 八、脚本速查

| 脚本 | 用途 | 常用参数 |
|------|------|---------|
| `common/reconcile.py` | 四方对账 | `--assign` 回填 split |
| `common/pull.py` | 下载 LS 视频 | 需要 `LS_HOST` + `LS_TOKEN` 环境变量 |
| `yolo/build.py` | 构建 group 数据集 | `--auto-assign` `--force` |
| `yolo/augment.py` | 旋转/缩放增强（备用） | `--threshold=150 --copies=3 --dry-run` |
| `yolo/train.py` | YOLO 训练 | `yolo/train.py group2_small` |
| `yolo/validate.py` | 验收评估 | 输出 PASS/FAIL |
| `yolo/upload.py` | 上传 group 数据集 | — |

---

## 九、版本管理

### 增量构建机制

```
yolo/completed_tasks.json     ← 记录已处理任务的版本信息
    ↓
yolo/build.py 读取
    ↓
跳过 export + stride 未变的任务
    ↓
只处理新增/变化的任务
    ↓
.ms_upload_cache              ← SDK 维护，只传增量文件
```

### 强制全量重建

```bash
python yolo/build.py --force
```

以下情况需要 `--force`：
- 改了 `stride`、`jpg_quality`
- 改了 `config.yaml` 的 `groups`（增删类别）
- 修复了 `labelstudio.py` 的核心逻辑（如旋转 AABB）
- 换了新的 LS 导出 JSON

### 追踪文件

| 文件 | 内容 | 位置 |
|------|------|------|
| `DATASET_STATUS.md` | 数据集状态表 | 项目根目录 + ModelScope |
| `tracking.md` | 构建追踪表（自动生成） | `cleansight-pipeline/yolo/` |
| `completed_tasks.json` | 增量构建记录 | `cleansight-pipeline/yolo/` |

---

## Links

- Raw 数据：[lhh010/cleansight-raw](https://www.modelscope.cn/datasets/lhh010/cleansight-raw)
- Group 数据集：[lhh010/cleansight-yolo](https://www.modelscope.cn/datasets/lhh010/cleansight-yolo)
- 项目仓库：[lhh010/cleansight-dataset](https://github.com/lhh010/cleansight-dataset)
- ActionSequence 数据集（已归档,不再更新）：[lhh010/cleansight-ActionSequence](https://www.modelscope.cn/datasets/lhh010/cleansight-ActionSequence)
