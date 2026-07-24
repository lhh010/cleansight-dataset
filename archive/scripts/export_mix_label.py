"""Export Label Studio project annotations and upload to ModelScope."""
import os, sys, json, requests
from config import (
    MS_ACCESS_TOKEN, MS_REPO_ID,
    LS_BASE_URL, LS_API_TOKEN, LS_PROJECT_ID,
    EXPORT_BASE_DIR,
)

# Fix Windows GBK encoding for emoji
sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"Authorization": f"Token {LS_API_TOKEN}"}

# Export into a project-specific folder
export_dir = os.path.join(EXPORT_BASE_DIR, f"project-{LS_PROJECT_ID}")
os.makedirs(export_dir, exist_ok=True)

# ========== 1. Export ==========
print("=" * 60)
print(f"[1/3] Exporting Project {LS_PROJECT_ID} from Label Studio...")
resp = requests.get(
    f"{LS_BASE_URL}/api/projects/{LS_PROJECT_ID}/export",
    headers=HEADERS,
    params={"exportType": "JSON"}
)
if resp.status_code != 200:
    print(f"[FAIL] Export failed: HTTP {resp.status_code}")
    print(resp.text[:500])
    exit(1)

all_data = resp.json()
print(f"  Total tasks: {len(all_data)}")

# ========== 2. Filter annotated only ==========
print("\n[2/3] Filtering annotated tasks...")
annotated = []
for task in all_data:
    annotations = task.get("annotations", [])
    if annotations:
        has_content = any(
            ann.get("result") and len(ann["result"]) > 0
            for ann in annotations
        )
        if has_content:
            annotated.append(task)

print(f"  Annotated: {len(annotated)} / {len(all_data)}")

# Save
export_path = os.path.join(export_dir, "annotations.json")
with open(export_path, "w", encoding="utf-8") as f:
    json.dump(annotated, f, ensure_ascii=False, indent=2)
file_size = os.path.getsize(export_path)
print(f"  [OK] Saved: {export_path} ({file_size/1024:.1f} KB)")

# Metadata
meta = {
    "project_id": LS_PROJECT_ID,
    "total_tasks": len(all_data),
    "annotated_tasks": len(annotated),
    "export_time": "2026-07-04",
}
with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

# Label stats
print("\n  Label statistics:")
label_counts = {}
for task in annotated:
    for ann in task.get("annotations", []):
        for r in ann.get("result", []):
            t = r.get("type", "")
            vals = r.get("value", {})
            if isinstance(vals, dict):
                if t == "labels":
                    for ln in vals.get("labels", []):
                        label_counts[ln] = label_counts.get(ln, 0) + 1
                elif t == "timelinelabels":
                    for ln in vals.get("timelinelabels", []):
                        label_counts[f"[timeline] {ln}"] = label_counts.get(f"[timeline] {ln}", 0) + 1
                elif t == "rectanglelabels":
                    for ln in vals.get("rectanglelabels", []):
                        label_counts[f"[bbox] {ln}"] = label_counts.get(f"[bbox] {ln}", 0) + 1

for k, v in sorted(label_counts.items(), key=lambda x: -x[1]):
    print(f"    {k}: {v}")

# ========== 3. Upload ==========
print("\n[3/3] Uploading to ModelScope...")
from modelscope.hub.api import HubApi

api = HubApi()
api.login(MS_ACCESS_TOKEN)

api.upload_folder(
    repo_id=MS_REPO_ID,
    folder_path=export_dir,
    path_in_repo=f"project-{LS_PROJECT_ID}",
    commit_message=f"Upload Project {LS_PROJECT_ID} annotations ({len(annotated)} tasks)",
    repo_type="dataset",
)
print("Upload complete!")
print(f"  View: https://www.modelscope.cn/datasets/{MS_REPO_ID}")
