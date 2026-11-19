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

        # 【顺序很重要，而且必须先确认托盘起得来】
        # 如果托盘没起来却把关闭改成"藏起来"，用户点 ✕ 之后窗口就
        # 永远找不回来了 —— 程序还在跑，但看不见、点不到。
        # 所以：先起托盘，起来了才允许"关闭 = 隐藏"。
        if _tp.qi_dong():
            # 【真退出时必须放行，否则托盘「退出」点不动】
            # closing 处理函数返回 False = 取消关闭。托盘退出走的是
            # chuang.destroy()，而 destroy() **也会触发 closing** ——
            # 于是被这里拦下：窗口没销毁、主循环还活着、进程不退出。
            # 实测：点托盘「退出」后 closing 被触发，然后什么都没发生。
            # 治法：加一个"正在真退出"的开关，置上之后就让关。
            _zheng_tui = {"zai": False}

            def _guan(*_):
                """点 ✕：藏到托盘。返回 False 阻止 pywebview 销毁窗口。

                pywebview 的 closing 事件：处理函数**返回 False = 取消关闭**。
                但托盘「退出」已经把 _zheng_tui 置 True，那就放行。
                """
                if _zheng_tui["zai"]:
                    return True         # 放行，让窗口真的关掉
                try:
                    chuang.hide()
                    try:
                        qiao.ji_cang_zhe(True)
                    except Exception:
                        pass
                    # 第一次藏起来时告诉她一声，否则用户会以为程序没了
                    if not getattr(_tp, "_ti_guo", False):
                        _tp._ti_guo = True
                        try:
                            chuang.evaluate_js(
                                "setTimeout(function(){"
                                "LiaoTian.加消息('ta','（躲到右下角去了）"
                                "要我再出来，点一下托盘里我。',"
                                "'小笨蛋 （・ω・） 招手');}, 60)")
                        except Exception:
                            pass
                except Exception:
                    pass
                return False

            chuang.events.closing += _guan
            # 把开关交给托盘，它退出前置一下
            _tp.zhen_tui = lambda: _zheng_tui.__setitem__("zai", True)
            print("[main] 关闭 = 藏到托盘已启用（托盘退出会放行）")

            # ---- 主动消息 ----
            # 每分钟问一次"现在该说话吗"，该说就推气泡或发通知。
            # 窗口藏起来时要发系统通知，所以先告诉它怎么判断可见。
            try:
                from core.zhu_dong import ZhuDong
                _zd = ZhuDong(chuang, qiao)
                qiao.ji_cang_zhe(False)
                _zd.qi_dong()

                # 托盘「显示她」时把标记清掉
                _yuan_xian = _tp._xian

                def _xian_le(*a):
                    try:
                        qiao.ji_cang_zhe(False)
                    except Exception:
                        pass
                    return _yuan_xian(*a)

                _tp._xian = _xian_le
            except Exception as e:
                print("[main] 主动消息没起来（不影响使用）：%s" % e)
        else:
            print("[main] 托盘没起来，关闭仍是真退出（安全起见）")
    except Exception as e:
        print("[main] 托盘没起来（不影响使用）：%s" % e)

    webview.start(
        xian_shi_hou,
        debug=("--debug" in sys.argv),
        icon=zi_yuan("ui", "素材", "app_icon.ico"),
        # 运行数据（WebView2 缓存）落程序目录，不写 C 盘
        storage_path=zi_yuan("_数据"),
        private_mode=False,
    )
    return 0


if __name__ == "__main__":
    if "--自检" in sys.argv:
        # 打包后最怕"能开窗口但识图用不了"。这个模式不开窗口，
        # 只把依赖 / 模型 / 素材能不能用写成一份 txt，扔在 exe 旁边。
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from core import shitu as _st
            from core import luoji as _lj
            from core import zhengli as _zl
            _hang = [
                "小笨蛋 自检",
                "Python  %s" % sys.version.split()[0],
                "程序目录  %s" % zi_yuan(),
                "打包运行  %s" % bool(getattr(sys, "frozen", False)),
                "",
            ]
            for _m in ("PIL", "numpy", "cv2", "onnxruntime",
                       "rapidocr_onnxruntime", "webview"):
                try:
                    __import__(_m)
                    _hang.append("  库 %-22s 有" % _m)
                except Exception as _e:
                    _hang.append("  库 %-22s 缺  %s" % (_m, _e))
            _hang.append("")
            for _b, _lu in (("人脸模型", _st.FACE_MOGEN),
                            ("物体模型", _st.WUTI_MOGEN)):
                _hang.append("  %s  %s  %s" % (
                    _b, "在" if os.path.exists(_lu) else "缺！", _lu))
            _hang.append("")
            _hang.append("  素材 %d 个" % len(_lj.JUZI))
            _hang.append("  演示夹 %s" % _zl.zl_yanshi_lu())
            try:
                import cv2
                import numpy as _np
                _tu = _np.zeros((80, 80, 3), dtype=_np.uint8)
                _r1, _c1 = _st.zhao_renlian(_tu)
                _r2, _c2 = _st.zhao_wuti(_tu)
                _hang.append("  认人 跑通（%d 个，%s）" % (len(_r1), _c1 or "无错"))
                _hang.append("  认物 跑通（%d 个，%s）" % (len(_r2), _c2 or "无错"))
            except Exception as _e:
                _hang.append("  识别 跑不起来：%s" % _e)

            _lu = zi_yuan("自检结果.txt")
            with open(_lu, "w", encoding="utf-8") as _f:
                _f.write("\n".join(_hang) + "\n")
            print("\n".join(_hang))
            print("\n已写入 %s" % _lu)
        except Exception as _e:
            print("自检失败：%s" % _e)
        sys.exit(0)
    sys.exit(main())
