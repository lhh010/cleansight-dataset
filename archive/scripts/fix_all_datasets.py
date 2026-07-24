"""
批量修复 ModelScope 数据集的 Git LFS 配置并重新上传。

问题：ModelScope 默认 .gitattributes 将所有文件(含 .txt)纳入 LFS，
导致 clone 时报错或出现 "should have been pointers" 警告。

修复：.gitattributes 只让图片(.jpg/.png)走 LFS，.txt 等文本文件直接存 Git。

用法：
    python fix_all_datasets.py

会依次修复:
    - lhh010/cleansight-yolo            (group1_large, group2_small)
    - lhh010/cleansight-ActionSequence  (air_injection, flush, etc.)
"""

import os
import sys
import shutil
import subprocess
import tempfile
from typing import Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import (
    MS_ACCESS_TOKEN,
    MS_YOLO_REPO_ID,
    MS_ACTIONSEQ_REPO_ID,
)


# ============================================================
# Git 操作工具
# ============================================================

def run(cmd: list[str], cwd: str = None, check: bool = True,
        skip_lfs_smudge: bool = False) -> subprocess.CompletedProcess:
    """运行命令并打印输出。"""
    print(f"  $ {' '.join(cmd)}")
    env = os.environ.copy()
    if skip_lfs_smudge:
        env["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if result.stdout:
        lines = result.stdout.strip().splitlines()
        # 只打印前20行，避免刷屏
        for line in lines[:20]:
            print(f"    {line}")
        if len(lines) > 20:
            print(f"    ... (共 {len(lines)} 行，省略)")
    if result.stderr:
        stderr_stripped = result.stderr.strip()
        if stderr_stripped:
            # 只打印前10行 stderr
            stderr_lines = stderr_stripped.splitlines()
            for line in stderr_lines[:10]:
                print(f"    [stderr] {line[:200]}")
            if len(stderr_lines) > 10:
                print(f"    [stderr] ... (共 {len(stderr_lines)} 行)")
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit={result.returncode}): {' '.join(cmd)}"
        )
    return result


def write_gitattributes(path: str) -> None:
    """写入正确的 .gitattributes：只对图片/视频使用 LFS。"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Git LFS - only track large binary files (images/videos)\n")
        f.write("*.jpg filter=lfs diff=lfs merge=lfs -text\n")
        f.write("*.png filter=lfs diff=lfs merge=lfs -text\n")
        f.write("*.jpeg filter=lfs diff=lfs merge=lfs -text\n")
        f.write("*.mp4 filter=lfs diff=lfs merge=lfs -text\n")
        f.write("# Text files - stored directly in Git (NOT LFS)\n")
        f.write("*.txt !filter !diff !merge text\n")
        f.write("*.yaml !filter !diff !merge text\n")
        f.write("*.yml !filter !diff !merge text\n")
        f.write("*.md !filter !diff !merge text\n")


# ============================================================
# 核心修复流程
# ============================================================

def fix_dataset(repo_id: str, local_dataset_path: str,
                subdirs: Optional[List[str]] = None,
                extra_docs: Optional[List[str]] = None) -> None:
    """修复单个 ModelScope 数据集的 LFS 配置并重新上传。

    Args:
        repo_id: ModelScope repo ID, e.g. "lhh010/cleansight-yolo"
        local_dataset_path: 本地数据集根目录
        subdirs: 需要同步的子目录列表（默认直接同步整个目录）
        extra_docs: 额外需要上传的文档文件列表
    """
    repo_url = (
        f"https://oauth2:{MS_ACCESS_TOKEN}"
        f"@www.modelscope.cn/datasets/{repo_id}.git"
    )

    work_dir = tempfile.mkdtemp(prefix=f"fix_{repo_id.replace('/', '_')}_")
    repo_dir = os.path.join(work_dir, "repo")
    print(f"\n{'=' * 60}")
    print(f"  修复: {repo_id}")
    print(f"  工作目录: {work_dir}")
    print(f"{'=' * 60}")

    try:
        # ---- 1. Clone ----
        print(f"\n[1/5] Clone 仓库（跳过 LFS smudge）...")
        run(["git", "clone", repo_url, repo_dir], skip_lfs_smudge=True)

        # ---- 2. Fix .gitattributes ----
        print(f"\n[2/5] 修复 .gitattributes ...")
        ga_path = os.path.join(repo_dir, ".gitattributes")
        write_gitattributes(ga_path)
        run(["git", "add", ".gitattributes"], cwd=repo_dir)
        run(["git", "commit", "-m",
             "Fix .gitattributes: LFS only for images, text files stored in git"],
            cwd=repo_dir)

        # ---- 3. Sync data ----
        print(f"\n[3/5] 同步数据文件 ...")
        target_subdirs = subdirs or [""]  # "" means root level

        # 删除 repo 中旧数据 + 复制本地最新数据
        for sub in target_subdirs:
            src = os.path.join(local_dataset_path, sub) if sub else local_dataset_path
            dst = os.path.join(repo_dir, sub) if sub else repo_dir

            if not os.path.isdir(src):
                print(f"  [skip] 源目录不存在: {src}")
                continue

            # 只操作子目录内的 images/ labels/ frames/ 和 data.yaml
            for item in ["images", "labels", "frames", "data.yaml"]:
                old = os.path.join(dst, item)
                new = os.path.join(src, item)

                if os.path.exists(old):
                    if os.path.isdir(old):
                        shutil.rmtree(old)
                    else:
                        os.remove(old)

                if os.path.exists(new):
                    if os.path.isdir(new):
                        shutil.copytree(new, old)
                        print(f"  [{sub or '.'}/{item}] 已同步目录")
                    else:
                        shutil.copy2(new, old)
                        print(f"  [{sub or '.'}/{item}] 已同步文件")

        # 同步额外的文档文件
        if extra_docs:
            for doc in extra_docs:
                src_doc = os.path.join(local_dataset_path, doc)
                dst_doc = os.path.join(repo_dir, doc)
                if os.path.exists(src_doc):
                    shutil.copy2(src_doc, dst_doc)
                    print(f"  [{doc}] 已同步")

        # ---- 4. Commit ----
        print(f"\n[4/5] Git add & commit ...")
        run(["git", "add", "--all"], cwd=repo_dir)

        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_dir,
            capture_output=True, text=True
        )
        if not status.stdout.strip():
            print("  无变更，跳过 commit。")
        else:
            # 统计变更
            lines = status.stdout.strip().splitlines()
            print(f"  变更文件数: {len(lines)}")
            run(["git", "commit", "-m",
                 f"Re-upload {repo_id} with fixed LFS config\n\n"
                 "- .txt / .yaml / .md files: stored directly in git\n"
                 "- .jpg / .png files: tracked by Git LFS"],
                cwd=repo_dir)

        # ---- 5. Push ----
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True
        )
        branch = branch_result.stdout.strip()

        print(f"\n[5/5] Git push → origin/{branch} ...")
        run(["git", "push", "origin", branch], cwd=repo_dir)

        print(f"\n  [OK] {repo_id} 修复完成!")
        print(f"  View: https://www.modelscope.cn/datasets/{repo_id}")

    finally:
        print(f"  清理: {work_dir}")
        shutil.rmtree(work_dir, ignore_errors=True)


# ============================================================
# Main
# ============================================================

def main():
    pipeline_root = os.path.join(BASE_DIR, "cleansight-yolo-pipeline")

    # ---- cleansight-yolo ----
    print("\n" + "=" * 60)
    print("  [1/2] 修复 cleansight-yolo")
    print("=" * 60)
    fix_dataset(
        repo_id=MS_YOLO_REPO_ID,
        local_dataset_path=os.path.join(pipeline_root, "datasets"),
        subdirs=["group1_large", "group2_small"],
        extra_docs=["tracking.md"],
    )

    # ---- cleansight-ActionSequence ----
    print("\n" + "=" * 60)
    print("  [2/2] 修复 cleansight-ActionSequence")
    print("=" * 60)
    fix_dataset(
        repo_id=MS_ACTIONSEQ_REPO_ID,
        local_dataset_path=os.path.join(pipeline_root, "datasets_actionseq"),
        subdirs=["air_injection", "flush", "long_brush_insert",
                 "long_brush_withdraw", "short_brush_cleaning"],
        extra_docs=["README.md", "data_records.md"],
    )

    print("\n" + "=" * 60)
    print("  全部修复完成!")
    print("=" * 60)
    print(f"  https://www.modelscope.cn/datasets/{MS_YOLO_REPO_ID}")
    print(f"  https://www.modelscope.cn/datasets/{MS_ACTIONSEQ_REPO_ID}")


if __name__ == "__main__":
    main()
