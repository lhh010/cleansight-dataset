# CleanSight Dataset Status

**Generated**: 2026-07-08 11:36:06
**Export**: project-10-at-2026-07-08-03-05-4444bae3.json

## Task Status

| LS Task ID | Video | Confirmed | Split | Phases | Det Labels | Sampled Frames |
|-----------|------|-----------|-------|--------|------------|----------------|
| 50 | 218f9117-clip_1781583985044_1781584 | [OK] | train | long_brush_insert | 4 | 187 |
| 51 | b004acff-clip_1781584008145_1781584 | [OK] | test | long_brush_withdraw | 4 | 62 |
| 52 | 05ba4406-clip_1781584018103_1781584 | [OK] | train | long_brush_insert | 5 | 174 |
| 53 | 9f93cf16-clip_1781584034867_1781584 | [OK] | test | long_brush_withdraw | 4 | 68 |
| 54 | af0e7803-clip_1781584048438_1781584 | [OK] | train | long_brush_insert | 6 | 114 |
| 55 | 7e8f5b4f-clip_1781584064111_1781584 | [OK] | train | — | 4 | 40 |
| 56 | 687e3c78-clip_1781155551819_1781155 | [NO] | — | — | 6 | — |
| 58 | ed1f1353-clip_1781659288372_1781659 | [NO] | — | short_brush_cleaning | 3 | — |
| 59 | 4807dbbe-clip_1781659328328_1781659 | [OK] | train | air_injection, long_brush_insert, long_brush_withdraw | 4 | 1726 |
| 60 | a2ade960-clip_1781660307856_1781660 | [NO] | — | long_brush_insert, long_brush_withdraw, short_brush_cleaning | 4 | — |
| 61 | 65d70028-clip_1781661552468_1781661 | [OK] | val | flush, long_brush_insert, long_brush_withdraw | 6 | 2366 |
| 62 | 3614fb62-clip_1782091187000_1782091 | [NO] | — | — | 0 | — |
| 63 | 54b6e047-clip_1782097591695_1782097 | [NO] | — | — | 0 | — |
| 64 | 14e6fadd-clip_1782094867317_1782095 | [NO] | — | — | 0 | — |
| 68 | 63a848d5-clip_1782695363948_1782695 | [OK] | train | flush, long_brush_insert, long_brush_withdraw | 6 | 3183 |
| 69 | 2c635ddc-clip_1782695261284_1782695 | [OK] | train | short_brush_cleaning | 6 | 1331 |
| 75 | af4ea419-clip_1782955721678_1782955 | [NO] | — | air_injection, long_brush_insert, short_brush_cleaning | 6 | — |

## Group Summary

| Group | Split | Images | Boxes |
|-------|-------|--------|-------|
| group1_large | train | 4199 | 14850 |
| group1_large | val | 1244 | 4722 |
| group1_large | test | 124 | 431 |
| group2_small | train | 2556 | 3562 |
| group2_small | val | 1122 | 1350 |
| group2_small | test | 6 | 6 |

## Split Assignment

| Split | Tasks |
|-------|-------|
| train | 50, 52, 54, 55, 59, 68, 69 |
| val | 61 |
| test | 51, 53 |

> Each LS task's frames stay entirely in one split.
> Rotated bboxes auto-converted to AABB.
> Rare classes (< 200 keyframes) have dense neighbor-frame sampling.
