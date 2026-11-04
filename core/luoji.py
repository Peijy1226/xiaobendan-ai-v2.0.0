# -*- coding: utf-8 -*-
"""luoji.py —— 小笨蛋的逻辑层（从作业版整段搬过来，一个字节没改）

来源：旧版 xiaobendan-open/小笨蛋.py（21,255 行）
      第 1-5539 行 + 第 19840-21255 行
由 测试文件/10_抽取逻辑层.py 自动生成。不要手改这个文件 ——
要改就改作业版再重跑脚本，否则下次重跑会覆盖。

搬了什么：
  · 读语料 -> 倒排索引 -> 二字模型 -> generate
  · 七个工具：报时 / 算数 / 笑话 / 天气 / 美食 / 王者
  · 对话路由 shuohua / shuohua_jilu（含危机句硬拦截、闲聊层、追问层）
  · 情绪引擎 Qingxu（好感度 / 七种脸色 / 恋人模式 / 礼物）
  · 表情挑选 bq_xuan
  · 存档 du_cundang / xie_cundang
  · 头像 tou_lu / tou_tu
  · 灵光联网 du_api_peizhi / diaoyong_llm / 真实天气 tianqi_chaxun

没搬：
  · tkinter 界面（新版用 HTML + CSS 重写）
  · 整理助手（要 cmd 窗口，第三阶段）
  · 识图（要 opencv/rapidocr，第三阶段）
  · 语音 edge-tts（第四阶段）
"""
import os
import sys

# 素材目录：默认取本文件的上两级（core/ -> 纯净版/）。
# 调用方 import 之后可以改 DIR（比如打包后指到 exe 目录）。
DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# 小笨蛋 1.0　作者：Pei
# ------------------------------------------------------------------------------
# 一个会聊天的小程序：聊天、报时、天气、笑话、美食、王者、算数、识图，共八件事，
# 入口都收在右上角的「☰ 功能」里。
#
#   · 从哪来   —— 从一个最小的大模型程序长出来的（看着上文猜下一个字），
#                 素材是放在同目录的几份 txt。
#   · 会看脸色 —— 情绪引擎：好感度、五颗心、委屈/得意/关心，满 100 转恋人语气。
#   · 会看图   —— 识图窗口提取文字、给人和东西画框（需 opencv/rapidocr/pillow）。
#   · 会装扮   —— 聊天背景可换图片、GIF、视频，还能调透明度。
#
# 1.0 相比上一版：
#   ① 说话不再"露馅"（不提素材、不提训练），像正常人在聊
#   ② 聊天气泡改成猫形（橘猫是你，灰猫是我），左右分列
#   ③ 窗口整体不再透明；背景本身可调透明度，并支持 GIF / 视频
#   ④ 叫到工具时气泡上方写"正在调用算数…"，纯聊天时什么都不写
#   ⑤ 好感度换成五颗心，点满放彩蛋，之后话术转暧昧
#   ⑥ 六个功能入口全搬到顶栏并可折叠（按钮「☰ 功能」，快捷键 F3）
#   ⑦ 名字统一叫「小笨蛋1.0」
#
# 第二轮（本次）改动：
#   ① 五颗心改成"从 1 颗起步、100 才满 5 颗"（原来 55 分就亮三颗）
#   ② 「清空聊天」加确认弹窗，默认焦点在「取消」上
#   ③ 识图：识别阈值调低（补回漏掉的 89）、结果按阅读顺序排、
#      把被认成雨伞的领带纠回来、新增【穿搭】描述、大图先缩再检测
#   ④ 去掉对话区右侧滚动条（滚轮照旧可用）
#   ⑤ 功能「背景」改名「壁纸」；视频壁纸改成后台解码 + 原速播放
#   ⑥ 视频帧在后台缩放（界面每帧只贴图），拖动窗口期间不贴新帧
#   ⑦ 视频壁纸下玻璃按钮改成轮播刷新（原来会一直挂着上一张壁纸的磨砂）
#   ⑧ 联网（第三轮）：顶栏「小笨蛋」右边多了个联网开关，开着走 DeepSeek
#      V4.1-Flash，关着完全回到原来的规则引擎；天气联网时改用实时数据。
#      配置在「API.txt」（中文键名：钥匙/模型/地址…），代码在第十部分。
#   ⑨ 整理助手（本次）：只扫演示夹；别的文件用「指定删除」自己挑。只移到回收站，
#      默认关着，单次最多 10 个 / 200 MB；执行时开一个 cmd 窗口显示过程，
#      删完自动打开回收站。代码在第十一部分。
#
# 运行：双击本文件即可。纯标准库；识图要 opencv / rapidocr / pillow。
# ------------------------------------------------------------------------------

import os                                       # 找到本程序所在的文件夹
import re                                       # 正则：从一句话里“抠”出算式
import ast                                      # 把算式字符串解析成语法树（安全计算的关键）
import math                                     # 数学常数和函数：pi、sqrt、factorial……
import operator                                 # 把“+ - * /”这些符号映射成真正的运算
import random                                   # generate 抽签用
import sys                                      # 判断平台（爱心字体查字形要用）
import shutil                                   # 复制模型到纯英文目录
import threading                                # 视频壁纸后台解码、识图子线程
import time                                     # 视频按原速排帧（perf_counter）
import datetime                                 # 看时钟：今天几号、现在几点、星期几
from collections import defaultdict, Counter, deque  # 计票本 + 会话窗口
import difflib                                  # 判两句像不像（检索去重）


# 打包成"无控制台"的 exe 后 sys.stdout 是 None，任何 print 都会抛
# AttributeError（Try 里 print 也一样）。这里塞一个什么都不做的替身。
if sys.stdout is None or sys.stderr is None:
    class _KongShuChu(object):
        def write(self, *_a):
            return 0

        def flush(self):
            pass

        def isatty(self):
            return False
    if sys.stdout is None:
        sys.stdout = _KongShuChu()
    if sys.stderr is None:
        sys.stderr = _KongShuChu()


# ══════════════════════════════════════════════════════════════════════════════
# 第一部分：读素材、建模型、定义 generate（与第 1 步完全一样，原样复用）
# 这部分是智能体的“大脑”：先训练（建表），后生成（接话）
# ══════════════════════════════════════════════════════════════════════════════

# 【打包成 exe 之后】__file__ 指向的是解包目录（_internal），而素材/模型是放在
# exe 旁边的，所以冻结运行时要按 exe 所在目录找；直接跑 .py 时行为完全不变。
# 【抽取时改过这一行】旧版按 __file__ 算，搬进 core/ 后 __file__
# 变成 core/ 目录就错了。改成读环境变量，由 api.py 在 import
# 之前设好 XBD_DIR（开发时=纯净版/，打包后=exe 目录）。
DIR = os.environ.get("XBD_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
# 素材统一放在「素材/」里。老版本是把 素材*.txt 散在程序根目录的，
# 升级过来的用户不会自动搬家，所以两处都扫，子目录优先、同名去重。
SUCAI_MU = os.path.join(DIR, "素材")


def su_cai_lu(ming):
    """素材文件的实际路径：先找 素材/，找不到退回根目录（兼容老版本）"""
    for mu in (SUCAI_MU, DIR):
        lu = os.path.join(mu, ming)
        if os.path.exists(lu):
            return lu
    return os.path.join(SUCAI_MU, ming)


quanbu = []
for _mu in (SUCAI_MU, DIR):
    try:
        for _n in sorted(os.listdir(_mu)):
            if _n.startswith("素材") and _n.endswith(".txt") and _n not in quanbu:
                quanbu.append(_n)
    except Exception:
        pass

# ── 表情包 ──────────────────────────────────────────────────────────
# 两个池子：
#   表情/离线/  —— 联网关掉时只从这里拿（安静、克制，跟人设一致）
#   表情/灵光/  —— 只有开了灵光才允许拿（可以放网络流行表情）
# 灵光池为空时自动退回离线池，不会出现"开了灵光反而没表情"。
BIAOQING_MU = os.path.join(DIR, "表情")
BQ_LIXIAN = os.path.join(BIAOQING_MU, "离线")
BQ_LINGGUANG = os.path.join(BIAOQING_MU, "灵光")
BQ_GAO = 148                       # 屏幕上显示的高度（宽按比例）
BQ_ZUI_KUAN = 300                  # 宽度上限，别把气泡列撑歪
BQ_TU_GE = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
BQ_QINGXU = ("平静", "开心", "兴奋", "得意", "委屈", "困惑", "关心", "恋人")
# 情绪对得上时，仍有这个概率去整池随机 —— 给"招手/晚安/比心"这类
# 场景表情一个出场机会（它们文件名里没有情绪词，按情绪筛永远轮不到）
BQ_SUIJI = 0.35
# 最近用过的几张，挑的时候先避开：同一张图连着出现两次，一眼就露馅
BQ_BU_CHONGFU = 5
_BQ_ZUIJIN = []


def bq_lie(mu):
    """列出一个池子里的所有表情图（文件名排序，稳定）"""
    try:
        return sorted(os.path.join(mu, n) for n in os.listdir(mu)
                      if n.lower().endswith(BQ_TU_GE))
    except Exception:
        return []


def bq_zhunbei():
    """只保证两个池子的目录在，**不再自己画表情**

    第一版到第三十三轮这里是"池子空着就现画 8 张米白猫脸"—— 开箱能看，
    但用户第三十四轮明确要换：自绘的太像图标，不像聊天用的表情包。
    现在素材由 `表情/离线/`（随程序附带的一套表情图）和用户自己放进
    `表情/灵光/` 的图提供；这里只负责建目录，不再生成任何图。

    保留函数名是因为 `bq_xuan()` 里还调它 —— 目录不在的话，
    后面 os.listdir 会一直抛异常，表情就永远出不来。
    """
    try:
        os.makedirs(BQ_LIXIAN, exist_ok=True)
        os.makedirs(BQ_LINGGUANG, exist_ok=True)
    except Exception:
        return False
    # 顺便把"怎么放图"的说明补上（用户可能把说明删了）
    shuo = os.path.join(BIAOQING_MU, "说明.txt")
    try:
        if not os.path.exists(shuo):
            with open(shuo, "w", encoding="utf-8") as f:
                f.write("表情包放这里，分两个池子：\n\n"
                        "离线/  —— 灵光关掉时只从这里拿\n"
                        "灵光/  —— 只有开了灵光才用；空着就退回 离线/\n\n"
                        "文件名带情绪词就能对上号：开心_1.png / 委屈2.jpg\n"
                        "情绪词：平静 开心 兴奋 得意 委屈 困惑 关心 恋人\n"
                        "格式：png / jpg / jpeg / gif / webp / bmp，高 200~600px\n")
    except Exception:
        pass
    return False


# ── 对话文本：压成一段 ───────────────────────────────────────────────
def he_bing_hang(wenben):
    """把一条回复里的换行吃掉，压成"一整段"，只让气泡自己按像素折行

    【为什么要这个】第三十四轮用户的原话：
        「正文和旁白就在一行……好多行看着就不像和真人聊天」，
        「不要现在这样，一个字换一行」。

    实际是两件事叠在一起：
      ① 模型（灵光）和不少人设文案会自己在句子之间塞 \\n —— 每句一行，
         看着像写诗、像文档，不像聊天；
      ② 更糟的时候它逐字换行，屏幕上就是一列单字。
    两者都不是"排版"，是文本里真的带着换行符。

    所以显示之前统一压平：气泡的宽度是 520px，正常一句话会自动折行 ——
    那才是聊天窗口该有的样子。想留"一屏放不下"的长文，交给折行就行，
    不用手动分。

    拼接规则（既要连成话，又不能把清单挤成一坨）：
      · 上一行以标点收尾 / 本行以括号旁白开头 / 有一边是极短碎片 → 直接接上
        （覆盖"逐字换行""旁白另起一行"这两种）；
      · 其余（像"今天 小雨 12~20℃""明天 中雨…"这种一行一条的清单）→ 中间补一个
        逗号，念出来也顺。
    """
    if wenben is None:
        return ""
    s = str(wenben).replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\t", " ").replace("\u3000", " ")
    if "\n" not in s:
        return re.sub(r" {2,}", " ", s).strip()
    hang = []
    for seg in s.split("\n"):
        seg = re.sub(r" {2,}", " ", seg).strip()
        if seg:
            hang.append(seg)
    if not hang:
        return ""
    out = hang[0]
    for seg in hang[1:]:
        qian = out[-1] if out else ""
        if (qian in "。！？…～!?，、；：,;:）)」』”\"'") or seg[0] in "（(「『“‘" \
                or len(out) <= 3 or len(seg) <= 3:
            out += seg
        else:
            out += "，" + seg
    return out


# ── 语音播报 ────────────────────────────────────────────────────────
# 用 edge-tts（微软 Edge 朗读引擎）：音色接近真人，中文有晓伊/晓晓可选。
# 播放走 Windows 自带 MCI（winmm），零依赖，不需要装 playsound/pydub。
#
# 三条设计原则：
#   ① 括号里的动作一律不读 —— 正常对话没人会把"把脸埋进兜帽里"念出来；
#   ② 断句处按标点补停顿，不然短句会紧贴着念，听着像机器；
#   ③ 断网就安安静静地不出声，绝不弹框报错。
TTS_YIN = "zh-CN-XiaoyiNeural"       # 晓伊：年轻、偏软，贴人设
TTS_SUDU = "-12%"                    # 语速慢 12%，说话更温柔
TTS_YINLIANG = "+0%"
TTS_YINCHANG = "+0Hz"
TTS_HUANCUN = os.path.join(DIR, "语音缓存")
TTS_KAIWEN = os.path.join(DIR, "语音开关.txt")
TTS_CHAOGUO = 180                    # 单句超过这么多字就截断（别念一整篇）
_tts_shu = [0]                       # 当前播放的 MCI 别名序号

# 情绪 → (语速偏移, 音调偏移)。
# 【为什么要有这张表】同一副嗓子把所有话说成一个调，听着就是朗读器。
# 高兴的时候快一点、高一点，委屈的时候慢下来、压低声，才有"语气语调"。
# 数值都压得很小（3~7Hz / 几个百分点）：过了就成演戏，一听就假。
TTS_QINGXU = {
    "平静": ("-12%", "+0Hz"),
    "关心": ("-16%", "-3Hz"),
    "开心": ("-6%", "+4Hz"),
    "兴奋": ("+2%", "+7Hz"),
    "得意": ("-8%", "+5Hz"),
    "委屈": ("-20%", "-6Hz"),
    "困惑": ("-10%", "+2Hz"),
}
TTS_DUAN_ZUI_CHANG = 30              # 一段最多这么多字，超了就在逗号处再切
TTS_DUAN_ZUI_DUO = 5                 # 一条回复最多切这么多段
# 【第四十二轮·别念太长】用户的原话："小笨蛋生成的太多，语音播报下载下来更慢了，
# 我问新问题时上一轮的答案还在播。"
# 天气那种一条七天的答案有两百多字，分成 5 段、每段还要跟服务器握一次手，
# 光合成就要十几秒；再加上第五段把剩下的全并进去，那一整段能念四十秒。
# 所以给"要念出来的字"加一道总长上限：超了只在开头念一部分。
# 为什么是 100：30 字一段的话正好 4 段，第一声 1 秒内能出来，整条一分钟内能念完。
TTS_ZUI_CHANG = 100
# 为什么段数不放开：每段都要单独跟服务器握手（实测光握手就 1.1 秒），
# 段越多总耗时越长。切段的目的只是"让第一声尽快出来"，不是把话拆碎。
# 【第三十二轮回退】上一轮为了"首声更快"把段数压到 3、首段硬切到 12 字、
# 还加了流式切块 —— 结果断句变得很怪（一句话被切在词中间）。现在退回按标点
# 切、最多 5 段的版本：宁可首声晚半秒，也别把话说碎。

# 开场白。写成常量是因为它要出现两次（画气泡、播报），
# 两处各写一遍的话，改了文案只改一处就会对不上。
TTS_KAI_CHANG = "（拉了拉深色的兜帽，脸颊微红）你来了……小笨蛋今天也在这里等你哦。"


def tts_qingli(wenben):
    """把一条气泡文字处理成"该念出来的话"

    去掉的东西：
      · 括号里的动作/神态 —— （把脸埋进兜帽里）（轻声）（脸颊微红）
      · 颜文字 —— （-__-）（＾▽＾）
      · markdown 符号、多余空白、连续的标点
    保留：文字、句号问号感叹号逗号（逗号留一个，读起来有呼吸感）
    """
    if not wenben:
        return ""
    t = str(wenben)
    # 中文括号、英文括号、方括号、书名号里的说明，全去掉（书名号保留内容）
    t = re.sub(r"（[^（）]*）", "", t)
    t = re.sub(r"\([^()]*\)", "", t)
    t = re.sub(r"\[[^\[\]]*\]", "", t)
    t = re.sub(r"【[^【】]*】", "", t)
    # 颜文字残渣：单独成段的符号串
    t = re.sub(r"[\^\-~_=+*<>/\\|·ω∀皿﹏]{2,}", "", t)
    # 图标类字符
    for ch in "♥♡★☆♪♫→←↑↓•◆◇■□●○":
        t = t.replace(ch, "")
    # 连续标点压成一个，避免"……。"念成三个停顿
    t = re.sub(r"[。]{2,}", "。", t)
    t = re.sub(r"[，,]{2,}", "，", t)
    t = re.sub(r"[！!]{2,}", "！", t)
    t = re.sub(r"[？?]{2,}", "？", t)
    t = re.sub(r"\s+", " ", t).strip()
    # 头尾的停顿符号削掉（念出来没意义）："……你来了" → "你来了"
    # 【本轮改】句号/问号/感叹号**留着** —— 它们不是装饰，edge-tts 靠它们
    # 定语调：留着问号才会上扬，留着感叹号才会重一点。全削了就成了平铺直叙。
    t = t.strip(" ，、；：…·")
    # 剩下全是标点（"。。"、""）就当没内容 —— 现在句末标点留着了，
    # 不判这一下会把一串标点送去合成，白等一次网络
    if not any(ch.isalnum() or "\u4e00" <= ch <= "\u9fa5" for ch in t):
        return ""
    if len(t) > TTS_CHAOGUO:
        # 从中间截断不好听，找最近的句号
        qie = t[:TTS_CHAOGUO]
        for biao in ("。", "！", "？", "；"):
            i = qie.rfind(biao)
            if i > TTS_CHAOGUO // 2:
                qie = qie[:i + 1]
                break
        t = qie
    return t


def tts_yuanwen(wenben):
    """给 edge-tts 的最终文本（已清洗）

    【为什么不用 SSML 的 <break>】实测 edge-tts 会先 `escape()` 整段文本再
    拼 SSML，`<break time='350ms'/>` 被转义成字面字符 —— 引擎把它当文字念了
    出来（同一句话从 3.2 秒变成 5.9 秒，多出来的就是"break time 350ms"）。
    所以靠 SSML 加停顿这条路在这个库里走不通。

    实测标点本身的停顿：句号 3216ms / 逗号 2904ms / 省略号 2952ms ——
    句号已经是最长的了，再堆标点反而更短（双逗号 2904ms）。所以这里只做
    清洗，停顿交给标点自己。
    """
    return tts_qingli(wenben)


def tts_qieduan(wenben):
    """把一条回复切成"能一段一段念"的小块

    【为什么要切】原来是把整段话交给 edge-tts 的 `c.save()`，它要等整段音频
    全部下载完才返回；一句 60 字的回复光合成就要 3 秒多，用户说"要等 4 秒"。
    切成小段之后，**第一段合成好就开念**，后面的段在"念上一段"的同时排队合成，
    听到第一声的时间只剩 0.6~1.2 秒。

    切法：先按句末标点切；一段超过 30 字的再按逗号切；还超就硬切。
    段数超过 5 段时把剩下的并到最后一段。
    【为什么不再压第一段】试过把首段硬切到 12 字，断句立刻变怪（切在词中间），
    用户原话"断句很奇怪"。所以首段也按标点走，宁可多等半秒。

    【第四十二轮·总长截到 TTS_ZUI_CHANG】天气那种两百多字的答案，切 5 段
    每段都跟服务器握一次手，合成要十几秒；念起来要一分钟，用户问下一句时
    上一句还在响。现在超长的只在**句号处**截到 100 字左右，末尾补一句
    "（详情看屏幕）"—— 念的是摘要，屏上是全文。
    """
    t = tts_qingli(wenben)
    if not t:
        return []
    # 先按总长截一次：只在句末标点处切，不把一句话劈成两半
    if len(t) > TTS_ZUI_CHANG:
        tou = t[:TTS_ZUI_CHANG]
        i = max(tou.rfind("。"), tou.rfind("！"), tou.rfind("？"),
                tou.rfind("；"), tou.rfind("."), tou.rfind("!"), tou.rfind("?"))
        if i >= 20:                     # 至少留下二十来字，别只剩半句
            tou = tou[:i + 1]
        t = tou + "剩下的你看屏幕吧。"
    # 先粗切成句子（保留标点，念的时候那点停顿还靠它们）
    ju = [x for x in re.split(r"(?<=[。！？；!?;])", t) if x.strip()]
    duan = []
    for x in ju:
        x = x.strip()
        while len(x) > TTS_DUAN_ZUI_CHANG:
            # 在 30 字以内找一个逗号断开，找不到就硬切
            qie = x[:TTS_DUAN_ZUI_CHANG]
            i = max(qie.rfind("，"), qie.rfind(","), qie.rfind("、"))
            if i < 6:
                i = TTS_DUAN_ZUI_CHANG - 1
            duan.append(x[:i + 1].strip())
            x = x[i + 1:].strip()
        if x:
            duan.append(x)
    # 纯标点的碎片（比如硬切之后剩下的一个"。"）并回上一段：
    # 直接丢掉的话，前一句就少了句末标点，语气会变平
    chun = []
    for d in duan:
        if tts_qingli(d):
            chun.append(d)
        elif chun and any(ch in "。！？；!?;" for ch in d):
            chun[-1] = chun[-1] + d
    duan = chun
    if len(duan) > TTS_DUAN_ZUI_DUO:
        duan = duan[:TTS_DUAN_ZUI_DUO - 1] + ["".join(duan[TTS_DUAN_ZUI_DUO - 1:])]
    return duan


def tts_lujing(wenben, sudu=None, yinchang=None):
    """同一句话只合成一次：按文本哈希存 mp3，第二次直接播本地文件

    语速/音调也算进哈希 —— 同一句话在"开心"和"委屈"两种情绪下是两条音频，
    只按文本存会串味。
    """
    import hashlib
    t = tts_qingli(wenben)
    if not t:
        return None, ""
    sudu = sudu or TTS_SUDU
    yinchang = yinchang or TTS_YINCHANG
    try:
        os.makedirs(TTS_HUANCUN, exist_ok=True)
    except Exception:
        pass
    hao = hashlib.md5(("%s|%s|%s|%s" % (TTS_YIN, sudu, yinchang, t))
                      .encode("utf-8")).hexdigest()[:20]
    return os.path.join(TTS_HUANCUN, hao + ".mp3"), t


def tts_hecheng(wenben, chaoshi=20, qingxu=None):
    """合成一段语音，返回 mp3 路径（失败返回 None, 原因）

    qingxu 传进来就按 TTS_QINGXU 调语速和音调；不传用默认那副嗓子。
    edge-tts 是 async 接口，这里用 asyncio.run 收成一个同步函数，
    调用方在后台线程里跑，不阻塞界面。
    """
    sudu, yinchang = TTS_QINGXU.get(qingxu or "", (TTS_SUDU, TTS_YINCHANG))
    lu, t = tts_lujing(wenben, sudu, yinchang)
    if not lu:
        return None, "没有可念的内容"
    if os.path.exists(lu) and os.path.getsize(lu) > 512:
        return lu, ""
    ban = lu + ".part"               # 先写 .part 再改名：中途断了不会留下半截"缓存"
    try:
        import asyncio
        import edge_tts
    except Exception as e:
        return None, "没装 edge-tts（%s）" % e

    async def _zuo():
        c = edge_tts.Communicate(t, TTS_YIN, rate=sudu,
                                 volume=TTS_YINLIANG, pitch=yinchang)
        await c.save(ban)

    try:
        # Python 3.14 里没有运行中的事件循环，asyncio.run 安全
        asyncio.run(_zuo())
    except Exception as e:
        try:
            os.remove(ban)
        except OSError:
            pass
        return None, "合成失败（%s）" % e
    try:
        if os.path.getsize(ban) > 512:
            os.replace(ban, lu)
        else:
            os.remove(ban)
            return None, "合成的文件是空的"
    except Exception as e:
        return None, "落盘失败（%s）" % e
    return lu, ""


def tts_bofang(lu):
    """用 Windows 自带 MCI 播 mp3，返回 (别名, 原因)

    为什么不用 winsound：它只认 wav，mp3 直接播是没声音的（而且不报错）。
    MCI 的 mpegvideo 驱动系统自带，零依赖就能放 mp3。
    """
    if not lu or not os.path.exists(lu):
        return None, "文件不在"
    try:
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        _tts_shu[0] += 1
        bie = "xbpy%d" % _tts_shu[0]
        buf = ctypes.create_unicode_buffer(256)

        def cmd(c):
            try:
                r = mci(c, buf, 255, None)
                return r, buf.value
            except Exception:
                return -1, ""

        # 先关掉同名的（上一轮没清干净时）
        cmd('close %s' % bie)
        r, _ = cmd('open "%s" type mpegvideo alias %s' % (lu, bie))
        if r != 0:
            return None, "MCI 打不开（错误码 %d）" % r
        r, _ = cmd('play %s' % bie)
        if r != 0:
            cmd('close %s' % bie)
            return None, "MCI 播不了（错误码 %d）" % r
        return bie, ""
    except Exception as e:
        return None, "播放异常（%s）" % e


def tts_ting(bie):
    """停掉一段正在播的语音"""
    if not bie:
        return
    try:
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        buf = ctypes.create_unicode_buffer(64)
        mci('stop %s' % bie, buf, 63, None)
        mci('close %s' % bie, buf, 63, None)
    except Exception:
        pass


def tts_zhuangtai(bie):
    """MCI 那段音频现在是什么状态：playing / stopped / paused / ""（读不到）"""
    if not bie:
        return ""
    try:
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        buf = ctypes.create_unicode_buffer(64)
        r = mci('status %s mode' % bie, buf, 63, None)
        if r != 0:
            return ""
        return buf.value.strip().lower()
    except Exception:
        return ""


def tts_deng(bie, chaoshi=40):
    """等这段音频念完（被打断/被关掉也会立刻返回）

    分段播放要靠它：上一段念完才接下一段，不然几段音频会叠在一起。
    只在这个播放线程里等，界面线程一点都不碰。
    """
    if not bie:
        return
    jiezhi = time.time() + chaoshi
    time.sleep(0.1)                       # 刚 play 时状态可能还没切过去
    while time.time() < jiezhi:
        if tts_zhuangtai(bie) != "playing":
            return
        time.sleep(0.12)


def tts_du_kai():
    """语音开关的落盘状态：默认关（不想一开程序就吵）"""
    try:
        with open(TTS_KAIWEN, "r", encoding="utf-8") as f:
            for hang in f:
                if hang.strip().startswith("开启"):
                    return hang.split("=", 1)[-1].strip() in ("1", "是", "开", "on")
    except Exception:
        pass
    return False


def tts_xie_kai(kai):
    try:
        with open(TTS_KAIWEN, "w", encoding="utf-8") as f:
            f.write("# 语音播报开关：1 = 开，0 = 关\n开启=%d\n" % (1 if kai else 0))
    except Exception:
        pass


# ── 场景 → 该用哪几张 ────────────────────────────────────────────
# 情绪只说明"她什么脸色"，说明不了"现在是什么场合"：同样是开心，
# 开场的招手、被夸的害羞、道谢的比心，是三种完全不同的图。
# 所以除了情绪，再按场景挑一层 —— 先认场景，认不出才退回按情绪挑。
#
# 表里写的是"文件名主干"：写 "关心" 会同时命中 关心.png 和 关心_2.png。
BQ_CHANGJING = {
    "hi":       ("招手", "开心"),                       # 打招呼 / 我回来了
    "bye":      ("拜拜", "晚安"),                       # 晚安 / 走了 / 下次聊
    "comfort":  ("关心", "关心_2"),                      # 他说累、难受、想哭
    "praise":   ("害羞", "害羞_2", "害羞_3"),            # 夸她可爱 / 好看
    "laugh":    ("偷笑", "开心", "开心_2"),              # 哈哈 / 笑死
    "sad":      ("委屈", "委屈_2", "大哭"),              # 她委屈 / 被冷落
    "angry":    ("生气", "无语"),                        # 她生气 / 无语
    "thanks":   ("比心", "开心_2"),                      # 道谢
    "surprise": ("惊讶", "兴奋"),                        # 居然 / 真的吗
    "ask":      ("困惑", "发呆"),                        # 追问 / 听不懂
    "love":     ("恋人", "恋人_2", "撒娇", "比心"),       # 恋人之间黏糊
}

# 场景关键词。顺序就是优先级：先说"晚安"再提到"累"，算告别不算安慰。
# 注意"你好可爱"这种句子里带"你好"，但它是夸人不是打招呼 ——
# 所以 praise/thanks/laugh 都排在 hi 前面，hi 放最后。
BQ_CHANGJING_CI = (
    ("bye",      ("晚安", "睡了", "我先去", "再见", "拜拜", "下线", "走了", "下次聊", "不聊了")),
    ("comfort",  ("好累", "累了", "难受", "难过", "不开心", "想哭", "崩溃", "烦死",
                  "加班", "压力", "睡不着", "生病", "感冒")),
    ("praise",   ("可爱", "好看", "漂亮", "喜欢你", "真棒", "厉害", "温柔", "萌")),
    ("thanks",   ("谢谢", "感谢", "谢了", "麻烦你了")),
    ("laugh",    ("哈哈", "笑死", "搞笑", "好笑", "逗死", "什么梗")),
    ("angry",    ("生气", "讨厌", "过分", "烦人", "气死")),
    ("surprise", ("居然", "真的吗", "太好了", "没想到", "天啊", "竟然")),
    ("ask",      ("为什么", "怎么会", "什么意思", "不懂", "啥意思")),
    ("hi",       ("你好", "在吗", "在不在", "早上好", "早呀", "我回来了", "好久不见")),
)

# 认不出场合时，允许"随手撒一张"的通用款（不带明确场景含义的才放这儿）
BQ_TONG_YONG = ("害羞", "偷笑", "比心", "得意", "发呆", "惊讶", "兴奋")

# 恋人之间才用的黏糊词（好感没满时说了也只是普通关心，不切"love"场景）
BQ_LIANREN_CI = ("想你", "抱抱", "抱一下", "亲", "喜欢你", "别走", "一起睡",
                 "陪我", "在不在我身边")


def bq_changjing(wenti, lianren=False):
    """从用户那句话里认"现在是什么场合"，认不出返回空串

    只认得出十来种常见场合，认不出就交给情绪那套 ——
    宁可退回"按脸色挑"，也别硬猜，猜错了比没有更糟。
    """
    s = str(wenti or "").strip()
    if not s:
        return ""
    if lianren and any(k in s for k in BQ_LIANREN_CI):
        return "love"
    for ming, ci in BQ_CHANGJING_CI:
        if any(k in s for k in ci):
            return ming
    return ""


def _bq_an_ming(lie, mingzi):
    """按文件名主干筛：写"关心"能同时拿到 关心.png / 关心_2.png"""
    out = []
    for p in lie:
        b = os.path.basename(p)
        b = b.rsplit(".", 1)[0]
        for m in mingzi:
            if b == m or b.startswith(m + "_"):
                out.append(p)
                break
    return out


def _bq_tiao(houxuan):
    """从候选里挑一张，避开最近用过的（避不开就放开）

    为什么需要：抽签是独立的，连着两句抽到同一张完全可能 —— 用户会觉得
    "就这一张图？"。记住最近 5 张，先在候选里排除它们再抽。
    候选本身就少（比如"平静"只有 3 张）时，排除完可能一张不剩 ——
    那就挑"最久没用过"的那张，而不是纯随机（纯随机可能上一张刚用过又抽到它）。
    """
    if not houxuan:
        return None
    sheng = [p for p in houxuan if p not in _BQ_ZUIJIN]
    if sheng:
        p = random.choice(sheng)
    else:
        def _jiu(x):
            try:
                return _BQ_ZUIJIN[::-1].index(x)   # 数字越大 = 越久没出现
            except ValueError:
                return 99
        p = max(houxuan, key=_jiu)
    _BQ_ZUIJIN.append(p)
    if len(_BQ_ZUIJIN) > BQ_BU_CHONGFU:
        del _BQ_ZUIJIN[:-BQ_BU_CHONGFU]
    return p


def bq_xuan(qingxu, lianren=False, lingguang=False, changjing=""):
    """挑一张表情：先看场合，再看脸色

    顺序（重要）：
      ① 场合（changjing）对得上就先按场合挑 —— 说"晚安"就该是拜拜/晚安，
         不能因为当下心情是"开心"就贴一张大笑；
      ② 认不出场合，退回按情绪挑；同一个情绪有多张（开心 / 开心_2）时轮流用；
      ③ 都没有就整池随机，绝不返回空。

    池子按模式分：灵光开着先用 表情/灵光，空了退回离线；灵光关着只用离线。
    """
    bq_zhunbei()
    mu = BQ_LIXIAN
    if lingguang:
        if bq_lie(BQ_LINGGUANG):
            mu = BQ_LINGGUANG
    lie = bq_lie(mu)
    if not lie:
        return None

    # ① 场合优先
    if changjing:
        ming = BQ_CHANGJING.get(changjing)
        if ming:
            an_chang = _bq_an_ming(lie, ming)
            if an_chang:
                return _bq_tiao(an_chang)

    # ② 按情绪
    yao = "恋人" if lianren else (qingxu or "平静")
    zhong = [p for p in lie if yao in os.path.basename(p)]
    if not zhong and yao == "恋人":
        zhong = [p for p in lie if "害羞" in os.path.basename(p)]
    # 灵光池里没有这个情绪 → 回退到离线池找同情绪的，
    # 总比"该委屈的时候抽到一张大笑的流行图"强
    if not zhong and mu != BQ_LIXIAN:
        zhong = [p for p in bq_lie(BQ_LIXIAN) if yao in os.path.basename(p)]
    # 委屈/困惑 不参与随机：这两种情绪下抽到一张"比心"会很不合时宜
    # 随机也只从"通用款"里挑 —— 拜拜/晚安/生气/大哭/恋人 这些带了明确场景，
    # 平时蹦出来只会莫名其妙
    if zhong and not lianren and yao not in ("委屈", "困惑") \
            and random.random() < BQ_SUIJI:
        ping = [p for p in lie
                if any(os.path.basename(p).startswith(k) for k in BQ_TONG_YONG)]
        return _bq_tiao(ping or zhong)
    return _bq_tiao(zhong or lie)

# 素材分两拨：
#   表格类素材（笑话、天气、美食、王者）是给各个工具查的“数据库”，
#     它们要么是「问：…答：…」，要么是「A|B|C」竖线表，学进聊天模型只会把天聊成表格；
#   其余素材，才是给大模型学的聊天语料。
# 第 2 步只排除了笑话；第 3 步把另外三张表也排除掉，
# 否则闲聊会蹦出“射手推荐”“18~26℃”这种断句（第 2 步实测确实会）。
GONGJU_SUCAI = ("笑话", "天气", "美食", "王者")
LIAOTIAN_SUCAI = [n for n in quanbu if not any(c in n for c in GONGJU_SUCAI)]

# 【第 3 步改动】聊天语料只认“一份主素材”，不再把几份风格不同的素材混在一起学着说。
# 为什么？这个模型是“看上文猜下一个字”，几份素材拼在一起，它就会把校园对话、
# 科幻小说、科普文章的口吻缝在一句里（实测会蹦出“陈屿和爸爸听说番茄炖牛腩不难”这种）。
# 优先级：文件名带“日常”的 > 带“对话”的 > 其余排第一份。
# 想换“腔调”，把新的素材命名成 素材X_日常对话.txt 就行，代码不用动。
def _xuan_zhu_sucai(biao):
    """按优先级挑一份主素材。先排除“校园”题材，日常/生活题材优先。"""
    # 第一优先：带“日常”又不带“校园”的（就是 素材八_日常对话.txt）
    for tiaojian in (lambda n: "日常" in n and "校园" not in n,
                     lambda n: "生活" in n,
                     lambda n: "对话" in n and "校园" not in n,
                     lambda n: "日常" in n,
                     lambda n: "对话" in n):
        mingzhong = [n for n in biao if tiaojian(n)]
        if mingzhong:
            return mingzhong[:1]
    return biao[:1]


wenjian = _xuan_zhu_sucai(LIAOTIAN_SUCAI) if LIAOTIAN_SUCAI else []

# 【新增·健壮性】第 1 步在这里直接 raise SystemExit，双击运行会黑屏闪退。
# 现在改成：没素材也能启动，只是大模型没读过书，报时和算数照样能用。
if not wenjian:
    print("【提示】没找到聊天用的 素材*.txt，大模型暂时没读过书。")
    print("        把素材文件放到这里就能聊天了：%s" % SUCAI_MU)
    print("        现在能用的功能：报时、算数、讲笑话。")
    print()

# 素材里偶尔有“写法说明”这种给人看的行（例如“不含本行标题和本行说明”），
# 学进模型会变成鬼话，所以读的时候就把它剔掉。
SHUOMING_CI = ("本行标题", "不含本行", "用途：", "写法说明", "以下为", "请勿修改")


def _shi_shuoming(hang):
    """判断这一行是不是“给人看的说明”，而不是语料正文"""
    return any(ci in hang for ci in SHUOMING_CI)


duanluo = []
for name in wenjian:
    with open(su_cai_lu(name), encoding="utf-8") as f:
        zhengwen = "\n".join(h for h in f.read().splitlines() if not _shi_shuoming(h))
    duanluo.append(zhengwen)
TEXT = "".join(duanluo).replace("\r", "").replace("\n", "").replace(" ", "")

# 【第 3 步新增】把素材再拆成“一句一句”，存成句子库。
# 为什么需要它？因为二字模型只会接字，回答不了“人工智能是什么”。
# 但素材里其实**写着**答案，只是需要按关键词把它捞出来 —— 这就是检索式回答。
#
# 【本轮改·检索池】句子库不再只收“主素材一份”（44 句），改成收全部聊天素材
#   + 程序旁边的「语料」目录。
#   为什么以前只收一份：怕几份素材混了腔调。但“学腔调”和“查资料”是两件事 ——
#   学腔调仍然只用一份（见上面 _xuan_zhu_sucai，TEXT/model 一行没动），
#   检索池越大越答得上话，两者不冲突。
#   为什么加一百份素材也不会抢关键词：这些句子只进检索池，不进话题表 HUATI_KU ——
#   没被检索到就一辈子不开口，不存在“关键词互相抢”。
YU_LIAO_MU = os.path.join(DIR, "语料")          # 用户自建：一行一句，放多少都行

# 素材里混着“给人看的说明”和对话体的说话人前缀，命中它们会答出鬼话，先洗一遍。
_SHOU_CI = re.compile(r"^[^\s：:]{1,5}[：:]\s*")  # 「小林：」「问：」这类说话人前缀
_XI_GAN_CI = ("min_lm", "generate", "本行标题", "不含本行", "用途：", "换进去",
              "重点观察", "语料约", "写法说明", "以下为", "请勿修改")


def _xi_gan_juzi(hang):
    """把一行素材洗成可以拿去回答的句子；洗不出来返回空串。

    要处理的三种脏东西：
      ① 说明行（讲怎么用这份素材的）—— 命中会答出“把 generate 的 start 改成…”
      ② 对话体的说话人前缀（小林：）—— 原样念出来像在念剧本
      ③ 素材三那种 Python 字符串壳（"..." ,）—— 引号会被一起念出来
    """
    s = (hang or "").strip()
    if not s or any(ci in s for ci in _XI_GAN_CI):
        return ""
    s = s.rstrip(",").rstrip("，").strip()
    s = s.strip("\"“”'‘’")
    s = _SHOU_CI.sub("", s).strip()
    s = s.strip("\"“”'‘’")
    # 以转折/因果词开头的句子，多半是上一句被切走后的尾巴。
    # 念出来就是「但是大模型也有明显的缺点」这种半截话，宁可不要这一句。
    if s.startswith(("但是", "但", "所以", "因为", "而且", "并且", "不过",
                     "然而", "因此", "于是", "同时", "另外", "也就是")):
        return ""
    return s


def _juzi_quan(name):
    """每句配一个可信度权重。

    日常/科普最可信（真能回答“是什么”），校园次之，叙事小说最次
    （它答不了知识题，但能接住“后来呢”这类话头，所以留着不删）。
    「语料」目录是用户自己筛过的，权重最高。
    """
    if name.startswith("语料/"):
        return 1.20
    if "日常" in name:
        return 1.15
    if "人工智能" in name or "科普" in name:
        return 1.10
    if "校园" in name:
        return 1.00
    if "叙事" in name or "小说" in name:
        return 0.85
    return 1.00


JUZI = []            # 检索池：一句一条
JUZI_QUAN = []       # 与 JUZI 一一对应的出处权重
JUZI_LAI = []        # 出处文件名，自检/调试用


def _pin_hang(wenben):
    """把“排版换行”接回去，只保留“真正的句子边界”。

    为什么需要：素材三是把一个长段拆成好几行带引号的字符串，按行切开就会得到
    「超大规模神经网络，它把学到的知识压缩在参数里」这种从半截开始的话 ——
    检索出来念给用户听，一眼就能看出是断句错误。
    规则：上一行没有句末标点，就认为它是被排版切断的，直接接上；否则另起一句。
    """
    jie = ""
    for hang in (wenben or "").splitlines():
        hang = hang.strip().strip("\"“”'‘’").strip()   # 先摘掉行首行尾的引号
        if not hang or hang.startswith("#"):
            continue
        if jie and jie[-1] not in "。！？；…":
            jie += hang
        else:
            jie += "\n" + hang
    return jie


def _shou_juzi(wenben, lai):
    quan = _juzi_quan(lai)
    for _j in re.split(r"[。！？；\n]+", _pin_hang(wenben)):
        _j = _xi_gan_juzi(_j)
        if len(_j) >= 10:
            JUZI.append(_j)
            JUZI_QUAN.append(quan)
            JUZI_LAI.append(lai)


for _name in LIAOTIAN_SUCAI:            # 四份聊天素材全收（原来是只收一份）
    try:
        with open(su_cai_lu(_name), encoding="utf-8") as _f:
            _shou_juzi(_f.read(), _name)
    except Exception:
        pass

if os.path.isdir(YU_LIAO_MU):           # 用户自建语料：一行一句
    for _name in sorted(os.listdir(YU_LIAO_MU)):
        if not _name.lower().endswith(".txt"):
            continue
        try:
            with open(os.path.join(YU_LIAO_MU, _name), encoding="utf-8") as _f:
                for _hang in _f:
                    _hang = _hang.strip()
                    if not _hang or _hang.startswith("#"):
                        continue
                    _j = _xi_gan_juzi(_hang)
                    if len(_j) >= 6:        # 自建语料允许短句（“我一般十一点睡”）
                        JUZI.append(_j)
                        JUZI_QUAN.append(_juzi_quan("语料/" + _name))
                        JUZI_LAI.append("语料/" + _name)
        except Exception:
            pass

# ---------- 倒排索引：二元组 → [(句子编号, 这个词在这句里出现几次)] ----------
# 为什么要索引：以前每问一句都要把整个句子库从头扫一遍（每个候选句数一遍命中几个
# 二字片段）。句子一多就慢，而且句子到几百条以后“覆盖率 ≥ 0.5”这种粗糙打分
# 会把无关短句也捞上来。索引 + BM25 是这件事的标准做法，纯标准库就能写。
TING_YONG = set("的了是我你他她它们这那就在有和也都很不个上下来去说会要可对就又才把被给让呢吗啊吧呀哦嗯么什怎么这个那个")


def _er_yuan(s):
    """只留汉字，切成二字片段；不足两字就整句当一个片段"""
    s = "".join(ch for ch in s if "\u4e00" <= ch <= "\u9fa5")
    if len(s) < 2:
        return [s] if s else []
    return [s[i:i + 2] for i in range(len(s) - 1)]


DAOPAI = defaultdict(list)      # 二元组 → [(句号, 词频)]
CHANG_DU = []                   # 每句的片段数（BM25 的长度归一要用）

for _i, _j in enumerate(JUZI):
    _tf = Counter(_er_yuan(_j))
    for _t, _c in _tf.items():
        DAOPAI[_t].append((_i, _c))
    CHANG_DU.append(sum(_tf.values()) or 1)

PINGJUN_CHANG = (sum(CHANG_DU) / len(CHANG_DU)) if CHANG_DU else 1.0

N = 2                                           # 上文长度：看前 2 个字
model = defaultdict(Counter)                    # 计票本：{上文: Counter(下一个字: 票数)}

for i in range(len(TEXT) - N):
    context = TEXT[i:i + N]
    next_char = TEXT[i + N]
    model[context][next_char] += 1


def generate(start="大模型", length=60, temperature=1.0):
    """从 start 开始，一个字一个字地往外写，写满 length 个字为止"""
    out = start
    for _ in range(length):
        qianwen = out[-N:]                      # 取刚写出的最后 2 个字当上文
        if qianwen not in model:
            qianwen = out[-1]                   # 2 字上文没见过，退而求其次看 1 个字
            if qianwen not in model:
                break                           # 连 1 个字都不认识，只好停笔
        candidates = model[qianwen]
        chars = list(candidates.keys())
        piaoshu = [c ** (1.0 / temperature) for c in candidates.values()]
        out += random.choices(chars, weights=piaoshu)[0]
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 第二部分【新增】工具 1：查看时间
# 思路：先用关键词判断“这句话是不是在问时间”，再从 datetime 取当前系统时间
# ══════════════════════════════════════════════════════════════════════════════

# 只要句子里出现下面任何一个词，就认定这是“时间类问题”
SHIJIAN_CI = (
    "几点", "时间", "时刻", "钟点", "报时",
    "日期", "几号", "多少号",
    "星期几", "周几", "礼拜几", "星期",
    "今年", "哪年",
    "now", "time", "date", "today",
)

XINGQI = ("一", "二", "三", "四", "五", "六", "日")   # 星期一 ~ 星期日


def is_time_question(text):
    """判断一句话是不是在问时间：命中任一关键词就算

    【本轮修正】「时间」这两个字也是人生话题里的常用词（「时间过得真快」「时间会冲淡一切」），
    原来一律被报时抢走，回一句「现在是 16:07:40」，答非所问。
    现在加一道闸：句子里带这些**聊时间**的说法，就不当报时处理，让给话题层。
    """
    low = text.lower()
    # 先排除「在聊时间」而不是「在问几点」的说法
    if any(ci in text for ci in LIAO_SHIJIAN_CI) and not any(
            ci in text for ci in ("几点", "报时", "现在时间", "当前时间")):
        return False
    # 【本轮补充】「时间是什么」「时间会倒流吗」也是在聊时间这个概念，
    # 不是问几点。要求句子里出现明确的**求时间点**说法，才算报时。
    # 这样「现在几点」「今天几号」「星期几」照旧报时，概念提问让给话题层。
    QIU_SHIJIAN_DIAN = ("几点", "几号", "多少号", "星期几", "周几", "礼拜几",
                        "报时", "现在时间", "当前时间", "今天日期", "今年是哪年",
                        "什么时间了", "现在是什么时候", "几点了")
    if not any(ci in low for ci in QIU_SHIJIAN_DIAN):
        return False
    # 【本轮补】「食堂几点开」「宿舍几点关门」「作业几号交」里的「几点/几号」
    # 问的是**那件事的时间**，不是现在几点。原来一律报时，答成「现在是 15:02」。
    # 句子里点了具体的事，就交回具体信息层。
    _JUTI_SHI = ("食堂", "宿舍", "教室", "图书馆", "操场", "超市", "校门", "教学楼",
                 "课", "作业", "考试", "放假", "开学", "假期", "自习", "老师", "班",
                 "快递", "医务室", "食堂饭", "校车")
    if any(ci in text for ci in _JUTI_SHI) and not any(
            ci in text for ci in ("现在", "当前", "报时", "几点了", "现在时间")):
        return False
    # 【本轮补】「咖啡几点后不能喝」「几点睡最好」问的是“那个时间点该干什么”，
    # 不是“现在几点”。这类带时间短语的说法一律不当报时。
    if any(ci in text for ci in _FEI_BAOSHI_CI):
        return False
    return any(ci in low for ci in SHIJIAN_CI)


# 「几点 + 这件事」= 问时间点该怎么安排，不是问现在几点
_FEI_BAOSHI_CI = ("几点后", "几点前", "几点睡", "几点起", "几点上班", "几点下班",
                  "几点上课", "几点下课", "几点吃", "几点开始", "几点结束",
                  "几点到", "几点走", "几点关", "几点合适", "几点比较好",
                  "几点最好", "几点好", "学到几点", "练到几点")


# 出现这些词，说明是在感叹/议论时间，不是要报时
LIAO_SHIJIAN_CI = ("过得真快", "过得好快", "时间真", "时间会", "时间能",
                   "时间不", "珍惜时间", "浪费时间", "时间就是", "没时间",
                   "一段时间", "段时间", "这段时间", "那段时间")


def look_time(text=""):
    """回答时间类问题。问什么就答什么，问得不具体就全报一遍。"""
    now = datetime.datetime.now()
    xingqi = "星期" + XINGQI[now.weekday()]
    riqi = "%d 年 %d 月 %d 日" % (now.year, now.month, now.day)
    shike = "%02d:%02d:%02d" % (now.hour, now.minute, now.second)
    # %02d 的意思是：按整数打印，不够 2 位就在前面补 0 —— 9 点会显示成 09

    if any(k in text for k in ("星期几", "周几", "礼拜几")):
        return "今天是%s。" % xingqi
    if any(k in text for k in ("日期", "几号", "多少号")):
        return "今天是 %s，%s。" % (riqi, xingqi)
    if any(k in text for k in ("几点", "时间", "时刻", "钟点", "报时")):
        return "现在是 %s（%s，%s）。" % (shike, riqi, xingqi)
    return "现在是 %s，%s %s。" % (riqi, shike, xingqi)


# ══════════════════════════════════════════════════════════════════════════════
# 第三部分【新增】工具 2：会算数
# 思路分两步：
#   ① 从一句中文里“抠”出算式：全角转半角、×÷^ 换成 * / **、中文运算符换符号
#   ② 用 ast 解析这棵语法树，只放行加减乘除和少数数学函数，逐个节点手算
#      —— 千万不能直接 eval()，那是把用户输入当代码执行，有安全风险
# ══════════════════════════════════════════════════════════════════════════════

# 中文数字 → 阿拉伯数字
ZH_DIGIT = {"零": 0, "〇": 0, "一": 1, "壹": 1, "二": 2, "两": 2, "贰": 2,
            "三": 3, "叁": 3, "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6,
            "陆": 6, "七": 7, "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9}
# 中文数位 → 权重
ZH_UNIT = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}
# 能组成中文数字的全部字符（拼成正则字符类用）
ZH_CHARS = "".join(ZH_DIGIT) + "".join(ZH_UNIT)

# 中文运算符 → 符号。注意顺序：长的词先替换，否则“除以”会被“除”抢先拆开
ZH_OP = (("乘以", "*"), ("乘", "*"), ("除以", "/"), ("除", "/"),
         ("加上", "+"), ("加", "+"), ("减去", "-"), ("减", "-"))

# ast 节点 → 真正的运算（白名单：只认这几种，别的节点一律拒绝）
YUNSUAN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# 允许调用的数学函数（同样是白名单，写别的一律拒绝）
HANSHU = {
    "abs": abs, "round": round, "sqrt": math.sqrt, "pow": math.pow,
    "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "floor": math.floor, "ceil": math.ceil, "factorial": math.factorial,
    "degrees": math.degrees, "radians": math.radians,
}

# 允许出现的常数名
CHANGLIANG = {"pi": math.pi, "e": math.e, "π": math.pi}


def zh_to_num(s):
    """把一段中文数字翻译成整数，如“一百二十三”→123、“十五”→15、“一二三”→123。
    遇到“万”“亿”这种没实现的单位返回 None，让调用方跳过，绝不瞎猜。"""
    if not s or "万" in s or "亿" in s:
        return None
    if all(ch in ZH_DIGIT for ch in s):          # 纯数字串：一二三 → 123
        return int("".join(str(ZH_DIGIT[ch]) for ch in s))
    result, num = 0, 0
    for ch in s:
        if ch in ZH_DIGIT:
            num = ZH_DIGIT[ch]
        elif ch in ZH_UNIT:
            u = ZH_UNIT[ch]
            if num == 0:                         # “十五”里的“十”前面省略了 1
                num = 1
            result += num * u
            num = 0
    return result + num


def guifanhua(text):
    """规范化前半段：全角符号转半角、×÷^ 换成 * / **、中文运算符换成符号。
    （中文数字留到“片段”里再换，这样“算一下”的“一”不会被误当成数字 1）"""
    # 全角转半角：全角字符的编码比半角大 0xFEE0，直接减掉即可
    text = "".join(chr(ord(ch) - 0xFEE0) if 0xFF01 <= ord(ch) <= 0xFF5E else ch
                   for ch in text)
    text = text.replace("×", "*").replace("✖", "*").replace("＊", "*")
    text = text.replace("÷", "/").replace("／", "/")
    text = text.replace("^", "**")               # 乘方：^ 换成 **
    for ci, fuhao in ZH_OP:                      # 中文运算符 → 符号（先长后短）
        text = text.replace(ci, fuhao)
    text = re.sub(r"(\d+)\s*的\s*(\d+)\s*次方", r"\1**\2", text)   # 2的10次方 → 2**10
    # 【本轮补】平方/立方/开根：原来「3的平方是多少」完全认不出，掉到陈述句兜底
    # 回一句「嗯，我在听」。这是有确定答案的问题，必须算出来。
    text = re.sub(r"(\d+(?:\.\d+)?)\s*的?\s*平方", r"\1**2", text)   # 3的平方 → 3**2
    text = re.sub(r"(\d+(?:\.\d+)?)\s*的?\s*立方", r"\1**3", text)   # 3的立方 → 3**3
    text = re.sub(r"(?:根号|开根号?|开平方)\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*的?\s*开根号?", r"sqrt(\1)", text)
    text = re.sub(r"(\d+)\s*!", r"factorial(\1)", text)            # 5! → factorial(5)
    return text


# 候选片段：由“数字/字母/运算符/括号/空格/中文数字”连成的一段
PIAN = re.compile(r"[0-9A-Za-zπ.+\-*/%()\s" + ZH_CHARS + r"]+")


def _zh_huan_pian(pian):
    """只在这一小段里把中文数字换成阿拉伯数字（“一百二十三*四”→“123*4”）"""
    def _huan(m):
        n = zh_to_num(m.group())
        return str(n) if n is not None else m.group()
    return re.sub("[" + ZH_CHARS + "]+", _huan, pian)


def anquan_qiusuan(biaodashi):
    """用 ast 安全地计算一个表达式，只放行白名单里的运算符和函数。
    返回 (成功与否, 结果或错误说明)。"""
    if len(biaodashi) > 200:                     # 先挡住超长式子，防止卡死
        return False, "式子太长了"
    try:
        tree = ast.parse(biaodashi, mode="eval")
    except SyntaxError:
        return False, "这个式子我看不懂"
    if sum(1 for _ in ast.walk(tree)) > 120:     # 节点数上限，防止巨型式子
        return False, "式子太复杂了"

    def _suan(node):
        # ── 数字：直接返回 ────────────────────────────────────────
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError("只支持数字")
        # ── 二元运算：先算左右，再套用白名单里的运算 ───────────────
        if isinstance(node, ast.BinOp):
            op = YUNSUAN.get(type(node.op))
            if op is None:
                raise ValueError("不支持的运算符")
            zuo, you = _suan(node.left), _suan(node.right)
            if isinstance(node.op, ast.Pow) and abs(you) > 1000:
                raise ValueError("指数太大了，算不动")
            if isinstance(node.op, ast.LShift | ast.RShift):
                raise ValueError("不支持的运算符")
            return op(zuo, you)
        # ── 一元运算：正负号 ─────────────────────────────────────
        if isinstance(node, ast.UnaryOp):
            op = YUNSUAN.get(type(node.op))
            if op is None:
                raise ValueError("不支持的正负号")
            return op(_suan(node.operand))
        # ── 函数调用：名字必须在白名单里 ─────────────────────────
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in HANSHU:
                raise ValueError("函数 %s 不在允许清单里" % getattr(node.func, "id", "?"))
            if getattr(node, "keywords", None):
                raise ValueError("不支持写参数名")
            args = [_suan(a) for a in node.args]
            if node.func.id == "factorial":
                if args and (args[0] < 0 or args[0] > 170):
                    raise ValueError("阶乘只算 0~170 的数")
                if args and args[0] != int(args[0]):
                    raise ValueError("阶乘只算整数")
            return HANSHU[node.func.id](*args)
        # ── 常数：pi、e ──────────────────────────────────────────
        if isinstance(node, ast.Name):
            if node.id in CHANGLIANG:
                return CHANGLIANG[node.id]
            raise ValueError("不认识 %s" % node.id)
        raise ValueError("不支持的写法")

    try:
        return True, _suan(tree.body)
    except ZeroDivisionError:
        return False, "除数不能是 0 哦"
    except ValueError as e:
        return False, str(e)
    except OverflowError:
        return False, "数字太大，算不动"
    except Exception:
        return False, "这个式子算不出来"


def tiqu_suanshi(text):
    """从一句话里抠出算式并算好。
    返回 (算式片段, 结果, 错误说明)：成功时错误说明为 None；没有算式时片段是 ""。"""
    s = guifanhua(text)
    # 抠出所有候选片段，长的排前面（越长越可能是用户真正想问的算式）
    houxuan = [p.strip() for p in PIAN.findall(s)]
    houxuan = [p for p in houxuan if p]
    houxuan.sort(key=len, reverse=True)

    cuowu = None
    for pian in houxuan:
        tip = _zh_huan_pian(pian).strip().strip("+-*/% ")
        # 候选必须“有数字”，并且“有运算符或函数名”，否则不是算式
        if not re.search(r"[0-9π]", tip):
            continue
        if not re.search(r"[+\-*/%]|[A-Za-z]+\s*\(", tip):
            continue
        ok, jieguo = anquan_qiusuan(tip)
        if ok:
            return tip, jieguo, None
        cuowu = cuowu or jieguo                 # 记下第一个错误原因，用于提示
    return "", None, cuowu


def is_calc_question(text):
    """判断一句话是不是在算数：能抠出算式，而且确实算得出来"""
    shi, jieguo, _ = tiqu_suanshi(text)
    return bool(shi)


# 用户“想算”的口头暗号：出现这些词，说明他是来算数的，不是来聊天的
# 注意：“多少”太常见（“语料有多少字”），不放进来自动判断，只在算式不完整时兜底
# 注意：“计算”单独两个字太宽 —— “量子计算怎么样”会被误判成来算数的。