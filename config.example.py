"""
项目配置文件（包含敏感信息，请勿提交到 git）
将本文件复制为 config.py 并填入真实值
"""
import os

# ============================================================
# ModelScope 配置
# ============================================================
# 访问令牌: https://modelscope.cn/my/myaccesstoken
MS_ACCESS_TOKEN = "your_access_token_here"
# 数据集仓库 ID，格式: <username>/<dataset_name>
# 旧的通用 raw/project-10 仓库（archive/scripts/ 里的老脚本仍引用）
MS_REPO_ID = "your_username/your_dataset_name"

# 三套数据集各自的 ModelScope 仓库 ID（活跃上传器 <dataset>/upload.py 使用）
MS_YOLO_REPO_ID = "your_username/cleansight-yolo"              # cleansight-pipeline/yolo/upload.py
MS_ACTIONMIXED_REPO_ID = "your_username/cleansight-ActionMixed"   # cleansight-pipeline/actionmixed/upload.py
MS_ACTIONSEQ_REPO_ID = "your_username/cleansight-ActionSequence"  # 已弃用,仅 archive/actionseq/upload.py 用

# ============================================================
# Label Studio 配置
# ============================================================
# Label Studio 服务地址
LS_BASE_URL = "http://your-label-studio-host:8080"
# API Token: 右上角头像 -> Account & Settings -> Access Token
LS_API_TOKEN = "your_label_studio_token_here"
# 要导出的项目 ID
LS_PROJECT_ID = 10

# ============================================================
# 本地路径配置
# ============================================================
# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 导出数据存放目录
EXPORT_BASE_DIR = os.path.join(BASE_DIR, "exports")

# 待上传的本地文件夹路径（用于 upload_to_modelscope.py）
UPLOAD_FOLDER_PATH = os.path.join(BASE_DIR, "your-folder-to-upload")
