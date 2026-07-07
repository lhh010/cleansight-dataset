# CleanSight Dataset Status

**生成时间**: 2026-07-07 19:49:10
**导出文件**: project-10-at-2026-07-07-19-32.json

## 任务状态总览

| LS Task ID | 视频 | 确认完成标注 | Split | 动作阶段 | 检测类别数 | 阶段帧数(采样后) |
|-----------|------|-------------|-------|---------|-----------|----------------|
| 50 | 218f9117-clip_1781583985044_178158400628 | [NO] | — | long_brush_insert | 4 | — |
| 51 | b004acff-clip_1781584008145_178158401651 | [NO] | — | long_brush_withdraw | 3 | — |
| 52 | 05ba4406-clip_1781584018103_178158403361 | [NO] | — | long_brush_insert | 5 | — |
| 53 | 9f93cf16-clip_1781584034867_178158404329 | [NO] | — | long_brush_insert | 4 | — |
| 54 | af0e7803-clip_1781584048438_178158406373 | [NO] | — | — | 6 | — |
| 55 | 7e8f5b4f-clip_1781584064111_178158406866 | [NO] | — | long_brush_withdraw | 4 | — |
| 56 | 687e3c78-clip_1781155551819_178115562950 | [NO] | — | — | 6 | — |
| 58 | ed1f1353-clip_1781659288372_178165932536 | [NO] | — | short_brush_cleaning | 3 | — |
| 59 | 4807dbbe-clip_1781659328328_178165946792 | [OK] | train | air_injection(30), long_brush_insert(134), long_brush_withdraw(69) | 4 | 233 |
| 60 | a2ade960-clip_1781660307856_178166058523 | [NO] | — | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 4 | — |
| 61 | 65d70028-clip_1781661552468_178166170290 | [OK] | val | flush(111), long_brush_insert(42), long_brush_withdraw(38) | 6 | 191 |
| 62 | 3614fb62-clip_1782091187000_178209137695 | [NO] | — | — | 0 | — |
| 63 | 54b6e047-clip_1782097591695_178209779479 | [NO] | — | — | 0 | — |
| 64 | 14e6fadd-clip_1782094867317_178209516573 | [NO] | — | — | 0 | — |
| 68 | 63a848d5-clip_1782695363948_178269559030 | [OK] | train | flush(257), long_brush_insert(83), long_brush_withdraw(54) | 6 | 394 |
| 69 | 2c635ddc-clip_1782695261284_178269533117 | [NO] | — | — | 1 | — |
| 75 | af4ea419-clip_1782955721678_178295596614 | [NO] | — | air_injection, long_brush_insert, short_brush_cleaning | 6 | — |

## 阶段汇总

| 阶段 | 任务 | Train 帧 | Val 帧 | Test 帧 | 合计帧 |
|------|------|---------|--------|---------|--------|
| long_brush_insert | 59, 61, 68 | 217 | 42 | 0 | 259 |
| long_brush_withdraw | 59, 61, 68 | 123 | 38 | 0 | 161 |
| air_injection | 59 | 30 | 0 | 0 | 30 |
| flush | 61, 68 | 257 | 111 | 0 | 368 |

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
| 2026-07-07 19:49:10 | lhh010/cleansight-raw | 原始 Label Studio 导出 + tracking.md |
| 2026-07-07 19:49:10 | lhh010/cleansight-yolo | 按动作阶段切分的 YOLO 数据集 |

> ⚠️ 每个 LS 任务的所有帧完整保留在同一 split 内，不存在跨 split 的时间相邻帧泄漏。
