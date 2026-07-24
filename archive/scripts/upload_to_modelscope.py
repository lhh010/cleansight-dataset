"""Upload raw Label Studio exports and tracking table to ModelScope at lhh010/cleansight-raw.

Uploads:
  - raw-from Label Studio/  (LS export JSON files)
  - DATASET_STATUS.md / cleansight-yolo-pipeline/tracking.md

Usage:
    python upload_to_modelscope.py
"""
import os
from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_REPO_ID, UPLOAD_FOLDER_PATH

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload raw export folder ----
print("Uploading raw LS exports ...")
api.upload_folder(
    repo_id=MS_REPO_ID,
    folder_path=UPLOAD_FOLDER_PATH,
    commit_message="Upload Label Studio exported dataset + tracking table",
    repo_type="dataset",
)
print("  raw exports done")

# ---- Upload tracking table ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_PATH = os.path.join(BASE_DIR, "DATASET_STATUS.md")
if os.path.exists(TRACKING_PATH):
    print("Uploading DATASET_STATUS.md ...")
    api.upload_file(
        repo_id=MS_REPO_ID,
        path_or_fileobj=TRACKING_PATH,
        path_in_repo="DATASET_STATUS.md",
        commit_message="Update dataset status tracking table",
        repo_type="dataset",
    )
    print("  DATASET_STATUS.md done")

print("Upload complete!")
print(f"View: https://www.modelscope.cn/datasets/{MS_REPO_ID}")
