# CleanSight Dataset Status

**生成时间**: 2026-07-31 10:58
**导出文件**: project-10-at-2026-07-31-02-40-8cc4d930.json
**管线版本**: yolo 两轨分离（train.yaml + test.yaml），配置与清单下沉至 yolo/

## 任务状态总览

| LS Task ID | 视频 | 确认 | Split | 动作段 | 检测类别数 | 采样帧数 |
|-----------|------|------|-------|--------|----------|---------|
| 50 | 218f9117-clip_1781583985044_178158400628 | ✅ | train | long_brush_insert | 4 | 187 |
| 51 | b004acff-clip_1781584008145_178158401651 | ✅ | train | long_brush_withdraw | 4 | 62 |
| 52 | 05ba4406-clip_1781584018103_178158403361 | ✅ | train | long_brush_insert | 5 | 174 |
| 53 | 9f93cf16-clip_1781584034867_178158404329 | ✅ | train | long_brush_withdraw | 4 | 68 |
| 54 | af0e7803-clip_1781584048438_178158406373 | ✅ | train | long_brush_insert | 6 | 114 |
| 55 | 7e8f5b4f-clip_1781584064111_178158406866 | ✅ | train | long_brush_withdraw | 4 | 40 |
| 56 | 687e3c78-clip_1781155551819_178115562950 | — | — | — | 6 | — |
| 58 | ed1f1353-clip_1781659288372_178165932536 | — | — | short_brush_cleaning | 3 | — |
| 59 | 4807dbbe-clip_1781659328328_178165946792 | ✅ | train | air_injection, long_brush_insert, long_brush_withdraw | 4 | 1,726 |
| 60 | a2ade960-clip_1781660307856_178166058523 | ✅ | train | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 6 | 4,519 |
| 61 | 65d70028-clip_1781661552468_178166170290 | ✅ | val | flush, long_brush_insert, long_brush_withdraw | 6 | 2,366 |
| 62 | 3614fb62-clip_1782091187000_178209137695 | ✅ | train | air_injection, flush, long_brush_insert, long_brush_withdraw | 7 | 3,145 |
| 63 | 54b6e047-clip_1782097591695_178209779479 | — | — | — | 1 | — |
| 64 | 14e6fadd-clip_1782094867317_178209516573 | — | — | — | 0 | — |
| 68 | 63a848d5-clip_1782695363948_178269559030 | ✅ | train | flush, long_brush_insert, long_brush_withdraw | 6 | 3,183 |
| 69 | 2c635ddc-clip_1782695261284_178269533117 | ✅ | train | short_brush_cleaning | 6 | 1,331 |
| 71 | 37c53d37-clip_1782286495080_178228663118 | — | — | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 4 | — |
| 73 | f4b10ad8-clip_1782264442808_178226445707 | — | — | air_injection | 4 | — |
| 75 | af4ea419-clip_1782955721678_178295596614 | — | — | air_injection, long_brush_insert, short_brush_cleaning | 6 | — |
| 76 | b3f244c7-clip_1782954681773_178295496970 | — | — | — | 4 | — |
| 77 | fedf6ff9-clip_1783393131145_178339318440 | ✅ | train | flush, short_brush_cleaning | 6 | 1,894 |
| 78 | b1b042a9-clip_1783395777441_178339580934 | ✅ | train | long_brush_insert, long_brush_withdraw | 3 | 239 |
| 80 | 6b722939-clip_1782802545949_178280262474 | — | — | air_injection, flush, short_brush_cleaning | 6 | — |
| 82 | 3d3ec766-clip_1782869840929_178286986646 | — | — | air_injection | 4 | — |
| 83 | 1301ed4c-clip_1782871306647_178287134851 | — | — | air_injection, long_brush_insert, long_brush_withdraw | 4 | — |
| 84 | f0d28b80-clip_1783302144895_178330218785 | ✅ | train | air_injection, short_brush_cleaning | 4 | 693 |
| 85 | 1fcfcdea-clip_1783302201419_178330226191 | ✅ | train | long_brush_insert, long_brush_withdraw | 5 | 592 |
| 86 | 78f3593a-clip_1783301769259_178330181038 | — | — | — | 0 | — |
| 87 | b3778449-clip_1783301814930_178330192624 | — | — | — | 0 | — |
| 88 | 3b2dcda0-clip_1783306816456_178330686171 | — | — | — | 0 | — |
| 89 | ab4e3537-clip_1783306867441_178330697676 | — | — | — | 0 | — |
| 90 | 3c6d95a9-clip_1783306980410_178330699344 | — | — | — | 0 | — |
| 91 | 8379a7c3-clip_1783566098640_178356624035 | — | — | — | 4 | — |

> ✅ = 已确认并登记在册（train.yaml tasks），— = 未质检/未登记，不在训练集中

## Group 汇总

| Group | Split | 图像数 | 框数 |
|-------|-------|--------|------|
| group1_large | train | 10,410 | 35,090 |
| group1_large | val | 1,244 | 4,722 |
| group2_small | train | 7,557 | 10,901 |
| group2_small | val | 1,122 | 1,350 |

## 类别定义

### group1_large — 大目标
| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `hand` | 操作者手部 |
| 1 | `scope_control_body` | 内镜操控部 |
| 2 | `scope_mid_section` | 内镜中部 |

### group2_small — 小目标
| class_id | 标签 | 说明 |
|----------|------|------|
| 0 | `syringe` | 注射器 |
| 1 | `air_gun` | 气枪 |
| 2 | `scope_distal_end` | 内镜头端 |
| 3 | `short_brush` | 短毛刷 |
| 4 | `brush_tip_out` | 刷头外露 |

## Split 分配

| Split | Task ID |
|-------|---------|
| train | 50, 51, 52, 53, 54, 55, 59, 60, 62, 68, 69, 77, 78, 84, 85 |
| val | 61 |
| test | —（benchmark 轨独立策展，见 yolo/test.yaml） |

> 每个 LS 任务的所有帧完整保留在同一 split 内，杜绝时间相邻帧泄漏。
> 旋转标注框已自动转换为外接轴对齐矩形 (AABB)。
> 稀有类别 (< 200 keyframes) 启用密集相邻帧采样：air_gun, brush_tip_out, short_brush。
> 帧名 `t{task_id}_{frame:06d}`，身份键是 LS task id（全局唯一，重传视频不变）。

## 已知缺口

- `air_gun` 和 `short_brush` 在 val 中无样本（val 仅 task#61，这两类在其采样帧中未出现）
- test 集未构建（待 yolo-test LS 项目标注完成 + benchmark 策展）
- 异内镜型号 / 异操作者泛化：暂无数据源（见 docs/BENCHMARK_DETECTION.md §1）

## 上传记录

| 日期 | 仓库 | 说明 |
|------|------|------|
| 2026-07-31 | lhh010/cleansight-yolo | 管线重构后首次全量构建：16 task、stride=4、20,333 张图、5 类小目标 |
