# CleanSight ActionMixed — Processing Record

**Generated**: 2026-07-08 22:28:05
**Export**: project-10-at-2026-07-08-03-42-1df45c91.json

## Dataset Overview

Action recognition dataset combining detection bboxes with action labels.
Each action segment is extended with idle frames (up to half segment length,
constrained by adjacent-segment midpoints and video bounds).
**Splits are at segment level** — different segments from the same video
may belong to different splits (train/val/test).

## Directory Structure

```
datasets_actionmixed/
├── images/{train,val,test}/{video_id}-{frame_id:06d}.jpg
├── frames/{train,val,test}/{video_id}-{frame_id:06d}.txt   (YOLO bbox)
│   └── data.yaml                                             (detection classes)
└── labels/{train,val,test}/{video_id}.txt                    (action labels)
    └── data.yaml                                             (action classes)
```

## Task Processing Status

| LS Task ID | Video | Total Frames | Phases | Segments (split:frames) |
|-----------|------|-------------|--------|------------------------|
| 50 | 218f9117-clip_1781583985044_17 | 637 | long_brush_insert | long_brush_insert[1-637]→val(175) |
| 51 | b004acff-clip_1781584008145_17 | 251 | long_brush_withdraw | long_brush_withdraw[1-251]→train(63) |
| 52 | 05ba4406-clip_1781584018103_17 | 465 | long_brush_insert | long_brush_insert[45-388]→train(141) |
| 53 | 9f93cf16-clip_1781584034867_17 | 253 | long_brush_withdraw | long_brush_withdraw[1-253]→train(64) |
| 54 | af0e7803-clip_1781584048438_17 | 458 | long_brush_insert | long_brush_insert[65-392]→val(115) |
| 55 | 7e8f5b4f-clip_1781584064111_17 | 137 | long_brush_withdraw | long_brush_withdraw[1-137]→train(35) |
| 59 | 4807dbbe-clip_1781659328328_17 | 4189 | air_injection, long_brush_insert, long_brush_withdraw | long_brush_insert[51-240]→test(70), long_brush_withdraw[323-476]→val(61), long_brush_insert[570-936]→test(112), long_brush_withdraw[1005-1168]→train(62), long_brush_insert[1270-1605]→test(114), long_brush_withdraw[1744-1884]→train(60), long_brush_insert[1948-2470]→val(147), long_brush_withdraw[2539-2688]→train(60), long_brush_insert[2796-3005]→train(73), long_brush_withdraw[3068-3296]→val(93), air_injection[3520-3691]→train(230), air_injection[3881-4074]→train(255) |
| 61 | 65d70028-clip_1781661552468_17 | 4514 | flush, long_brush_insert, long_brush_withdraw | long_brush_insert[1-250]→train(82), long_brush_withdraw[253-369]→val(43), long_brush_insert[438-701]→train(116), long_brush_withdraw[713-1050]→train(241), flush[2215-2325]→train(43), flush[2338-2638]→train(79), flush[2656-2800]→train(40), flush[2813-3000]→train(51), flush[3025-3150]→train(38), flush[3175-3413]→val(64), flush[3425-3563]→train(38), flush[3581-3681]→train(40) |
| 68 | 63a848d5-clip_1782695363948_17 | 6791 | flush, long_brush_insert, long_brush_withdraw | flush[56-250]→train(64), flush[262-456]→test(53), flush[481-644]→train(46), flush[662-906]→train(94), long_brush_insert[1475-1537]→train(29), long_brush_withdraw[1544-1787]→train(66), long_brush_insert[1812-2275]→train(129), long_brush_withdraw[2281-2537]→train(72), long_brush_insert[2550-3025]→test(141), long_brush_withdraw[3031-3175]→train(59), flush[3337-3550]→train(75), flush[3562-3837]→val(72), flush[3850-4037]→val(50), flush[4050-4225]→val(47), flush[4237-4556]→train(82), flush[4562-4787]→val(58), flush[4800-5062]→train(99), flush[5312-5487]→train(77), flush[5575-5744]→val(57), flush[5775-6050]→train(107) |
| 69 | 2c635ddc-clip_1782695261284_17 | 2096 | short_brush_cleaning | short_brush_cleaning[187-282]→train(100), short_brush_cleaning[320-384]→train(53), short_brush_cleaning[486-661]→val(193) |

## Split Summary (by segment-level assignment)

| Split | Segments | Frames |
|-------|----------|--------|
| train | 35 | 2963 |
| val | 13 | 1175 |
| test | 5 | 490 |

## Per-Task Split Breakdown

| Task ID | Train | Val | Test |
|---------|-------|-----|------|
| 50 | 0 | 175 | 0 |
| 51 | 63 | 0 | 0 |
| 52 | 141 | 0 | 0 |
| 53 | 64 | 0 | 0 |
| 54 | 0 | 115 | 0 |
| 55 | 35 | 0 | 0 |
| 59 | 740 | 301 | 296 |
| 61 | 768 | 107 | 0 |
| 68 | 999 | 284 | 194 |
| 69 | 153 | 193 | 0 |

## Action Classes

| ID | Name |
|---|------|
| 0 | idle |
| 1 | air_injection |
| 2 | flush |
| 3 | long_brush_insert |
| 4 | long_brush_withdraw |
| 5 | short_brush_cleaning |

## Detection Classes

| ID | Name |
|---|------|
| 0 | hand |
| 1 | scope_control_body |
| 2 | scope_mid_section |
| 3 | scope_distal_end |
| 4 | syringe |
| 5 | air_gun |
| 6 | short_brush |
| 7 | brush_tip_out |

> Splits are assigned per-segment (not per-video). Same video may span multiple splits.
> Action segments extended with idle padding: half-length + midpoint rule.
> Rotated bboxes auto-converted to AABB (YOLO compatible).
