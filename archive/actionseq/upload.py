"""Upload ActionSequence phase-segmented YOLO dataset to lhh010/cleansight-ActionSequence.

Uploads:
  - cleansight-yolo-pipeline/datasets_actionseq/<phase>/  (images, labels, data.yaml)
  - cleansight-yolo-pipeline/datasets_actionseq/README.md
  - cleansight-yolo-pipeline/datasets_actionseq/data_records.md

Usage (在 cleansight-yolo-pipeline/ 下执行):
    python actionseq/upload.py              # 上传前自动校验
    python actionseq/upload.py --skip-check # 跳过校验直接上传
"""
import os
import sys

# 本脚本位于 cleansight-yolo-pipeline/actionseq/;定位 pipeline 根(取 utils/)与仓库根(取 config.py)
from pathlib import Path
HERE = Path(__file__).resolve()
PIPELINE_ROOT = HERE.parents[1]          # cleansight-yolo-pipeline/
REPO_ROOT = HERE.parents[2]              # 仓库根(config.py 所在,含密钥)
sys.path.insert(0, str(PIPELINE_ROOT))   # → utils/
sys.path.insert(0, str(REPO_ROOT))       # → config.py

from modelscope.hub.api import HubApi
from config import MS_ACCESS_TOKEN, MS_ACTIONSEQ_REPO_ID
from utils.check import check_dataset, print_result

DATASETS_PATH = str(PIPELINE_ROOT / "datasets_actionseq")

SKIP_CHECK = "--skip-check" in sys.argv

if not os.path.isdir(DATASETS_PATH):
    raise SystemExit(
        f"ActionSequence dataset not found at {DATASETS_PATH}. "
        f"Run actionseq/02_build.py first."
    )

# ---- 推送前校验 ----
if not SKIP_CHECK:
    print("=" * 60)
    print("  推送前校验 (05_check)")
    print("=" * 60)
    any_fail = False
    for phase_name in sorted(os.listdir(DATASETS_PATH)):
        phase_dir = os.path.join(DATASETS_PATH, phase_name)
        if not os.path.isdir(phase_dir) or not os.path.exists(
            os.path.join(phase_dir, "data.yaml")
        ):
            continue
        from pathlib import Path
        r = check_dataset(Path(phase_dir), f"ActionSequence/{phase_name}")
        if not print_result(r):
            any_fail = True
    if any_fail:
        raise SystemExit(
            "\n❌ 数据集校验未通过，拒绝推送。\n"
            "   修复后重试，或 python actionseq/upload.py --skip-check 强制上传。"
        )
    print("\n✅ 校验通过，开始上传...\n")
else:
    print("[--skip-check] 跳过校验，直接上传\n")

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
