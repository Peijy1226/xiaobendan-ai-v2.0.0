# -*- coding: utf-8 -*-
"""下载模型.py —— 把两个大模型拉下来（约 105 MB）

【为什么模型不放进仓库】
识图模型 39 MB + 语音模型 66 MB = 105 MB。Git 里塞这种二进制，
每改一次就多存一份完整副本，仓库很快就几个 G。
所以源码只放代码，模型让用户自己跑一次这个脚本。

用法：
    D:/PyThon/python.exe 下载模型.py
"""
import os
import sys
import urllib.request
import zipfile

# 【必须】GitHub Actions 的 Windows runner 默认控制台编码是 cp1252，
# 打中文直接 UnicodeEncodeError 崩掉。这里强制改成 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MU = os.path.join(HERE, "core", "models")

# (目标文件/目录, 下载地址, 说明, 大约多少 MB)
DONG_XI = [
    ("face_detection_yunet_2023mar.onnx",
     "https://github.com/opencv/opencv_zoo/raw/main/models/"
     "face_detection_yunet/face_detection_yunet_2023mar.onnx",
     "识图 · 认人", 0.3),
    ("object_detection_yolox_2022nov.onnx",
     "https://github.com/opencv/opencv_zoo/raw/main/models/"
     "object_detection_yolox/object_detection_yolox_2022nov.onnx",
     "识图 · 认物（大）", 35),
    ("object_detection_nanodet_2022nov.onnx",
     "https://github.com/opencv/opencv_zoo/raw/main/models/"
     "object_detection_nanodet/object_detection_nanodet_2022nov.onnx",
     "识图 · 认物（小，备选）", 3.8),
]


def _jin_du(kuai, kuai_daxiao, zong):
    if zong <= 0:
        return
    bai = min(100, int(kuai * kuai_daxiao * 100 / zong))
    if bai != getattr(_jin_du, "_shang", -1):
        _jin_du._shang = bai
        sys.stdout.write("\r    %d%%" % bai)
        sys.stdout.flush()


def xia(url, dao, ming):
    """下载一个文件。失败返回 False，不抛异常（让后面的继续下）"""
    if os.path.exists(dao) and os.path.getsize(dao) > 1024:
        print("  ✓ %s 已存在，跳过" % ming)
        return True
    print("  ↓ %s" % ming)
    try:
        urllib.request.urlretrieve(url, dao, _jin_du)
        print("\n  ✓ 完成（%.1f MB）" % (os.path.getsize(dao) / 1048576))
        return True
    except Exception as e:
        print("\n  ✗ 失败：%s" % e)
        if os.path.exists(dao):
            try:
                os.remove(dao)
            except Exception:
                pass
        return False


def xia_yuyin():
    """语音模型是 zip，要解压"""
    mu = os.path.join(MU, "stt")
    yiyou = os.path.join(mu, "vosk-model-small-cn-0.22")
    if os.path.isdir(yiyou) and os.listdir(yiyou):
        print("  ✓ 语音模型已存在，跳过")
        return True
    os.makedirs(mu, exist_ok=True)
    url = ("https://alphacephei.com/vosk/models/"
           "vosk-model-small-cn-0.22.zip")
    zip_lu = os.path.join(mu, "_m.zip")
    print("  ↓ 语音识别模型（42 MB）")
    # 这个源在国内不稳，断点续传 + 重试
    ZONG = 43898754
    for i in range(30):
        have = os.path.getsize(zip_lu) if os.path.exists(zip_lu) else 0
        if have >= ZONG:
            break
        try:
            hd = {"Range": "bytes=%d-" % have} if have else {}
            req = urllib.request.Request(url, headers=hd)
            with urllib.request.urlopen(req, timeout=90) as r:
                mode = "ab" if have and getattr(r, "status", 0) == 206 else "wb"
                if mode == "wb":
                    have = 0
                with open(zip_lu, mode) as f:
                    while True:
                        b = r.read(524288)
                        if not b:
                            break
                        f.write(b)
                        if ZONG:
                            sys.stdout.write("\r    %d%%" % min(
                                99, int(os.path.getsize(zip_lu) * 100 / ZONG)))
                            sys.stdout.flush()
        except Exception as e:
            print("\n    第 %d 次重试（%s）" % (i + 1, str(e)[:40]))
            import time
            time.sleep(1)
    if os.path.getsize(zip_lu) != ZONG:
        print("\n  ✗ 语音模型没下完（%d / %d 字节）"
              % (os.path.getsize(zip_lu), ZONG))
        return False
    print("\n    解压中…")
    with zipfile.ZipFile(zip_lu) as z:
        z.extractall(mu)
    os.remove(zip_lu)
    print("  ✓ 语音模型完成")
    return True


def main():
    print("=" * 60)
    print("  小笨蛋 · 下载模型")
    print("=" * 60)
    print()
    os.makedirs(MU, exist_ok=True)

    cheng = 0
    for wenjian, url, shuo, mb in DONG_XI:
        print()
        if xia(url, os.path.join(MU, wenjian), "%s（%.0f MB）" % (shuo, mb)):
            cheng += 1

    print()
    if xia_yuyin():
        cheng += 1

    print()
    print("=" * 60)
    if cheng == len(DONG_XI) + 1:
        print("  全部就绪。现在可以 D:/PyThon/python.exe main.py 了。")
    else:
        print("  有 %d 项失败。检查网络后重跑本脚本即可（已下载的会跳过）。"
              % (len(DONG_XI) + 1 - cheng))
    print("=" * 60)
    return 0 if cheng == len(DONG_XI) + 1 else 1


if __name__ == "__main__":
    sys.exit(main())
