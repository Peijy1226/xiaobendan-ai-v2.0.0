# -*- coding: utf-8 -*-
"""main.py —— 小笨蛋 产品版

窗口 900×680，无边框自绘标题栏，Win11 系统圆角（DWM），
关窗口藏托盘（托盘起不来就保持真退出，安全）。

运行：
    D:/PyThon/python.exe main.py            正常
    D:/PyThon/python.exe main.py --debug    开 F12
    D:/PyThon/python.exe main.py --自检      不开窗口，写环境清单
"""
import os
import sys

import webview


def zi_yuan(*ming):
    """取资源路径。

    打包后 exe 在 dist/小笨蛋/ 下，ui 与 exe 同级放（不打进 exe）——
    这样用户自己能换壁纸、加表情，和旧版 打包.spec 的思路一致。
    """
    if getattr(sys, "frozen", False):
        ji = os.path.dirname(sys.executable)
    else:
        ji = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ji, *ming)


def ding_chi_cun(chuang, kuan, gao, ju_zhong=True):
    """把窗口**客户区**精确设成 kuan × gao（逻辑像素），并居中。

    【为什么必须自己设一遍】
    pywebview 建无边框窗口时用 FormBorderStyle=None，但它在设边框之前
    就已经按带边框的窗口分配过尺寸，客户区实际只剩 884×641 ——
    create_window(width=900, height=680) 出来的不是 900×680。
    这是 pywebview 6.2.1 在 Windows 上的行为，实测 CreateWindow 时
    GetWindowRect 和 GetClientRect 都是 884×641（不是边框占位，是根本没给够）。

    所以这里在显示之后用 SetWindowPos 按物理像素重设一次；
    有 DPI 缩放时按 GetDpiForWindow 换算，保证 CSS 里的 900×680 是真尺寸。
    """
    try:
        import ctypes
        u = ctypes.windll.user32
        hwnd = chuang.native.Handle.ToInt32()
        scale = u.GetDpiForWindow(hwnd) / 96.0
        pw, ph = int(round(kuan * scale)), int(round(gao * scale))
        if ju_zhong:
            sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
            x, y = max(0, (sw - pw) // 2), max(0, (sh - ph) // 2)
        else:
            x = y = 80
        # SWP_NOZORDER = 0x0004
        u.SetWindowPos(hwnd, None, x, y, pw, ph, 0x0004)
        return True
    except Exception as e:
        print("[main] 设窗口尺寸失败（不影响使用，只是尺寸不精确）：%s" % e)
        return False


def hui_fu_zhong_hua(chuang, yan_shi=0.12):
    """从最小化恢复后，强制重绘一次。

    【为什么需要】WebView2 在窗口被最小化时会丢掉合成层的表面，恢复之后
    它不一定会自己重新提交 —— 表现是一整片深蓝底（#1a2029），聊天区、
    壁纸、气泡全没了，看着像死机。
    实测：放着不管永远不恢复；把窗口尺寸改 1px 再改回来（或移出屏幕再
    移回、或 InvalidateRect）都能立刻刷出来。这里用"尺寸抖 1px"，
    用户看不到窗口位置和大小有任何变化。
    """
    import ctypes
    import ctypes.wintypes as wt
    import time
    try:
        time.sleep(yan_shi)            # 等 WebView 处理完恢复事件
        u = ctypes.windll.user32
        hwnd = chuang.native.Handle.ToInt32()
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w < 8 or h < 8:
            return False
        # SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
        u.SetWindowPos(hwnd, None, 0, 0, w - 1, h, 0x0002 | 0x0004 | 0x0010)
        time.sleep(0.03)
        u.SetWindowPos(hwnd, None, 0, 0, w, h, 0x0002 | 0x0004 | 0x0010)
        return True
    except Exception as e:
        print("[main] 恢复重绘失败 %s" % e)
        return False


# 【必须在 import api 之前设好】
# core/luoji.py 的 DIR 是 import 那一刻就算出来、并据此推导出
# 素材/表情/存档等一堆路径常量的。晚一步设，它就已经指向 core/ 了。
# 打包后 __file__ 在 _internal/ 里，所以要用 sys.executable 的目录。
if getattr(sys, "frozen", False):
    _GEN = os.path.dirname(sys.executable)
else:
    _GEN = os.path.dirname(os.path.abspath(__file__))
os.environ["XBD_DIR"] = os.path.join(_GEN, "ui")

# 【vendor 目录】pystray 装在会话目录的 vendor/ 里，不进系统 site-packages。
# 必须在 import pystray 之前塞进 sys.path —— 打包后 vendor 会在 _internal 里。
_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if not os.path.isdir(_VENDOR):
    _VENDOR = os.path.join(getattr(sys, "_MEIPASS", _GEN), "vendor")
if os.path.isdir(_VENDOR) and _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)


def yuan_jiao_he_yin_ying(chuang):
    """给无边框窗口加 Win11 圆角和系统阴影（DWM 两行属性）

    【为什么必须借 DWM，不靠 CSS】
    frameless=True 的窗口在 Windows 上是一块**方形**的客户区。
    CSS 的 border-radius 只能圆"网页内容"，圆不了窗口本身 ——
    四角会露出底色，看着像贴了一块方形画布。
    正确的做法是让 DWM 自己去圆：Win11 的 DWMWA_WINDOW_CORNER_PREFERENCE
    会让整个窗口（含投影）按系统规范圆角、顺便给一层真投影。

    实测（本机 Win11 26200）：SetWindowAttribute(hwnd, 33, 2) 返回 0，
    GetWindowAttribute 读回 2 —— 真的生效了，不是"调用成功但被忽略"。
    失败的机器（Win10）会返回非 0，那就静默跳过，窗口退化成方形，不影响使用。
    """
    try:
        import ctypes
        import ctypes.wintypes as wt
        dwm = ctypes.windll.dwmapi
        hwnd = wt.HWND(chuang.native.Handle.ToInt32())

        # ① 圆角：DWMWA_WINDOW_CORNER_PREFERENCE(33) = DWMWCP_ROUND(2)
        v = ctypes.c_int(2)
        if dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v), 4) == 0:
            print("[main] 窗口圆角已生效")

        # ② 系统阴影：DWMWA_NCRENDERING_POLICY(2) = DWMNCRP_ENABLED(2)
        v2 = ctypes.c_int(2)
        dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(v2), 4)
    except Exception as e:
        print("[main] 圆角/阴影设置失败（不影响使用）：%s" % e)


def main():
    import api

    html = zi_yuan("ui", "index.html")
    if not os.path.isfile(html):
        print("找不到界面文件：%s" % html)
        return 1

    qiao = api.Qiao()

    # pywebview 发现 url 是本地文件时会自动起 127.0.0.1 的 http 服务再加载。
    # 必须走 http 而不是 file:// —— file:// 协议下 WebView2 会限制页面取背景
    # 像素，backdrop-filter 会退成一块纯色，透光那套就废了。
    chuang = webview.create_window(
        "小笨蛋",
        url=html,
        js_api=qiao,
        width=900,
        height=680,
        min_size=(660, 300),
        frameless=True,       # 无边框，自绘标题栏
        easy_drag=False,      # 不要整窗可拖，只让 .pywebview-drag-region 拖
        text_select=False,
        background_color="#1a2029",
    )
    qiao.gua_chuang(chuang)

    def xian_shi_hou():
        """窗口一显示就把客户区校成 900×680 —— 见 ding_chi_cun 的说明"""
        import time
        time.sleep(0.25)       # 等 WebView 挂上 Handle
        ding_chi_cun(chuang, 900, 680)

    chuang.events.restored += lambda: hui_fu_zhong_hua(chuang)
    chuang.events.shown += lambda: yuan_jiao_he_yin_ying(chuang)

    # ---- 托盘 ----
    # 关窗口 = 藏到托盘，不是退出（用户要的是"她住在电脑里"）。
    # 真退出走托盘右键「退出」。
    # 【必须复用同一个 qiao】第一次写错了，这里又 new 了一个 Qiao()，
    # 前端连的是第一个、托盘操作的是第二个 —— 对话历史和情绪全分家。
    try:
        from core.tuopan import TuoPan
        _tp = TuoPan(chuang, qiao)