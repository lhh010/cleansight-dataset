"""Upload dataset folder to ModelScope."""
import os
from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_REPO_ID, UPLOAD_FOLDER_PATH

api = HubApi()
api.login(MS_ACCESS_TOKEN)

print("Starting upload...")
api.upload_folder(
    repo_id=MS_REPO_ID,
    folder_path=UPLOAD_FOLDER_PATH,
    commit_message="Upload Label Studio exported dataset",
    repo_type="dataset",
)
print("Upload completed successfully!")
