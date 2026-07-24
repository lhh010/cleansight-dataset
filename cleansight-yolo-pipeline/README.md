# cleansight-pipeline · 数据集构建/训练/评测流水线

内镜清洗巡检的**自包含**数据流水线。同一份 Label Studio 导出 + 视频,派生 **2 套活跃数据集**,脚本**按数据集粒度分目录**:

| 数据集 | 目录 | 产物 | 说明 |
|--------|------|------|------|
| **yolo**(目标检测) | `yolo/` | `datasets/<组>/` | `videorectangle` bbox → 分组 YOLO 检测集,含训练/验收 |
| **actionmixed**(动作识别/时序分割) | `actionmixed/` | `datasets_actionmixed/` | bbox + 逐帧动作标签同存,段级采样 |

> **ActionSequence**(按动作阶段切的检测子集)已从活跃流水线移除,脚本归档在仓库根 `archive/actionseq/`——它只能做"分阶段检测",不含动作序列标签,分割任务以段级 **ActionMixed** 为准。

**自包含**:输入、脚本、产物、依赖全部落在本目录内。所有命令都在 `cleansight-yolo-pipeline/` 下执行(脚本从这里 `import utils`)。

---

## 仓库结构

结构约定:**顶层是共享层(`utils/`、`raw/`、`config.yaml`、`splits.yaml`);`common/` 放跨数据集编排;每个数据集一个子目录,内含自己的 build/训练/上传脚本与 state 文件。**

```
cleansight-yolo-pipeline/
  # ---- 共享层 ----
  config.yaml            # 中央配置:分组/白名单/抽帧/切分/超参/验收阈值 —— 改这里
  splits.yaml            # 视频 -> split 划分清单,稳定切分唯一真源(yolo 用)
  requirements.txt
  utils/                 # 各脚本共用工具(不单独运行)
    common.py            # 定位根目录、加载 config、白名单判断(ROOT=本目录)
    lsexport.py          # LS 解析核心:fps 对齐、关键帧插值、坐标转换
    split.py             # 稳定切分逻辑(读写 splits.yaml)
    stats.py             # 样本分布统计(扫描落盘 label)
    check.py             # 推送前数据集校验核心
  raw/
    exports/             # LS 导出 JSON(入库);脚本取文件名排序最后一份
    videos/              # 下载的原始视频(不入库)

  # ---- 跨数据集编排 ----
  common/
    00_status.py         # 对账/增量前置:列出待办;--assign 回填 split
    01_pull_data.py      # 从 LS 下视频到 raw/videos/ + 完整性抽查
    05_check.py          # 推送前校验(yolo)
    upload_all.py        # 统一 git 版:一键把两套数据集全传 ModelScope(--dry-run)
    count_classes.py     # 跨数据集的类别计数报表
    parse_tasks.py       # 解析导出,建立 task→视频→类 映射
    build_checklist.py   # 稀缺类补采/补标清单

  # ---- 数据集:yolo(检测)----
  yolo/
    02_build.py          # 转 YOLO,按 splits.yaml 整段路由,打印样本分布
    02b_augment.py       # 稀有类别数据增强(备用,仅 train)
    03_train.py          # 各组训练
    04_validate.py       # 验证集指标 + 验收判定 + 报告
    upload.py            # SDK 上传 → cleansight-yolo(带校验门)
    completed_tasks.json # 增量完成清单(state)
    tracking.md          # 生成的追踪表

  # ---- 数据集:actionmixed(动作识别)----
  actionmixed/
    02_build.py          # bbox+动作同存;段级内存哈希切分(不碰 splits.yaml)
    upload.py            # SDK 上传 → cleansight-ActionMixed
    completed_tasks_actionmixed.json
    tracking_actionmixed.md

  # ---- 产物(均不入库)----
  datasets/<组>/  datasets_actionmixed/  runs/<组>/
  .venv/
```

入库的只有:脚本、`config.yaml`、`splits.yaml`、`requirements.txt`、各数据集的 state 文件(`completed_*`/`tracking*`)、`raw/exports/` 里的导出 JSON。`raw/videos/`、`datasets*/`、`runs/`、`.venv/` 及 `*.pt`/`*.mp4` 由 `.gitignore` 排除。

### 各部分功能定位

| 部分 | 定位 | 何时用 |
|------|------|--------|
| `common/00_status.py` | **对账中枢**:比对"导出/磁盘/splits/白名单"四方,列出待办;`--assign` 回填 split | 每次开工、每次增量前先跑 |
| `common/01_pull_data.py` | **取数**:按导出 JSON 从 LS 下视频到 `raw/videos/` + 完整性抽查 | 有"未下载"视频时 |
| `common/05_check.py` | **推送前校验**:扫 yolo 产物,不达标拒推 | 上传前 |
| `common/upload_all.py` | **一键全传**:git 方式把两套数据集推 ModelScope | 两套都就绪、要统一发布时 |
| `yolo/02_build.py` | yolo 转换:导出+视频 → 分组 YOLO 集,按 `splits.yaml` 整段路由 | 数据/切分变化后重建 |
| `yolo/03_train.py` · `yolo/04_validate.py` | yolo 训练 / 验收(阈值门禁,FAIL 退出码非零) | 出/更新权重、交付卡口 |
| `actionmixed/02_build.py` | 动作识别转换:bbox+动作同存,段级采样 | mixed 数据变化后重建 |
| `<数据集>/upload.py` | 该数据集单独上传(SDK,yolo 带校验门) | 只发布某一套时 |
| `config.yaml` | **唯一改动入口**:分组、白名单、抽帧、切分、超参、验收阈值 | 调任何行为先改它,别改脚本 |
| `splits.yaml` | **切分唯一真源**:视频 stem→split,人工可改、入库(yolo 用) | 手工调整 train/val/test 归属 |
| `utils/` | 各脚本共用逻辑,尤其 `lsexport.py`(fps 对齐/插值/坐标)集中一份 | 改脚本时复用,别各写一套 |

---

## 环境

自带虚拟环境,不复用外部 venv。数据阶段(`00`/`01`/`02`)只需 `cv2`、`numpy`、`pyyaml`;训练/验证(`03`/`04`)另需 `ultralytics`(含 torch);`upload.py` 需 `modelscope`。

```bash
cd cleansight-yolo-pipeline
python3 -m venv .venv
# 只做数据(无需 torch)
.venv/bin/pip install opencv-python-headless numpy pyyaml
# 要训练/验证:装全部依赖(含 ultralytics/torch)
.venv/bin/pip install -r requirements.txt
```

下文用 `.venv/bin/python` 跑脚本(数据阶段用系统 `python3` 也行,只要装了前三个包)。

---

## 使用流程

### 场景一:生成数据集(拉数据 → 转两套)

```bash
cd cleansight-yolo-pipeline
export LS_HOST=http://<LS地址>:8080 LS_TOKEN=<AccessToken>
# 把 LS 导出 JSON 放进 raw/exports/
.venv/bin/python common/01_pull_data.py     # 1. 下视频到 raw/videos/
.venv/bin/python common/00_status.py        # 2. 看对账;质检合格的加进 config.only_videos
.venv/bin/python common/00_status.py --assign  # 3. 给已质检视频确定性回填 split(写回 splits.yaml,提交它)
.venv/bin/python yolo/02_build.py           # 4a. yolo 检测集 → datasets/
.venv/bin/python actionmixed/02_build.py    # 4b. 动作识别集 → datasets_actionmixed/
```

各 `02_build.py` 会打印逐 split × 逐类的帧数/框数,并对"每视频尾部覆盖 < 80%""某类 val 无样本"等给出告警——务必扫一眼。样本分布可随时独立重算:`.venv/bin/python common/count_classes.py`。

### 场景二:训练与评估(仅 yolo)

```bash
.venv/bin/python yolo/03_train.py           # 各组训练;权重落 runs/<组>/weights/best.pt
.venv/bin/python yolo/04_validate.py        # 验证集指标 + 验收报告 runs/<组>/acceptance_report.md
```

- 训练:`config.train.model`(默认 `yolo11n.pt`),各组一套独立权重;超参在 `config.train`。
- 评估:在 **val** 上跑 `ultralytics.val`,逐类 P/R/mAP 对照 `config.acceptance` 判 PASS/FAIL;**任一组 FAIL → 退出码非零**,可做交付卡口。

### 场景三:增量更新(有新导出/新视频时——每次这么走)

```bash
# 把新的 LS 导出 JSON 放进 raw/exports/
.venv/bin/python common/00_status.py           # 看差异:未下载/未质检/未归属/遗失/孤儿
.venv/bin/python common/01_pull_data.py        # 补下"未下载"
# 人工质检合格的,追加到 config.yaml 的 only_videos
.venv/bin/python common/00_status.py --assign  # 回填"未归属"(已有视频 split 不变 → 天然增量)
.venv/bin/python yolo/02_build.py              # 重建(增量跳过已完成任务)
.venv/bin/python actionmixed/02_build.py
.venv/bin/python yolo/04_validate.py           # (如重训了)重新验收
```

`common/00_status.py` 的分类与动作:

| 分类 | 含义 | 该做什么 |
|------|------|---------|
| 未下载 | 导出引用了但磁盘没有 | 跑 `common/01_pull_data.py` |
| 未质检 | 已下载但不在 `only_videos` | 人工质检后追加到 `config.only_videos` |
| 未归属 | 已质检但 `splits.yaml` 无 split | 跑 `common/00_status.py --assign` |
| 遗失 | `splits.yaml` 有但磁盘没有 | 重下,或从 `splits.yaml` 删(不自动删) |
| 孤儿 | 磁盘有但导出没引用 | 陈旧下载,可清理 |

**增量之所以安全**:`splits.yaml` 里已有视频的 split 永不被自动改动,`--assign` 只回填新视频 → 天然增量,重建不会打乱既有划分。

### 场景四:上传 ModelScope

```bash
# 单独发布某一套(SDK,yolo 上传前自动校验)
.venv/bin/python yolo/upload.py               # → cleansight-yolo
.venv/bin/python actionmixed/upload.py        # → cleansight-ActionMixed
# 或一键全传(git 方式)
.venv/bin/python common/upload_all.py --dry-run
```

各数据集的 ModelScope 仓库 ID 在仓库根 `config.py`(由 `config.example.py` 复制填写,含密钥,不入库)。

---

## 额外考量(设计契约,改动前先读)

### 1. 数据来源与关联

- **视频**:存 LS 服务器,`common/01_pull_data.py` 下到 `raw/videos/`;**身份 = 文件名 stem**(如 `687e3c78-clip_<起>_<止>`)。
- **标注**:LS 导出 JSON 放 `raw/exports/`,脚本取**文件名排序最后一份**。同一份导出里 bbox(`videorectangle`)与时序(`timelinelabels`)聚合,两套 build 各取所需。
- 视频与标注靠 `task.data.video` 的文件名关联;`common/00_status.py` 对齐"导出/磁盘/splits/白名单"四方。

### 2. 关键帧对齐(不做就框漂移 + 尾部丢标注)

- LS 的 `sequence` 只存**关键帧**,中间帧**线性插值**得框;`enabled=False` = 目标离场那段不出框。
- LS 帧号按**标注端 fps**(`ls_fps = framesCount/duration`)计,真实 fps 往往不同 → 用 `scale = ls_fps/real_fps`、`ls_frame = real_frame × scale` 把真实解码帧号映射回 LS 帧号。**绝不能拿真实帧号直接查框**。
- 逻辑集中在 `utils/lsexport.py`,勿各写一套。自查:每视频"尾部覆盖 ≈ 100%"(`02_build` 会打印,<80% 告警)。

### 3. 采样帧率

- `config.stride`:每隔 N 个真实帧抽 1 张。调 `stride` 改抽帧密度(越小越密、图越多)。
- **只有"含目标框"的帧才落盘**,空帧丢弃,避免大量负样本稀释。
- 稀有类(总框数 < `rare_threshold`)在正常 stride 外**额外密集采样相邻帧**,自然增加样本,避免人工增强失真。

### 4. 稳定切分契约(重点)

- **`splits.yaml` 是唯一真源**:`视频stem -> train/val/test/e2e_test`。人工可改,永不被自动重排。**yolo 用**(`utils/split.py` 的 `SPLITS_PATH`)。
- **actionmixed 不用 `splits.yaml`**:它按**段级内存哈希**(seeded by `config.seed`)在内存中分 split,不落 per-video 清单。
- 未归属视频由 `--assign` 按 `hash(seed:stem)` **确定性**落到 train/val/test,并写回清单。
- **同一视频永远同一 split**、新增视频不打乱已有、**一个视频的所有帧只进一个 split**——杜绝时间相邻泄漏,指标可信可复现。
- `test`/`e2e_test` 视频**不进** YOLO 数据集,预留端到端评测。
- 回填是**显式步骤**(`--assign`),不在 `build` 里静默改动;`02_build` 遇未归属视频报错提示(或 `--auto-assign` 当场回填)。

### 5. 数据集格式规范

- **label 文件**:每行一个框 `class_id cx cy w h`,均为**归一化 [0,1]**;yolo 各组 `class_id` 从 0 起(顺序即 `config.groups`);actionmixed 用统一 8 类映射。
- **图片命名**:`{task:02d}_{stem12}_{frame:06d}.jpg`。
- **坐标约定**:LS 左上角百分比 → YOLO 归一化中心点 `(cx,cy,w,h)`,裁剪到 [0,1];旋转框自动转 AABB。
- **类别**:只能**追加到 `config.groups` 列表末尾**,插中间会打乱已训权重的 class id 映射。
- 转换后核对:每视频"尾部覆盖"接近 100%;抽一帧反归一化画框确认落在目标上。

### 6. 模型验收标准(yolo)

`yolo/04_validate.py` 在**验证集**上跑 `ultralytics.val`,逐类 P/R/mAP 对照 `config.acceptance` 判 PASS/FAIL,写 `runs/<组>/acceptance_report.md`。默认门槛(在 `config.yaml` 调):整体 mAP@0.5 ≥ 0.5、mAP@0.5:0.95 ≥ 0.3、逐类 recall ≥ 0.7、precision ≥ 0.5、每类都要有验证样本。

> ⚠️ 当前数据集很小,大概率 FAIL,**属实**——先把流程与门槛立起来,数据变多后再收紧。

### 7. 关键约定速查(改脚本别破坏)

- 所有路径以 pipeline 根为基(`utils/common.py` 的 `ROOT`),别往上级目录写,破坏自包含。
- 移入子目录的脚本靠顶部 `sys.path.insert(..., parent)` 引导才能 `import utils`——别删。
- 各数据集的 state 文件(`completed_*`/`tracking*`)放在**各自子目录**(脚本里 `HERE`),别写回 pipeline 根。
- fps 对齐、插值、坐标转换集中在 `utils/lsexport.py`,共用一份。
- 类别只能追加到 `config.groups` 末尾。
- 样本分布不放 `00_status`(它是无解码、秒级对账工具),由 `02_build` / `common/count_classes.py` 统计。

---

## 相关

- 已失效/一次性脚本(旧 project-10 单仓库上传、LFS 修复、mix-label 导出)已移入仓库根 `archive/`。
- 数据集卡片文档见仓库根 `README.md` / `USAGE.md`。
