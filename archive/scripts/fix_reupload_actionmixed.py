"""
修复并重新上传 ActionMixed 数据集到 ModelScope。

问题：ModelScope 默认 .gitattributes 将 .txt 文件也纳入 LFS，
但 LFS 对象未正确存储 → clone 时 404。

解决：使用 Git 直接推送，只将图片(.jpg)走 LFS，.txt 文件直接存 Git。

用法：
    python fix_reupload_actionmixed.py

前提：
    - 已安装 git 和 git-lfs
    - config.py 中 MS_ACCESS_TOKEN 有效
"""

import os
import sys
import shutil
import subprocess
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import MS_ACCESS_TOKEN, MS_ACTIONMIXED_REPO_ID

DATASETS_PATH = os.path.join(
    BASE_DIR, "cleansight-yolo-pipeline", "datasets_actionmixed"
)

if not os.path.isdir(DATASETS_PATH):
    raise SystemExit(
        f"数据集目录不存在: {DATASETS_PATH}\n"
        f"先运行: python cleansight-yolo-pipeline/02_build_actionmixed.py"
    )

REPO_URL = (
    f"https://oauth2:{MS_ACCESS_TOKEN}"
    f"@www.modelscope.cn/datasets/{MS_ACTIONMIXED_REPO_ID}.git"
)


def run(cmd: list[str], cwd: str = None, check: bool = True,
        skip_lfs: bool = False) -> subprocess.CompletedProcess:
    """运行命令，打印输出。skip_lfs=True 时跳过 LFS smudge 下载。"""
    print(f"  $ {' '.join(cmd)}")
    env = os.environ.copy()
    if skip_lfs:
        env["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if result.stdout:
        print(f"    {result.stdout.strip()}")
    if result.stderr:
        # git-lfs 经常把进度信息写到 stderr，不一定是错误
        stderr_stripped = result.stderr.strip()
        if stderr_stripped:
            print(f"    [stderr] {stderr_stripped[:500]}")
    if check and result.returncode != 0:
        raise RuntimeError(f"命令失败 (exit={result.returncode}): {' '.join(cmd)}")
    return result


def main():
    # ---- 1. 创建工作目录 ----
    work_dir = tempfile.mkdtemp(prefix="actionmixed_reupload_")
    repo_dir = os.path.join(work_dir, "repo")
    print(f"工作目录: {work_dir}")

    try:
        # ---- 2. Clone 现有仓库（跳过 LFS smudge，反正我们会替换所有数据） ----
        print("\n[1/6] Clone 现有仓库（跳过 LFS 下载，因为旧数据 LFS 对象缺失）...")
        run(["git", "clone", REPO_URL, repo_dir], skip_lfs=True)

        # ---- 3. 设置正确的 .gitattributes ----
        print("\n[2/6] 配置 Git LFS — 只追踪图片文件...")
        gitattributes_path = os.path.join(repo_dir, ".gitattributes")
        # 先清空旧的 .gitattributes（ModelScope 可能自动生成了不合适的规则）
        with open(gitattributes_path, "w", encoding="utf-8") as f:
            f.write("# Git LFS — 只追踪大文件（图片/视频/模型权重）\n")
            f.write("*.jpg filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.png filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.jpeg filter=lfs diff=lfs merge=lfs -text\n")
            f.write("*.mp4 filter=lfs diff=lfs merge=lfs -text\n")
            f.write("# 以下类型强制不使用 LFS（覆盖可能的全局模板）\n")
            f.write("*.txt !filter !diff !merge text\n")
            f.write("*.yaml !filter !diff !merge text\n")
            f.write("*.yml !filter !diff !merge text\n")
            f.write("*.md !filter !diff !merge text\n")
            f.write("*.py !filter !diff !merge text\n")
            f.write("*.json !filter !diff !merge text\n")

        run(["git", "add", ".gitattributes"], cwd=repo_dir)
        run(["git", "commit", "-m", "Fix: LFS only for images, txt files stored directly in git"],
            cwd=repo_dir)

        # ---- 4. 同步数据集文件 ----
        print("\n[3/6] 同步数据集文件...")
        # 先删除旧的 frames/ images/ labels/（保留 README.md 等）
        for sub in ["images", "frames", "labels"]:
            old_path = os.path.join(repo_dir, sub)
            if os.path.exists(old_path):
                print(f"  删除旧的 {sub}/ ...")
                shutil.rmtree(old_path)

        # 复制新的数据集文件
        for sub in ["images", "frames", "labels"]:
            src = os.path.join(DATASETS_PATH, sub)
            dst = os.path.join(repo_dir, sub)
            if os.path.isdir(src):
                print(f"  复制 {sub}/ ...")
                shutil.copytree(src, dst)

        # 同步 README 等文档
        for doc in ["tracking_actionmixed.md"]:
            src_doc = os.path.join(BASE_DIR, "cleansight-yolo-pipeline", doc)
            if os.path.exists(src_doc):
                shutil.copy2(src_doc, os.path.join(repo_dir, doc))

        # ---- 5. Git Add & Commit ----
        print("\n[4/6] Git add & commit...")
        run(["git", "add", "--all"], cwd=repo_dir)

        # 检查是否有变更
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_dir,
            capture_output=True, text=True
        )
        if not status.stdout.strip():
            print("  没有新变更，跳过 commit。")
        else:
            print(f"  变更文件:\n{status.stdout.strip()[:2000]}")
            run([
                "git", "commit",
                "-m", "Re-upload ActionMixed dataset with fixed LFS config\n\n"
                       "- frames/*.txt: YOLO bbox labels → stored in git directly\n"
                       "- images/*.jpg: sampled frames → tracked by LFS\n"
                       "- labels/*.txt: action labels per video → stored in git directly"
            ], cwd=repo_dir)

        # ---- 6. 检测当前分支名 ----
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True
        )
        branch = branch_result.stdout.strip()
        print(f"\n[5/6] Git push → origin/{branch}（含 LFS 对象）...")
        # 注意：不用 git lfs push --all，因为旧 commit 的 txt LFS 对象已损坏
        # git push 自带的 LFS pre-push hook 会自动推送本次 commit 中的新 LFS 对象（.jpg）
        run(["git", "push", "origin", branch], cwd=repo_dir)

        print(f"\n[6/6] ✅ 上传完成！")
        print(f"查看: https://www.modelscope.cn/datasets/{MS_ACTIONMIXED_REPO_ID}")

    finally:
        # 清理工作目录
        print(f"\n清理工作目录: {work_dir}")
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
