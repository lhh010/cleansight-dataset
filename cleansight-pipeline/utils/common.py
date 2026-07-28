"""脚本共用:定位仓库根、加载 yaml 配置、白名单判断。"""
from pathlib import Path

import yaml

PKG_ROOT = Path(__file__).resolve().parent.parent   # cleansight-pipeline/
ROOT = PKG_ROOT                                      # 自包含:raw/datasets/runs 全在其内
CONFIG_PATH = PKG_ROOT / "config.yaml"


def load_config(path=CONFIG_PATH) -> dict:
    """读一份 yaml 配置。

    配置已按数据集下沉(yolo 见 yolo/{train,test}.yaml),各脚本传自己的路径;
    默认值只服务尚未下沉的 actionmixed。
    """
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def is_whitelisted(name: str, only_videos) -> bool:
    """only_videos 为空 = 全部通过;否则文件名前缀匹配任一。

    仅供尚未下沉的 actionmixed 使用。yolo 两轨已改为按 LS task id 登记
    (见 yolo/manifest.py)—— 视频文件名会随 LS 重传而变,task id 不会。
    """
    if not only_videos:
        return True
    return any(name.startswith(p) for p in only_videos)
