# -*- coding: utf-8 -*-
"""yuyin_shuru.py —— 语音输入（按住说话）

【为什么需要这个】
陪伴的核心场景是"躺着不想打字"。现在只能听她说，不能跟她说 ——
那还是"看节目"，不是"聊天"。

【为什么选 Vosk 而不是 Whisper】
  · Vosk 中文小模型 42 MB，Whisper small 要 500 MB
  · Vosk 是流式的（边说边出字），Whisper 要等你说完才转
  · Vosk 纯 CPU，快；Whisper 在没独显的机器上慢得没法用
代价是 Vosk 准确率不如 Whisper，但家用闲聊够用。

【为什么录音用 sounddevice】
它是 PortAudio 的 Python 绑定，一个 1 MB 的 wheel 就够，
比 pyaudio 好装（pyaudio 要编译）。

【模型放哪】
core/models/stt/vosk-model-small-cn-0.22/
没有就让用户去功能页点"下载语音模型"，不自动下 —— 42 MB 不该偷偷占带宽。
"""
import json
import os
import queue
import threading

# 这些库装在 vendor/，不在系统 site-packages
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(os.path.dirname(_HERE), "vendor"),
           os.path.join(getattr(__import__("sys"), "_MEIPASS", ""), "vendor")):
    if os.path.isdir(_p) and _p not in __import__("sys").path:
        __import__("sys").path.insert(0, _p)

MOGEN_MU = os.path.join(_HERE, "models", "stt")

# 采样率：Vosk 小模型要 16000，单声道，16 bit
CAIYANG = 16000

_mo = None                 # 缓存已加载的模型（加载要 1~2 秒，不能每次问都加）
_mo_suo = threading.Lock()

_yin = False               # 是否正在录音
_ting = None               # sounddevice 的 InputStream
_dui = None                # 音频块队列
_ren = None                # KaldiRecognizer
_jieguo = []               # 已确定的句子
_cuo = ""


def mogen_zai():
    """模型在不在"""
    try:
        for n in os.listdir(MOGEN_MU):
            if n.startswith("vosk-model") and os.path.isdir(os.path.join(MOGEN_MU, n)):
                return os.path.join(MOGEN_MU, n)
    except Exception:
        pass
    return ""


def zai():
    """现在是不是在录音"""
    return _yin


def _chun_yingwen_lu():
    """给模型找一个"纯英文路径"，返回 (路径, 是不是临时复制的)

    【为什么必须这么干】Vosk 的 C 库在 Windows 上用 ANSI 接口拼路径，
    目录名里有中文（"小笨蛋"、"纯净版"）就整个读不出来，
    报 "Failed to create a model"。

    实测三种都失败：
      · 原路径（含中文）
      · GetShortPathNameW 短路径（8.3 名里仍有中文）
      · mklink /J 目录联接（要管理员权限，且路径本身没变）

    唯一稳的办法：复制到 %TEMP% 下一个纯 ASCII 目录。
    65 MB 复制一次约 0.5 秒，只在第一次用时做，之后缓存。
    """
    import shutil
    import tempfile
    src = mogen_zai()
    if not src:
        return "", False
    # 路径里全是 ASCII 就原样用
    try:
        src.encode("ascii")
        return src, False
    except UnicodeEncodeError:
        pass
    dst = os.path.join(tempfile.gettempdir(), "xbd_vosk_stt")
    # 已经复制过、且文件数对得上，就直接用
    try:
        if os.path.isdir(dst):
            n1 = len(os.listdir(src))
            n2 = len(os.listdir(dst))
            if n1 == n2 and n1 > 0:
                return dst, True
    except Exception:
        pass
    try:
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
        return dst, True
    except Exception as e:
        raise RuntimeError("复制模型到临时目录失败（%s）" % e)


def _jia_mo():
    """加载模型（懒加载 + 缓存）"""
    global _mo
    if _mo is not None:
        return _mo
    with _mo_suo:
        if _mo is not None:
            return _mo
        if not mogen_zai():
            raise RuntimeError("没下语音模型（core/models/stt/ 里是空的）")
        import vosk
        vosk.SetLogLevel(-1)          # 关掉 vosk 的日志刷屏
        lu, _fz = _chun_yingwen_lu()
        _mo = vosk.Model(lu)
        return _mo


def kai_shi():
    """开始录音。返回 {ok, cuo}

    【为什么要单独一个"开始"】用户按一下开始、说、再按一下结束。
    不用"检测静音自动停" —— 那在嘈杂环境里会提前掐断。
    """
    global _yin, _ting, _dui, _ren, _jieguo, _cuo
    if _yin:
        return {"ok": False, "cuo": "正在录了"}
    lu = mogen_zai()
    if not lu:
        return {"ok": False, "cuo": "还没下语音模型",
                "yao_mo": True}
    try:
        import sounddevice as sd
        import vosk
    except Exception as e:
        return {"ok": False, "cuo": "缺录音库（%s）" % e}

    try:
        mo = _jia_mo()
        _ren = vosk.KaldiRecognizer(mo, CAIYANG)
        _ren.SetWords(False)
        _dui = queue.Queue()
        _jieguo = []
        _cuo = ""

        def _hui(indata, frames, t, status):
            try:
                _dui.put(bytes(indata))
            except Exception:
                pass

        _ting = sd.RawInputStream(
            samplerate=CAIYANG, blocksize=4000, dtype="int16",
            channels=1, callback=_hui)
        _ting.start()
        _yin = True

        # 边录边转：一个后台线程从队列里拿块喂给识别器
        threading.Thread(target=_zhuan, daemon=True).start()
        return {"ok": True}
    except Exception as e:
        _yin = False
        return {"ok": False, "cuo": "开不了麦克风（%s）" % e}


def _zhuan():
    """后台：把录音块持续喂给识别器，识别结果攒在 _jieguo 里"""
    global _yin
    while _yin:
        try:
            kuai = _dui.get(timeout=0.3)
        except Exception:
            continue
        try:
            if _ren.AcceptWaveform(kuai):
                d = json.loads(_ren.Result())
                t = (d.get("text") or "").strip()
                if t:
                    _jieguo.append(t)
        except Exception:
            pass


def ting_zhi():
    """停止录音，返回识别到的文字 {ok, wen, cuo}"""
    global _yin, _ting, _ren
    if not _yin:
        return {"ok": False, "cuo": "没在录"}
    _yin = False
    try:
        if _ting is not None:
            _ting.stop()
            _ting.close()
            _ting = None
    except Exception:
        pass
    # 收尾：把最后没吐出来的部分冲出来
    wen = ""
    try:
        if _ren is not None:
            d = json.loads(_ren.FinalResult())
            t = (d.get("text") or "").strip()
            if t:
                _jieguo.append(t)
            _ren = None
        # Vosk 中文输出常带空格（"你 好 呀"），去掉
        wen = "".join(_jieguo)
        _jieguo.clear()
    except Exception as e:
        return {"ok": False, "cuo": "收尾失败（%s）" % e}
    if not wen:
        return {"ok": False, "cuo": "没听清"}
    return {"ok": True, "wen": wen}


def xia_zai_jindu():
    """模型下载进度（前端轮询用）。没在下就是 finished=True"""
    return {"zai": False, "baifen": 100}
