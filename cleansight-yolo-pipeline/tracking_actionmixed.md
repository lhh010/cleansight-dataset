# CleanSight ActionMixed — Processing Record

**Generated**: 2026-07-18 18:14:24
**Export**: project-10-at-2026-07-18-07-58-e8b8781a.json

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
| 50 | 218f9117-clip_1781583985044_17 | — | long_brush_insert | — |
| 51 | b004acff-clip_1781584008145_17 | — | long_brush_withdraw | — |
| 52 | 05ba4406-clip_1781584018103_17 | — | long_brush_insert | — |
| 53 | 9f93cf16-clip_1781584034867_17 | — | long_brush_withdraw | — |
| 54 | af0e7803-clip_1781584048438_17 | — | long_brush_insert | — |
| 55 | 7e8f5b4f-clip_1781584064111_17 | — | long_brush_withdraw | — |
| 59 | 4807dbbe-clip_1781659328328_17 | — | air_injection, long_brush_insert, long_brush_withdraw | — |
| 60 | a2ade960-clip_1781660307856_17 | — | long_brush_insert, long_brush_withdraw, short_brush_cleaning | — |
| 61 | 65d70028-clip_1781661552468_17 | — | flush, long_brush_insert, long_brush_withdraw | — |
| 62 | 3614fb62-clip_1782091187000_17 | — | air_injection, flush, long_brush_insert, long_brush_withdraw | — |
| 68 | 63a848d5-clip_1782695363948_17 | — | flush, long_brush_insert, long_brush_withdraw | — |
| 69 | 2c635ddc-clip_1782695261284_17 | — | short_brush_cleaning | — |
| 77 | fedf6ff9-clip_1783393131145_17 | — | flush, short_brush_cleaning | — |
| 78 | b1b042a9-clip_1783395777441_17 | — | long_brush_insert, long_brush_withdraw | — |
| 84 | f0d28b80-clip_1783302144895_17 | 1289 | air_injection, short_brush_cleaning | short_brush_cleaning[1-563]→train(161), short_brush_cleaning[726-854]→val(64), air_injection[1005-1119]→test(198) |
| 85 | 1fcfcdea-clip_1783302201419_17 | 1815 | long_brush_insert, long_brush_withdraw | long_brush_insert[180-361]→train(91), long_brush_insert[599-832]→train(122), long_brush_withdraw[899-976]→train(40), long_brush_insert[1021-1306]→test(83), long_brush_withdraw[1361-1442]→train(34), long_brush_insert[1494-1735]→train(87) |

## Split Summary (by segment-level assignment)

| Split | Segments | Frames |
|-------|----------|--------|
| train | 6 | 535 |
| val | 1 | 64 |
| test | 2 | 281 |

## Per-Task Split Breakdown

| Task ID | Train | Val | Test |
|---------|-------|-----|------|
| 84 | 161 | 64 | 198 |
| 85 | 374 | 0 | 83 |

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
