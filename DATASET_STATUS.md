# CleanSight Dataset Status

**生成时间**: 2026-07-08 12:20
**导出文件**: project-10-at-2026-07-08-03-42-1df45c91.json

## 任务状态总览

| LS Task ID | 视频                                       | 确认完成标注 | Split | 动作阶段                                                         | 检测类别数 | 采样帧数 |
| ---------- | ---------------------------------------- | ------ | ----- | ------------------------------------------------------------ | ----- | ---- |
| 50         | 218f9117-clip_1781583985044_178158400628 | [OK]   | train | long_brush_insert                                            | 4     | 187  |
| 51         | b004acff-clip_1781584008145_178158401651 | [OK]   | test  | long_brush_withdraw                                          | 4     | 62   |
| 52         | 05ba4406-clip_1781584018103_178158403361 | [OK]   | train | long_brush_insert                                            | 5     | 174  |
| 53         | 9f93cf16-clip_1781584034867_178158404329 | [OK]   | test  | long_brush_withdraw                                          | 4     | 68   |
| 54         | af0e7803-clip_1781584048438_178158406373 | [OK]   | train | long_brush_insert                                            | 6     | 114  |
| 55         | 7e8f5b4f-clip_1781584064111_178158406866 | [OK]   | train | long_brush_withdraw                                          | 4     | 40   |
| 56         | 687e3c78-clip_1781155551819_178115562950 | [NO]   | —     | —                                                            | 6     | —    |
| 58         | ed1f1353-clip_1781659288372_178165932536 | [NO]   | —     | short_brush_cleaning                                         | 3     | —    |
| 59         | 4807dbbe-clip_1781659328328_178165946792 | [OK]   | train | air_injection, long_brush_insert, long_brush_withdraw        | 4     | 1726 |
| 60         | a2ade960-clip_1781660307856_178166058523 | [NO]   | —     | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 4     | —    |
| 61         | 65d70028-clip_1781661552468_178166170290 | [OK]   | val   | flush, long_brush_insert, long_brush_withdraw                | 6     | 2366 |
| 62         | 3614fb62-clip_1782091187000_178209137695 | [NO]   | —     | —                                                            | 0     | —    |
| 63         | 54b6e047-clip_1782097591695_178209779479 | [NO]   | —     | —                                                            | 0     | —    |
| 64         | 14e6fadd-clip_1782094867317_178209516573 | [NO]   | —     | —                                                            | 0     | —    |
| 68         | 63a848d5-clip_1782695363948_178269559030 | [OK]   | train | flush, long_brush_insert, long_brush_withdraw                | 6     | 3183 |
| 69         | 2c635ddc-clip_1782695261284_178269533117 | [OK]   | train | short_brush_cleaning                                         | 6     | 1331 |
| 75         | af4ea419-clip_1782955721678_178295596614 | [NO]   | —     | air_injection, long_brush_insert, short_brush_cleaning       | 6     | —    |

## Group 汇总

| Group | Split | 图像数 | 框数 |
|-------|-------|--------|------|
| group1_large | train | 4,199 | 14,850 |
| group1_large | val | 1,244 | 4,722 |
| group1_large | test | 124 | 431 |
| group2_small | train | 2,556 | 3,562 |
| group2_small | val | 1,122 | 1,350 |
| group2_small | test | 6 | 6 |

## ActionSequence 汇总

| 阶段 | Train | Val | Test | 合计 |
|------|-------|-----|------|------|
| short_brush_cleaning | 252 | 0 | 0 | 252 |
| long_brush_insert | 1,022 | 184 | 0 | 1,206 |
| long_brush_withdraw | 408 | 228 | 124 | 760 |
| air_injection | 367 | 0 | 0 | 367 |
| flush | 770 | 339 | 0 | 1,109 |

## Split 分配

| Split | 任务 | 视频 |
|-------|------|------|
| train | 50 | 218f9117-clip_1781583985044_1781584006285 |
| train | 52 | 05ba4406-clip_1781584018103_1781584033616 |
| train | 54 | af0e7803-clip_1781584048438_1781584063735 |
| train | 55 | 7e8f5b4f-clip_1781584064111_1781584068667 |
| train | 59 | 4807dbbe-clip_1781659328328_1781659467929 |
| train | 68 | 63a848d5-clip_1782695363948_1782695590302 |
| train | 69 | 2c635ddc-clip_1782695261284_1782695331171 |
| val | 61 | 65d70028-clip_1781661552468_1781661702909 |
| test | 51 | b004acff-clip_1781584008145_1781584016511 |
| test | 53 | 9f93cf16-clip_1781584034867_1781584043290 |

## 上传记录

| 日期 | 仓库 | 说明 |
|------|------|------|
| 2026-07-08 12:05 | lhh010/cleansight-raw | 更新 DATASET_STATUS.md，最新 LS 导出 |
| 2026-07-08 12:05 | lhh010/cleansight-yolo | 新增 task#50-55, #69 → 9,251 张 |
| 2026-07-08 12:17 | lhh010/cleansight-ActionSequence | 新增 task#50-55, #69 → 3,694 张 |

> 每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏。
> 旋转标注框已自动转换为外接轴对齐矩形 (AABB)。
> 稀有类别 (< 200 keyframes) 启用密集相邻帧采样。
