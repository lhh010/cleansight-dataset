# CleanSight LS 采集方案 · **action-test**（benchmark）

> 项目类型：视频级完整标注（bbox + 动作时序 + 环境等价类 + 对抗可见性）
> 服务对象：**benchmark test**——`cleansight-ActionMixed` 时序分割 benchmark（全部）+ `cleansight-yolo` 检测 benchmark（供帧）
> 原始需求源：[BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md)（主）、[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md)（供帧）
> 生命周期：**源级隔离**；评测集一旦定版，标注**只增不改**。版本管理（冻结/发版/打 tag）**由 pipeline 侧负责，不在 LS**。

---

## 0. 定位与边界

- **这是 benchmark test，不进 train/val**。每条源视频整条源级隔离，写入 `benchmark_test.yaml`，从所有构建脚本 hard-exclude。
- **整段保留、禁止散帧**：分割指标必须在完整序列上算；每条 test 含动作前后上下文与边界，绝不截散帧。ActionMixed 现有「段级 hash 切分」对 benchmark **禁用**（同视频跨 split = 转移先验泄漏，见 [BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md) §5）。
- **一条序列多重复用**：完整标注后，seg benchmark 用整段、det benchmark 切帧用——两者共用同一批 test 源。
- **策展目标**：在 P0/P1 等价类上**密集**（尤其对抗-可见性 + 少样本动作），而非反映日常分布。

---

## 1. LS Settings（labeling config）

标准 8 类目标框 + 5 类动作时序配置(同 [README.md](README.md) §7.1),再加 `ec_env` 环境时序 + `adv_visibility` 对抗可见性标记(EC 词表见 [README.md](README.md) §7.2):

```xml
<View>
  <Header value="Benchmark TEST · 目标框 + 动作时序 + 环境等价类"/>
  <Video name="video" value="$video" frameRate="$fps" height="560" timelineHeight="180"/>

  <Header value="目标检测/跟踪:给每个可见目标画框"/>
  <VideoRectangle name="objects" toName="video"/>
  <Labels name="object_labels" toName="video" choice="single" allowEmpty="true">
    <Label value="hand" background="#E4572E"/>
    <Label value="short_brush" background="#FFC914"/>
    <Label value="syringe" background="#FFA39E"/>
    <Label value="air_gun" background="#D4380D"/>
    <Label value="scope_control_body" background="#FFC069"/>
    <Label value="scope_mid_section" background="#AD8B00"/>
    <Label value="scope_distal_end" background="#9dd756"/>
    <Label value="brush_tip_out" background="#389E0D"/>
  </Labels>

  <Header value="动作时序:标清洗动作起止"/>
  <TimelineLabels name="actions" toName="video">
    <Label value="short_brush_cleaning" background="#FFC914"/>
    <Label value="flush" background="#FFA39E"/>
    <Label value="air_injection" background="#D4380D"/>
    <Label value="long_brush_insert" background="#FFC069"/>
    <Label value="long_brush_withdraw" background="#AD8B00"/>
  </TimelineLabels>

  <Header value="环境等价类(ec_env):一整段覆盖,可叠加"/>
  <TimelineLabels name="ec_env" toName="video">
    <Label value="dark" background="#5B5B8A"/>
    <Label value="glare_water" background="#4EA8DE"/>
    <Label value="cluttered_bg" background="#8D6E63"/>
    <Label value="similar_distractor" background="#B39DDB"/>
    <Label value="fast_blur" background="#F06292"/>
    <Label value="overexposed" background="#FFD54F"/>
    <Label value="visual_jitter" background="#FF8A65"/>
    <Label value="abnormal_action" background="#E53935"/>
  </TimelineLabels>

  <Header value="对抗-可见性(seg P0,自动出候选后人工确认)"/>
  <Choices name="adv_visibility" toName="video" choice="multiple">
    <Choice value="present_not_operating"/>
    <Choice value="multi_tool_one_active"/>
    <Choice value="tool_fully_occluded"/>
    <Choice value="none"/>
  </Choices>
</View>
```

**约定**
- `ec_env` 段**可叠加**（一段可同时 dark + glare_water），标一整段覆盖其中所有帧。
- `adv_visibility` 是**整条序列级**多选标记，用于生成「对抗-可见性子集」做指标切片。
- `idle` 仍走 gap 隐式。

---

## 2. 采集目标（按等价类桶，P0 优先）

### 2.1 对抗-可见性（[BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md) §2 Group A + §5 用例表，本套最核心 P0）

benchmark 必须含「detection 单看会判错」的序列，否则捷径模型虚高。每类至少 1–2 条独立源序列：

| 用例 | 场景 | 正确判定 | `adv_visibility` |
|---|---|---|---|
| 在场未操作·气枪 | flush/idle 段，气枪躺台上同框 | 非 air_injection | present_not_operating |
| 在场未操作·注射器 | air_injection 段，注射器杂物同框 | 非 flush | present_not_operating |
| 多器具同框仅一件在用 | 多件小器械同时可见，仅一件在手操作 | 按在用件判 | multi_tool_one_active |
| 在用器具被手全遮挡 | 器具 bbox 消失但手仍在动 | 靠手运动维持当前动作 | tool_fully_occluded |

### 2.2 少样本动作 + split 缺口（Group B / Group E · P0）

| 目标 | 现状 | benchmark 要求 |
|---|---|---|
| `air_injection` 序列 | **仅 1 源，val+test=0** | **≥1 独立源**（与 train 侧那 2 源均不同场次） |
| `short_brush_cleaning` 序列 | 2 源，val=0 | **≥1 独立源** |

### 2.3 时序结构 / 歧义（Group C · P0/P1）

| 桶 | 要求 | 优先级 |
|---|---|---|
| insert vs withdraw（纯运动方向） | 同源含双向、外观相同靠方向区分 | **P0** |
| 罕见转移对（训练未见 A→B） | 选片时刻意制造非标准顺序 | **P0** |
| 模糊渐变边界（器具不变、动作渐变） | 边界定位主难点 | **P0** |
| 段内遮挡 / 手离场 | 过分割头号诱因 | **P0** |
| 极短段 / 超长段 / 长短悬殊相邻 | 段数比 & 吞并 | P1 |
| 动作重复、缺失 phase、无停顿衔接 | 顺序鲁棒性 | P1 |

### 2.4 来源多样性（Group E · P0/P1，全缺）

- **异内镜型号**（P0，全缺）、异操作者（P1）、异机位/角度（P1）——能取得就优先纳入 test，做 seen vs 异型号衰减切片。

---

## 3. 源级与隔离规则（**benchmark 生命线**）

1. **整条源级隔离**：每条 test 源 `source_id` 写入 `benchmark_test.yaml`,所有训练侧项目(`yolo-train` / `action-train`,及退役存量 `mixed-train` bootstrap)与 `splits.yaml` / `splits_actionmixed.yaml` 一律 hard-exclude。
2. **禁用段级切分**：ActionMixed 的 benchmark test 走「视频级·整段」，**不进** `splits_actionmixed.yaml` 的段级 hash。
3. **同场次即泄漏**：与任一 train/val 视频同一次录制的相邻片段**不得**当 test（转移先验泄漏）。
4. **与 `yolo-test` 的关系**：det benchmark = 本项目切帧 ∪ `yolo-test` 帧；两者可共享 test 源，但都不得触碰 train 源。
5. **定版后标注只增不改**：后续只追加新序列，不改已交付的标注（版本冻结/发版由 pipeline 侧做，不在 LS）。

---

## 4. 标注规范

- **完整序列**：从动作前 idle 上下文标到动作后 idle，中间 `actions` 连续不断。
- **动作段边界贴齐交互突变**（换器械/明显切换 = 清晰边界；器具不变动作渐变 = 模糊边界，尽量标出你判定的过渡点，供边界误差评测）。
- **对抗序列人工确认**：自动派生先出「在场未操作 / 多器具同框」候选，标注员**逐条核对是否确实未操作**（手是否抓握 + 是否共动），确认后勾 `adv_visibility`。
- **ec_env 打段**：反光/晃动/偏暗/异常动作等按时间窗口标整段；一段多条件叠加。
- **bbox 全程**：即便是对抗段，台上所有可见器械照常画框（这正是「可见≠在用」的对抗信号来源）。

---

## 5. 自查清单（交付评测集前）

- [ ] 每条源 `source_id` 已入 `benchmark_test.yaml`，且不与任何 train/val 源同场次。
- [ ] 对抗-可见性 4 类用例各 ≥1 条独立源序列，`adv_visibility` 已勾。
- [ ] air_injection / short_brush_cleaning 各 ≥1 独立源（非 train 侧源）。
- [ ] insert↔withdraw、罕见转移、模糊边界、段内遮挡桶均有覆盖。
- [ ] 每条为完整序列，`actions` 连续无碎段，未散帧。
- [ ] 生成 EC 覆盖矩阵，对照 [BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md) §2 的 P0/P1 逐桶核对为 ✅。
- [ ] 标注定版后不再改动，交 pipeline 侧冻结发版。
