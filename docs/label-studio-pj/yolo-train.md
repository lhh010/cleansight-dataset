# CleanSight LS 采集方案 · **yolo-train**

> 项目类型：视频级**纯目标框**（bbox only，无动作时序）
> 服务对象：**常规训练集** `cleansight-yolo` 的**检测短板动态补量池**
> 原始需求源：[BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §2 Group A（类别×尺度 EC）+ 逐类 P/R 阈值（`config.yaml`）+ 模型评测结果
> 配套项目：`action-train`（动作轨,另一条训练轨,不标框）
> 存量来源：`mixed-train`〔**已退役**〕的 bbox+动作全标数据仍作 bootstrap 种子(见 [README.md](README.md) §3),可派生本轨训练框

---

## 0. 定位与边界

- **哪类差补哪类，不锁定单一目标**：本项目是**评测驱动的检测补量池**——按最新一轮模型评测的**逐类 recall / precision**，谁弱补谁、弱多少补多少。不预先窄化到某一类；下面 §2 列的是**当前已知短板**，但真正的采集清单以**每轮 `validate` 的逐类指标**为准，随之滚动更新。
- **只补检测框、不碰动作**：不需要动作语义，砍掉 `actions` timeline，标注成本大幅降低。适合「只想给某几类多喂框」的快速迭代。
- **用视频模式而非图像单帧**：`VideoRectangle` 的关键帧插值对「目标连续出现的相邻帧」远快于逐张图像标注。
- **框只在本轨手标**：解耦后动作采集走 `action-train`,而 `action-train` **不标框**(框由 YOLO 推理生成,见 [README.md](README.md) §2 框的出处铁律)。因此**所有手标检测框都集中在本项目**——包括从前指望 `mixed-train` 完整序列"顺带带出"的框(如 air_injection 时段的 air_gun):这类框现由**存量 mixed bootstrap 派生**补上,新增补量则直接在本项目标该时段帧。
- **复用规则**:可复用**存量 mixed bootstrap 源**、或与 `action-train` 共享的原始视频,挑欠标类时段补框;它们进同一 `splits.yaml` 视频级 split,不产生跨 split 泄漏。但**不得**碰任何 benchmark test 源(`benchmark_test.yaml`)。

---

## 1. LS Settings（labeling config）

标准 8 类目标框配置(同 [README.md](README.md) §7.1),无 timeline、无动作:

```xml
<View>
  <Header value="YOLO 强化采集 · 仅目标框(稀缺类补量)"/>
  <Video name="video" value="$video" frameRate="$fps" height="560" timelineHeight="120"/>

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
</View>
```

**约定**(标签块同 [README.md](README.md) §7.1)
- 8 类标签保持不变——即便本批次只关心少数类，其它可见目标也**照常画框**（bbox=可见，漏框会变成 recall 训练噪声）。
- `allowEmpty="true"` 保留空帧。

---

## 2. 采集目标（评测驱动，动态更新）

**判据（不是实例数，是模型表现）**：每轮训练后看 `validate` 的逐类指标——
- `recall < per_class_recall`（config.yaml 现设 0.7）→ 该类**漏检**，优先补；
- `precision < per_class_precision`（0.5）→ 该类**误检**，多为混淆/负样本不足，补对应负样本或干扰帧；
- 弱得越多、补得越多；达到阈值即停，把标注预算转给下一个短板。

> 采集清单 = 「上一轮跌破阈值的类」的排序，**每轮滚动重排**。下表是**首轮已知短板**（[archive/DATASET_BALANCE_REVIEW.md](../archive/DATASET_BALANCE_REVIEW.md) §2.2/§3 的实例数偏低类，作起点），跑出评测后以实测逐类 P/R 覆盖它。

| 起点优先级 | 检测类 | 现状（实例/占比） | 补量方向 | 采集来源 |
|---|---|---|---|---|
| P0 | `brush_tip_out` | 318 / 4.8%，全集最稀缺 | 密采刷头露出帧 | 已有 long_brush 源（覆盖不足，非缺视频） |
| P0 | `air_gun` | 394 / 5.9% | 注气时段密采(air_injection 序列走 action-train 不带框,故 air_gun 框在本轨补) | 存量 bootstrap / 本轨标注气时段帧 |
| P1 | `short_brush` | 910 / 13.6% | 视评测决定是否补 | short_brush_cleaning / flush 时段 |
| 滚动 | **任意逐类指标跌破阈值的类** | 以 `validate` 为准 | 按实测短板补 | 对应类出现的时段 |

> **不预设终点数字**：不锁「brush_tip_out 补到 1000」这类固定目标——占比达标但 recall 仍低说明是难度问题而非数量问题，此时该换难样本而非继续堆量；反之评测已过阈值就停。让**指标**决定停不停。

**帧内条件（顺手强化，对齐 [BENCHMARK_DETECTION.md](../BENCHMARK_DETECTION.md) §2 Group B）**
- **极小尺度 <1%**：目标刚露出/远景状态的框；
- **快速运动模糊**：快速运动致目标模糊的帧；
- **重遮挡 30–70%**：手挡器械时仍可见部分的框。
- 这些难度维度往往是「占比够但 recall 低」的真正原因——比堆同质样本更能拉指标。

---

## 3. 源级与隔离规则

1. **不碰 benchmark 源**：选片先查 `benchmark_test.yaml`，任何 test 源及其同场次相邻片段排除。
2. **复用存量/共享训练源允许**:存量 mixed bootstrap 源、或与 `action-train` 共享的原始训练视频,均可在本项目补稀有类框——它们进同一 `splits.yaml` 视频级 split,不产生跨 split 泄漏。
3. **数据增强不替代真实补标**：`augment.py` 只在 train 上对 air_gun/brush_tip_out 轻量增强（P2），是补充不是替代（[archive/DATASET_BALANCE_REVIEW.md](../archive/DATASET_BALANCE_REVIEW.md) §6 P2）。

---

## 4. 标注规范

- **可见即框**：本轮补量的目标只要**露出可见**就框（哪怕极小/模糊），不可见的帧不画该框。例：brush_tip_out 仅刷头露出时框，缩回不框。
- **框紧贴目标**：小目标尤其忌松框，极小目标的 IoU 对框精度敏感。
- **每帧其它可见目标一并标**：不能只标本轮关心的那一类而漏掉同帧的 hand / scope，否则这些帧变成缺标负例污染训练。
- **关键帧密度**：稀有类出现窗口内多打关键帧，让 VideoRectangle 插值贴合运动。

---

## 5. 自查清单（导出前）

- [ ] 本批次源均不在 `benchmark_test.yaml`。
- [ ] 本批次补的是**上一轮评测跌破阈值的类**（有据可查，不是拍脑袋堆量）。
- [ ] 补量类出现帧内**其它可见目标未漏标**。
- [ ] 补完后重跑 `validate`，对应类逐类 recall/precision 有回升（达阈值即可停，未回升则改补难样本而非继续堆量）。
- [ ] `python cleansight-pipeline/common/check.py --strict` 全 PASS。
