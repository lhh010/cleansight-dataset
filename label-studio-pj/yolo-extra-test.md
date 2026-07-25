# CleanSight LS 采集方案 · **yolo-extra-test**（benchmark）

> 项目类型：视频级**目标框 + 环境等价类**（bbox + ec_env，无动作时序）
> 服务对象：**检测 benchmark test**——`cleansight-yolo`，补齐「不需要时序/动作」的检测 EC 桶
> 原始需求源：[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md)
> 生命周期：**源级隔离 + 冻结（只增不改）**，定版打 tag `benchmark-det-v0.1`

---

## 0. 定位与边界

- **det benchmark 专用、纯检测**：只关心「每帧每个可见目标框得准不准」，不需要动作语义，故无 `actions` timeline。
- **测试单元 = 单帧，允许散帧**：检测 test 可按帧策展、跨视频抽帧（与 seg 的整段要求相反）。
- **与 `mixed-label-test` 分工**：det benchmark = `mixed-label-test` 切帧 ∪ 本项目帧。本项目专收**时序无关但检测很难**的桶——极小尺度、跨源泛化、负样本、拥挤 NMS。
- **保留 `ec_env`**：检测难度切片（偏暗/反光/背景杂乱桶 vs 正常桶的衰减）需要手标环境段。

---

## 1. LS Settings（labeling config）

= `yolo-extra-train` 的纯框配置 + `ec_env` 环境时序：

```xml
<View>
  <Header value="Benchmark TEST(检测) · 目标框 + 环境等价类"/>
  <Video name="video" value="$video" frameRate="$fps" height="560" timelineHeight="140"/>

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

  <Header value="环境等价类(ec_env):一整段覆盖,可叠加"/>
  <TimelineLabels name="ec_env" toName="video">
    <Label value="dark" background="#5B5B8A"/>
    <Label value="glare_water" background="#4EA8DE"/>
    <Label value="cluttered_bg" background="#8D6E63"/>
    <Label value="similar_distractor" background="#B39DDB"/>
    <Label value="fast_blur" background="#F06292"/>
    <Label value="overexposed" background="#FFD54F"/>
  </TimelineLabels>
</View>
```

> `ec_env` 去掉了 seg 专用的 `visual_jitter` / `abnormal_action`（检测不评过分割/异常动作），留 6 条检测相关环境条件。留着那两条也无害，看标注习惯。

**约定**
- 8 类照常全标（bbox=可见）；空帧 `allowEmpty` 保留作负样本。
- `idle`/动作不标——本项目无时序语义。

---

## 2. 采集目标（按检测 EC 桶，P0 优先）

依据 [BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §1 Group B/C/D、§2：

### 2.1 极端尺度 · 稀缺小目标（Group A/B · P0）

| 桶 | 要求 | 优先级 |
|---|---|---|
| 极小尺度 <1%（远景气枪/刷头） | air_gun / brush_tip_out 远景小框，全集缺失 | **P0** |
| 小 1–5% | scope_distal_end / syringe / short_brush 小目标 | P1 |
| 检测下限 <0.3% | 允许漏检，作边界基线 | P2 |

### 2.2 来源多样性（Group D · P0/P1，全缺）

| 桶 | 要求 | 优先级 |
|---|---|---|
| **异内镜型号** | 不同型号内镜的检测帧，seen vs 异型号衰减切片 | **P0** |
| 异操作者 | 不同操作者机位/手法 | P1 |
| 异机位/角度 | 不同相机位置/视角 | P1 |

> 这类多为**跨源散帧**，正是 det「按帧策展、跨视频抽帧」的用武之地；VideoRectangle 插值收益不大，逐帧标即可。

### 2.3 视觉难度（Group B · P1，多为自动派生 + 顺采）

| 桶 | 派生依据 | 采集侧要做的 |
|---|---|---|
| 重遮挡 30–70%（手挡器械） | 与 hand IoU | 选含手器重叠的帧 |
| 边缘截断（仅露一角） | bbox 触边 | 选目标出画边的帧 |
| 密集共现 ≥4 / 拥挤重叠（NMS 易错） | 同帧 bbox 数 / 互 IoU | 选多器械同框帧 |
| 快速运动模糊 | 手标 `fast_blur` | 打 ec_env 段 |
| 偏暗 / 反光水珠 / 背景杂乱 | 手标 ec_env | 打 ec_env 段 |

### 2.4 负样本（Group C · P1/P2）

| 桶 | 画面 | 该输出 | 标注 |
|---|---|---|---|
| 空帧负样本（P1） | 无任何目标 | 什么都不报 | 整帧无框，`allowEmpty` |
| 相似干扰物（P2） | 有外部相似物（非目标器械/管路） | 不报该物 | 该物**不画框** + `similar_distractor` 段 |

---

## 3. 源级与隔离规则

1. **源级隔离 + 入册**：所有 test 源 `source_id` 写入 `benchmark_test.yaml`，从 train 侧项目与 `splits.yaml` hard-exclude。
2. **可与 `mixed-label-test` 共享 test 源**：det benchmark 合并两者的帧；但**跨源散帧仍需确保每个 source 整条不在 train/val**。
3. **不与 train 源同场次**：相似型号/同次录制的相邻片段不得当 test。
4. **冻结**：定版打 tag `benchmark-det-v0.1`，只增不改。

---

## 4. 标注规范

- **极小目标框务必紧贴**：<1% 目标 IoU 对框精度极敏感，宁可放大画面逐个框准。
- **每帧全类标全**：跨源泛化帧里 hand/scope 等常见类也要标，漏标会污染该帧的 precision/recall 评测。
- **相似干扰物**：明确「长得像但不是目标器械/管路」的外部物**不画框**，并在其出现时段打 `similar_distractor`——这是防外部误检的评测依据。
- **ec_env 打段**：偏暗/反光/背景杂乱按时间窗口标整段，供环境衰减切片。
- **负样本纯净**：空帧确保画面确实无任何 8 类目标再留作负样本。

---

## 5. 自查清单（冻结前）

- [ ] 所有源 `source_id` 已入 `benchmark_test.yaml`，且不与 train/val 源同场次。
- [ ] 极小 <1% air_gun/brush_tip_out 桶有覆盖（det Group B 最缺）。
- [ ] 异内镜型号帧已纳入（P0 全缺项），标记好来源以便切片。
- [ ] 空帧负样本、相似干扰物各有覆盖，干扰物未画框且已打 `similar_distractor`。
- [ ] 每帧全类标全、极小目标框紧贴。
- [ ] 生成 EC 覆盖矩阵，对照 [BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §2 P0/P1 逐桶核对为 ✅。
- [ ] 定版打 tag `benchmark-det-v0.1`。
