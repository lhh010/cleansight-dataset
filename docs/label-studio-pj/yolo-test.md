# CleanSight LS 采集方案 · **yolo-test**（检测 benchmark）

> 项目类型：帧/短片级**目标框 + 等价类 tag**（bbox + clip 级 `ec_tags`，**无 timeline、无动作**）
> 服务对象：**检测 benchmark test**——`cleansight-yolo`
> 原始需求源：[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md)
> 生命周期：**源级隔离**；评测集一旦定版，标注**只增不改**。版本管理（冻结/发版/打 tag）**由 pipeline 侧负责，不在 LS**。
> （本文的 clip 级 `ec_tags` 是标注标签，与版本无关。）
> 总纲：[README.md](README.md)

---

## 0. 定位与边界

- **det benchmark 专用、纯检测**：只关心「每帧每个可见目标框得准不准」，无动作、无 timeline。
- **测试单元 = 帧 / 同质短片，允许散帧**：检测可按帧策展、跨源抽帧（与 seg 的整段要求相反）。
- **不拿整条刷洗任务当测试单元**：训练侧 clip = 一次完整刷洗任务，但那是**明暗/反光/模糊混杂**的异质片。检测 test 要为等价类切片,须从任务里**裁出「单一条件」的同质短片/帧**（专挑那段暗的、那几帧模糊的）——检测可散帧,正好做得到。
- **等价类用 clip 级 `ec_tags`（多选），取代旧的段级 `ec_env` timeline**：因为测试片已裁成单一条件,整片打一个 tag 就干净,不必再逐段画时间范围。
- **几何类桶不打 tag**：尺度/遮挡/拥挤/截断由 build **从框自动派生**（见 §2.2）,采集侧只需「采到含该情形的帧」。
- **与 `action-test` 分工**：det benchmark = `action-test` 切帧 ∪ 本项目帧。本项目专收**时序无关但检测很难**的桶——极小尺度、跨源泛化、负样本、拥挤 NMS。

---

## 1. LS Settings（labeling config）

标准 8 类目标框配置(同 [README.md](README.md) §7.1) + **clip 级 `ec_tags`**（`Choices` 多选,整片打标；无 timeline；ec_tags 词表见 [README.md](README.md) §7.2）：

```xml
<View>
  <Header value="yolo-test: 目标框 + 等价类 tag"/>
  <Video name="video" value="$video" frameRate="$fps" height="560"/>

  <Header value="目标框:每帧每个可见目标画框(8类)"/>
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

  <Header value="等价类 tag(整条测试片打标,已按单一条件裁好)"/>
  <Choices name="ec_tags" toName="video" choice="multiple" showInLine="true">
    <!-- 视觉/环境:测试片裁成同质,一片一条件 -->
    <Choice value="dark"/>
    <Choice value="glare_water"/>
    <Choice value="overexposed"/>
    <Choice value="fast_blur"/>
    <Choice value="cluttered_bg"/>
    <!-- 干扰 -->
    <Choice value="similar_distractor"/>
    <!-- 来源(整片级) -->
    <Choice value="diff_scope_model"/>
    <Choice value="diff_operator"/>
    <Choice value="diff_viewpoint"/>
  </Choices>
</View>
```

**约定**
- 8 类照常全标（bbox=可见）；空帧 `allowEmpty` 保留作负样本。
- `ec_tags` 是**整条测试片级**多选：片已按单一视觉条件裁好,通常勾 1 个视觉条件 +（可能的）来源/干扰标；正常光照片可不勾视觉条件。
- **不打 timeline、不标动作**。
- 几何类桶（尺度/遮挡/拥挤/截断）**不在此勾**,由 build 从框算（§2.2）。

---

## 2. 采集目标（按检测 EC 桶，P0 优先）

依据 [BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §2 Group B/C/D(等价类维度全在 §2)。分两类:**需人裁+打 `ec_tags`** 的（§2.1）,与 **从框自动派生、只需采到** 的（§2.2）。

### 2.1 需人裁同质片 + 打 `ec_tags`

| 组 | tag | 要求 | 优先级 |
|---|---|---|---|
| 视觉/环境 | `dark` / `glare_water` / `overexposed` / `fast_blur` / `cluttered_bg` | 每类**裁 ≥1 条同质片**,整片就是该条件 | P1 |
| 来源多样性(全缺) | `diff_scope_model` | **异内镜型号**帧,seen vs 异型号衰减切片 | **P0** |
| 来源多样性 | `diff_operator` / `diff_viewpoint` | 异操作者 / 异机位角度 | P1 |
| 干扰 | `similar_distractor` | 外部相似物在场（**不画框**,见 §4） | P1 |

> 来源类多为**跨源散帧**,正是检测「按帧策展、跨视频抽帧」的用武之地。

### 2.2 从框自动派生的桶（**不打 tag**,采集侧只需采到）

| 桶 | build 派生依据 | 采集侧要做的 |
|---|---|---|
| 极小尺度 <1%（远景气枪/刷头,**最缺**） | 框面积占比 | 采到 air_gun / brush_tip_out 远景小框（**P0**） |
| 小 1–5% | 框面积占比 | 采到 scope_distal_end / syringe / short_brush 小目标 |
| 重遮挡 30–70% | 与 hand 的 IoU | 选含手器重叠的帧 |
| 边缘截断（仅露一角） | bbox 触边 | 选目标出画边的帧 |
| 密集共现 ≥4 / 拥挤重叠（NMS 易错） | 同帧 bbox 数 / 互 IoU | 选多器械同框帧 |

### 2.3 负样本（Group C）

| 桶 | 画面 | 该输出 | 标注 |
|---|---|---|---|
| 空帧负样本（P1） | 无任何目标 | 什么都不报 | 整帧无框,`allowEmpty` |
| 相似干扰物（P2） | 有外部相似物（非目标器械/管路） | 不报该物 | 该物**不画框** + 勾 `similar_distractor` |

---

## 3. 源级与隔离规则

1. **源级隔离 + 入册**：所有 test 源写入 benchmark 清单，从 train 侧项目 hard-exclude。
   > 落地形态：`cleansight-pipeline/yolo/test.yaml` 的 `tasks`。**登记的是 LS task id 而非 source_id/视频名** —— 视频在 LS 重传会换 uuid 前缀、文件名跟着变，task id 不会。与训练轨清单 `yolo/train.yaml` 的零交集由 `yolo/manifest.py` 的 `assert_disjoint()` 强制。
2. **裁片仍是源级隔离**：为 EC 切片从某刷洗任务裁同质短片时,**整条源任务**都归 test,不得再拿它的其它片段进 train/val。
3. **可与 `action-test` 共享 test 源**：det benchmark 合并两者的帧；但每个 source 整条不在 train/val。
4. **不与 train 源同场次**：相似型号/同次录制的相邻片段不得当 test。
5. **定版后标注只增不改**：评测集选定后，LS 侧不再改动已有标注（版本冻结/发版由 pipeline 侧做 —— `yolo/test.yaml` 的 `version` / `frozen_at`，非空后 `build_test.py` 只许追加新 task）。

---

## 4. 标注规范

- **极小目标框务必紧贴**：<1% 目标 IoU 对框精度极敏感,宁可放大画面逐个框准。
- **每帧全类标全**：跨源泛化帧里 hand/scope 等常见类也要标,漏标会污染该帧的 precision/recall 评测。
- **相似干扰物**：「长得像但不是目标器械/管路」的外部物**不画框**,并勾 `ec_tags = similar_distractor`——防外部误检的评测依据。
- **`ec_tags` 打标**：测试片已裁成单一条件,勾对应视觉条件；来源/干扰照实勾；正常片可不勾视觉条件。
- **负样本纯净**：空帧确保画面确实无任何 8 类目标再留作负样本。

---

## 5. 自查清单（交付评测集前）

- [ ] 所有 test task 已登记进 `cleansight-pipeline/yolo/test.yaml`,且不与 train/val 源同场次。
- [ ] 每条测试片**已裁成单一视觉条件**（`ec_tags` 干净可切）。
- [ ] 极小 <1% air_gun/brush_tip_out 桶有覆盖（det Group B 最缺）。
- [ ] 异内镜型号帧已纳入（P0 全缺项）,勾 `diff_scope_model`。
- [ ] 空帧负样本、相似干扰物各有覆盖,干扰物未画框且已勾 `similar_distractor`。
- [ ] 每帧全类标全、极小目标框紧贴。
- [ ] 几何桶（尺度/遮挡/拥挤/截断）采集侧已覆盖（bucket 由 build 自动算）。
- [ ] 标注定版后不再改动，交 pipeline 侧冻结发版。
