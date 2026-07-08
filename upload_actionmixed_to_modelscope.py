"""Upload ActionMixed dataset to lhh010/cleansight-ActionMixed.

Uploads:
  - datasets_actionmixed/images/   (sampled frames)
  - datasets_actionmixed/frames/   (YOLO bbox per frame)
  - datasets_actionmixed/labels/   (action labels per video)
  - datasets_actionmixed/README.md (if exists)
  - tracking_actionmixed.md

Usage:
    python upload_actionmixed_to_modelscope.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cleansight-yolo-pipeline"))

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_ACTIONMIXED_REPO_ID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_PATH = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", "datasets_actionmixed")

if not os.path.isdir(DATASETS_PATH):
    raise SystemExit(
        f"ActionMixed dataset not found at {DATASETS_PATH}. "
        f"Run cleansight-yolo-pipeline/02_build_actionmixed.py first."
    )

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload top-level docs ----
for doc in ["README.md", "tracking_actionmixed.md"]:
    doc_path = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", doc) \
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
