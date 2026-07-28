# cleansight-pipeline · 数据集构建流水线

内镜清洗巡检的**自包含**数据流水线。同一份 Label Studio 导出 + 视频,派生 **2 套活跃数据集**,脚本**按数据集粒度分目录**:

| 数据集 | 目录 | 产物 | 说明 |
|--------|------|------|------|
| **yolo**(目标检测) | `yolo/` | `datasets/<组>/` | `videorectangle` bbox → 分组 YOLO 检测集。**两条独立轨**:训练轨(train/val,LS 项目 `yolo-train`)与 benchmark 轨(test,LS 项目 `yolo-test`,策展+冻结)——详见 [yolo/README.md](yolo/README.md) |
| **actionmixed**(动作识别/时序分割) | `actionmixed/` | `datasets_actionmixed/` | bbox + 逐帧动作标签同存,段级采样 |

> **ActionSequence**(按动作阶段切的检测子集)已从活跃流水线移除,脚本归档在仓库根 `archive/actionseq/`——它只能做"分阶段检测",不含动作序列标签,分割任务以段级 **ActionMixed** 为准。

**自包含**:输入、脚本、产物、依赖全部落在本目录内。所有命令都在 `cleansight-pipeline/` 下执行(脚本从这里 `import utils`)。

---

## 仓库结构

结构约定:**顶层是共享层(`utils/`、`raw/`、`config.yaml`);`common/` 放跨数据集编排;每个数据集一个子目录,内含自己的 build/上传脚本、配置清单与 state 文件。**

```
cleansight-pipeline/
  # ---- 共享层 ----
  config.yaml  # ⚠️ 现在只服务 actionmixed(yolo 的已下沉);待其也下沉后即可删除
  requirements.txt
  utils/            # 各脚本共用工具(不单独运行)。只懂 LS JSON 结构,不含业务语义
    common.py       # 定位根目录、加载 yaml 配置(ROOT=本目录)
    labelstudio.py  # LS 解析核心:fps 对齐、关键帧插值、坐标转换、按项目取导出
    split.py        # 确定性切分的纯函数(不再读写任何清单文件)
    stats.py        # 样本分布统计(扫描落盘 label,split 由调用方给)
    check.py        # 推送前数据集校验核心(判据由调用方按轨传入)
  raw/
    exports/<LS 项目>/  # 导出 JSON 按项目分子目录(入库);各取文件名排序最后一份
    videos/             # 下载的原始视频(不入库),各轨共用

  # ---- 跨数据集编排 ----
  common/
    reconcile.py         # 对账/增量前置:双轨状态表 + 待办;--assign 回填(仅训练轨)
    pull.py              # 从 LS 下视频到 raw/videos/(扫全部项目取并集)+ 完整性抽查
    check.py             # 推送前校验(yolo);按轨给判据
    upload_git.py        # 统一 git 版:一键把两套数据集全传 ModelScope(--dry-run)
    count_classes.py     # 跨数据集的类别计数报表
    scarce_sources.py    # 稀缺类的来源片段汇总
    scarce_checklist.py  # 稀缺类补采/补标清单

  # ---- 数据集:yolo(检测)—— 两轨解耦,详见 yolo/README.md ----
  yolo/
    classes.yaml      # 类别分组(两轨唯一共享配置)
    train.yaml        # 训练轨:配置 + 在册 task 清单(取代原 config+splits.yaml)
    test.yaml         # benchmark 轨:同上独立一份 + version/frozen_at
    build.py          # 训练轨 → datasets/<组>/{train,val}
    build_test.py     # benchmark 轨 → datasets/<组>/test
    builder.py        # 两轨共用构建引擎;frames.py 抽帧;dataset.py 落盘布局;manifest.py 清单
    augment.py        # 稀有类增强(备用,仅 train)
    upload.py         # SDK 上传 → cleansight-yolo(带校验门)
    completed_{train,test}.json   # 增量完成清单(state)
    tracking_{train,test}.md      # 生成的追踪表

  # ---- 数据集:actionmixed(动作识别)----
  actionmixed/
    build.py   # bbox+动作同存;段级内存哈希切分(无 per-video 清单)
    upload.py  # SDK 上传 → cleansight-ActionMixed
    completed_tasks_actionmixed.json
    tracking_actionmixed.md

  # ---- 产物(均不入库)----
  datasets/<组>/  datasets_actionmixed/
  .venv/
```

入库的只有:脚本、`config.yaml`、`yolo/*.yaml`、`requirements.txt`、各数据集的 state 文件(`completed_*`/`tracking*`)、`raw/exports/` 里的导出 JSON。`raw/videos/`、`datasets*/`、`.venv/` 及 `*.mp4` 由 `.gitignore` 排除。

### 各部分功能定位

| 部分 | 定位 | 何时用 |
|------|------|--------|
| `common/reconcile.py` | **对账中枢**:比对"导出/磁盘/清单"三方,按轨列待办;`--assign` 回填(仅训练轨) | 每次开工、每次增量前先跑 |
| `common/pull.py` | **取数**:扫全部项目的导出取并集,从 LS 下视频到 `raw/videos/` + 完整性抽查 | 有"未下载"视频时 |
| `common/check.py` | **推送前校验**:扫 yolo 产物,不达标拒推;判据按轨给 | 上传前 |
| `common/upload_git.py` | **一键全传**:git 方式把两套数据集推 ModelScope | 两套都就绪、要统一发布时 |
| `yolo/build.py` | 训练轨:导出+视频 → `datasets/<组>/{train,val}`,按 `train.yaml` 清单整条路由 | 训练数据/归属变化后重建 |
| `yolo/build_test.py` | benchmark 轨:独立项目 → `datasets/<组>/test`,策展 + 冻结 | benchmark 清单变化后重建 |
| `actionmixed/build.py` | 动作识别转换:bbox+动作同存,段级采样 | mixed 数据变化后重建 |
| `<数据集>/upload.py` | 该数据集单独上传(SDK,yolo 带校验门) | 只发布某一套时 |
| `yolo/{classes,train,test}.yaml` | **yolo 的改动入口**:类别、数据源、产物路径、抽帧参数、在册清单 | 调 yolo 任何行为先改它们,别改脚本 |
| `config.yaml` | 只剩 actionmixed 用(其 yolo 部分已下沉) | 调 actionmixed 行为 |
| `utils/` | 各脚本共用逻辑,尤其 `labelstudio.py`(fps 对齐/插值/坐标)集中一份 | 改脚本时复用,别各写一套 |

---

## 环境

自带虚拟环境,不复用外部 venv。本仓库**只做数据**,依赖很轻:`cv2`、`numpy`、`pyyaml`、`pillow`;`upload.py` 另需 `modelscope`。模型训练与评测不在本仓库,故不需要 torch/ultralytics。

```bash
cd cleansight-pipeline
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

下文用 `.venv/bin/python` 跑脚本(装了这几个包的系统 `python3` 也行)。

---

## 使用流程

### 场景一:生成数据集(拉数据 → 转两套)

```bash
cd cleansight-pipeline
export LS_HOST=http://<LS地址>:8080 LS_TOKEN=<AccessToken>
# 把 LS 导出 JSON 按项目放进 raw/exports/{yolo-train,yolo-test}/
.venv/bin/python common/pull.py                # 1. 下视频到 raw/videos/(各项目取并集)
.venv/bin/python common/reconcile.py           # 2. 看双轨对账;质检合格的登记进对应清单
.venv/bin/python common/reconcile.py --assign  # 3. 训练轨未登记 task 确定性回填(写回 yolo/train.yaml,提交它)
.venv/bin/python yolo/build.py                 # 4a. 训练轨 → datasets/<组>/{train,val}
.venv/bin/python yolo/build_test.py            # 4b. benchmark 轨 → datasets/<组>/test
.venv/bin/python actionmixed/build.py          # 4c. 动作识别集 → datasets_actionmixed/
```

各 `build` 会打印逐 split × 逐类的帧数/框数,并对"尾部覆盖 < 80%""某类某 split 无样本"等给出告警——务必扫一眼。样本分布可随时独立重算:`.venv/bin/python common/count_classes.py`。

> benchmark 轨的 `test.yaml` 清单为空时 `build_test.py` 会正常结束并提示——在 LS 项目 `yolo-test` 产出首批标注前,这是预期状态。

### 场景二:增量更新(有新导出/新视频时——每次这么走)

```bash
# 把新的 LS 导出 JSON 放进 raw/exports/<项目>/
.venv/bin/python common/reconcile.py           # 看差异:未登记/遗失/导出缺失/孤儿
.venv/bin/python common/pull.py                # 补下缺的视频
.venv/bin/python common/reconcile.py --assign  # 训练轨:回填"未登记"(已在册的不变 → 天然增量)
# benchmark 轨:人工把选定的 task id 登记进 yolo/test.yaml(策展决策,不自动回填)
.venv/bin/python yolo/build.py                 # 重建(增量跳过已完成 task)
.venv/bin/python yolo/build_test.py
.venv/bin/python actionmixed/build.py
.venv/bin/python common/check.py --strict      # 推送前校验
```

`common/reconcile.py` 的分类与动作(按轨分别列):

| 分类 | 含义 | 该做什么 |
|------|------|---------|
| 未登记 | 导出里有但清单没有 | 人工质检后登记进对应清单;训练轨可 `--assign` 回填 |
| 遗失/未下载 | 在册但视频不在磁盘 | 跑 `common/pull.py`;确已作废则从清单删(不自动删) |
| 导出缺失 | 在册但导出里查无此 task | 导出过期,或 task 已在 LS 删除 |
| 孤儿 | 磁盘有但任何导出都没引用 | 陈旧下载,可清理 |

**增量的粒度是 LS task**。每个 task 在 `completed_*.json` 里存一份**重建签名**,四项任一变化就清掉它的旧产物重建,否则 `[skip]` 连视频都不解码:

| 签名项 | 变了意味着 |
|---|---|
| `annotations` | 该 task 标注内容的指纹(sha1)。**只有这条 task 的标注真的改了才重建它** |
| `sampling` | 抽帧/编码参数(stride、jpg_quality、空帧、密采阈值……)全量指纹 |
| `rare` | 稀有类集合。它由全部在册 task 共同决定 —— 某类跨过阈值后,已建好的 task 里那些密采帧就过时了 |
| `split` | 归属。手工把清单里的 `val` 改回 `train`,帧要真的搬过去 |

> 签名里**刻意不含导出文件名**。LS 每次导出的文件名都带时间戳,拿它当签名会让"放一份新导出"退化成全量重建 —— 增量在最常用的那个场景里恰好失效。导出文件名仍记在 `completed_*.json` 的 `export` 字段里备查,但不参与比对。

**增量之所以安全**:清单里已在册 task 的 split 永不被自动改动,`--assign` 只回填新 task → 天然增量,重建不会打乱既有划分。帧名 `t{task_id}_*` 让清理能精确删掉某个 task 的产物而不误伤别人。

**已知缺口**:从清单里删掉一个 task,它已落盘的帧不会被自动清理(成为孤儿),`completed_*.json` 里的记录也留着。目前只能 `--force` 全量重建来消除。

> ⚠️ 校验与对账的整体口径待重新明确(尤其 benchmark 达标的定义:覆盖率?每桶最少样本?还是只出报告不判 PASS/FAIL),本轮 `reconcile.py` / `check.py` 只做了"能跑"的最小适配,逻辑未重构。

### 场景三:上传 ModelScope

```bash
# 单独发布某一套(SDK,yolo 上传前自动校验)
.venv/bin/python yolo/upload.py               # → cleansight-yolo
.venv/bin/python actionmixed/upload.py        # → cleansight-ActionMixed
# 或一键全传(git 方式)
.venv/bin/python common/upload_git.py --dry-run
```

各数据集的 ModelScope 仓库 ID 在仓库根 `config.py`(由 `config.example.py` 复制填写,含密钥,不入库)。

---

## 额外考量(设计契约,改动前先读)

### 1. 数据来源与关联

- **标注**:LS 导出 JSON 放 `raw/exports/<项目>/`,**按 LS 项目分子目录**,各取文件名排序最后一份。检测轨的两个项目(`yolo-train` / `yolo-test`)互不相干;actionmixed 读哪个项目由 `config.exports_project` 指定。
- **视频**:存 LS 服务器,`common/pull.py` 扫全部项目的导出取并集,下到 `raw/videos/`(各轨共用一个目录)。
- **身份 = LS task id**,不是文件名。视频在 LS 重传会换 uuid 前缀、文件名跟着变,而 task id 是数据库主键、全局递增、跨项目唯一。因此 yolo 的清单只登记 task id,视频名 build 时从 `task.data.video` 现查。
- `common/reconcile.py` 对齐"导出/磁盘/清单"三方(原先是四方——"已质检"与"已定 split"已合并成清单里的一条登记记录)。

### 2. 关键帧对齐(不做就框漂移 + 尾部丢标注)

- LS 的 `sequence` 只存**关键帧**,中间帧**线性插值**得框;`enabled=False` = 目标离场那段不出框。
- LS 帧号按**标注端 fps**(`ls_fps = framesCount/duration`)计,真实 fps 往往不同 → 用 `scale = ls_fps/real_fps`、`ls_frame = real_frame × scale` 把真实解码帧号映射回 LS 帧号。**绝不能拿真实帧号直接查框**。
- 逻辑集中在 `utils/labelstudio.py`,勿各写一套。自查:每视频"尾部覆盖 ≈ 100%"(`build` 会打印,<80% 告警)。

### 3. 采样帧率

- `config.stride`:每隔 N 个真实帧抽 1 张。调 `stride` 改抽帧密度(越小越密、图越多)。
- **只有"含目标框"的帧才落盘**,空帧丢弃,避免大量负样本稀释。
- 稀有类(总框数 < `rare_threshold`)在正常 stride 外**额外密集采样相邻帧**,自然增加样本,避免人工增强失真。

### 4. 切分契约(重点 —— 与旧版相反,注意)

**yolo 的 test 不再是从训练池随机 hold-out 的。** 它来自独立的 LS 项目 `yolo-test`,是策展 + 冻结的 benchmark,整条源不进 train/val。旧版把 `test` 当作 `hash(seed:stem)` 切出来的第三份,那实质只是 val 的第二份,不能当评测尺子。

- **各轨清单是唯一真源**:`yolo/train.yaml` 的 `tasks`(task id → train/val)、`yolo/test.yaml` 的 `tasks`(恒 test)。人工可改,永不被自动重排。
- **两表 task id 零交集**,由 `yolo/manifest.py` 的 `assert_disjoint()` 强制(源头就是两个独立 LS 项目)。
- 未登记 task 由 `--assign` 按 `hash(seed:task_id)` **确定性**落到 train/val 并写回清单——**只作用于训练轨**;benchmark 入册是人工策展决策(选哪条片当评测集),不自动回填。
- 回填是**显式步骤**,不在 build 里静默改动(`yolo/build.py --auto-assign` 可当场回填,但会打印并要求 review)。
- **同一 task 永远同一 split**、新增不打乱已有、**一个 task 的所有帧只进一个 split**——杜绝时间相邻泄漏。帧名 `t{task_id}_{frame:06d}` 让这一条可被 `utils/check.py` 直接校验。
- **actionmixed 不用 per-video 清单**:它按**段级内存哈希**(seeded by `config.seed`)在内存中分 split。

### 5. 数据集格式规范

- **label 文件**:每行一个框 `class_id cx cy w h`,均为**归一化 [0,1]**;yolo 各组 `class_id` 从 0 起(顺序即 `yolo/classes.yaml` 的 groups);actionmixed 用统一 8 类映射。
- **图片命名**:`t{task_id}_{frame:06d}.jpg`(密采帧加 `_dense`、增强帧加 `_aug{n}`)。不含视频名(会随 LS 重传变)、不含导出下标(增删 task 就重排)。
- **空标签文件**是合法的:benchmark 轨保留空帧作负样本(`sampling.keep_empty_frames`),训练轨则丢弃空帧。
- **坐标约定**:LS 左上角百分比 → YOLO 归一化中心点 `(cx,cy,w,h)`,裁剪到 [0,1];旋转框自动转 AABB。
- **类别**:只能**追加到 `yolo/classes.yaml` 的列表末尾**,插中间会打乱已训权重的 class id 映射。
- 转换后核对:每视频"尾部覆盖"接近 100%;抽一帧反归一化画框确认落在目标上。

### 6. 边界:本仓库只做数据

模型训练、评测、验收门槛、权重与报告**都不在本仓库**。这里的产物止于"一份可用的数据集 + 它的追踪表",训练侧拿走 `datasets/<组>/data.yaml` 自行开跑。

因此:
- 依赖里没有 torch/ultralytics;`common/check.py` 校验的是**数据**是否自洽(结构、标注合法性、split 覆盖、泄漏),不是模型是否达标。
- `yolo/train.yaml` 文件名里的 `train` 指的是 **split**,不是模型训练。
- 数据侧关心的两件事按轨分开:训练轨看**数据量与分布**,benchmark 看**等价类覆盖**。后者的口径(覆盖率?每桶最少样本?)尚未定稿,见 §7 下方说明。

### 7. 关键约定速查(改脚本别破坏)

- **yaml 只放真会变的**:数据源、路径、抽帧参数、比例、清单、门槛。结构固定的东西(YOLO 的 `train`/`val`/`test` 布局、state 文件命名规则、标签行格式)留在代码里,否则配置就成了摆设。
- **`utils/` 只懂 LS JSON 结构,不含业务语义**。检测的等价类与时序的等价类设计不同,不要为了"通用"硬抽象——各数据集的判据留在各自目录(`yolo/` 里的 `manifest.py` / `frames.py` / `dataset.py` 只服务 yolo)。
- 所有路径以 pipeline 根为基(`utils/common.py` 的 `ROOT`),别往上级目录写,破坏自包含。
- 移入子目录的脚本靠顶部 `sys.path.insert(..., parent)` 引导才能 `import utils`——别删。
- 各数据集的 state 文件(`completed_*`/`tracking*`)放在**各自子目录**,别写回 pipeline 根。
- fps 对齐、插值、坐标转换集中在 `utils/labelstudio.py`,共用一份。
- 类别只能追加到 `yolo/classes.yaml` 末尾。
- 样本分布不放 `reconcile`(它是无解码、秒级对账工具),由 `build` / `common/count_classes.py` 统计。

---

## 相关

- 已失效/一次性脚本(旧 project-10 单仓库上传、LFS 修复、mix-label 导出)已移入仓库根 `archive/`。
- 数据集卡片文档见仓库根 `README.md` / `USAGE.md`。
