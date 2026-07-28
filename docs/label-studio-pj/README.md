# CleanSight · Label Studio 采集设计总览

> 服务对象:**两模型推理链路**——上游 `cleansight-yolo`(逐帧目标检测)+ 下游时序动作分割(`cleansight-ActionMixed`)。
> 本文是各 LS 项目的**总纲与路由**;每个项目的 labeling config、采集清单、隔离规则见各自 `*.md`。

---

## 0. 为什么要解耦(读之前先懂这个)

链路是两段式:**YOLO 抽帧检测 → 时序模型在 YOLO 输出上做动作分割**。两个模型是**分开训练**的,而且:

1. **YOLO 在上游、且是时序造数据的前置**:时序训练要吃 YOLO 的框,YOLO 不达标,时序连输入都造不出来。所以**先把 YOLO 拉起来**是关键路径。
2. **框的出处铁律**:喂给**时序训练**的框,**来自 YOLO 推理,不是手标**。理由是训练-推理一致性——上线时时序模型吃的是 YOLO 带噪声的框,训练时也必须吃 YOLO 的框,否则分布漂移。
3. **两套 coverage 维度正交**:YOLO 看**外观空间**(角度/光照/遮挡/尺度),时序看**行为空间**(动作类型/时长/转场)。同一份素材无法同时满足两套采样口径,硬绑对两边都平庸 → **选材与送标分两条轨**。

> 推论:**训练侧不再混标**。手标框只在**评测侧**保留(那里 GT 框用来算上限、做 gap 测试、当对抗信号)。"一条视频只服务一个模型"是**正确结果**,不是退步。

---

## 1. 项目矩阵(两条轨 × 训练/评测)

评测侧和训练侧一样,**按检测轨 / 动作轨分开**;差别只在:训练侧动作轨纯动作(框走 YOLO),**评测侧动作轨故意混标**(留 GT 框做 gap 测试,见 §2.1)。

**检测轨(detection-label · 标框)**

| 阶段 | 项目 | 标什么 | 服务 | coverage / 生命周期 |
|------|------|--------|------|----------|
| 训练 | **yolo-train** | 纯 bbox | YOLO 训练(**主**) | 外观空间,滚动 |
| 评测 | **yolo-test** | bbox + `ec_tags`(clip 级) | 检测 benchmark | 检测难度桶,冻结 |

**动作轨(action-label · 标动作)**

| 阶段 | 项目 | 标什么 | 服务 | coverage / 生命周期 |
|------|------|--------|------|----------|
| 训练 | **action-train** 🆕 | 纯动作(**不标框**) | 时序训练 | 行为空间,滚动 |
| 评测 | **action-test**(=动作轨评测) | **动作 + GT 框** + ec_env + 对抗 | 时序 benchmark + gap 测试 + GT 上限 | P0/P1 密集,冻结 |

**退役**:~~mixed-train~~(bbox+动作混标的训练项目)→ 存量当 bootstrap,不再新采。

> 四个项目名对称:`{yolo,action}-{train,test}`,一眼看出"哪条轨 + 训练还是评测"。`action-test` 的"混标"(动作 + GT 框)是它作为评测的**手段**(做 gap 测试),不是独立品类。
>
> **EC tag 设计(两套形式,有意为之)**:检测 test 用 **clip 级 `ec_tags`**(测试片裁成单一条件,整片一个 tag),动作 test 用 **段级 `ec_env` timeline**(整段测、条件按时段出现,须逐段标)——**形式不同是因为测试单元不同**(det 可散帧/单一条件短片,seg 必须整条序列),不是遗留待改。两套词表的逐项映射见 [§7 共享口径](#7-共享口径标签集--ec-词表映射--优先级)。几何桶(尺度/遮挡/拥挤)一律由 build **从框自动派生、不打 tag**——详见 [yolo-test.md](yolo-test.md)。

---

## 2. 框的出处铁律(整套设计的地基)

| 数据 | 框从哪来 | 为什么 |
|------|---------|--------|
| YOLO 训练/评测(检测轨) | **手标** | 框就是产品本身 |
| 时序**训练**(action-train) | **YOLO 推理 + 缓存** | 训练-推理一致:上线吃 YOLO 框,训练也得吃 YOLO 框 |
| 时序**评测**(action-test) | **手标(GT)+ YOLO 推理,两版都要** | 见 §2.1 gap 测试 |

所以:**`action-train` 里没有 `VideoRectangle`,标注员不碰框**;时序 build 时用训好的 YOLO 在这些视频上推理出框、缓存,再配上手标的动作段。

### 2.1 为什么评测侧动作轨要混标(和训练侧相反)

训练和评测**目的相反**,所以对框的取舍相反:

| | 训练侧动作轨 | 评测侧动作轨 |
|---|---|---|
| 目的 | 训练-推理**一致性** | 框来源的**可比性** |
| 框 | 只用 YOLO 推理(纯动作项目) | **手标 GT + YOLO 推理,两版并存** |
| 用法 | 让时序模型习惯 YOLO 噪声 | 同一批评测视频、同一个时序模型,分别喂 GT 框和 YOLO 框,量出 **gap = 检测端给下游拖了多少后腿** |

这就是 `action-test` 保留手标框的**唯一理由**:它需要 GT 框当对照组。gap 小 → YOLO 达标;gap 大 → 瓶颈在检测端。GT 框顺带还是**上限基线**和对抗-可见性("在场未操作")的信号源。

---

## 3. 存量 mixed 数据的去向(现有 16 个视频)

存量已 bbox + 动作全标,是两条轨共同的 **bootstrap 种子**。按两阶段复用,**导出不搬**,留 `raw/exports/` 当真源:

1. **阶段一(现在)**:全部先派生成 **YOLO 训练集**(`datasets/`)→ 训 YOLO → 用 gap 测试判达标。
2. **阶段二(YOLO 达标后)**:同一份导出取**动作标签** + 用训好的 YOLO 推框 → **时序训练集**(`datasets_temporal/`)。
3. **留 ~3 条不进 YOLO 训练**,划归 `action-test`(= `handeval`):两个模型都没训过 → 既当时序诚实评测集,又当 GT-box 上限,还兼 yolo_test。

> 存量数据是在**没有任何一方 coverage 视角**下采的——是起点,不是目标分布。增量按 §1 两条轨各自补。

---

## 4. 两条 coverage 维度(增量选材的判据)

| | YOLO 轨(yolo-train) | 时序轨(action-train) |
|---|---|---|
| coverage = | 每类目标的外观都见过 | 每种动作/转场/时长都见过 |
| 数据单元 | 单帧,帧间尽量多样、去近重复 | 完整连续段,保时序上下文 |
| 平衡看 | 框级(逐类框数 / 逐类 P/R) | 段级(每种动作实例数、转场组合) |
| "加数据"= | 加视觉多样性(可散帧/短片/难例) | 加完整动作序列 |
| 缺口清单工具 | `common/scarce_checklist.py`(已有,按检测类) | **待建:按动作类/转场的缺口清单**(对标前者) |

> 时序轨目前缺一套**动作 coverage 清单**(对标检测侧的 `scarce_checklist.py`)——这是解耦后要补的工具。

---

## 5. 送标决策流(来了一段新素材,进哪个项目)

```
是 benchmark/eval 用途(源级隔离、要冻结)?
├─ 是 → 需要动作语义? → 是: action-test   否: yolo-test
└─ 否(训练侧)
     ├─ 目的是补检测短板(某类 P/R 低)      → yolo-train(纯框)
     └─ 目的是补动作/转场覆盖              → action-train(纯动作,不标框)
```

- 同一段原始视频**可以**分别进两条训练轨(各标各的),但那是偶然,不是要求;别为"一次标全"去混标。
- 训练侧优先看**最新一轮评测的短板**:YOLO 逐类 P/R 掉的 → yolo 轨;时序动作/转场缺的 → 动作轨。

---

## 6. 红线(违反即数据不可信)

1. **时序训练框不得手标**:一律走 YOLO 推理。手标框只在 `action-test`。
2. **评测源零重叠**:`action-test` / `yolo-test` 的源写入 `benchmark_test.yaml`,训练侧项目 hard-exclude,且不得为同场次相邻片段。
3. **同视频不跨 split**:一条视频所有帧只进一个 split。
4. **handeval 不进 YOLO 训练**:否则在其上跑 YOLO 出框做 gap 测试会虚低(YOLO 见过 → 框偏乐观)。

---

## 7. 共享口径(标签集 · EC 词表映射 · 优先级)

> 本节是全项目**唯一权威口径**。各项目 `*.md` 的 labeling config、EC 词表、优先级说法**必须与此一致**;冲突以本节 + 冻结的 `BENCHMARK_*.md` 需求源为准。

### 7.1 规范标签集(所有项目逐字一致)

**8 类目标框 `object_labels`**(检测轨全部项目 + action-test 共用):

| value | 颜色 | value | 颜色 |
|---|---|---|---|
| `hand` | `#E4572E` | `scope_control_body` | `#FFC069` |
| `short_brush` | `#FFC914` | `scope_mid_section` | `#AD8B00` |
| `syringe` | `#FFA39E` | `scope_distal_end` | `#9dd756` |
| `air_gun` | `#D4380D` | `brush_tip_out` | `#389E0D` |

**5 类动作 `actions`**(TimelineLabels,action-train / action-test / mixed-train 共用):
`short_brush_cleaning` `#FFC914` · `flush` `#FFA39E` · `air_injection` `#D4380D` · `long_brush_insert` `#FFC069` · `long_brush_withdraw` `#AD8B00`。

> 约定:`object_labels` 语义 = **该类在画面中可见**(与是否在用无关),`allowEmpty="true"` 保留空帧;`idle` 不显式标(timeline 空隙即 idle,派生脚本按 gap 补齐);新增类**只能追加到列表末尾**,且 action-train / action-test 保持同一套动作类。各文件的 config 块凡写"标准 8 类目标框配置 / 标准动作时序配置"均指本表。

### 7.2 EC 词表映射(两套并存,一表对照)

`ec_env`(段级 TimelineLabels,`action-test`)与 `ec_tags`(片级 Choices,`yolo-test`)是**两种形式、部分重叠**的等价类词表。形式差异源于测试单元(seg 整段 → 段级 timeline;det 单一条件短片 → 片级 tag)。几何桶(尺度/遮挡/拥挤/截断)两套都**不打 tag**,由 build 从框几何自动派生。

| 类别 | `ec_env`(seg 段级) | `ec_tags`(det 片级) | 对应 benchmark EC 维度 |
|---|---|---|---|
| 偏暗 | `dark` | `dark` | DET §2 D-成像环境 / SEG §2 Group D |
| 反光水珠 | `glare_water` | `glare_water` | DET §2 D-成像环境 |
| 过曝逆光 | `overexposed` | `overexposed` | DET §2 D-成像环境 |
| 快速模糊 | `fast_blur` | `fast_blur` | DET §2 D-运动模糊 |
| 背景杂乱 | `cluttered_bg` | `cluttered_bg` | DET §2 D-成像环境 |
| 相似干扰物 | `similar_distractor` | `similar_distractor` | DET §2 Group C 负样本 |
| 镜头晃/视觉突变 | `visual_jitter` | —(seg 独有) | SEG §2 Group D 过分割诱因 |
| 异常/未定义动作 | `abnormal_action` | —(seg 独有) | SEG §2 Group D idle/异常 |
| 异内镜型号 | —(det 独有) | `diff_scope_model` | DET §2 Group D 来源多样性 |
| 异操作者 | —(det 独有) | `diff_operator` | DET §2 Group D 来源多样性 |
| 异机位/角度 | —(det 独有) | `diff_viewpoint` | DET §2 Group D 来源多样性 |

> 前 6 项两套共享(**同名**);`visual_jitter` / `abnormal_action` 是时序侧特有(段内噪声/异常段);`diff_*` 三项是检测侧整片级来源标(seg 的来源多样性走源级选片,不打段级 tag)。det 的**对抗-可见性**不用 ec 词表,走 `action-test` 的 `adv_visibility` Choices(见 SEG §2 Group A / §5)。

### 7.3 优先级词汇(全项目统一)

采用 `BENCHMARK_*.md §0` 的定义:**P0** = 任务核心 + 当前最弱 + 失败代价高,必测/必补;**P1** = 重要难点/边界,应覆盖;**P2 / 基线** = 鲁棒性补充或已饱和作对照。训练侧文件表中的"起点优先级 / 滚动"是在 P0/P1 之上的补充说明(首轮起点 + 逐轮按评测重排),不另立一套档位。

---

## 相关

- 各项目详情:[yolo-train.md](yolo-train.md) · [action-train.md](action-train.md) · [action-test.md](action-test.md) · [yolo-test.md](yolo-test.md) · [mixed-train.md](mixed-train.md)(退役,存量说明)
- 需求源:[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) · [BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md)
- 流水线:[cleansight-pipeline/README.md](../cleansight-pipeline/README.md)
