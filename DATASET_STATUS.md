# CleanSight Dataset Status

**生成时间**: 2026-07-07 21:27:43
**导出文件**: project-10-at-2026-07-07-19-32.json

## 任务状态总览

| LS Task ID | 视频 | 确认完成标注 | Split | 动作阶段 | 检测类别数 | 采样帧数 |
|-----------|------|-------------|-------|---------|-----------|---------|
| 50 | 218f9117-clip_1781583985044_178158400628 | [NO] | — | long_brush_insert | 4 | — |
| 51 | b004acff-clip_1781584008145_178158401651 | [NO] | — | long_brush_withdraw | 3 | — |
| 52 | 05ba4406-clip_1781584018103_178158403361 | [NO] | — | long_brush_insert | 5 | — |
| 53 | 9f93cf16-clip_1781584034867_178158404329 | [NO] | — | long_brush_insert | 4 | — |
| 54 | af0e7803-clip_1781584048438_178158406373 | [NO] | — | — | 6 | — |
| 55 | 7e8f5b4f-clip_1781584064111_178158406866 | [NO] | — | long_brush_withdraw | 4 | — |
| 56 | 687e3c78-clip_1781155551819_178115562950 | [NO] | — | — | 6 | — |
| 58 | ed1f1353-clip_1781659288372_178165932536 | [NO] | — | short_brush_cleaning | 3 | — |
| 59 | 4807dbbe-clip_1781659328328_178165946792 | [OK] | train | air_injection, long_brush_insert, long_brush_withdraw | 4 | 1128 |
| 60 | a2ade960-clip_1781660307856_178166058523 | [NO] | — | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 4 | — |
| 61 | 65d70028-clip_1781661552468_178166170290 | [OK] | val | flush, long_brush_insert, long_brush_withdraw | 6 | 2012 |
| 62 | 3614fb62-clip_1782091187000_178209137695 | [NO] | — | — | 0 | — |
| 63 | 54b6e047-clip_1782097591695_178209779479 | [NO] | — | — | 0 | — |
| 64 | 14e6fadd-clip_1782094867317_178209516573 | [NO] | — | — | 0 | — |
| 68 | 63a848d5-clip_1782695363948_178269559030 | [OK] | train | flush, long_brush_insert, long_brush_withdraw | 6 | 3108 |
| 69 | 2c635ddc-clip_1782695261284_178269533117 | [NO] | — | — | 1 | — |
| 75 | af4ea419-clip_1782955721678_178295596614 | [NO] | — | air_injection, long_brush_insert, short_brush_cleaning | 6 | — |

## Group 汇总

| Group | Split | 图像数 | 框数 |
|-------|-------|--------|------|
| group1_large | train | 2684 | 9494 |
| group1_large | val | 1067 | 4035 |
| group2_small | train | 1552 | 2329 |
| group2_small | val | 945 | 945 |

## Split 分配

| Split | 任务 | 视频 |
|-------|------|------|
| train | 59 | 4807dbbe-clip_1781659328328_1781659467929 |
| train | 68 | 63a848d5-clip_1782695363948_1782695590302 |
| val | 61 | 65d70028-clip_1781661552468_1781661702909 |
| test | — | — |

## 上传记录

| 日期 | 仓库 | 说明 |
|------|------|------|
| 2026-07-07 21:27:43 | lhh010/cleansight-raw | 原始 Label Studio 导出 + DATASET_STATUS.md |
| 2026-07-07 21:27:43 | lhh010/cleansight-yolo | group1_large / group2_small YOLO 数据集 |

> 每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏。
> 旋转标注框已自动转换为外接轴对齐矩形 (AABB)。
