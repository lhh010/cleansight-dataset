#!/usr/bin/env python3
"""
Upload built datasets to ModelScope repos via git.

Repos:
  - lhh010/cleansight-yolo           ← datasets/{group1_large,group2_small}
  - lhh010/cleansight-ActionSequence  ← datasets_actionseq/
  - lhh010/cleansight-ActionMixed     ← datasets_actionmixed/

Usage: python upload_to_modelscope.py [--dry-run]
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TMP = ROOT.parent / "_upload_tmp"

REPOS = [
    {
        "name": "cleansight-yolo",
        "url": "https://www.modelscope.cn/datasets/lhh010/cleansight-yolo.git",
        "sources": [
            (ROOT / "datasets" / "group1_large", "group1_large"),
            (ROOT / "datasets" / "group2_small", "group2_small"),
        ],
        "extra_files": [],  # tracking.md etc not needed in repo
    },
    {
        "name": "cleansight-ActionSequence",
        "url": "https://www.modelscope.cn/datasets/lhh010/cleansight-ActionSequence.git",
        "sources": [
            (ROOT / "datasets_actionseq", "."),
        ],
        "extra_files": [],
    },
    {
        "name": "cleansight-ActionMixed",
        "url": "https://www.modelscope.cn/datasets/lhh010/cleansight-ActionMixed.git",
        "sources": [
            (ROOT / "datasets_actionmixed", "."),
        ],
        "extra_files": [],
    },
]


def run(cmd, cwd=None):
    print(f"  $ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=isinstance(cmd, str))
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}")
    return result


def upload_repo(repo, dry_run=False):
    name = repo["name"]
    url = repo["url"]
    sources = repo["sources"]
    repo_dir = TMP / name

    print(f"\n{'='*60}")
    print(f"Uploading: {name}")
    print(f"{'='*60}")

    # Clone or update
    if (repo_dir / ".git").exists():
        print(f"  Pulling latest from {url}...")
        run(["git", "fetch", "origin", "master"], cwd=repo_dir)
        run(["git", "reset", "--hard", "origin/master"], cwd=repo_dir)
    else:
        print(f"  Cloning {url} (shallow)...")
        run(["git", "clone", "--depth", "1", url, str(repo_dir)])

    if not (repo_dir / ".git").exists():
        print(f"  FAILED to clone {name}")
        return False

    # Remove old tracked files (keep .git)
    print("  Removing old files...")
    for item in repo_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink()

    # Copy new files
    print("  Copying new dataset files...")
    for src_dir, dst_rel in sources:
        if not src_dir.exists():
            print(f"  WARNING: source {src_dir} not found, skipping")
            continue
        dst_dir = repo_dir / dst_rel
        # Copy everything except .git
        _copytree(src_dir, dst_dir)

    # Count files
    total_files = sum(1 for _ in repo_dir.rglob("*") if _.is_file() and ".git" not in str(_))
    print(f"  Total files copied: {total_files}")

    if dry_run:
        print("  [DRY RUN] Skipping git add/commit/push")
        return True

    # Git add all
    print("  git add -A ...")
    run(["git", "add", "-A"], cwd=repo_dir)

    # Check if there are changes
    result = run(["git", "diff", "--cached", "--stat"], cwd=repo_dir)
    if not result.stdout.strip():
        print("  No changes to commit. Skipping push.")
        return True

    # Commit
    from datetime import datetime
    msg = f"Update dataset: {datetime.now().strftime('%Y-%m-%d %H:%M')} (tasks #60, #62, #84, #85 added)"
    print(f"  git commit -m '{msg}'")
    run(["git", "commit", "-m", msg], cwd=repo_dir)

    # Push
    print("  git push origin master...")
    result = run(["git", "push", "origin", "master"], cwd=repo_dir)
    if result.returncode == 0:
        print(f"  ✅ {name} pushed successfully!")
        return True
    else:
        print(f"  ❌ Push failed for {name}")
        return False


def _copytree(src, dst):
    """Recursively copy src to dst."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        s = src / item.name
        d = dst / item.name
        if s.is_dir():
            _copytree(s, d)
        else:
            shutil.copy2(s, d)


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("*** DRY RUN MODE — no actual push ***")

    TMP.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    for repo in REPOS:
        try:
            if upload_repo(repo, dry_run=dry_run):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  Exception: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Done: {success} success, {failed} failed")
    if dry_run:
        print("(dry run — no changes were pushed)")


if __name__ == "__main__":
    main()
