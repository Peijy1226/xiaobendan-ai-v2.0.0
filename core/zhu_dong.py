# -*- coding: utf-8 -*-
"""zhu_dong.py —— 主动消息 + 系统通知

【为什么这块是"陪伴"和"聊天"的分界线】
只在你说话时才回应的是客服。她该在你半天没来的时候戳你一下。

节奏逻辑在 core/luoji.py 的 zhu_dong_na()（旧版搬来的）：
一天最多 6 次、两次之间至少 40 分钟、深夜一天一次、久别一天一次。
这一层只负责**定时问她"现在该说吗"**，以及**把话说出去**。

【通知为什么不用第三方库】
`win10toast` / `plyer` 都要额外装包，而且在新版 Windows 上经常不弹。
这里直接用 shell32 的 Shell_NotifyIconW —— 系统自带、零依赖。
托盘图标本来就是 pystray 在管，但它的 balloon 接口在不同版本上行为不一，
所以这里自己建一个隐藏的 NOTIFYICONDATAW，只为弹气泡。

【失败就静默】通知弹不出来不是致命问题，绝不能因此让主程序崩。
"""
import ctypes
import ctypes.wintypes as wt
import threading
import time

# ---- Shell_NotifyIcon 常量 ----
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
NIF_INFO = 0x10
NIIF_INFO = 0x01
NIIF_USER = 0x04
NIIF_NOSOUND = 0x10

WM_USER = 0x0400


class NOTIFYICONDATAW(ctypes.Structure):
    """Win32 NOTIFYICONDATAW（Vista+ 的结构，够用）"""
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", wt.WCHAR * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64),
        ("dwInfoFlags", wt.DWORD),
    ]


def tong_zhi(biaoti, neirong, tubiao_lu=None):
    """弹一条系统通知。返回 True/False，绝不抛异常。

    实测（Win11 26200）：能弹，且会出现在右下角通知中心。
    """
    try:
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # 建一个隐藏窗口当"通知的宿主" —— Shell_NotifyIcon 必须挂在一个 HWND 上。
        # 用 STATIC 类最省事，不用注册自己的窗口类。
        hwnd = user32.CreateWindowExW(
            0, "STATIC", "xbd_tongzhi", 0, 0, 0, 0, 0,
            None, None, kernel32.GetModuleHandleW(None), None)
        if not hwnd:
            return False

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_INFO | NIF_TIP | NIF_ICON | NIF_MESSAGE
        nid.uCallbackMessage = WM_USER + 1
        nid.szTip = "小笨蛋"
        nid.szInfoTitle = (biaoti or "小笨蛋")[:63]
        nid.szInfo = (neirong or "")[:255]
        nid.dwInfoFlags = NIIF_INFO | NIIF_NOSOUND
        # 图标：不设就用系统信息图标（hIcon=0 在某些系统上不显示，所以给个通用图标）
        try:
            nid.hIcon = user32.LoadIconW(None, wt.LPCWSTR(32516))  # IDI_INFORMATION
        except Exception:
            nid.hIcon = None

        # 先 ADD（不带 INFO），再 MODIFY 带 INFO ——
        # 直接 ADD 带 INFO 在部分系统上不弹
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            user32.DestroyWindow(hwnd)
            return False

        nid.uFlags = NIF_INFO
        ok = bool(shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid)))

        # 留 6 秒让它显示，然后撤掉（不撤会永久占一个托盘位，但图标是空的）
        def _che():
            time.sleep(6)
            try:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
                user32.DestroyWindow(hwnd)
            except Exception:
                pass

        threading.Thread(target=_che, daemon=True).start()
        return ok
    except Exception as e:
        print("[通知] 弹不出来（不影响使用）：%s" % e)
        return False


class ZhuDong:
    """主动消息的定时器

    每 CHECK 秒问一次 luoji.zhu_dong_na()：现在该说话吗？
    该说就：
      · 窗口看得见 → 直接推一条气泡进聊天区
      · 窗口藏着  → 发一条系统通知（点一下能唤回来）
    """

    CHECK = 60          # 一分钟看一次。zhu_dong_na 自己管"40 分钟间隔"，这里不用太密

    def __init__(self, chuang, qiao):
        self._chuang = chuang
        self._qiao = qiao
        self._ting = threading.Event()
        self._xian = None        # 回调：判断窗口现在可见吗

    def she_xian_shi_pan(self, fn):
        """告诉它怎么判断窗口可见 —— 不同版本 API 不一样，让调用方决定"""
        self._xian = fn

    def qi_dong(self):
        threading.Thread(target=self._zhuan, daemon=True).start()
        print("[主动] 定时器已启动（%d 秒一次）" % self.CHECK)
        return True

    def ting(self):
        self._ting.set()

    def _zhuan(self):
        # 启动后先等 90 秒 —— 别刚打开就冒一句，像在催
        if self._ting.wait(90):
            return
        while not self._ting.is_set():
            try:
                self._yi_ci()
            except Exception as e:
                print("[主动] 这一轮出错（继续跑）：%s" % e)
            if self._ting.wait(self.CHECK):
                return

    def _yi_ci(self):
        try:
            jie = self._qiao.zhu_dong_shuo()
        except Exception as e:
            print("[主动] 取话失败：%s" % e)
            return
        wen = (jie or {}).get("wen", "")
        if not wen:
            return          # 不到时候，什么都不做

        # 窗口开着 → 直接进聊天区（用户看得见，不用打扰系统通知）
        ke_jian = True
        try:
            ke_jian = bool(self._xian()) if self._xian else True
        except Exception:
            ke_jian = True

        if ke_jian:
            try:
                self._chuang.evaluate_js(
                    "LiaoTian.加消息('ta', %r, %r);"
                    % (wen, (jie or {}).get("biao") or ""))
                print("[主动] 说话了：%s" % wen[:24])
            except Exception as e:
                print("[主动] 推入界面失败：%s" % e)
        else:
            # 窗口藏着 → 系统通知
            tong_zhi("小笨蛋", wen)
            print("[主动] 发通知：%s" % wen[:24])
            # 通知发完也要把话记进对话，用户点开时能看到
            try:
                self._qiao.ji_zhu_dong(wen, (jie or {}).get("biao") or "")
            except Exception:
                pass
