# CleanSight 数据集完善计划

> 生成时间：2026-07-17
> 目标：把现有数据集从「能训练」补到「能通过 30 条测试用例（`DATASET_TEST_CASES.md`）的 P0/P1 全覆盖」
> 依据：`DATASET_BALANCE_REVIEW.md`（2026-07-14 分布快照）、`DATASET_COLLECTION_CHECKLIST.md`（现成待构建任务）、`DATASET_TEST_SCENARIOS.md` / `DATASET_TEST_CASES.md`（场景与缺口）
> 核心原则：**先零成本（构建现成标注）→ 再低成本（标注已有视频）→ 再补采（难点 / 泛化 / 异常）→ 最后增强**

---

## 1. 完善目标与验收标准

### 1.1 类别均衡（检测类）
- 每类占比 **≥ 5%**；最大/最小类实例比 **≤ 8×**。
- 当前差距：YOLO g2 ≈ 11×、ActionMixed frames ≈ 33×；`brush_tip_out`(318)、`air_gun`(394)、`short_brush`(910 in g2) 为短板。

### 1.2 动作 split 覆盖
- 每个动作在 **train / val / test 各 ≥ 1 个源视频**。
- 当前差距：`air_injection`(1 源视频，val+test=0)、`short_brush_cleaning`(2 源视频，val=0)。

### 1.3 场景覆盖（对齐 30 条用例）
- **P0 用例（11 条）全部 ✅**；P1 用例（14 条）至少 ⚠️→✅。
- 难点维度（极小 / 重遮挡 / 模糊 / 反光 / 偏暗）每类各有 **≥ 100 实例**。

### 1.4 负样本与异常
- 空帧占比 **5–10%**（防过检）；按动作×目标矩阵 `—` 单元构造**不可能组合校验集**。

### 1.5 泛化（最薄弱项）
- `splits.yaml` 的 `e2e_test` 通道补 **≥ 6 个域外视频**：异型号 ≥3、异操作者 ≥2、异机位 ≥1。

### 1.6 自动化卡口
- `count_classes.py`：稀缺类占比回升、`air_injection`/`short_brush_cleaning` 在 val/test > 0。
- `05_check.py --strict`：全 PASS、无 warning。

---

## 2. 现状诊断（缺口一览）

| 缺口类别 | 影响用例 | 现状 | 根因 |
|---|---|---|---|
| 动作 split 缺失 | S01、S05 | air_injection val+test=0；short_brush_cleaning val=0 | 源视频数不足（1/2 个），视频级划分落空 |
| 检测稀缺类 | S03、S04、S24–S27 | brush_tip_out 318、air_gun 394、short_brush×flush 135 | 物体出现帧少 + 标注覆盖不足 |
| 极小/遮挡/模糊/反光/偏暗难点 | S07–S12 | 基本缺失或偶发 | 仅随机抽帧，未刻意采集难点帧 |
| 负样本与异常 | S14、S15、S19、S20 | 缺失 | 未系统保留空帧、未构造不可能组合、未录异常 |
| 泛化 | S21–S23 | 全缺 | 源视频 12–14 个、型号/操作者/机位单一 |

---

## 3. 任务清单（六类，按 ROI 排序）

### 任务 1 —— 零成本构建现成标注（修 split 缺口 + 补稀缺类，最高 ROI）

依据 `DATASET_COLLECTION_CHECKLIST.md`：7 个已标注任务尚未构建，恰好含全部稀缺类来源。

| 操作 | task | 视频 | 建议 split | 修复的缺口 / 用例 |
|---|---|---|---|---|
| 构建 | #62 | 3614fb62 | **test** | air_gun+brush_tip_out 的 test（S03/S24/S25）；air_injection 的 test（S01） |
| 构建 | #75 | af4ea419 | **val** | air_injection+short_brush 的 val（S01/S05/S28） |
| 构建 | #56 | 687e3c78 | val（保持） | air_gun 的 val（S24） |
| 构建 | #58 | ed1f1353 | train（保持） | short_brush 补量（S05/S28） |
| 构建（可选） | #60 | a2ade960 | train | short_brush 补量 |

**操作**：
```bash
cd cleansight-yolo-pipeline
# 1) 编辑 splits.yaml：把 #62 钉 test、#75 钉 val（人工分配，永不被重排）
#    3614fb62-clip_1782091187000_1782091376956: test
#    af4ea419-clip_1782955721678_1782955966143: val
python 01_pull_data.py
python 02_build_dataset.py --auto-assign        # YOLO
python 02_build_actionseq.py --auto-assign      # ActionSequence
python 02_build_actionmixed.py --auto-assign    # ActionMixed
python count_classes.py
python 05_check.py --strict
```
**预期收益**：4 个稀缺类的 train/val/test split 缺口从 6 处 → 0 处；air_injection 源视频 1→3、air_gun 2→4、brush_tip_out 5→6（含 test）。

---

### 任务 2 —— 低成本标注已有视频（补稀缺类数量）

| 操作 | task | 视频 | 预期补的类 | 用例 |
|---|---|---|---|---|
| 标注 | #64 | 14e6fadd（最长 29MB） | 大概率内容丰富，按内容分配 | S24–S27 主力 |
| 标注 | #63 | 54b6e047 | 按内容分配 | S24–S27 |
| 重下视频→构建 | #71 | 37c53d37 | short_brush（long_brush/short_brush_cleaning） | S05/S28 |

**操作**：在 Label Studio 用 videorectangle + timelinelabels 标注 → 加入 `config.yaml:only_videos` → `00_status.py --assign` → 按稀缺类需求钉 split → 重建。

**目标**：`brush_tip_out` ≥ 1000、`air_gun` ≥ 1000、`short_brush` ≥ 1500、`air_injection` 帧 ≥ 800。

---

### 任务 3 —— 难点场景补采（S07–S12）

现有抽帧不覆盖难点，需**从已有/新录视频中专门筛选 + 补标**难点帧。

| 难点 | 用例 | 目标实例 | 采集方式 |
|---|---|---|---|
| 极小目标远景 | S07 | ≥100/类（air_gun、brush_tip_out 远景） | 筛远景入画帧；必要时长焦/远机位补录 |
| 重遮挡 | S08 | ≥150 | 筛手部遮挡器械的密集操作帧 |
| 边缘截断 | S09 | ≥100 | 筛目标半出画的边缘帧 |
| 快速运动模糊 | S10 | ≥150（brush_tip_out） | 筛长刷快速抽出段；提高该段抽帧密度（stride=1） |
| 反光 / 水珠 | S11 | ≥150 | 筛冲洗台面反光/水珠帧 |
| 偏暗光照 | S12 | ≥100 | 补录低光清洗段（或对正常段做暗光仿真，仅作辅助） |

**操作**：写一个筛选脚本（按 bbox 面积 < 1% 画幅筛极小；按相邻帧位移筛模糊等）→ 导入 Label Studio 补标 → 进 train。

---

### 任务 4 —— 负样本与异常（S14、S15、S19、S20）

| 类型 | 用例 | 目标 | 方式 |
|---|---|---|---|
| 空帧负样本 | S15 | 占比 5–10% | 修改 `02_build_dataset.py`：保留无标注帧入 train（当前丢弃空帧） |
| 不可能组合校验 | S19 | 覆盖 5.1 矩阵 18 个 `—` 单元 | 脚本自动采样：在 air_injection 段校验"不应报 syringe"等 |
| 干扰物防误检 | S14 | ≥200 | 补采含其他器械/管路的帧，标注为"非目标" |
| 异常动作 | S20 | ≥3 段 | 补录器械掉落/误操作段，标为 idle 或告警 |

**操作**：负样本主要靠 pipeline 改造 + 脚本构造；异常段需少量补录。

---

### 任务 5 —— 泛化集（S21–S23，最关键也最缺）

`splits.yaml` 已预留 `e2e_test` 通道（只评不训）。需补录**域外**视频：

| 维度 | 用例 | 目标 | 说明 |
|---|---|---|---|
| 异内镜型号 | S21 | ≥3 视频 | 不同品牌/型号内镜，覆盖 S01–S05 各动作 |
| 异操作者 | S22 | ≥2 视频 | 不同人员执行标准流程 |
| 异机位/角度 | S23 | ≥1 视频（重点刷头时段） | 不同摄像头位置/俯仰角 |

**操作**：录制 → 标注 → `splits.yaml` 钉 `e2e_test` → 构建（**不进 train/val/test**）→ 单独跑 S21–S23 评估。

---

### 任务 6 —— 数据增强（兜底，不替代真实补标）

对稀缺类在 **train 内**做轻量增强（`02b_augment.py`）：
- 目标类：`brush_tip_out`、`air_gun`、`short_brush`。
- 方式：旋转 / 缩放 / 亮度抖动（对应 S11/S12 难点也可用增强缓解）。
- 约束：**仅 train，绝不增强 val/test/e2e_test**，否则指标失真。

```bash
python 02b_augment.py --threshold=150 --copies=3 --dry-run   # 先 dry-run 看量
```

---

## 4. 分阶段路线图

| 阶段 | 内容 | 对应用例 | 成本 | 验收 |
|---|---|---|---|---|
| **Phase 0** | 任务 1：构建 #62/#75/#56/#58 | S01、S05、S24–S26（split 部分） | 零标注 | 稀缺类 split 缺口=0；`05_check.py --strict` PASS |
| **Phase 1** | 任务 2：标注 #63/#64、重下 #71 | S24–S28（数量） | 低 | 稀缺类实例达 1.1.1 目标 |
| **Phase 2** | 任务 3：难点帧筛选 + 补标 | S07–S12 | 中 | 各难点 ≥100 实例 |
| **Phase 3** | 任务 4：负样本 + 异常 | S14、S15、S19、S20 | 中 | 空帧 5–10%；不可能组合校验通过 |
| **Phase 4** | 任务 5：泛化集录制 | S21–S23 | 高（需新录） | e2e_test ≥6 视频；recall 衰减≤15pp |
| **Phase 5** | 任务 6：稀缺类增强 | — | 低 | 稀缺类 train 增强 3× |

> Phase 0 可立即执行且收益最大；Phase 4 是最大缺口，建议尽早立项录制。

---

## 5. 数量测算汇总

| 项目 | 现有 | 目标 | 需补 |
|---|---|---|---|
| brush_tip_out 实例 | 318 | ≥1000 | ~700 |
| air_gun 实例 | 394 | ≥1000 | ~600 |
| short_brush 实例（g2） | 910 | ≥1500 | ~600（重点 flush 侧 135） |
| air_injection 帧 | 366 | ≥800 | ~430 |
| 各难点维度实例 | 0 / 偶发 | ≥100/维度 | ~100–150/维度 |
| 空帧负样本 | 0 | 占比 5–10% | pipeline 改造 |
| 域外泛化视频 | 0 | ≥6 | 全新录制 |
| 源视频总数 | 12–14 | ≥24 | +10 左右 |

---

## 6. 复核与卡口

每次补数据后必须重跑，全部通过方可上传：

```bash
cd cleansight-yolo-pipeline
python count_classes.py            # 类别占比 / split 覆盖
python 05_check.py --strict        # 严格校验，warning 即失败
```

**通过条件**：
- 4 个稀缺类在 train/val/test 各 ≥1 源视频；
- `brush_tip_out`/`air_gun` 占比 ≥5%、max:min ≤8×；
- P0 用例（11 条）指标达 `DATASET_TEST_CASES.md` 判定基线；
- `e2e_test` 泛化集 recall 衰减 ≤15pp；
- `05_check.py --strict` 全 PASS。

---

## 7. 与现有文档的关系

- `DATASET_BALANCE_REVIEW.md`：类别分布与 split 缺口的**诊断**（本文 §2 的数据来源）。
- `DATASET_COLLECTION_CHECKLIST.md`：现成待构建任务的**清单**（本文任务 1 的操作来源；本文比其更乐观，因核查后确认现成标注已足够修 split 缺口）。
- `DATASET_TEST_SCENARIOS.md`：维度 / 等价类 / 组合**设计**。
- `DATASET_TEST_CASES.md`：30 条**用例**与判定（本文 §1.3、§4 验收的对照标准）。
- 本文：**完善计划**（把诊断 → 任务 → 路线图 → 验收串起来）。
