# CleanSight 稀缺类补采 / 补标清单

> 生成时间：2026-07-14
> 数据来源：Label Studio Project #10 最新导出 `raw/exports/project-10-at-2026-07-12-02-49-086781a3.json`（21 个任务）+ `completed_tasks.json`（已构建 12 个）+ `splits.yaml`
> 配套工具：`cleansight-yolo-pipeline/build_checklist.py`（可复跑）
> 关联文档：`DATASET_BALANCE_REVIEW.md`（类别分布与问题汇总）

## 0. 核心结论（先看这条）

经核对，**补采不必从零开始**。Label Studio 里已有 **21 个任务、19 个已标注**，但当前只把其中 **12 个**构建进了数据集。**有 7 个已标注任务还没构建**，其中恰好包含全部稀缺类的来源：

| 稀缺类 | 已构建来源 | 已标注但**未构建**的来源（现成可用） |
|---|---|---|
| air_injection | task#59（train） | **task#62、task#75** |
| air_gun | task#54、#59（train） | **task#56、task#62** |
| brush_tip_out | task#50、#52、#54、#61、#68 | **task#62** |
| short_brush | task#51、#69、#77 | **task#58、#60、#75** |

**只要把 task#56、#62、#75 三个已标注任务构建进数据集并分配 split，4 个稀缺类的 train/val/test 覆盖缺口全部补齐（见 §4），无需新标注。** 新标注（task#63、#64）和重新录制只在"还要继续加量"时才需要。

---

## 1. 稀缺类来源定位（每个稀缺类来自哪些视频/任务）

### 1.1 动作类 `air_injection`（全数据集最少）
| task | 视频 | split | 磁盘 | 状态 |
|---|---|---|---|---|
| #59 | 4807dbbe | train | ✓ | 已构建（唯一来源） |
| **#62** | **3614fb62** | 未分配 | ✓ | **已标注待构建** |
| **#75** | **af4ea419** | 未分配 | ✓ | **已标注待构建** |

### 1.2 检测类 `air_gun`（≈394 实例）
| task | 视频 | split | 磁盘 | 状态 |
|---|---|---|---|---|
| #54 | af0e7803 | train | ✓ | 已构建 |
| #59 | 4807dbbe | train | ✓ | 已构建 |
| **#56** | **687e3c78** | val | ✓ | **已标注待构建** |
| **#62** | **3614fb62** | 未分配 | ✓ | **已标注待构建** |

### 1.3 检测类 `brush_tip_out`（≈318 实例，全局最稀缺）
| task | 视频 | split | 磁盘 | 状态 |
|---|---|---|---|---|
| #50 | 218f9117 | train | ✓ | 已构建 |
| #52 | 05ba4406 | train | ✓ | 已构建 |
| #54 | af0e7803 | train | ✓ | 已构建 |
| #61 | 65d70028 | val | ✓ | 已构建 |
| #68 | 63a848d5 | train | ✓ | 已构建 |
| **#62** | **3614fb62** | 未分配 | ✓ | **已标注待构建** |

### 1.4 检测类 `short_brush`（≈873 实例）
| task | 视频 | split | 磁盘 | 状态 |
|---|---|---|---|---|
| #51 | b004acff | test | ✓ | 已构建 |
| #69 | 2c635ddc | train | ✓ | 已构建 |
| #77 | fedf6ff9 | test | ✓ | 已构建 |
| **#58** | **ed1f1353** | train | ✓ | **已标注待构建** |
| **#60** | **a2ade960** | 未分配 | ✓ | **已标注待构建** |
| **#75** | **af4ea419** | 未分配 | ✓ | **已标注待构建** |
| #71 | 37c53d37 | 未分配 | ✗ 缺视频 | 已标注待下载 |

---

## 2. 补采清单（按优先级分四类）

### 类别 A — 立即构建（已标注 + 磁盘有视频，零标注成本，最高 ROI）

| 优先级 | task | 视频 | 帧数 | 动作 | 补的稀缺类 | 当前 split | **建议 split** |
|---|---|---|---|---|---|---|---|
| **A1** | **#62** | 3614fb62 | 4559 | air_injection / flush / long_brush_insert / long_brush_withdraw | **air_gun + air_injection + brush_tip_out** | 未分配 | **test** |
| **A2** | **#75** | af4ea419 | 5866 | air_injection / long_brush_insert / short_brush_cleaning | **air_injection + short_brush** | 未分配 | **val** |
| **A3** | **#56** | 687e3c78 | 1865 | （无动作标注，纯检测） | **air_gun** | val | val（保持） |
| A4 | #60 | a2ade960 | 6658 | long_brush_insert / withdraw / short_brush_cleaning | short_brush（补量） | 未分配 | train |
| A5 | #58 | ed1f1353 | 888 | short_brush_cleaning | short_brush（补量） | train | train（保持） |

> A1–A3 是**修 split 缺口的必做项**（缺一不可，见 §4 分配矩阵）；A4–A5 是纯加量，可一起做。

### 类别 B — 待标注（视频在磁盘，但 Label Studio 里还没标注）

| task | 视频 | 文件大小 | 动作/稀缺类 | 处理 |
|---|---|---|---|---|
| #63 | 54b6e047 | 16 MB | 未知（待标注后确认） | 标注 → 查内容 → 按稀缺类需求分配 split |
| #64 | 14e6fadd | 29 MB（最长片段） | 未知（待标注后确认） | 同上，大概率内容丰富，优先标注 |

> 这两个是"补量"的主力候选。标注后若含 air_injection / brush_tip_out / air_gun，按 §4 矩阵补进相应缺 split。

### 类别 C — 已标注但视频不在磁盘（需先从 Label Studio 重新下载视频）

| task | 视频 | 帧数 | 动作 | 稀缺类 | 处理 |
|---|---|---|---|---|---|
| #71 | 37c53d37 | 3266 | long_brush_insert / withdraw / short_brush_cleaning | short_brush | 重下视频 → 构建（补 short_brush 量） |
| #76 | b3f244c7 | 6910 | （无动作标注，纯检测，无稀缺类） | — | 低优先，可跳过 |

### 类别 D — 需新录制 / 新采集（仅当 A+B+C 仍不够时）

当前 A 类已能修满 split 覆盖，D 类只在**继续压低 imbalance 比**时考虑，目标方向：
- 更多 **air_injection**（气枪吹气）片段 —— 同时补 air_gun 检测类与 air_injection 动作类
- 更多含 **brush_tip_out**（刷头外露）的 long_brush 片段
- 录制时确保新片段来自**不同源视频/不同内镜型号**，避免单一来源

---

## 3. 视频与任务的完整对照（备查）

| task | 视频 stem | split | 磁盘 | 帧 | 已构建 | 动作 | 含稀缺类 |
|---|---|---|---|---|---|---|---|
| #50 | 218f9117 | train | ✓ | 510 | ✓ | long_brush_insert | brush_tip_out |
| #51 | b004acff | test | ✓ | 201 | ✓ | long_brush_withdraw | short_brush |
| #52 | 05ba4406 | train | ✓ | 372 | ✓ | long_brush_insert | brush_tip_out |
| #53 | 9f93cf16 | test | ✓ | 202 | ✓ | long_brush_withdraw | — |
| #54 | af0e7803 | train | ✓ | 366 | ✓ | long_brush_insert | air_gun, brush_tip_out |
| #55 | 7e8f5b4f | train | ✓ | 110 | ✓ | long_brush_withdraw | — |
| **#56** | 687e3c78 | val | ✓ | 1865 | ✗ | — | air_gun |
| **#58** | ed1f1353 | train | ✓ | 888 | ✗ | short_brush_cleaning | short_brush |
| #59 | 4807dbbe | train | ✓ | 3351 | ✓ | air_injection / long_brush×2 | air_gun, air_injection |
| **#60** | a2ade960 | 未分配 | ✓ | 6658 | ✗ | long_brush×2 / short_brush_cleaning | short_brush |
| **#62** | 3614fb62 | 未分配 | ✓ | 4559 | ✗ | air_injection / flush / long_brush×2 | air_gun, air_injection, brush_tip_out |
| **#63** | 54b6e047 | 未分配 | ✓ | — | ✗ | （未标注） | ? |
| **#64** | 14e6fadd | 未分配 | ✓ | — | ✗ | （未标注） | ? |
| #68 | 63a848d5 | train | ✓ | 5433 | ✓ | flush / long_brush×2 | brush_tip_out |
| #69 | 2c635ddc | train | ✓ | 1677 | ✓ | short_brush_cleaning | short_brush |
| **#71** | 37c53d37 | 未分配 | ✗ | 3266 | ✗ | long_brush×2 / short_brush_cleaning | short_brush |
| **#75** | af4ea419 | 未分配 | ✓ | 5866 | ✗ | air_injection / long_brush_insert / short_brush_cleaning | air_injection, short_brush |
| **#76** | b3f244c7 | 未分配 | ✗ | 6910 | ✗ | — | — |
| #77 | fedf6ff9 | test | ✓ | 1278 | ✓ | flush / short_brush_cleaning | short_brush |
| #78 | b1b042a9 | test | ✓ | 766 | ✓ | long_brush×2 | — |

（✗=未构建；#56/#58 虽在 `splits.yaml` 有 split，但未进 `completed_tasks.json`，故未构建。）

---

## 4. 划分分配矩阵（修复前 vs 修复后）

**修复前**（仅已构建的 12 个任务）—— 4 个稀缺类均有 split 缺口：

| 稀缺类 | train | val | test | 缺口 |
|---|---|---|---|---|
| air_gun | #54, #59 | — | — | 缺 val、test |
| air_injection | #59 | — | — | 缺 val、test |
| brush_tip_out | #50,#52,#54,#68 | #61 | — | 缺 test |
| short_brush | #69 | — | #51, #77 | 缺 val |

**修复方案**：构建并分配 `#56→val`、`#62→test`、`#75→val`，即可：

| 稀缺类 | train | val | test | 结果 |
|---|---|---|---|---|
| air_gun | #54, #59 | **#56** | **#62** | ✅ 全覆盖 |
| air_injection | #59 | **#75** | **#62** | ✅ 全覆盖 |
| brush_tip_out | #50,#52,#54,#68 | #61 | **#62** | ✅ 全覆盖 |
| short_brush | #69 | **#75** | #51, #77 | ✅ 全覆盖 |

> 为什么 #62 必须进 test：它是唯一能给 **air_gun 和 brush_tip_out** 提供 test 来源的可用视频（其余 air_gun/brush_tip_out 来源都已固定在 train/val）。#75 进 val 同时补 air_injection 和 short_brush 的 val 缺口。

---

## 5. 执行步骤

### 第一步：分配 split（编辑 `cleansight-yolo-pipeline/splits.yaml`）

把以下三条加进 `assignments`（人工钉死，永不被自动重排）：

```yaml
  3614fb62-clip_1782091187000_1782091376956: test     # task#62  air_injection/air_gun/brush_tip_out 补 test
  af4ea419-clip_1782955721678_1782955966143: val       # task#75  air_injection/short_brush 补 val
  # 687e3c78 已是 val（task#56），保持不变
  # a2ade960 / ed1f1353 若要补量，分别钉 train / 保持 train
  a2ade960-clip_1781660307856_1781660585237: train     # task#60  short_brush 补量（可选）
```

> 注意：`splits.yaml` 是 YOLO + ActionSequence 共用真源，改它会同时影响两者——这正是我们想要的。

### 第二步：拉取并构建（在 `cleansight-yolo-pipeline/` 下）

```bash
# 从 Label Studio 拉最新标注（含 #56 #62 #75 等未构建任务）
python 01_pull_data.py

# 重建三个数据集（带 --auto-assign 让新视频按 splits.yaml 落位）
python 02_build_dataset.py --auto-assign          # YOLO
python 02_build_actionseq.py --auto-assign        # ActionSequence
# ActionMixed 走段级切分，单独的 split 文件
python 02_build_actionmixed.py --auto-assign      # ActionMixed
```

### 第三步：复核（必须 warning 清零）

```bash
python count_classes.py          # 看 air_injection/short_brush 在 val、test 是否 >0
python 05_check.py --strict      # 严格模式，稀缺类 split 无样本的 warning 应消失
```

通过条件：
- 4 个稀缺类在 train/val/test **各 ≥1 个源视频**（见 §4 修复后矩阵全 ✅）；
- `brush_tip_out`、`air_gun` 各数据集占比回升（预计 +30%~50%，因并入 #62、#56、#75）；
- `05_check.py --strict` 全 PASS。

### 第四步（可选）：补量
- 标注 #63、#64（类别 B）→ 按其内容补进缺量 split；
- 重下载 #71 视频（类别 C）→ 构建，补 short_brush；
- 仍不够时进入类别 D（新录制 air_injection / brush_tip_out 片段）。

---

## 6. 预期效果（构建 A1–A3 后的粗估）

| 指标 | 修复前 | 修复后（构建 #56/#62/#75） |
|---|---|---|
| air_injection 源视频数 | 1 | 3（train/val/test 各 1） |
| air_gun 源视频数 | 2（均 train） | 4（train×2 / val / test） |
| brush_tip_out 源视频数 | 5（无 test） | 6（含 test） |
| 稀缺类 split 缺口总数 | 6 处 | **0 处** |
| `05_check.py` 相关 warning | 多条 | 清零 |

> 说明：本文档的"修 split 缺口"结论比 `DATASET_BALANCE_REVIEW.md` §5 更乐观——经核查 Label Studio 后发现已有足够多的标注任务尚未构建，原"必须新标注"的判断在此被修正为"先构建现成的即可"。
