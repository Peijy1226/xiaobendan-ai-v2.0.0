# -*- coding: utf-8 -*-
"""zhengli.py —— 整理助手（只把文件移到回收站，绝不真删）

从旧版第 9472-10290 行整段搬来，一个字没改。

【四条硬规矩，改的时候别破坏】
  1. 只认白名单里的文件夹（现在只剩「演示夹」），别处一律不动；
     唯一例外是「指定删除」—— 用户亲手挑的那几个文件，仍要过
     快捷方式 / 程序自己 / 系统目录几道闸。
  2. 只动文件：文件夹、快捷方式、程序自己那一摊（素材/模型/壁纸/日志）全不碰。
  3. 只调回收站 —— 全模块唯一的"删"就是 _zl_song_huishouzhan()，
     代码里没有 os.remove / shutil.rmtree，删错了还能从回收站捞回来。
  4. 单次最多 10 个文件、合计不超过 200 MB，每次执行都往「整理日志.txt」记一笔。

【和旧版的差别】旧版执行时开一个 cmd 窗口逐条打进度（_zl_mingling_hang），
新版改成 WebView 里的进度面板，所以那个函数保留但不再调用；
进度由 zl_zhi_xing 的返回值一次性给出（文件不多，10 个以内，够用）。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

DIR = os.environ.get("XBD_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# 第十一部分：整理助手 —— 只把文件移到回收站，绝不真删
# ------------------------------------------------------------------------------
# 四条硬规矩，改的时候别破坏：
#   1. 只认白名单里的文件夹（现在只剩「演示夹」），别处一律不动；
#      唯一的例外是「指定删除」—— 用户亲手在对话框里点中的那几个文件，
#      走 zl_weixian(lu, mingque=True)，其余几道闸（快捷方式/程序自己/系统目录）照拦；
#   2. 只动文件：文件夹、快捷方式、程序自己那一摊（素材/模型/壁纸/日志）全不碰；
#   3. 只调回收站 —— 全程序唯一的"删"就是 _zl_song_huishouzhan()，代码里
#      没有 os.remove / shutil.rmtree，删错了还能从回收站捞回来；
#   4. 单次最多 10 个文件、合计不超过 200 MB，每次执行都往「整理日志.txt」记一笔。
#
# 【为什么用 ctypes 而不是 send2trash】send2trash 是第三方包，打成 exe 要多塞
# 一个依赖；SHFileOperationW 是系统自带的 shell32，零依赖，和现有的打包方式
# （只 collect rapidocr/onnxruntime）不冲突。
# ══════════════════════════════════════════════════════════════════════════════
ZL_KAIWEN = os.path.join(DIR, "整理助手开关.txt")
ZL_RIZHI = os.path.join(DIR, "整理日志.txt")
ZL_ZUI_DUO = 10                        # 单次最多几个文件
ZL_ZUI_DA = 200 * 1024 * 1024          # 单次总大小上限（200 MB）

import tempfile                                # 清单/结果文件放临时目录
# 清单和结果都走临时文件，不在程序目录里堆：这两样是"一次性的传递介质"
ZL_QINGDAN = os.path.join(tempfile.gettempdir(), "小笨蛋_整理清单.txt")
ZL_JIEGUO = os.path.join(tempfile.gettempdir(), "小笨蛋_整理结果.txt")
ZL_CHUANGKOU_MIAO = 20                 # cmd 窗口最后停留多少秒（按键可提前关）

# 类型 → 扩展名。第一个「全部」不筛，靠空元组表示。
ZL_LEIXING = (
    ("全部",   ()),
    ("安装包", (".exe", ".msi", ".msix", ".apk", ".pkg", ".appx")),
    ("文档",   (".doc", ".docx", ".pdf", ".txt", ".ppt", ".pptx",
                ".xls", ".xlsx", ".md", ".csv")),
    ("图片",   (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
                ".heic", ".tif", ".tiff")),
    ("压缩包", (".zip", ".rar", ".7z", ".tar", ".gz", ".xz")),
)

# 这两个文件哪怕躺在桌面/下载里也不许删 —— 系统自己会重建，但删了桌面会抽风
ZL_BU_DONG = ("desktop.ini", "thumbs.db", "$recycle.bin")


def zl_baimingdan():
    """允许整理的三个文件夹：[(名字, 路径), ...]

    每次现算，不在导入时定死：桌面有可能被 OneDrive 接走（路径就变了），
    而且用户换了电脑也不至于指向一个不存在的目录。
    """
    jia = os.path.expanduser("~")
    # 【本条改·桌面和下载不再扫】
    # 用户原话："桌面、下载两个文件夹就不要了，容易误删"。
    # 扫描只剩演示夹（程序自己造的那一个），真正要删的东西走「指定删除」——
    # 由用户亲手在文件对话框里点，点中哪个才动哪个。
    return (("演示夹", os.path.join(jia, "小笨蛋演示夹")),)


def zl_du_kai():
    """总闸读盘：默认关（文件不存在也算关）"""
    try:
        with open(ZL_KAIWEN, "r", encoding="utf-8") as f:
            for hang in f:
                hang = hang.strip()
                if hang.startswith("开启"):
                    zhi = hang.split("=", 1)[-1].strip()
                    return zhi in ("1", "是", "开", "on", "true", "True")
    except Exception:
        pass
    return False


def zl_xie_kai(kai):
    """总闸落盘 —— 关掉程序再开，还得是上次那个状态"""
    try:
        with open(ZL_KAIWEN, "w", encoding="utf-8") as f:
            f.write("# 整理助手总闸：1 = 开启，0 = 关闭（默认关闭）\n")
            f.write("# 开着才会把文件移到回收站；关着只看清单、不动手。\n")
            f.write("开启=%d\n" % (1 if kai else 0))
        return True
    except Exception:
        return False


def _zl_zai(shu, mu):
    """shu 是不是在 mu 里面（含 mu 本身）—— 路径前缀比较的唯一出口"""
    try:
        shu = os.path.normcase(os.path.realpath(shu))
        mu = os.path.normcase(os.path.realpath(mu))
        return shu == mu or shu.startswith(mu.rstrip("\\/") + os.sep)
    except Exception:
        return False


# 「我自己那一摊」的名字前缀。只在"程序就摊在桌面/下载里"这种情况下用 ——
# 机房演示时程序往往被整个拷到桌面根目录，那时不能拿"整个桌面"当禁区。
ZL_ZIJI_MING = ("小笨蛋", "素材", "灵光开关", "API", "整理助手开关", "整理日志",
                "自检结果", "背景示例", "readme", "models", "壁纸", "识图")


def _zl_ziji(lu):
    """这个文件是不是"我自己的" —— 程序本身和它的素材、开关、日志

    【为什么要分两种情况】原来一刀切"在程序目录里就禁删"。自己电脑上没问题
    （程序在 桌面\\小笨蛋 子文件夹里），但**机房演示时程序经常被直接摊在桌面
    根目录**，那时 DIR 就等于桌面，一刀切会把整个桌面全禁掉 —— 演示当场做不了。

    所以：
      · 程序在**子文件夹**里 → 该子文件夹整个禁掉（含 models/壁纸/识图）；
      · 程序就摊在白名单目录里（DIR == 桌面/下载）→ 只按名字保护自己那几个文件，
        同一层别的文件照常可整理。
    """
    try:
        lu = os.path.abspath(lu)
        di = os.path.normcase(os.path.dirname(lu))
        gen = os.path.normcase(os.path.abspath(DIR))
    except Exception:
        return True                      # 看不明白就当自己的，宁可不动
    if di == gen:
        ming = os.path.basename(lu).lower()
        for qian in ZL_ZIJI_MING:
            if ming.startswith(qian.lower()):
                return True
        # 程序目录本身就是桌面/下载 → 同层其它文件不是我的
        for _ming, mu in zl_baimingdan():
            if _zl_zai(gen, mu):
                return False
        return True
    return _zl_zai(lu, DIR)


def zl_weixian(lu, mingque=False):
    """这个路径能不能动 —— 返回 (能不能, 不能的原因)

    所有判断都收在这一处：面板列清单、执行前复查、演示造文件都调它，
    免得"列表里筛过一遍、执行时又漏了"。

    mingque=True 表示"这个文件是用户自己在对话框里点中挑出来的"（指定删除）。
    那种情况下不再要求它必须躺在演示夹里 —— 但仍要过上面那几道：
    快捷方式、程序自己那一摊、系统目录、系统文件，一律照拦。
    """
    try:
        lu = os.path.abspath(lu)
    except Exception:
        return False, "路径看不懂"
    if os.path.islink(lu):
        return False, "快捷方式不动"
    if not os.path.isfile(lu):
        return False, "不是文件"
    # 程序自己那一摊（素材、模型、壁纸、开关、日志）整片禁掉。
    # 必须先于白名单判断：程序常常就装在桌面上，白名单会把整个目录放进来。
    if _zl_ziji(lu):
        return False, "是我自己的文件"
    for xi in ("C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
               "C:\\ProgramData", os.environ.get("SystemRoot") or ""):
        if xi and _zl_zai(lu, xi):
            return False, "系统目录"
    if os.path.basename(lu).lower() in ZL_BU_DONG:
        return False, "系统文件"
    if mingque:
        return True, ""                  # 用户亲手点的，不再要求"必须在演示夹"
    for _ming, mu in zl_baimingdan():
        if _zl_zai(lu, mu):
            return True, ""
    return False, "不在允许的文件夹里"


def zl_lie(mu, leixing="全部"):
    """扫一个文件夹，返回 [{'lu','ming','da','shi'}, ...]，新的排前面"""
    kuo = ()
    for ming, e in ZL_LEIXING:
        if ming == leixing:
            kuo = e
            break
    jieguo = []
    try:
        ming_lie = os.listdir(mu)
    except Exception:
        return jieguo
    for ming in ming_lie:
        lu = os.path.join(mu, ming)
        neng, _li = zl_weixian(lu)          # 顺手把文件夹和快捷方式筛掉
        if not neng:
            continue
        if kuo and os.path.splitext(ming)[1].lower() not in kuo:
            continue
        try:
            st = os.stat(lu)
        except Exception:
            continue
        jieguo.append({"lu": lu, "ming": ming, "da": st.st_size,
                       "shi": st.st_mtime})
    jieguo.sort(key=lambda x: x["shi"], reverse=True)
    return jieguo


def zl_daxiao(n):
    """字节数 → 人话（1.2 MB 这种）"""
    try:
        n = float(n)
    except Exception:
        return "—"
    for dan in ("B", "KB", "MB", "GB"):
        if n < 1024 or dan == "GB":
            return ("%.0f %s" % (n, dan)) if dan == "B" else ("%.1f %s" % (n, dan))
        n /= 1024.0
    return "—"


def _zl_song_huishouzhan(lu):
    """把「一个」文件送进回收站 —— 全程序唯一真正删东西的地方

    用 SHFileOperationW + FOF_ALLOWUNDO（= 走回收站，不是直接抹掉）。
    几个标志的意思：FOF_SILENT / FOF_NOCONFIRMATION 是"别弹系统框"，
    FOF_NOERRORUI 是"出错也别弹"——界面上的提示我们自己说，弹系统框
    会盖住小笨蛋的窗口，看着像程序崩了。

    返回 (成不成, 原因)。一个文件一个文件地送，不打包成一串：批量送的时候
    只要有一个失败，整批的返回值都说不清是谁的错。
    """
    if os.name != "nt":
        return False, "这个功能只在 Windows 上能用"
    try:
        import ctypes
        from ctypes import wintypes

        class _SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND),
                        ("wFunc", wintypes.UINT),
                        ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR),
                        ("fFlags", wintypes.WORD),
                        ("fAnyOperationsAborted", wintypes.BOOL),
                        ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", wintypes.LPCWSTR)]

        FO_DELETE = 3
        FOF_SILENT = 0x0004
        FOF_NOCONFIRMATION = 0x0010
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMMKDIR = 0x0200
        FOF_NOERRORUI = 0x0400

        op = _SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        # pFrom 要求"每个路径以 \0 结尾、整串再来一个 \0"，所以这里补一个
        op.pFrom = lu + "\0"
        op.pTo = None
        op.fFlags = (FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
                     | FOF_NOERRORUI | FOF_NOCONFIRMMKDIR)
        op.fAnyOperationsAborted = False
        op.hNameMappings = None
        op.lpszProgressTitle = None

        fu = ctypes.windll.shell32.SHFileOperationW
        fu.argtypes = [ctypes.POINTER(_SHFILEOPSTRUCTW)]
        fu.restype = ctypes.c_int
        ma = fu(ctypes.byref(op))          # 0 = 成功
        # 【返回码不能当判据】实测踩到：回收站里已经有同名文件时，系统照样把文件
        # 搬走了，却返回 2（看着像"找不到文件"）。所以先看"文件还在不在"这个事实，
        # 返回码只在失败时拿来说明原因。
        if not os.path.exists(lu):
            return True, ""
        if ma != 0:
            return False, "系统没收（错误码 %d）" % ma
        if op.fAnyOperationsAborted:
            return False, "被系统中断了"
        return False, "文件还在原处"
    except Exception as e:
        return False, "调系统接口时出错（%s）" % e


def zl_qidong_hezi(wenjian, ding=None):
    """起一个"看得见过程"的 cmd 子进程去移文件，返回 Popen；起不来返回 None

    【为什么要开窗口】老师要当面演示"删了能恢复"。GUI 里刷几行字不如一个真
    控制台直观：第几个、多大、成没成、最后去哪儿，全打在屏幕上。所以执行动作
    不在主进程里做，而是拉起同程序的子进程（`--整理删除 清单文件`），它在自己
    的窗口里逐个移，主界面只负责等结果。

    ding 是"用户亲手挑的"那批路径（指定删除）。清单里给它们加一个 "D|" 前缀，
    子进程读到就知道这几条不必再满足"必须在演示夹里"。

    CREATE_NEW_CONSOLE（0x10）：不给它一个新控制台，窗口就在当前控制台里跑，
    双击启动（无控制台）时就什么也看不见。
    """
    try:
        # 统一成绝对路径 + 反斜杠：SHFileOperationW 不认 "C:/Users/..." 这种写法，
        # 传进去会直接报错误码 2（找不到文件），而 os.path 拼出来的又多半是混合斜杠
        qin = set()
        for p in (ding or ()):
            try:
                qin.add(os.path.normcase(os.path.abspath(p)))
            except Exception:
                pass
        with open(ZL_QINGDAN, "w", encoding="utf-8") as f:
            for p in wenjian:
                p = os.path.abspath(p)
                qian = "D|" if os.path.normcase(p) in qin else ""
                f.write(qian + p + "\n")
        try:
            os.remove(ZL_JIEGUO)
        except OSError:
            pass
        if getattr(sys, "frozen", False):
            mingling = [sys.executable, "--整理删除", ZL_QINGDAN]
        else:
            mingling = [sys.executable, os.path.abspath(__file__),
                        "--整理删除", ZL_QINGDAN]
        import subprocess
        return subprocess.Popen(mingling, creationflags=0x00000010)
    except Exception:
        return None


def zl_du_jieguo():
    """读子进程写的结果文件：返回 (成功列表, 失败[(路径, 原因)])"""
    hao, huai = [], []
    try:
        with open(ZL_JIEGUO, "r", encoding="utf-8") as f:
            for hang in f:
                bufen = hang.rstrip("\n").split("\t")
                if bufen[0] == "OK" and len(bufen) >= 2:
                    hao.append(bufen[1])
                elif bufen[0] == "ERR" and len(bufen) >= 3:
                    huai.append((bufen[1], bufen[2]))
    except Exception:
        pass
    return hao, huai


def _zl_kai_kongzhi():
    """保证这个子进程有一个"打印得出来"的控制台 —— 窗口化 exe 也能看见过程

    【为什么需要】PyInstaller `--windowed` 打出来的 exe 没有自己的控制台，
    `sys.stdout` 是 None（模块顶部已经塞了个空写入器）。这时就算父进程用
    CREATE_NEW_CONSOLE 给它开了窗口，`print` 也全丢进黑洞，屏幕上一行不冒 ——
    演示"看得见的过程"就废了。

    做法：先确认有控制台窗口（没有就 AllocConsole），再判断现有 stdout 是不是
    真的（假的那个没有 fileno），是假的就把 `CONOUT$` 当 stdout 重新打开。
    `chcp 65001` 是因为新控制台默认是系统代码页，中文按 UTF-8 写才不是乱码。

    返回 True 表示"这次有控制台可以显示"。拿不到也不影响删除，结果照样回传。
    """
    try:
        import ctypes
        k = ctypes.windll.kernel32
        if not k.GetConsoleWindow():
            k.AllocConsole()
        k.SetConsoleTitleW("小笨蛋 · 整理助手（只移回收站）")
    except Exception:
        pass
    try:
        sys.stdout.fileno()                # 已经是真 stdout（命令行启动）
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
        return True
    except Exception:
        pass
    try:
        os.system("chcp 65001>nul")
        liu = open("CONOUT$", "w", buffering=1, encoding="utf-8",
                   errors="replace")
        sys.stdout = liu
        sys.stderr = liu
        return True
    except Exception:
        return False


def _zl_mingling_hang(lu_qingdan):
    """子进程主体：在 cmd 窗口里逐个移文件，全程打印，最后自动打开回收站

    父子进程靠 ZL_JIEGUO 传结果（一行一个 OK/ERR），不靠解析屏幕文字 ——
    屏幕上的东西是给人看的，随时可能被改文案。
    """
    you_kongzhi = _zl_kai_kongzhi()
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("小笨蛋 · 整理助手（只移回收站）")
    except Exception:
        pass
    # 机房/英文系统的控制台代码页可能不是 936：编码错一个字就整个子进程崩掉，
    # 屏幕上看不到任何东西。宁可打成"?"也不能因为一个字符把流程打断。
    for _liu in (sys.stdout, sys.stderr):
        try:
            _liu.reconfigure(errors="replace")
        except Exception:
            pass
    try:
        with open(lu_qingdan, "r", encoding="utf-8") as f:
            hang_lie = [x.strip() for x in f if x.strip()]
    except Exception as e:
        print("读不到清单：%s" % e)
        return 1
    wenjian = []
    qin = set()                       # 用户亲手挑的（"D|" 前缀）
    for x in hang_lie:
        if x.startswith("D|"):
            p = os.path.abspath(x[2:])
            qin.add(os.path.normcase(p))
            wenjian.append(p)
        else:
            wenjian.append(os.path.abspath(x))
    try:
        os.remove(ZL_JIEGUO)
    except OSError:
        pass

    zong = 0
    for lu in wenjian:
        try:
            zong += os.path.getsize(lu)
        except Exception:
            pass
    bian = "=" * 58
    print(bian)
    print("  小笨蛋 · 整理助手")
    print("  只把文件移到回收站，不是直接删除")
    print(bian)
    if wenjian:
        print("文件夹：%s" % os.path.dirname(wenjian[0]))
    print("一共 %d 个文件，合计 %s" % (len(wenjian), zl_daxiao(zong)))
    print("-" * 58)

    hao, huai = [], []
    for i, lu in enumerate(wenjian, 1):
        ming = os.path.basename(lu)
        try:
            da = zl_daxiao(os.path.getsize(lu))
        except Exception:
            da = "—"
        print("[%d/%d] %s  (%s)" % (i, len(wenjian), ming, da))
        neng, li = zl_weixian(lu, os.path.normcase(lu) in qin)
        if not neng:
            print("        × 跳过：%s" % li)
            huai.append((lu, li))
            zl_rizhi("跳过\t%s\t%s" % (lu, li))
            continue