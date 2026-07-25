# CleanSight LS 采集方案 · **mixed-label-train**

> 项目类型：视频级完整标注（bbox + 动作时序）
> 服务对象：**常规训练/验证集**——`cleansight-yolo`、`cleansight-ActionMixed`、`cleansight-ActionSequence` 的 train/val
> 原始需求源：[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md)、[BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md)（本项目采「训练侧少样本补齐」，不采 benchmark test）
> 配套项目：`yolo-extra-train`（纯 bbox 补量）、`mixed-label-test` / `yolo-extra-test`（benchmark，源级隔离）

---

## 0. 定位与边界

- **这是训练侧项目**，不是 benchmark。目标是**补齐少样本动作的完整序列**，让常规数据集在 train/val 上不再缺类、缺 split。
- **只做「完整序列」**：每条视频从动作前上下文标到动作后上下文，`actions` timeline 连续覆盖。因为它同时喂 ActionSequence（视频级）与 ActionMixed（段级），必须是整段。
- **不承担 benchmark test 采集**：benchmark 的 air_injection / short_brush_cleaning 测试序列在 `mixed-label-test` 里单独采，**源视频与本项目严格不重叠**（见 §3）。

---

## 1. LS Settings（labeling config）

沿用现行 mixed-label 配置，原样使用：

```xml
<View>
  <Header value="清洗视频标注:目标框 + 动作时序"/>
  <Video name="video" value="$video" frameRate="$fps" height="560" timelineHeight="180"/>

  <Header value="目标检测/目标跟踪:给每个可见目标画框"/>
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

  <Header value="动作时序:在时间轴上标清洗动作起止时间"/>
  <TimelineLabels name="actions" toName="video">
    <Label value="short_brush_cleaning" background="#FFC914"/>
    <Label value="flush" background="#FFA39E"/>
    <Label value="air_injection" background="#D4380D"/>
    <Label value="long_brush_insert" background="#FFC069"/>
    <Label value="long_brush_withdraw" background="#AD8B00"/>
  </TimelineLabels>
</View>
```

**约定**
- `object_labels` 语义 = **该类在画面中可见**（与是否在用无关）。台上未用的杂物器械**照样画框**，是合法正样本。
- `idle` 不显式标：`actions` timeline 的空隙即 idle，由派生脚本按 gap 补齐。
- `allowEmpty="true"`：无框帧（空帧）合法保留。

---

## 2. 采集目标（按等价类桶）

依据 [BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §1 Group A / [BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md) §1 Group B，训练侧最缺的是**少样本动作及其绑定的稀缺检测类**。

| 优先级 | 采集目标 | 现状（真源/帧数） | 目标 | 顺带补齐的检测类 |
|---|---|---|---|---|
| **P0** | `air_injection` 完整序列 | 366 帧 / **仅 1 源**（4807dbbe，train） | **新增 ≥2 源**，钉 1→val、1→test | `air_gun`（现 394 → +~700） |
| **P0** | `short_brush_cleaning` 完整序列 | 252 帧(train) / **仅 2 源**，val=0 | **新增 ≥1 源**，钉→val | `short_brush`（现 910） |
| P1 | `long_brush_withdraw` 补量 | 760 帧 | 顺采即可（有 insert 就有 withdraw） | `brush_tip_out`（见 `yolo-extra-train`） |

> **数量参考**（[archive/DATASET_BALANCE_REVIEW.md](../archive/DATASET_BALANCE_REVIEW.md) §6）：air_injection 动作帧再补 ~400；air_gun / brush_tip_out 各补 600–800 实例（air_gun 这部分由本项目的 air_injection 序列覆盖，brush_tip_out 交 `yolo-extra-train`）。

**采集时优先制造这些帧内条件**（顺手拿，不额外拍）：
- 稀有类的相邻帧密集出现（air_gun 出现的整个注气时段、short_brush 清洗往复）；
- 边界含 idle 停顿、动作重复（flush 多次 / insert-withdraw 反复）——供 seg 顺序鲁棒性。

---

## 3. 源级与隔离规则（**最关键**）

1. **与 benchmark 源零重叠**：本项目任一源视频，**不得**与 `mixed-label-test` / `yolo-extra-test` 的源同一视频、也不得为**同一场次/同一次录制的相邻片段**（同场次会泄漏动作转移先验）。凡进 benchmark test 的 source_id 一律写入 `benchmark_test.yaml`，本项目选片前先查排除。
2. **补 split 缺口的操作**（对齐 [archive/DATASET_BALANCE_REVIEW.md](../archive/DATASET_BALANCE_REVIEW.md) §5.4）：
   - 新视频导入本项目 → 标完 → 导出；
   - `python cleansight-pipeline/common/reconcile.py --assign` 让新视频按 hash 回填 `splits.yaml`；
   - 手工编辑 `splits.yaml`：把含 air_injection 的两个新源分别钉 `val` / `test`，含 short_brush_cleaning 的新源钉 `val`（保留老源 4807dbbe / 2c635ddc 原位）；
   - 重建 `build_dataset.py`（YOLO）、`build_actionseq.py`（ActionSequence）。
3. **同视频不跨 split**：一条视频所有帧只进一个 split（`splits.yaml` 视频级真值），杜绝相邻帧泄漏。

> ⚠️ 不要改老视频的 split 去救 air_injection——会破坏 YOLO 已验证划分，且把缺口在 split 间搬家。唯一正解是**补新源**。

---

## 4. 标注规范

- **画框（object_labels）**：可见即框，含台上杂物；遮挡时框可见部分的外接矩形；离场帧不画。旋转视角下标外接轴对齐矩形（AABB，与现有约定一致）。
- **动作时序（actions）**：
  - 段起止贴齐**交互开始/结束**（手抓握并操作 → 段起；松手/切换 → 段止），不是器具一出现就起段。
  - insert / withdraw 按**运动方向**分段，衔接处如无停顿则直接相邻（不插 idle）。
  - 停顿超过约 0.5s 的空档留给 idle（不打 timeline）。
- **稀有类密采**：air_gun / short_brush / brush_tip_out 出现的时段，确保关键帧足够密（pipeline 的 `rare_dense_sampling` 会对 <200 帧的类补相邻帧，标注侧只需保证该时段有关键帧）。

---

## 5. 自查清单（导出前）

- [ ] 本批次源视频均**不在** `benchmark_test.yaml`，且非 benchmark 源的同场次相邻片段。
- [ ] air_injection 新增 ≥2 源、short_brush_cleaning 新增 ≥1 源。
- [ ] `actions` timeline 连续、段边界贴齐交互、无碎段。
- [ ] `python cleansight-pipeline/common/count_classes.py`：air_injection / short_brush_cleaning 在 val、test 均 >0。
- [ ] `python cleansight-pipeline/common/check.py --strict` 全 PASS（无 val/test 缺类 warning）。
