# CleanSight LS 采集方案 · **action-train**

> 项目类型:视频级**纯动作时序**(timelinelabels only,**不标框**)
> 服务对象:**时序训练/验证集** `cleansight-ActionMixed` 的 train/val
> 原始需求源:[BENCHMARK_SEGMENTATION.md](../BENCHMARK_SEGMENTATION.md)(动作/转场覆盖是判据)
> 配套项目:`yolo-train`(纯框,另一条轨)、`action-test`(时序 benchmark + GT 上限)
> 总纲:[README.md](README.md)

---

## 0. 定位与边界

- **时序训练轨,只标动作,不碰框**。框在 build 时由**训好的 YOLO 推理生成并缓存**,标注员不画任何 `VideoRectangle`(见 [README.md](README.md) §2 框的出处铁律)。
- **为什么不标框**:上线时时序模型吃的是 YOLO 带噪声的框,训练时也必须吃 YOLO 的框 → 训练-推理一致。手标干净框会制造分布漂移。手标框在这里是**纯浪费**。
- **只做完整连续段**:每条视频从动作前 idle 上下文标到动作后 idle,`actions` timeline 连续覆盖——分割模型需要完整序列与转场,不能散帧。
- **coverage 维度 = 行为空间**:按动作类型 / 时长 / **转场组合**的缺口选材(与 YOLO 轨的外观空间正交)。
- **前置依赖**:本项目产出要能训时序,得先有一版达标 YOLO 来推框。YOLO 未起来前,存量 mixed 数据先走 YOLO 训练(见 [README.md](README.md) §3)。

---

## 1. LS Settings(labeling config)

标准 5 类动作时序配置(同 [README.md](README.md) §7.1),**无 `VideoRectangle` / `object_labels`**,只留动作时序:

```xml
<View>
  <Header value="清洗视频·仅动作时序(时序训练,框由 YOLO 推理生成)"/>
  <Video name="video" value="$video" frameRate="$fps" height="560" timelineHeight="200"/>

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
- **不标框**:本项目无 `VideoRectangle`。若标注端习惯性画了框,build 侧一律忽略(以 YOLO 推理框为准)。
- `idle` 不显式标:`actions` timeline 的空隙即 idle,派生脚本按 gap 补齐。
- 动作类沿用统一 5 类;新增动作只能**追加到列表末尾**,与 `action-test` 保持同一套动作类。

---

## 2. 采集目标(动作 coverage 驱动,动态更新)

**判据(不是视频数,是动作/转场覆盖)**:每轮时序评测后,看哪些动作/转场在 val 上弱或缺样本,谁弱补谁。

| 起点优先级 | 采集目标 | 现状 | 补量方向 |
|---|---|---|---|
| **P0** | `air_injection` 完整序列 | 少样本、源单一 | 新增独立源,覆盖不同注气时长 |
| **P0** | `short_brush_cleaning` 序列 | val 缺样本 | 新增独立源 |
| P1 | `insert ↔ withdraw` 双向段 | 靠运动方向区分 | 同源含往复,供方向鲁棒 |
| P1 | 罕见转移对(非标准 A→B 顺序) | 训练少见 | 选片刻意制造非标准顺序 |
| 滚动 | **上一轮评测弱的动作/转场** | 以时序 `validate` 为准 | 按实测缺口补 |

**采集时优先制造的时序条件**(顺手拿):
- 动作重复(flush 多次 / insert-withdraw 反复)、无停顿衔接、极短段 / 超长段——供顺序与边界鲁棒性。
- 段内遮挡、手短暂离场——过分割的头号诱因,主动覆盖。

> 待建工具:对标 [common/scarce_checklist.py](../cleansight-pipeline/common/scarce_checklist.py) 的**动作缺口清单**(按动作类/转场统计、产出补采清单),让本项目的采集清单可自动滚动。

---

## 3. 源级与隔离规则

1. **与 benchmark 源零重叠**:选片先查 `benchmark_test.yaml`,任何 `action-test` 源及其同场次相邻片段排除。
2. **与 YOLO 轨可共享原始视频**:同一段视频可同时进 `yolo-train`(标框)与本项目(标动作),各标各的——但那是偶然,不强求;别为"一次标全"退回混标。
3. **同视频不跨 split**:一条视频所有帧只进一个 split。
4. **框的诚实性**(乐观偏差):时序训练的框由 YOLO 推理。若某视频也在 YOLO 训练集里,YOLO 在其上出的框会偏干净 → 轻度乐观。现阶段**接受并用 `action-test` 盯**(在两个模型都没训过的 handeval 上测有无虚高);数据涨上来再议,不上 out-of-fold。

---

## 4. 标注规范

- **只标动作时序(actions)**:
  - 段起止贴齐**交互开始/结束**(手抓握并操作 → 段起;松手/切换 → 段止),不是器具一出现就起段。
  - insert / withdraw 按**运动方向**分段,衔接处如无停顿则直接相邻(不插 idle)。
  - 停顿超过约 0.5s 的空档留给 idle(不打 timeline)。
- **完整序列**:从动作前 idle 上下文标到动作后 idle,中间连续不断,无碎段。
- **不画框**:见 §1。目标可见性由 YOLO 推理负责,标注员无需关心画面里有哪些器械。

---

## 5. 自查清单(导出前)

- [ ] 本批次源均**不在** `benchmark_test.yaml`,且非 benchmark 源的同场次相邻片段。
- [ ] 补的是**上一轮时序评测弱/缺的动作或转场**(有据可查,不是拍脑袋)。
- [ ] `actions` timeline 连续、段边界贴齐交互、无碎段。
- [ ] 本项目**无手标框**(或即便有也确认 build 侧忽略)。
- [ ] 动作类与 `action-test` 同一套,新增类仅追加末尾。
