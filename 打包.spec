# -*- coding: utf-8 -*-
"""打包.spec —— 小笨蛋 产品版（pywebview）

要点（和旧版 tk 打包的区别）：
  · 不带 tcl/tk —— 界面走 WebView2，那些几百 MB 的 tk 数据全不需要了
  · onedir（文件夹版）：启动快，且 ui / 素材 在外面，用户能自己换壁纸
  · 不带控制台（windowed）：双击就出界面
  · WebView2 用系统的，不塞进包 —— 这是体积能压到 100MB 出头的原因

用法（在 纯净版 目录下）：
    D:/PyThon/python.exe -m PyInstaller 打包.spec --noconfirm
产物：
    dist/小笨蛋/小笨蛋.exe   +   ui/  +  素材（手动复制）
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(SPEC))

# 【必须】把 vendor/ 塞进 sys.path —— pystray 装在那里，
# 不在系统 site-packages 里。不塞的话 Analysis 找不到 pystray._win32，
# 打包能"成功"，但 exe 一跑托盘就 ImportError（实测报过：
# ERROR: Hidden import 'pystray._win32' not found）。
_VENDOR = os.path.join(ROOT, "vendor")
if os.path.isdir(_VENDOR) and _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

block_cipher = None

# pywebview 的 js 资源要带上（注入 window.pywebview.api 用）
datas = []
try:
    import webview
    _wv = os.path.dirname(webview.__file__)
    for sub in ("js", "lib"):
        p = os.path.join(_wv, sub)
        if os.path.isdir(p):
            datas.append((p, os.path.join("webview", sub)))
except Exception as e:
    print("警告：没找到 pywebview，界面会白屏：%s" % e)

hiddenimports = [
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
    "core.luoji",          # 逻辑层
    "core.shitu",          # 识图
    "core.zhengli",        # 整理助手
    "core.xiezuo",         # 写一篇
    "core.dashang",        # 打赏档位
    "cv2", "numpy", "onnxruntime", "rapidocr_onnxruntime",
    "pystray", "pystray._win32", "six",
    "core.tuopan", "core.zhu_dong", "core.yuyin_shuru",
    "sounddevice", "vosk",
]

# vendor/（pystray 装在这里，不进系统 site-packages）
_vd = os.path.join(ROOT, "vendor")
if os.path.isdir(_vd):
    datas.append((_vd, "vendor"))

# 识图的 3 个 onnx 模型（40 MB）要跟着走，否则 exe 里点识图会说"模型缺了"
_mu = os.path.join(ROOT, "core", "models")
if os.path.isdir(_mu):
    for _n in sorted(os.listdir(_mu)):
        if _n.endswith(".onnx"):
            datas.append((os.path.join(_mu, _n), "core/models"))

# 语音识别模型（Vosk 中文小模型，55 MB）
_stt = os.path.join(ROOT, "core", "models", "stt")
if os.path.isdir(_stt):
    for _n in sorted(os.listdir(_stt)):
        _p2 = os.path.join(_stt, _n)
        if os.path.isdir(_p2) and _n.startswith("vosk-model"):
            datas.append((_p2, os.path.join("core/models/stt", _n)))

# 不要的东西：tkinter（界面已改用 WebView）、用不上的科学计算/lint 包
# 【第三阶段改了】原来这里排除了 cv2 / onnxruntime / rapidocr ——
# 那时识图还没搬进来。现在识图进去了，这三个必须打，否则识图全废。
# 代价：体积从 79 MB 涨到 300 MB 上下（opencv 60MB + onnxruntime 40MB +
# rapidocr 自带模型 20MB + 我们的 3 个 onnx 40MB）。这是"功能要真的能用"
# 必须付的钱，没别的办法。
# vosk 的原生库在 vendor/vosk/ 下（libvosk.dll 等），要跟着走
_vosk_dll = os.path.join(ROOT, "vendor", "vosk")
if os.path.isdir(_vosk_dll):
    for _n in os.listdir(_vosk_dll):
        if _n.lower().endswith((".dll", ".lib")):
            datas.append((os.path.join(_vosk_dll, _n), "vendor/vosk"))

excludes = [
    "tkinter", "_tkinter", "turtle",
    "matplotlib", "scipy", "pandas", "notebook", "IPython",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "torch", "tensorflow", "jax",
    "edge_tts",          # 语音走独立子进程（见 core/tuopan.py 上方说明）
]

a = Analysis(
    ["main.py"],
    pathex=[ROOT, _VENDOR] if os.path.isdir(_VENDOR) else [ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon = os.path.join(ROOT, "ui", "素材", "app_icon.ico")
if not os.path.isfile(icon):
    icon = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="小笨蛋",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX 会拖慢启动，还容易被杀软误报
    console=False,           # 双击不弹黑窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="小笨蛋",
)
