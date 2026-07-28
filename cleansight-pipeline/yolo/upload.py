"""Upload YOLO detection dataset to ModelScope at lhh010/cleansight-yolo.

Uploads each group dir under the dataset root declared in yolo/train.yaml
(images, labels, data.yaml), plus both tracks' tracking tables.

  lhh010/cleansight-yolo/
    tracking_train.md      # 训练轨(train/val),yolo/build.py 生成
    tracking_test.md       # benchmark 轨(test),yolo/build_test.py 生成
    group1_large/
      images/{train,val,test}/*.jpg
      labels/{train,val,test}/*.txt
      data.yaml
    group2_small/
      ...

Usage (在 cleansight-pipeline/ 下执行):
    python yolo/upload.py              # 上传前自动校验
    python yolo/upload.py --skip-check # 跳过校验直接上传

Prerequisite:
    Run yolo/build.py (训练轨) 和 yolo/build_test.py (benchmark 轨) first.
"""
import os
import sys

# 本脚本位于 cleansight-pipeline/yolo/;定位 pipeline 根(取 utils/)与仓库根(取 config.py)
from pathlib import Path
HERE = Path(__file__).resolve()
PIPELINE_ROOT = HERE.parents[1]          # cleansight-pipeline/
REPO_ROOT = HERE.parents[2]              # 仓库根(config.py 所在,含密钥)
sys.path.insert(0, str(PIPELINE_ROOT))   # → utils/
sys.path.insert(0, str(REPO_ROOT))       # → config.py

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_YOLO_REPO_ID
from utils.check import check_dataset, print_result
from common.check import yolo_criteria
from yolo import manifest

_train_m = manifest.load(manifest.TRAIN_MANIFEST)
YOLO_DATASETS_PATH = str(manifest.out_root(_train_m))
TRACKING_PATHS = [manifest.tracking_path(_train_m),
                  manifest.tracking_path(manifest.load(manifest.TEST_MANIFEST))]

SKIP_CHECK = "--skip-check" in sys.argv

if not os.path.isdir(YOLO_DATASETS_PATH):
    raise SystemExit(
        f"YOLO dataset not found at {YOLO_DATASETS_PATH}. "
        f"Run yolo/build.py first."
    )

# ---- 推送前校验 ----
if not SKIP_CHECK:
    print("=" * 60)
    print("  推送前校验 (check)")
    print("=" * 60)
    any_fail = False
    criteria = yolo_criteria()
    for group_name in sorted(os.listdir(YOLO_DATASETS_PATH)):
        group_dir = os.path.join(YOLO_DATASETS_PATH, group_name)
        if not os.path.isdir(group_dir) or not os.path.exists(
            os.path.join(group_dir, "data.yaml")
        ):
            continue
        r = check_dataset(Path(group_dir), f"Group/{group_name}", **criteria)
        if not print_result(r):
            any_fail = True
    if any_fail:
        raise SystemExit(
            "\n❌ 数据集校验未通过，拒绝推送。\n"
            "   修复后重试，或 python yolo/upload.py --skip-check 强制上传。"
        )
    print("\n✅ 校验通过，开始上传...\n")
else:
    print("[--skip-check] 跳过校验，直接上传\n")

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload each track's tracking table ----
for tracking in TRACKING_PATHS:
    if not tracking.exists():
        print(f"  [skip] {tracking.name} 不存在(该轨尚未构建)")
        continue
    print(f"Uploading {tracking.name} ...")
    api.upload_file(
        repo_id=MS_YOLO_REPO_ID,
        path_or_fileobj=str(tracking),
        path_in_repo=tracking.name,
        commit_message=f"Update {tracking.name}",
        repo_type="dataset",
    )
    print(f"  {tracking.name} done")

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
