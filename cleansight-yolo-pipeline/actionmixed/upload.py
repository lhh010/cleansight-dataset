"""Upload ActionMixed dataset to lhh010/cleansight-ActionMixed.

Uploads:
  - datasets_actionmixed/images/   (sampled frames)
  - datasets_actionmixed/frames/   (YOLO bbox per frame)
  - datasets_actionmixed/labels/   (action labels per video)
  - datasets_actionmixed/README.md (if exists)
  - tracking_actionmixed.md

Usage (在 cleansight-yolo-pipeline/ 下执行):
    python actionmixed/upload.py
"""
import os
import sys

# 本脚本位于 cleansight-yolo-pipeline/actionmixed/;定位 pipeline 根(取 utils/)与仓库根(取 config.py)
from pathlib import Path
HERE = Path(__file__).resolve()
PIPELINE_ROOT = HERE.parents[1]          # cleansight-yolo-pipeline/
REPO_ROOT = HERE.parents[2]              # 仓库根(config.py 所在,含密钥)
sys.path.insert(0, str(PIPELINE_ROOT))   # → utils/
sys.path.insert(0, str(REPO_ROOT))       # → config.py

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_ACTIONMIXED_REPO_ID

DATASETS_PATH = str(PIPELINE_ROOT / "datasets_actionmixed")

if not os.path.isdir(DATASETS_PATH):
    raise SystemExit(
        f"ActionMixed dataset not found at {DATASETS_PATH}. "
        f"Run actionmixed/02_build.py first."
    )

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload top-level docs ----
for doc in ["README.md", "tracking_actionmixed.md"]:
    doc_path = str(HERE.parent / doc) \
        if doc == "tracking_actionmixed.md" else os.path.join(DATASETS_PATH, doc)
    if os.path.exists(doc_path):
        name = os.path.basename(doc_path)
        print(f"Uploading {name} ...")
        api.upload_file(
            repo_id=MS_ACTIONMIXED_REPO_ID,
            path_or_fileobj=doc_path,
            path_in_repo=name,
            commit_message=f"Upload {name}",
            repo_type="dataset",
        )
        print(f"  {name} done")

# ---- Upload subdirectories: images, frames, labels ----
subdirs = ["images", "frames", "labels"]
for sub in subdirs:
    sub_path = os.path.join(DATASETS_PATH, sub)
    if not os.path.isdir(sub_path):
        print(f"  [skip] {sub}/ not found")
        continue
    print(f"Uploading {sub}/ ...")
    api.upload_folder(
        repo_id=MS_ACTIONMIXED_REPO_ID,
        folder_path=sub_path,
        path_in_repo=sub,
        commit_message=f"Upload ActionMixed: {sub}",
        repo_type="dataset",
    )
    print(f"  {sub}/ done")

print(f"\nUpload complete!")
print(f"View: https://www.modelscope.cn/datasets/{MS_ACTIONMIXED_REPO_ID}")
