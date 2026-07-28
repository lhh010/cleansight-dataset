#!/usr/bin/env python3
"""
从 Label Studio 服务器下载导出 JSON 引用的原始视频到 raw/videos/。

扫 raw/exports/ 下**所有**导出(含按 LS 项目分的子目录),取并集下载 —— 各轨的
视频都落同一个 raw/videos/,由各自清单决定谁进哪个数据集。

JSON 只存路径引用(data.video),视频本体在服务器。已存在且非空的文件会 [skip]。
下载后做完整性抽查:优先 ffprobe 读时长/帧数;没有 ffprobe 时退化为"大小 > 0"。

用法(在 cleansight-pipeline/ 下执行):
    export LS_HOST=http://<LS地址>:8080
    export LS_TOKEN=<AccessToken>     # LS 页面 Account & Settings -> Access Token
    python3 common/pull.py
"""
import os
import shutil
import subprocess
import sys
import urllib.request

# --- 从子目录运行时也能 import 顶层 utils/ ---
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from utils import labelstudio

LS_HOST = os.environ.get("LS_HOST", "").rstrip("/")
LS_TOKEN = os.environ.get("LS_TOKEN", "")


def probe(path) -> str:
    """返回一行完整性信息;损坏返回以 'BAD' 开头的串。"""
    if shutil.which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=nb_read_packets", "-of", "default=nw=1",
                 "-select_streams", "v:0", "-count_packets", str(path)],
                capture_output=True, text=True, timeout=120,
            )
            info = out.stdout.replace("\n", " ").strip()
            return info or "BAD 无视频流"
        except Exception as e:  # noqa: BLE001
            return f"BAD ffprobe 失败: {e}"
    size = path.stat().st_size
    return f"size={size/1e6:.1f}MB" if size > 0 else "BAD 0 字节"


def main():
    if not LS_HOST or not LS_TOKEN:
        sys.exit("请先设置环境变量 LS_HOST 和 LS_TOKEN(见脚本头部说明)")

    exports = sorted(labelstudio.EXPORT_DIR.rglob("*.json"))
    if not exports:
        sys.exit(f"raw/exports/ 下没有导出 JSON: {labelstudio.EXPORT_DIR}")
    labelstudio.VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    # 视频名 -> LS 相对路径(并集去重:同一视频可能被多份导出引用)
    refs = {}
    for jp in exports:
        n = 0
        for t in labelstudio.load_tasks(jp):
            rel = t.get("data", {}).get("video")
            if rel:
                refs[os.path.basename(rel)] = rel
                n += 1
        print(f"导出 {jp.parent.name}/{jp.name}: {n} 个 task")
    print(f"合计 {len(refs)} 个不重复视频 -> {labelstudio.VIDEO_DIR}")

    ok, skip, fail, bad = 0, 0, 0, []
    for name, rel in sorted(refs.items()):
        out = labelstudio.VIDEO_DIR / name
        if out.exists() and out.stat().st_size > 0:
            print(f"  [skip] {name} 已存在")
            skip += 1
            continue
        url = f"{LS_HOST}{rel}"
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Token {LS_TOKEN}"})
            with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            info = probe(out)
            flag = "  ⚠️损坏" if info.startswith("BAD") else ""
            if info.startswith("BAD"):
                bad.append(name)
            print(f"  [ok]   {name}  {info}{flag}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [fail] {url}\n         {e}")
            fail += 1

    print(f"\n完成: 成功 {ok} / 跳过 {skip} / 失败 {fail}")
    if bad:
        print(f"⚠️ 疑似损坏 {len(bad)} 个,建议删掉重下: {', '.join(bad)}")
    if fail:
        print("失败多半是 LS_HOST/LS_TOKEN 不对,或视频接的是云存储(去云端原始位置取)")
    print("下一步:python3 common/reconcile.py 看增量待办")


if __name__ == "__main__":
    main()
