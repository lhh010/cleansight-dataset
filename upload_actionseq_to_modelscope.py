"""Upload ActionSequence phase-segmented YOLO dataset to lhh010/cleansight-ActionSequence.

Uploads:
  - cleansight-yolo-pipeline/datasets_actionseq/<phase>/  (images, labels, data.yaml)
  - cleansight-yolo-pipeline/datasets_actionseq/README.md
  - cleansight-yolo-pipeline/datasets_actionseq/data_records.md

Usage:
    python upload_actionseq_to_modelscope.py
"""
import os

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_ACTIONSEQ_REPO_ID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_PATH = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", "datasets_actionseq")

if not os.path.isdir(DATASETS_PATH):
    raise SystemExit(
        f"ActionSequence dataset not found at {DATASETS_PATH}. "
        f"Run cleansight-yolo-pipeline/02_build_actionseq.py first."
    )

api = HubApi()
api.login(MS_ACCESS_TOKEN)

# ---- Upload README + data_records ----
for doc in ["README.md", "data_records.md"]:
    doc_path = os.path.join(DATASETS_PATH, doc)
    if os.path.exists(doc_path):
        print(f"Uploading {doc} ...")
        api.upload_file(
            repo_id=MS_ACTIONSEQ_REPO_ID,
            path_or_fileobj=doc_path,
            path_in_repo=doc,
            commit_message=f"Upload {doc}",
            repo_type="dataset",
        )
        print(f"  {doc} done")

# ---- Upload each phase ----
phases = sorted([
    name for name in os.listdir(DATASETS_PATH)
    if os.path.isdir(os.path.join(DATASETS_PATH, name))
])

if not phases:
    raise SystemExit(f"No phase directories found in {DATASETS_PATH}")

print(f"Uploading {len(phases)} phase(s) to {MS_ACTIONSEQ_REPO_ID} ...")
for ph in phases:
    phase_dir = os.path.join(DATASETS_PATH, ph)
    print(f"  [{ph}] uploading ...")
    api.upload_folder(
        repo_id=MS_ACTIONSEQ_REPO_ID,
        folder_path=phase_dir,
        path_in_repo=ph,
        commit_message=f"Upload ActionSequence dataset: {ph}",
        repo_type="dataset",
    )
    print(f"  [{ph}] done")

print(f"Upload complete!")
print(f"View: https://www.modelscope.cn/datasets/{MS_ACTIONSEQ_REPO_ID}")
