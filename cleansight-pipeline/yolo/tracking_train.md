# CleanSight YOLO · 训练轨(train/val)

**生成**: 2026-07-31 10:58:56
**清单**: train.yaml
**项目**: yolo-train
**导出**: project-10-at-2026-07-31-02-40-8cc4d930.json

## 在册 task

| LS Task | 视频 | Split | 本次构建 | 动作段 | 检测类 | 落盘帧 |
|---------|------|-------|---------|--------|--------|--------|
| 50 | 218f9117-clip_1781583985044_1781584 | train | 是 | long_brush_insert | 4 | 187 |
| 51 | b004acff-clip_1781584008145_1781584 | train | 是 | long_brush_withdraw | 4 | 62 |
| 52 | 05ba4406-clip_1781584018103_1781584 | train | 是 | long_brush_insert | 5 | 174 |
| 53 | 9f93cf16-clip_1781584034867_1781584 | train | 是 | long_brush_withdraw | 4 | 68 |
| 54 | af0e7803-clip_1781584048438_1781584 | train | 是 | long_brush_insert | 6 | 114 |
| 55 | 7e8f5b4f-clip_1781584064111_1781584 | train | 是 | long_brush_withdraw | 4 | 40 |
| 59 | 4807dbbe-clip_1781659328328_1781659 | train | 是 | air_injection, long_brush_insert, long_brush_withdraw | 4 | 1726 |
| 60 | a2ade960-clip_1781660307856_1781660 | train | 是 | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 6 | 4519 |
| 61 | 65d70028-clip_1781661552468_1781661 | val | 是 | flush, long_brush_insert, long_brush_withdraw | 6 | 2366 |
| 62 | 3614fb62-clip_1782091187000_1782091 | train | 是 | air_injection, flush, long_brush_insert, long_brush_withdraw | 7 | 3145 |
| 68 | 63a848d5-clip_1782695363948_1782695 | train | 是 | flush, long_brush_insert, long_brush_withdraw | 6 | 3183 |
| 69 | 2c635ddc-clip_1782695261284_1782695 | train | 是 | short_brush_cleaning | 6 | 1331 |
| 77 | fedf6ff9-clip_1783393131145_1783393 | train | 是 | flush, short_brush_cleaning | 6 | 1894 |
| 78 | b1b042a9-clip_1783395777441_1783395 | train | 是 | long_brush_insert, long_brush_withdraw | 3 | 239 |
| 84 | f0d28b80-clip_1783302144895_1783302 | train | 是 | air_injection, short_brush_cleaning | 4 | 693 |
| 85 | 1fcfcdea-clip_1783302201419_1783302 | train | 是 | long_brush_insert, long_brush_withdraw | 5 | 592 |

## 各组产出

| 组 | Split | 图片 | 框 |
|----|-------|------|-----|
| group1_large | train | 10410 | 35090 |
| group1_large | val | 1244 | 4722 |
| group2_small | train | 7557 | 10901 |
| group2_small | val | 1122 | 1350 |

## Split 分配

| Split | Task |
|-------|------|
| train | 50, 51, 52, 53, 54, 55, 59, 60, 62, 68, 69, 77, 78, 84, 85 |
| val | 61 |

> 一个 task 的所有帧只进它的 split,杜绝时间相邻泄漏。
> 帧名 `t{task_id}_{frame:06d}` —— 身份键是 LS task id,不随视频重传而变。
> 旋转框自动转 AABB。
