# CleanSight 数据集类别分布与补充计划

> 统计时间：2026-07-14
> 统计工具：`cleansight-yolo-pipeline/count_classes.py`（可复跑复核）
> 统计范围：当前 pipeline 已构建的三个数据集目录
>   - YOLO 检测：`cleansight-yolo-pipeline/datasets/`
>   - ActionMixed（检测+动作）：`cleansight-yolo-pipeline/datasets_actionmixed/`
>   - ActionSequence（逐动作序列）：`cleansight-yolo-pipeline/datasets_actionseq/`

## 1. 三个数据集总览

| 数据集 | 用途 | 类别体系 | 划分粒度 | 划分配置 |
|---|---|---|---|---|
| **YOLO** | 目标检测（bbox） | group1: 3 类（hand / scope_control_body / scope_mid_section）；group2: 5 类（syringe / air_gun / scope_distal_end / short_brush / brush_tip_out） | **视频级**（整段视频只进一个 split） | `splits.yaml`（与 ActionSequence 共用） |
| **ActionMixed** | 检测框 + 动作阶段（逐帧） | 检测 8 类 + 动作 6 类（idle / air_injection / flush / long_brush_insert / long_brush_withdraw / short_brush_cleaning） | **段级**（同一视频的不同动作段可进不同 split） | `splits_actionmixed.yaml`（独立） |
| **ActionSequence** | 逐动作的目标检测序列 | 5 个动作子目录，每个子目录内做 8 类检测 | **视频级** | `splits.yaml`（与 YOLO 共用） |

**判定标准**
- 类别"样本量不足"：该类占比 < 10%，且数据集内最大/最小类实例比 > 10×。
- split 缺失：某类在 val 或 test 的样本数为 0（`utils/check.py` 会以 warning 形式提示）。

---

## 2. 类别分布统计

### 2.1 YOLO — group1_large（3 类，共 23,853 bbox / 6,753 标签文件）

| class_id | 类别 | bbox 实例 | 占比 | 状态 |
|---|---|---|---|---|
| 0 | hand | 12,632 | 53.0% | ✅ |
| 1 | scope_control_body | 5,828 | 24.4% | ✅ |
| 2 | scope_mid_section | 5,393 | 22.6% | ✅ |

→ **均衡，无需处理。**（hand 偏多是正常现象）

### 2.2 YOLO — group2_small（5 类，共 6,673 bbox / 4,631 标签文件）

| class_id | 类别 | bbox 实例 | 占比 | 状态 |
|---|---|---|---|---|
| 2 | scope_distal_end | 3,574 | 53.6% | ✅ |
| 0 | syringe | 1,477 | 22.1% | ✅ |
| 3 | short_brush | 910 | 13.6% | ✅ |
| 1 | **air_gun** | **394** | **5.9%** | ⚠️ 不足 |
| 4 | **brush_tip_out** | **318** | **4.8%** | ⚠️ 不足 |

→ 最大/最小 ≈ 11×，`air_gun` 与 `brush_tip_out` 严重偏低。

### 2.3 ActionMixed — frames/（检测框，8 类，共 25,521 bbox / 5,655 标签文件）

| class_id | 类别 | bbox 实例 | 占比 | 状态 |
|---|---|---|---|---|
| 0 | hand | 10,659 | 41.8% | ✅ |
| 1 | scope_control_body | 4,811 | 18.9% | ✅ |
| 2 | scope_mid_section | 4,512 | 17.7% | ✅ |
| 3 | scope_distal_end | 2,650 | 10.4% | ✅ |
| 4 | syringe | 1,304 | 5.1% | ⚠️ 偏低 |
| 6 | **short_brush** | **873** | **3.4%** | ⚠️ 不足 |
| 5 | **air_gun** | **394** | **1.5%** | ⚠️ 不足 |
| 7 | **brush_tip_out** | **318** | **1.2%** | ⚠️ 不足 |

→ 最大/最小 ≈ 33×，`brush_tip_out` / `air_gun` / `short_brush` 三类是短板。

### 2.4 ActionMixed — labels/（动作分类，逐帧，6 类，共 5,655 帧 / 21 标签文件）

| class_id | 类别 | 帧数 | 占比 | 状态 |
|---|---|---|---|---|
| 3 | long_brush_insert | 1,325 | 23.4% | ✅ |
| 2 | flush | 1,261 | 22.3% | ✅ |
| 0 | idle | 1,242 | 22.0% | ✅ |
| 4 | long_brush_withdraw | 792 | 14.0% | ✅ |
| 5 | short_brush_cleaning | 669 | 11.8% | ✅ |
| 1 | **air_injection** | **366** | **6.5%** | ⚠️ 不足 |

→ `air_injection` 是动作维度的唯一短板。

### 2.5 ActionSequence — 各动作子目录样本数（图像数）

| 动作类别 | train | val | test | 合计 | 状态 |
|---|---|---|---|---|---|
| long_brush_insert | 1,022 | 184 | 112 | 1,318 | ✅ |
| flush | 770 | 339 | 152 | 1,261 | ✅ |
| long_brush_withdraw | 408 | 228 | 153 | 789 | ✅ |
| short_brush_cleaning | 252 | **0** | 417 | 669 | ⚠️ val 缺失 |
| **air_injection** | **367** | **0** | **0** | **367** | ⚠️ val+test 缺失，且总量最少 |

各动作子目录内的目标检测 bbox 分布（仅列出非零项）：

| 动作 | 主要出现的检测类（bbox） |
|---|---|
| air_injection | hand 732 / scope_control_body 367 / scope_mid_section 367 / air_gun 367 |
| flush | hand 2508 / scope_control_body 1251 / scope_mid_section 1260 / scope_distal_end 898 / syringe 1190 / short_brush 135 |
| long_brush_insert | hand 2567 / scope_control_body 871 / scope_mid_section 1089 / scope_distal_end 354 / brush_tip_out 118 |
| long_brush_withdraw | hand 1425 / scope_control_body 639 / scope_mid_section 682 / scope_distal_end 405 / brush_tip_out 151 |
| short_brush_cleaning | hand 1291 / scope_control_body 595 / scope_mid_section 252 / scope_distal_end 417 / short_brush 585 |

> 说明：ActionSequence 每个动作只含该动作相关物体是**设计如此**，不算缺陷。但全局看，`brush_tip_out`（全 ActionSequence 仅 269 实例）、`short_brush`（仅 720）仍属稀缺类。

---

## 3. 问题汇总

### 3.1 样本量不足 / 需额外标注的类

| 跨数据集问题类 | YOLO g2 | ActionMixed frames | ActionMixed labels | ActionSequence | 根因 |
|---|---|---|---|---|---|
| **brush_tip_out** | 318 ⚠️ | 318 ⚠️ | — | 269（仅 long_brush 两动作） | 该物体出现帧本身少，标注覆盖不足 |
| **air_gun** | 394 ⚠️ | 394 ⚠️ | — | 367（仅 air_injection 动作） | 仅 air_injection 时段出现，时段短 |
| **short_brush**（检测类） | 910 | 873 ⚠️ | — | 720（flush+short_brush_cleaning） | 中等偏低 |
| **air_injection**（动作类） | — | — | 366 ⚠️ | 367（仅 1 个源视频） | 源视频少 + 时段短 |

**结论**：全局最稀缺的是 **`brush_tip_out`** 和 **`air_gun`**（检测类），以及动作维度的 **`air_injection`**。三者相互关联——air_gun 只在 air_injection 时段出现，brush_tip_out 主要在 long_brush 时段。

### 3.2 验证集 / 测试集缺失（仅 ActionSequence，视频级划分导致）

| 动作 | val | test | 原因 |
|---|---|---|---|
| **air_injection** | **0** | **0** | 该动作**只存在于 1 个源视频** `4807dbbe`（已被分到 train） |
| **short_brush_cleaning** | **0** | 417 | 该动作只有 **2 个源视频** `2c635ddc`(train) / `fedf6ff9`(test)，没有视频落到 val |

> ActionMixed 用**段级划分**，不存在此问题（air_injection 在 ActionMixed 的各 split 都有）。
> YOLO 的 group2_small 里 air_gun/brush_tip_out 偏少是**数量**问题，不是 split 缺失（三个 split 都有覆盖）。

---

## 4. 根因分析：为什么 ActionSequence 会缺 val/test

划分机制（见 `splits.yaml` 头部注释与 `utils/check.py:_check_splits`）：

1. **视频级划分**：一个视频的所有帧只进一个 split，杜绝跨 split 泄漏。
2. **单源真值**：视频 → split 的映射写死在 `splits.yaml`，人工可改、新视频按 hash 确定性回填。
3. **动作覆盖 = 视频覆盖 × split 分配**：某个动作只出现在少数视频里；若这些视频恰好都没分到 val（或 test），该动作在该 split 的样本就是 0。

各动作的源视频与所在 split（来自 `splits.yaml`）：

| 动作 | train 视频 | val 视频 | test 视频 |
|---|---|---|---|
| air_injection | 4807dbbe | — | — |
| flush | 63a848d5 | 65d70028 | fedf6ff9 |
| long_brush_insert | 05ba4406, 218f9117, 4807dbbe, 63a848d5, af0e7803 | 65d70028 | b1b042a9 |
| long_brush_withdraw | 4807dbbe, 63a848d5, 7e8f5b4f | 65d70028 | 9f93cf16, b004acff, b1b042a9 |
| short_brush_cleaning | 2c635ddc | — | fedf6ff9 |

→ 要保证一个动作在 train/val/test 都有样本，**该动作至少需要 3 个源视频**。当前 `air_injection`(1 个) 和 `short_brush_cleaning`(2 个) 不满足。

---

## 5. 划分修复方案

### 5.1 原则与约束
- `splits.yaml` 是 YOLO + ActionSequence **共用**的唯一真源；改一个视频的 split 会**同时影响两个数据集**。
- `splits_actionmixed.yaml` 独立，ActionMixed 走段级划分，本次不需要改。
- 目标：每个动作在 train/val/test **各至少 1 个源视频**；每类检测框在三个 split 都有覆盖。

### 5.2 ActionSequence — air_injection（val=0, test=0）
- **无法靠重分配修复**：只有 1 个源视频 `4807dbbe`，把它挪到 val/test 只会把缺口从 test/val 转移到 train，且违反"同视频不跨 split"。
- **正解**：**补充标注 ≥ 2 个含 air_injection 的新视频**，新视频经 `00_status.py --assign` 确定性分配后，手动在 `splits.yaml` 里把其中一个钉到 `val`、一个钉到 `test`（保留原 `4807dbbe` 在 train）。
- 临时缓解（不推荐）：若短期无法补标，可接受 ActionSequence 的 air_injection **暂时只做 train**，并在 README 注明 val/test 不可用；检测评估改用 ActionMixed（段级，已有 val/test）。

### 5.3 ActionSequence — short_brush_cleaning（val=0）
- 只有 2 个源视频（train `2c635ddc` / test `fedf6ff9`），重分配会牺牲另一个 split。
- **正解**：**补充标注 1 个含 short_brush_cleaning 的新视频**，在 `splits.yaml` 中钉到 `val`。
- 补标后该动作即满足 train/val/test 各 1 视频。

### 5.4 重分配的操作步骤（补标完成后）
1. 将新视频导入 Label Studio 标注（videorectangle + timelinelabels）。
2. `python 00_status.py --assign` —— 新视频按 hash 回填到 `splits.yaml`。
3. 手工编辑 `splits.yaml`：把含稀缺动作的新视频分别钉到 val/test，确保每个动作三个 split 各 ≥1 视频。
4. 重建：
   ```
   python 02_build_dataset.py          # YOLO
   python 02_build_actionseq.py        # ActionSequence
   ```
5. 复核（见第 7 节），warning 清零后再上传。

> ⚠️ 不要直接改老视频的 split 去救 air_injection：会破坏 YOLO 已验证的划分稳定性，并影响其他动作。

---

## 6. 补采 / 补标行动计划（按优先级）

| 优先级 | 动作 | 目标 | 预期收益 |
|---|---|---|---|
| P0 | 补标 **air_injection** 视频（≥2 段） | ActionSequence 补齐 val/test；ActionMixed labels 帧数翻倍 | 同时提升动作类 air_injection 与检测类 air_gun |
| P0 | 补标 **short_brush_cleaning** 视频（≥1 段） | ActionSequence 补齐 val | 同时补检测类 short_brush |
| P1 | 补标含 **brush_tip_out** 的 long_brush 片段 | 三数据集 brush_tip_out 实例数提升至 ≥1000（占比 >5%） | 全局最稀缺检测类 |
| P2 | 对 air_gun / brush_tip_out 做轻量数据增强 | `02b_augment.py`（仅 train） | 缓解 imbalance，不替代真实补标 |
| P3 | 重新评估 idle 帧占比 | ActionMixed labels idle 已 22%，无需再扩 | 防止 idle 过度膨胀 |

补标数量建议（粗略，以"占比 ≥ 8%、最大/最小比 ≤ 8×"为目标）：
- `air_gun` / `brush_tip_out`：各再补 **~600–800 个实例**（约对应若干段新视频的 air_injection 与 long_brush 时段）。
- `air_injection` 动作帧：再补 **~400 帧**，使其占比接近其他动作（≥11%）。

---

## 7. 复核方法

修复后重跑以下两步，确认问题清零：

```bash
cd cleansight-yolo-pipeline

# 1. 类别分布复核（本文档数据来源）
python count_classes.py

# 2. 推送前校验卡口（会把"某类 val/test 无样本"报为 warning）
python 05_check.py                 # 全部数据集
python 05_check.py --strict        # 严格模式：warning 也算失败
```

判定通过条件：
- `count_classes.py` 输出中，air_injection / short_brush_cleaning 在 val、test 均 > 0；
- `brush_tip_out`、`air_gun` 各数据集占比 ≥ 5%；
- `05_check.py --strict` 全部 PASS（无 warning）。

---

## 附：本次统计快照（2026-07-14）

- 数据集目录：`cleansight-yolo-pipeline/{datasets, datasets_actionmixed, datasets_actionseq}`
- 源视频数：`splits.yaml` 14 个、`splits_actionmixed.yaml` 12 个
- 关键缺口：ActionSequence air_injection(val/test=0)、short_brush_cleaning(val=0)；全局稀缺检测类 brush_tip_out / air_gun。
