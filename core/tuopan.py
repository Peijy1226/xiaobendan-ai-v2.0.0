# -*- coding: utf-8 -*-
"""tuopan.py —— 系统托盘（pystray）

三件事：
  ① 关窗口 = 最小化到托盘（不是退出）
  ② 托盘右键：显示 / 隐藏、让她说句话、退出
  ③ 左键单击：显示或隐藏窗口

【为什么托盘要单开一个线程】
pystray 的 run() 是阻塞的，它自己起消息循环。
pywebview 的 start() 也是阻塞的。两个主循环不能在一个线程里跑。
所以托盘跑在 daemon 线程 —— 主线程退出时它跟着死，不用手动收拾。

【为什么"关闭 = 最小化"而不是"关闭 = 退出"】
用户要的是"她住在我电脑里"。真退出了她就没了。
但退出这条路必须留：托盘右键 → 退出，或者关窗口时按住 Shift。
"""
import os
import threading

try:
    import pystray
    from pystray import MenuItem as 项
except Exception as e:      # pystray 没装时整个模块退化
    pystray = None
    _cuo = str(e)


class TuoPan:
    def __init__(self, chuang, qiao):
        self._chuang = chuang
        self._qiao = qiao
        self._icon = None
        self._xian_shi = True
        self.zhen_tui = None      # main.py 会塞一个"放行关闭"的回调进来
        self._ting_zhi = False    # 巡检线程的停止旗

    # ---------------- 图标 ----------------
    def _zuo_tu(self):
        """托盘图标：优先用 ui/素材/托盘/托盘图标.ico，没有就用程序图标"""
        from PIL import Image
        base = os.environ.get("XBD_DIR") or ""
        for lu in (os.path.join(base, "素材", "托盘", "托盘图标.ico"),
                   os.path.join(base, "素材", "app_icon.ico")):
            if os.path.isfile(lu):
                try:
                    return Image.open(lu).convert("RGBA")
                except Exception:
                    pass
        # 全都没有 —— 画一个最简的金圈
        from PIL import ImageDraw
        im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((2, 2, 61, 61), fill=(24, 31, 42, 255),
                  outline=(255, 209, 102, 255), width=4)
        return im

    # ---------------- 动作 ----------------
    def _xian(self, *_):
        try:
            self._chuang.show()
            self._chuang.restore()
            self._xian_shi = True
        except Exception as e:
            print("[托盘] 显示失败 %s" % e)

    def _cang(self, *_):
        try:
            self._chuang.hide()
            self._xian_shi = False
        except Exception as e:
            print("[托盘] 隐藏失败 %s" % e)

    def _fan(self, *_):
        """点一下托盘：显示/隐藏切换"""
        if self._xian_shi:
            self._cang()
        else:
            self._xian()

    def _shuo(self, *_):
        """让她主动说一句话 —— 走 zhu_dong_na（旧版搬来的）"""
        try:
            jieguo = self._qiao.zhu_dong_shuo(qiang_zhi=True)
            if not jieguo or not jieguo.get("wen"):
                return
            self._xian()
            try:
                self._chuang.evaluate_js(
                    "LiaoTian.加消息('ta', %r, %r);"
                    % (jieguo["wen"], jieguo.get("biao") or ""))
            except Exception as e:
                print("[托盘] 推到界面失败 %s" % e)
        except Exception as e:
            print("[托盘] 主动说话失败 %s" % e)

    def _tui(self, *_):
        """真退出：先告诉主窗口"这次是真关"，再存档、关窗口、停图标

        【为什么原来点了没反应】main.py 的 closing 处理函数永远 return False
        （点 ✕ 要藏到托盘）。而 chuang.destroy() 也会触发 closing ——
        于是被自己拦住：窗口没销毁、主循环还活着、进程不退出。
        实测点「退出」后日志只看到 closing 被触发，然后什么都没发生。
        所以这里必须先把 zhen_tui 开关打开。
        """
        print("[托盘] 退出")
        # ① 先放行关闭
        try:
            if callable(getattr(self, "zhen_tui", None)):
                self.zhen_tui()
        except Exception as e:
            print("[托盘] 放行关闭失败 %s" % e)

        # ② 存档（存档失败也要继续退出，不能因为存不上就不退了）
        try:
            self._qiao.guan_bi()
        except Exception as e:
            print("[托盘] 存档/关窗口出错（继续退出）：%s" % e)

        # ③ 停图标
        try:
            if self._icon:
                self._icon.stop()
        except Exception:
            pass

        # ④ 兜底：3 秒后如果进程还在，硬退。