"""Upload phase-segmented YOLO dataset to ModelScope at lhh010/cleansight-yolo.

Uploads cleansight-yolo-pipeline/datasets/<phase>/ (images, labels, data.yaml)
for each phase. Also uploads tracking.md to the repo root.

  lhh010/cleansight-yolo/
    tracking.md
    long_brush_insert/
      images/{train,val,test}/*.jpg
      labels/{train,val,test}/*.txt
      data.yaml
    long_brush_withdraw/
      ...
    air_injection/
      ...
    flush/
      ...

Usage:
    python upload_yolo_to_modelscope.py              # 上传前自动校验
    python upload_yolo_to_modelscope.py --skip-check # 跳过校验直接上传

Prerequisite:
    Run cleansight-yolo-pipeline/02_build_dataset.py first.
"""
import os
import sys

# 允许从 upload 脚本导入 pipeline 内的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cleansight-yolo-pipeline"))

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_YOLO_REPO_ID
from utils.check import check_dataset, print_result

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YOLO_DATASETS_PATH = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", "datasets")
TRACKING_PATH = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", "tracking.md")

SKIP_CHECK = "--skip-check" in sys.argv

if not os.path.isdir(YOLO_DATASETS_PATH):
    raise SystemExit(
        f"YOLO dataset not found at {YOLO_DATASETS_PATH}. "
        f"Run cleansight-yolo-pipeline/02_build_dataset.py first."
    )

# ---- 推送前校验 ----
if not SKIP_CHECK:
    print("=" * 60)
    print("  推送前校验 (05_check)")
    print("=" * 60)
    any_fail = False
    for group_name in sorted(os.listdir(YOLO_DATASETS_PATH)):
        group_dir = os.path.join(YOLO_DATASETS_PATH, group_name)
        if not os.path.isdir(group_dir) or not os.path.exists(
            os.path.join(group_dir, "data.yaml")
        ):
            continue
        from pathlib import Path
        r = check_dataset(Path(group_dir), f"Group/{group_name}")
        if not print_result(r):
            any_fail = True
    if any_fail:
        raise SystemExit(
            "\n❌ 数据集校验未通过，拒绝推送。\n"
            "   修复后重试，或 python upload_yolo_to_modelscope.py --skip-check 强制上传。"
        )
    print("\n✅ 校验通过，开始上传...\n")
else:
    print("[--skip-check] 跳过校验，直接上传\n")

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload tracking.md ----
if os.path.exists(TRACKING_PATH):
    print(f"Uploading tracking.md ...")
    api.upload_file(
        repo_id=MS_YOLO_REPO_ID,
        path_or_fileobj=TRACKING_PATH,
        path_in_repo="tracking.md",
        commit_message="Update dataset tracking table",
        repo_type="dataset",
    )
    print("  tracking.md done")

# ---- Upload each phase ----
groups = sorted([
    name for name in os.listdir(YOLO_DATASETS_PATH)
    if os.path.isdir(os.path.join(YOLO_DATASETS_PATH, name))
])

if not groups:
    raise SystemExit(f"No phase directories found in {YOLO_DATASETS_PATH}")

print(f"Uploading {len(groups)} phase(s) to {MS_YOLO_REPO_ID} ...")
for g in groups:
    group_dir = os.path.join(YOLO_DATASETS_PATH, g)
    print(f"  [{g}] uploading {group_dir} ...")
    api.upload_folder(
        repo_id=MS_YOLO_REPO_ID,
        folder_path=group_dir,
        path_in_repo=g,
        commit_message=f"Upload YOLO dataset: {g} (train/val/test splits)",
        repo_type="dataset",
    )
    print(f"  [{g}] done")

print(f"Upload complete!")
print(f"View: https://www.modelscope.cn/datasets/{MS_YOLO_REPO_ID}")
