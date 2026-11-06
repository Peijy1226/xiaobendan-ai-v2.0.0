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
# 所以要么带“帮我/一下”，要么干脆只认更明确的说法。
SUAN_CI = ("算一下", "算一算", "帮我算", "计算一下", "帮我计算", "等于", "等于多少",
           "得几", "答案是", "结果是", "求解", "=")


def is_calc_intent(text):
    """判断用户是不是“想算但没算成”：说了算数暗号，或者句子里有半截算式。
    用来给友好提示，而不是把“1/0”“abc+def”丢给大模型瞎接话。"""
    if any(ci in text for ci in SUAN_CI):
        return True
    s = guifanhua(text)
    # 纯英文/数字里夹着运算符（如 abc+def、3+、(*2)）：一看就是来算数的
    if not re.search(r"[\u4e00-\u9fa5]", text) and re.search(r"[+\-*/%^]", s):
        return True
    # 半截算式：有数字也有运算符
    if re.search(r"[0-9]", s) and re.search(r"[+\-*/%]", s):
        if is_time_question(text):            # “今天几号”归工具 1，不算算数
            return False
        return True
    return False


def _geshihua(x):
    """把计算结果排版成人看的样子：整数不带 .0，小数最多留 10 位有效数字"""
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x != x:                              # NaN
            return "不是一个有效的数"
        if x in (float("inf"), float("-inf")):
            return "无穷大"
        if x.is_integer() and abs(x) < 1e16:
            return str(int(x))
        return "%.10g" % x
    return str(x)


def calculate(text):
    """工具 2 的对外接口：算出来了就返回一句人话，算不出来返回 None"""
    shi, jieguo, _ = tiqu_suanshi(text)
    if not shi:
        return None
    return "%s = %s" % (shi, _geshihua(jieguo))


# ══════════════════════════════════════════════════════════════════════════════
# 第四部分【新增】工具 3：讲个笑话
# 思路和前面一样，素材也走“外置文件”：
#   ① 启动时顺手挑出 素材*笑话*.txt 这类文件（文件名里有“笑话”就算）
#   ② 每行写一条，格式固定为「问：……答：……」——用中文问号、中文冒号最好读
#   ③ 讲的时候按行随机抽一条，不重复上次讲过的那条
# 想加新笑话：直接用记事本往 素材四_笑话集.txt 里加一行，存盘重启程序即可，代码不用动。
# ══════════════════════════════════════════════════════════════════════════════

XIAOHUA_WENJIAN = [n for n in quanbu if "笑话" in n]     # 文件名里带“笑话”的素材
XIAOHUA = []                                             # [(问那一句, 答那一句), ……]

for _name in XIAOHUA_WENJIAN:
    with open(su_cai_lu(_name), encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or "答：" not in _line:
                continue                                 # 空行、不规范的跳过，不报错
            _wen, _da = _line.split("答：", 1)
            _wen = _wen.replace("问：", "").strip()
            _da = _da.strip()
            if _wen and _da:
                XIAOHUA.append((_wen, _da))

# 只要句子里出现下面任何一个词，就认定用户是想听笑话
XIAOHUA_CI = ("笑话", "段子", "逗我", "逗逗我", "搞笑", "幽默", "笑一笑", "乐一乐",
              "讲个笑", "来个笑", "说个笑", "开心一下",
              "再来一个", "再来一个笑话", "再来个", "换一个", "下一个", "还有吗",
              "再讲", "再来说个", "逗一逗")

_shang_ci_tiao = None            # 记住上一条，避免连着两次讲同一个


def is_joke_question(text):
    """判断这句话是不是在点笑话"""
    return any(ci in text for ci in XIAOHUA_CI)


def tell_joke(text=""):
    """工具 3 的对外接口：随机讲一条笑话"""
    global _shang_ci_tiao

    if not XIAOHUA:
        return ("我这会儿脑子空空的，一个段子都想不出来。过会儿再问我一次？")

    # 只有一条时就直接讲它；多条时避开上一条，免得连讲两遍
    if len(XIAOHUA) == 1:
        zhe_tiao = XIAOHUA[0]
    else:
        zhe_tiao = random.choice([x for x in XIAOHUA if x != _shang_ci_tiao])
    _shang_ci_tiao = zhe_tiao

    return "讲一个：\n  问：%s\n  答：%s" % zhe_tiao


# ══════════════════════════════════════════════════════════════════════════════
# 第五部分【新增】工具 4/5/6：查天气、推荐美食、讲王者荣耀
# 用的还是同一套思路：**知识全放外置素材，代码只负责查**。
#   素材五_天气.txt      每行：城市|天气|温度|风力|提示
#   素材六_美食推荐.txt  每行：菜名|类型|口味|一句话介绍
#   素材七_王者荣耀.txt  每行：关键词|答案
# 想加内容改 txt 就行，代码一个字不用动。
# ══════════════════════════════════════════════════════════════════════════════


def _du_biaoge(wenjian_ci):
    """把“竖线分隔”的素材读成二维表格：[[字段1, 字段2, ……], ……]"""
    hang = []
    for _n in quanbu:
        if wenjian_ci not in _n:
            continue
        with open(su_cai_lu(_n), encoding="utf-8") as _f:
            for _l in _f:
                _l = _l.strip()
                if not _l or _l.startswith("#"):
                    continue                         # 空行、# 开头是注释，跳过
                _ziduan = [x.strip() for x in _l.split("|")]
                if len(_ziduan) >= 2:
                    hang.append(_ziduan)
    return hang


TIANQI = _du_biaoge("天气")                       # [[城市, 天气, 温度, 风力, 提示], ……]
MEISHI = _du_biaoge("美食")                       # [[菜名, 类型, 口味, 介绍], ……]
WANGZHE = _du_biaoge("王者")                      # [[关键词, 答案], ……]

TIANQI_CI = ("天气", "气温", "下雨", "降温", "多少度", "穿什么")
MEISHI_CI = ("美食", "吃什么", "吃啥", "推荐菜", "推荐点", "有什么好吃", "好吃的",
             "饿", "点外卖", "来点吃", "推荐吃的", "有什么吃", "想吃")
KOUWEI_CI = ("辣的", "甜", "酸的", "清淡", "咸")   # 加口味词也能触发美食推荐
# 「英雄」和「新手」这两个词太泛：「新手机」含「新手」，「英雄电影」含「英雄」，
# 一匹配就答成「新手先练三个英雄：后羿、安琪拉、亚瑟」。
# 改成长组合词，只有真的在聊王者时才对得上。
WANGZHE_CI = ("王者", "荣耀", "峡谷", "段位", "上分", "五杀", "开黑",
              "打野", "射手", "法师", "辅助", "坦克", "刺客", "出装", "排位",
              "铭文", "皮肤", "新手玩", "新手入", "新手英雄", "举报",
              "王者荣耀", "五杀", "水晶", "团战", "开黑")


# 真的在问天气的说法。原来只要命中 TIANQI_CI 里的「下雨」就触发，
# 于是「今天下雨了心情很差」这种**拿天气当背景、其实在说心情**的句子
# 被抢去查天气，还因为没点城市，程序自作主张报了个南京出来 —— 牛头不对马嘴。
# 现在要求：命中天气词「并且」句子里有问句/求信息的口气，才算查天气。
TIANQI_WEN_FA = ("吗", "呢", "?", "？", "多少度", "几度", "穿什么", "要不要带伞",
                 "查一下", "查查", "怎么样", "如何", "什么天气", "天气预报")


def is_weather_question(text):
    # 【本轮补】「那明天呢」「扬州下周会下雨吗」这类追问：句子里可能一个
    # "天气"都没有，但它接的是上一句的天气问题 —— 漏掉就掉进闲聊层，
    # 模型只能现编一个温度。
    try:
        if _tq_genjin(text):
            return True
    except Exception:
        pass
    if not any(ci in text for ci in TIANQI_CI):
        return False
    # 【本轮补】「空调开多少度省电」被当成问天气，回了一屏城市列表。
    # 句子里说的是电器/水温/体温，就不是天气。
    if any(ci in text for ci in ("空调", "冰箱", "水温", "体温", "洗澡水", "暖气")):
        return False
    if any(ci in text for ci in TIANQI_WEN_FA):
        return True
    # 【本轮补】「今天天气」只有四个字，没有「吗/怎么样」这些话头，原来是当闲聊
    # 回了「天气一变人就容易犯懒」。点名了时段又说天气，就是在问。
    if any(ci in text for ci in ("今天", "明天", "后天", "这两天", "这几天")) and any(
            ci in text for ci in ("天气", "气温", "下雨", "多少度")):
        return True
    # 【本轮补】「北京天气」「上海天气」这种只说城市、不带问法的，原来一律不认，
    # 结果掉到闲聊层答「天气一变人就容易犯懒」。句子里点了能查的城市就算在问。
    try:
        if any((hang[0] in text) for hang in TIANQI):
            return True
    except Exception:
        pass
    return False


# 【本轮补】菜系词：用户说「推荐个川菜」时，句子里既没有「吃什么」也没有口味词，
# 原来的判据一个都不中，于是掉到兜底。菜系本身就是明确的点菜意图。
CAIXI_CI = ("川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
            "东北菜", "家常菜", "本帮菜", "西餐", "日料", "韩餐", "火锅",
            "烧烤", "川渝", "淮扬菜", "面食", "小吃")


def is_food_question(text):
    # 【本轮补】「猫能吃什么」被美食工具抢了，推了两道川菜。
    # 有宠物当主语的，问的是喂什么，不是点菜。
    if any(ci in text for ci in ("猫", "狗", "宠物", "仓鼠", "兔子")) and "吃" in text:
        return False
    if any(ci in text for ci in MEISHI_CI):
        return True
    if any(ci in text for ci in KOUWEI_CI) and ("吃" in text or "菜" in text or "推荐" in text):
        return True
    return any(ci in text for ci in CAIXI_CI)


# 「打游戏」「上分」这类词太泛：用户说「我男朋友打游戏不理我」，
# 本意是抱怨关系，却被拉去聊段位、出装。加一道闸：
# 出现关系/情绪词就说明在说人、不是说游戏，判给话题层处理。
_WANGZHE_BU_GAI = ("不理", "不管我", "不陪我", "不睡觉", "不吃饭", "不学习",
                   "不上班", "不还", "不给", "哭", "难过", "生气", "分手",
                   "吵架", "冷战", "孤独", "累", "烦", "心情", "不开心",
                   "郁闷", "压抑", "输了心里", "没意思")


def is_wangzhe_question(text):
    if any(ci in text for ci in _WANGZHE_BU_GAI):
        return False
    return any(ci in text for ci in WANGZHE_CI)


def cha_tianqi(text, moren=None):
    """工具 4：查天气 —— 走实时接口，不再念那张永远对不上的本地表

    【为什么重写】原来这里是从「素材五_天气.txt」里挑一行念：
    「北京|晴|18~26℃」这种值是写死的，八月写的表十一月还在念，
    用户说"天气根本不对"就是它。而且表里只有 15 座城，扬州、宿迁
    这种城市认不出，就随机报一座城充数 —— 等于答非所问。
    现在：城市和日期从问句里认（认不出就用上一次问过的城 / 默认城市），
    数据一律问 Open-Meteo（免费、不要 key、全球都能查），能查未来 7 天。
    只有"彻底连不上网"才回退那张旧表，并且会明说是旧数据。
    """
    if moren is None:
        try:
            moren = du_api_peizhi().get("默认城市", "北京") or "北京"
        except Exception:
            moren = "北京"
    wen, cuo, ok = tianqi_chaxun(text, moren)
    if ok and wen:
        return wen
    # 查不上：认得出城市就拿旧表兜一句（并说明是旧的），认不出就老实说
    chengshi, _ming = _zhao_chengshi(text, moren)
    for hang in TIANQI:
        if hang and hang[0] == chengshi:
            return ("【%s 天气】%s，气温 %s，%s。\n"
                    "（现在连不上天气接口，这条是本地存的旧数据，只能当个大概）"
                    % (hang[0], hang[1], hang[2],
                       "，".join(hang[3:]) if len(hang) > 3 else ""))
    return ("天气没查上：%s。\n网络通了再问我一次，我给你实时温度和未来几天。"
            % (cuo or "接口没回话"))


def tui_jian_meishi(text):
    """工具 5：推荐美食。说了口味（辣/甜/清淡）就按口味筛，否则随机推两道"""
    if not MEISHI:
        return "今天想吃什么，我一时没主意。你自己有馋的那口吗？"

    houxuan = MEISHI
    # 【本轮补】点名了菜系（川菜/粤菜/本帮菜/火锅…）就按菜系筛。
    # 只补判据不给筛法，等于认了这句话却没听 —— 「推荐个川菜」推一盘红烧肉，
    # 比不认更气人。
    ming_caixi = [cx for cx in CAIXI_CI if cx in text]
    if ming_caixi:
        guolv = [h for h in MEISHI
                 if any(cx in h[1] or cx in h[2] for cx in ming_caixi)]
        if guolv:
            houxuan = guolv
    else:
        for kouwei in ("辣", "甜", "酸", "清淡", "咸"):
            if kouwei in text:
                guolv = [h for h in MEISHI if kouwei in h[2]]
                if guolv:
                    houxuan = guolv
                break

    # 推两道，比只推一道更有得挑
    tiao = houxuan if len(houxuan) <= 2 else random.sample(houxuan, 2)
    xian = ["给你推荐 %d 道：" % len(tiao)]
    for h in tiao:
        xian.append("  · %s（%s·%s）—— %s"
                    % (h[0], h[1], h[2], h[3] if len(h) > 3 else ""))
    return "\n".join(xian)


def jiang_wangzhe(text):
    """工具 6：王者荣耀介绍。按“命中关键词最长”来挑答案，问得越具体答得越准"""
    if not WANGZHE:
        return "王者这方面我了解得不多，怕说错了带偏你。"

    zui_hao = None
    zui_chang = 0
    for hang in WANGZHE:
        guanjian = hang[0]
        if guanjian in text and len(guanjian) > zui_chang:
            zui_hao, zui_chang = hang, len(guanjian)
    if zui_hao:
        return zui_hao[1]

    # 没命中具体关键词 → 给一段总介绍
    for hang in WANGZHE:
        if "是什么" in hang[0]:
            return hang[1]
    return "《王者荣耀》是 5V5 的 MOBA 手游。你可以问我：怎么玩、段位、英雄、路线、出装、技巧。"


# ══════════════════════════════════════════════════════════════════════════════
# 第六部分：对话主循环（在第 1 步的基础上加“路由”）
# 判断顺序很重要：
#   退出 → 帮助 → 空输入 → 报时 → 天气 → 笑话 → 美食 → 王者 → 算数 → 大模型接话
# 为什么报时排在算数前面？因为“今天几号”若先过算数，会被当成数字去算。
# 为什么天气排最前？因为“今天几号”是时间，“今天天气”是天气，靠关键词区分得清。
# ══════════════════════════════════════════════════════════════════════════════

BANGZHU = """我这儿分两样东西：**工具**（打字就能用，我会去查）和**功能**（点右上角「☰ 功能」或按 F3）。

【工具 · 打字就能用】
  报时 —— 「现在几点」「今天几号」「星期几」
  天气 —— 「北京天气」「上海下雨吗」，走的是实时接口，会给温度和穿衣提示
  笑话 —— 「讲个笑话」，不说就一直换新的
  美食 —— 「推荐点好吃的」，说「想吃辣的/甜的」也行
  王者 —— 「王者射手玩什么」「打野怎么玩」，按关键词给答案
  算数 —— 直接甩算式（1234*56+78），或者用嘴说（一百二十三乘四）
  换算 —— 「1美元多少人民币」「5公里多少米」「200打8折」

  用工具时，气泡上方会写「正在调用XXX…」——
  看到这行就说明我真的去查了，不是在聊天。

【功能 · 点右上角「☰ 功能」或按 F3】
  识图   —— 挑张图提文字、给人和东西画框，还会说人的穿搭
  整理   —— 扫演示夹，或者自己挑文件删；只移到回收站，默认关着要先开启
  写作   —— 选体裁、填题目、定字数，写一篇作文
  壁纸 / 字号 / 打赏 / 清空聊天 / 收起

  另外：输入「退出」就关掉我；F2 收起对话区；Ctrl+加号/减号调字号。"""

BEIJING_BANGZHU = """几个只换外观、不影响聊天的入口（同样在「☰ 功能」里）：

  · 壁纸     —— 换聊天壁纸：图片、GIF 动图、视频都行，还能调壁纸透明度
  · 字体大小 —— 无级滑块，最大 18 号；Ctrl+加号/减号也行
  · 打赏     —— 打赏 token，从 1 token 到 1M token 七档，好感度会涨
  · 清空聊天 —— 清掉对话区里的记录（会先问一句再清）
  · 收起     —— 对话区折叠起来（F2），想安静打字的时候用

【人设只管说话的样子，不管功能】
「☰ 功能 → 关于」里那份人设，决定的是我怎么说话：语气、长度、遇到事的反应。
它**不影响**上面任何一个工具和功能 —— 人设里写着爱安静、不懂游戏，
问答王、讲笑话、查天气照样能答，因为那些是程序查好的，不是我自己瞎编。

顶上「小笨蛋」右边那个小开关，是「灵光 / 短路」：

  · 灵光=接外面的模型，说话更像人；短路=回原来那套本地规则
  · 想用灵光，先打开「API.txt」把钥匙填上，存盘后点一下开关，不用重启"""


# ══════════════════════════════════════════════════════════════════════════════
# 危机句：说「不想活了」的时候，答什么都不能是随口接话
# ------------------------------------------------------------------------------
# 这类句子必须硬拦截，不能进 _pipei_huati 的「最长词胜出」竞争 ——
# 实测「我想消失一段时间」会被「时间」抢走，回一句「回忆这东西…」。
#
# 回复的原则（照着写的，改的时候别破坏）：
#   1. 先接住人，不问「为什么」——问原因会让对方觉得要先证明自己值得被关心
#   2. 不评判、不劝「想开点」、不说「你家人怎么办」——那会加负担
#   3. 具体问一句当下的状态（现在在哪儿 / 身边有人吗），不要抽象
#   4. 认真对待但不演：不装专家，也不轻飘飘地说「会好的」
# ══════════════════════════════════════════════════════════════════════════════
_WEIJI_CI = (
    "不想活", "想死", "去死", "自杀", "轻生", "结束自己", "了断", "活不下去",
    "活着没意思", "活着没意义", "不想存在", "想消失", "消失一段时间",
    "跳下去", "割腕", "安眠药", "一了百了",
    # 补充：都是「带语境的长词」，单字「死了」绝不能加 ——
    # 「无聊死了」「累死了」会被误判成危机句。
    "死了更好", "死了算了", "不如死", "还不如死", "不想醒来", "不想睁眼",
    "活着太累", "活着好累", "活着很累", "没脸活", "没意思活着",
    "解脱了", "一睡不醒", "想结束", "结束这一切",
)

_WEIJI_HUI = (
    "我在。你先别急着说别的，就回答我一句：你现在是一个人吗？",
    "听到你这么说，我不会当作没听见。你现在安全吗？身边有没有人？",
    "我不劝你，也不讲道理。你先告诉我，这个念头是刚有的，还是已经很久了？",
    "这种时候别一个人扛。如果手边有能联系的人，现在就发一条消息给他，说什么都行。",
    "我陪你说话，但有件事我得说清楚：这种时候找专业的人比自己扛管用。你愿意的话，我可以帮你想想怎么开口。",
)


def _wei_ji(text):
    """危机句拦截：命中就返回一句「先接住人」的话，否则 None。

    单独成一个函数、在 shuohua 里最早调用，是为了不被任何话题表抢走。
    """
    if any(k in text for k in _WEIJI_CI):
        return random.choice(_WEIJI_HUI)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 会话状态 + 语料自增长（本轮新增）
# ------------------------------------------------------------------------------
# 为什么加：原来只记“上一轮”一句（SHANG_YI_LUN 一个字典），第三句就断片；
# 而且哪些话没答上，程序自己不知道，语料就一直不会变多。
# 现在记三样：
#   ① 最近 6 轮（你说的、我答的、走的哪层）—— 追问时能翻回去
#   ② 最近 4 个话题词 —— 短输入（「然后呢」）靠它续上文
#   ③ 没答上的话丢进「待补语料.txt」—— 人工挑一句改成一行，放进「语料/」就长本事
# 三条都只影响“检索和接话”，工具层（报时/算数/天气/整理）一律不经过这里。
# ══════════════════════════════════════════════════════════════════════════════

HUI_HUA = {
    "lun": deque(maxlen=6),     # [(你说的, 我答的, 来源), ...]
    "ti": deque(maxlen=4),      # 最近几个话题词
    "qing": deque(maxlen=6),    # 最近几轮的情绪分（负数=低落）
    "ju": deque(maxlen=3),      # 最近几句“有内容”的话（跳过嗯/然后呢这种）
}

# 情绪词只用来“决定怎么接”，不改任何一句文案：
#   连着两轮都低落 → 少用反问，多用接住的话。
_QING_LUO = ("难受", "难过", "累", "烦", "孤独", "委屈", "崩溃", "失眠", "睡不着",
             "压力", "焦虑", "失落", "想哭", "没人", "不开心", "郁闷", "丧", "撑不住",
             "想辞职", "考砸", "失恋", "吵架", "冷战", "没用", "自卑", "疼", "生病",
             "被骂", "挨骂", "被批评", "骂了")
_QING_GAO = ("开心", "高兴", "太好了", "顺利", "成功", "喜欢", "舒服", "幸福",
             "考过", "通过了", "涨工资", "好消息", "太好了", "棒")


def _qing_fen(text):
    """一句话的情绪分：正数偏高兴，负数偏低落。只用词表数个数，不做语义判断。"""
    t = text or ""
    luo = sum(1 for k in _QING_LUO if k in t)
    gao = sum(1 for k in _QING_GAO if k in t)
    return gao - luo


def _qing_di():
    """最近两轮是不是都低落"""
    q = list(HUI_HUA["qing"])
    return len(q) >= 2 and q[-1] < 0 and q[-2] < 0


def _wen_wei_duo():
    """最近三条回复里，是不是有两条以上以问号收尾。

    为什么管这个：每句都反问，人会累 —— 像被采访。连续反问两句之后，
    这一轮优先挑不带问号的候选，让节奏喘一口气。
    """
    da = [h[1].rstrip() for h in HUI_HUA["lun"]]
    if len(da) < 2:
        return False
    ji = sum(1 for x in da[-3:] if x.endswith(("？", "?")))
    return ji >= 2

DAI_BU_LU = os.path.join(DIR, "待补语料.txt")    # 没答上的话攒在这里
DAI_BU_SHANG_XIAN = 800                           # 攒到这么多条就不再写，免得文件无限长
DAI_BU_YI_YOU = set()


def _du_dai_bu():
    """启动时把已有记录读进内存，写之前先查重（免得同句话记几十遍）"""
    try:
        if os.path.exists(DAI_BU_LU):
            with open(DAI_BU_LU, encoding="utf-8") as f:
                for hang in f:
                    if "\t" in hang:
                        DAI_BU_YI_YOU.add(hang.rstrip("\n").split("\t")[-1])
    except Exception:
        pass


def _ji_dai_bu(text):
    """把“没答上”的话记一笔。失败一律吞掉 —— 记录不该影响聊天。"""
    try:
        t = (text or "").strip()
        if len(t) < 4 or t in DAI_BU_YI_YOU:
            return
        if not any("\u4e00" <= ch <= "\u9fa5" for ch in t):
            return
        if len(DAI_BU_YI_YOU) >= DAI_BU_SHANG_XIAN:
            return
        xin = not os.path.exists(DAI_BU_LU)
        with open(DAI_BU_LU, "a", encoding="utf-8") as f:
            if xin:
                f.write("# 这些是“没答上”的话，程序自动记的。\n"
                        "# 用法：挑有用的，改写成一句像人说的话，一行一句，存进 语料/ 目录。\n"
                        "# 格式：时间\t你当时说的话\n")
            f.write("%s\t%s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t))
        DAI_BU_YI_YOU.add(t)
    except Exception:
        pass


def _ji_hui_hua(text, da, lai):
    """每轮说完记一笔：最近 6 轮 + 话题词 + 情绪分"""
    try:
        HUI_HUA["lun"].append((text or "", da or "", lai or ""))
        ming = _pipei_huati(text or "")
        ti = ming[0] if ming else _ti_hua_ti(text or "")
        if ti and len(ti) >= 2:
            HUI_HUA["ti"].append(ti)
        HUI_HUA["qing"].append(_qing_fen(text or ""))
        # 单独存“有内容的话”：连问七八句「然后呢」时，6 轮窗口里全是追问，
        # 回头找不到一句能拿来填空的实句。
        w = (text or "").strip()
        if len(w) >= 4 and not any(k in w for k in _ZHUI_QUAN_CI):
            HUI_HUA["ju"].append(w)
    except Exception:
        pass


# 口语归一：把方言/口头语换成程序认识的说法，只改“理解”，不改回复用词
_KOU_YU = (("晓得", "知道"), ("咋办", "怎么办"), ("咋样", "怎么样"), ("咋回事", "怎么回事"),
           ("咋", "怎么"), ("啥意思", "什么意思"), ("啥玩意", "什么东西"), ("啥", "什么"),
           ("甭", "不用"), ("俺", "我"), ("整明白", "弄明白"), ("中不中", "行不行"),
           ("得瑟", "得意"), ("老铁", "朋友"))


def _gui_kou_yu(t):
    for a, b in _KOU_YU:
        t = t.replace(a, b)
    return t


def _shang_ti():
    """上一轮（或更早）聊的是什么 —— 短输入靠它续上文"""
    if HUI_HUA["ti"]:
        return HUI_HUA["ti"][-1]
    return SHANG_YI_LUN.get("ti") or ""


_du_dai_bu()



# ======================================================================
# 换算：汇率 / 亲戚称谓 / 单位 / 日期差 / 百分比 / 进制
# ----------------------------------------------------------------------
# 功能页那六张卡以前只是"把示例填进输入框"，而程序本身根本看不懂
# 「100美元换人民币」——点了等于没点。这一段真的把六类都算出来。
#
# 三条原则：
#   ① 认不出来就返回 None，绝不硬猜（猜错比不答更糟）。
#   ② 汇率是**离线参考表**，会过期，所以每句都注明"参考"和系数。
#   ③ 输出是一句人话，不是一串数字。
# ======================================================================

_HL_BILV = {
    "美元": 7.10, "美金": 7.10, "usd": 7.10,
    "欧元": 7.72, "eur": 7.72,
    "日元": 0.0475, "jpy": 0.0475,
    "英镑": 9.02, "gbp": 9.02,
    "港币": 0.912, "港元": 0.912, "hkd": 0.912,
    "韩元": 0.0052, "krw": 0.0052,
    "澳元": 4.65, "aud": 4.65,
    "加元": 5.18, "cad": 5.18,
    "新加坡元": 5.30, "sgd": 5.30,
    "瑞士法郎": 8.10, "chf": 8.10,
    "台币": 0.222, "twd": 0.222,
    "人民币": 1.0, "cny": 1.0, "rmb": 1.0, "元": 1.0,
}

_HL_QIN = {
    "爸爸的爸爸": "爷爷", "爸爸的妈妈": "奶奶",
    "爸爸的哥哥": "伯父", "爸爸的弟弟": "叔叔",
    "爸爸的姐姐": "姑妈", "爸爸的妹妹": "姑妈",
    "妈妈的爸爸": "外公", "妈妈的妈妈": "外婆",
    "妈妈的哥哥": "舅舅", "妈妈的弟弟": "舅舅",
    "妈妈的姐姐": "姨妈", "妈妈的妹妹": "姨妈",
    "哥哥的妻子": "嫂子", "弟弟的妻子": "弟媳",
    "姐姐的丈夫": "姐夫", "妹妹的丈夫": "妹夫",
    "儿子的妻子": "儿媳", "女儿的丈夫": "女婿",
    "姑妈的丈夫": "姑父", "姨妈的丈夫": "姨父",
    "舅舅的妻子": "舅妈", "伯父的妻子": "伯母",
    "叔叔的妻子": "婶婶",
    "哥哥的儿子": "侄子", "弟弟的儿子": "侄子",
    "哥哥的女儿": "侄女", "弟弟的女儿": "侄女",
    "姐姐的儿子": "外甥", "妹妹的儿子": "外甥",
    "姐姐的女儿": "外甥女", "妹妹的女儿": "外甥女",
    "儿子的儿子": "孙子", "儿子的女儿": "孙女",
    "女儿的儿子": "外孙", "女儿的女儿": "外孙女",
    "爷爷的爸爸": "曾祖父", "爷爷的妈妈": "曾祖母",
    "外公的爸爸": "外曾祖父", "外公的妈妈": "外曾祖母",
}


def _hl_cn_num(t):
    """中文数字 → float：八 → 8、十五 → 15、两 → 2"""
    if not t:
        return None
    biao = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    t = t.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return float(t)
    if t in biao:
        return float(biao[t])
    if len(t) == 2 and t[0] == "十" and t[1] in biao:
        return float(10 + biao[t[1]])
    if len(t) == 2 and t[1] == "十" and t[0] in biao:
        return float(biao[t[0]] * 10)
    if len(t) == 3 and t[1] == "十" and t[0] in biao and t[2] in biao:
        return float(biao[t[0]] * 10 + biao[t[2]])
    return None


# 每个单位换算到基准要乘多少（长度=米 / 重量=千克 / 面积=平方米 / 存储=字节 / 时间=秒）
_HL_DANWEI = {
    "公里": ("chang", 1000.0), "千米": ("chang", 1000.0), "km": ("chang", 1000.0),
    "米": ("chang", 1.0), "m": ("chang", 1.0),
    "分米": ("chang", 0.1), "厘米": ("chang", 0.01), "cm": ("chang", 0.01),
    "毫米": ("chang", 0.001), "mm": ("chang", 0.001),
    "英里": ("chang", 1609.34), "mile": ("chang", 1609.34),
    "英尺": ("chang", 0.3048), "ft": ("chang", 0.3048),
    "英寸": ("chang", 0.0254), "inch": ("chang", 0.0254),
    "码": ("chang", 0.9144),
    "吨": ("zhong", 1000.0), "t": ("zhong", 1000.0),
    "千克": ("zhong", 1.0), "公斤": ("zhong", 1.0), "kg": ("zhong", 1.0),
    "克": ("zhong", 0.001), "g": ("zhong", 0.001),
    "斤": ("zhong", 0.5), "两": ("zhong", 0.05),
    "磅": ("zhong", 0.4536), "lb": ("zhong", 0.4536),
    "盎司": ("zhong", 0.02835), "oz": ("zhong", 0.02835),
    "平方米": ("mianji", 1.0), "平米": ("mianji", 1.0),
    "亩": ("mianji", 666.667), "公顷": ("mianji", 10000.0),
    "平方公里": ("mianji", 1000000.0),
    "tb": ("cunchu", 1024.0 ** 4), "gb": ("cunchu", 1024.0 ** 3),
    "mb": ("cunchu", 1024.0 ** 2), "kb": ("cunchu", 1024.0), "b": ("cunchu", 1.0),
    "天": ("shijian", 86400.0), "小时": ("shijian", 3600.0),
    "分钟": ("shijian", 60.0), "分": ("shijian", 60.0),
    "秒": ("shijian", 1.0), "周": ("shijian", 604800.0),
}

_HL_DANWEI_DAN = ("km", "m", "cm", "mm", "kg", "g", "t", "lb", "oz",
                  "tb", "gb", "mb", "kb", "b", "mile", "ft", "inch")


def _hl_danwei(ming):
    """单位名 → (类, 系数)。先按全名查，再按小写缩写查"""
    ming = (ming or "").strip().lower()
    if ming in _HL_DANWEI:
        return _HL_DANWEI[ming]
    if ming in _HL_DANWEI_DAN:
        return _HL_DANWEI[ming]
    return None


def _hl_liang_ming(lei, zhi):
    """把基准值拼成人话：5000 米 → "5 公里" 这种更好读"""
    if lei == "chang":
        if zhi >= 1000:
            return "%.2f 公里" % (zhi / 1000.0)
        if zhi >= 1:
            return "%.2f 米" % zhi
        return "%.1f 厘米" % (zhi * 100)
    if lei == "zhong":
        if zhi >= 1000:
            return "%.2f 吨" % (zhi / 1000.0)
        if zhi >= 1:
            return "%.2f 千克" % zhi
        return "%.1f 克" % (zhi * 1000)
    if lei == "mianji":
        if zhi >= 10000:
            return "%.2f 公顷" % (zhi / 10000.0)
        return "%.2f 平方米" % zhi
    if lei == "cunchu":
        for dan, k in (("TB", 1024.0 ** 4), ("GB", 1024.0 ** 3),
                       ("MB", 1024.0 ** 2), ("KB", 1024.0)):
            if zhi >= k:
                return "%.2f %s" % (zhi / k, dan)
        return "%.0f B" % zhi
    if lei == "shijian":
        if zhi >= 86400:
            return "%.2f 天" % (zhi / 86400.0)
        if zhi >= 3600:
            return "%.2f 小时" % (zhi / 3600.0)
        if zhi >= 60:
            return "%.2f 分钟" % (zhi / 60.0)
        return "%.0f 秒" % zhi
    return "%.2f" % zhi


def _hl_bilv(text):
    """汇率：100美元换人民币"""
    if not re.search(r"换|兑换|等于|是多少|换算|to", text, re.I):
        return None
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(美元|美金|欧元|日元|英镑|港币|港元|韩元|澳元|加元|"
        r"新加坡元|瑞士法郎|台币|人民币|usd|eur|jpy|gbp|hkd|krw|aud|cad|sgd|chf|twd|cny|rmb)"
        r"\s*(?:换|兑换|换算成|等于|是多少|是|to)\s*(?:多少)?\s*"
        r"(美元|美金|欧元|日元|英镑|港币|港元|韩元|澳元|加元|新加坡元|瑞士法郎|"
        r"台币|人民币|usd|eur|jpy|gbp|hkd|krw|aud|cad|sgd|chf|twd|cny|rmb)?",
        text, re.I)
    if not m:
        return None
    shu = float(m.group(1))
    lai = m.group(2)
    qu = m.group(3) or "人民币"
    a = _HL_BILV.get(lai.lower() if lai.lower() in _HL_BILV else lai)
    b = _HL_BILV.get(qu.lower() if qu.lower() in _HL_BILV else qu)
    if a is None or b is None:
        return None
    jieguo = shu * a / b
    return ("%g %s ≈ %.2f %s。离线用的参考汇率：1 %s ≈ %.4g %s，"
            "实际以银行牌价为准。" % (shu, lai, jieguo, qu, lai, a / b, qu))


def _hl_qinqi(text):
    """亲戚称谓：爸爸的姐姐叫什么"""
    if "叫" not in text and "称呼" not in text:
        return None
    # 取出"叫"之前那串称谓链
    qian = re.split(r"怎么|该叫|应该|叫什么|叫啥|称呼", text)[0]
    qian = re.sub(r"^(请问|问一下|我想问|那个|那么|所以)+", "", qian).strip("，,。？?！! ")
    if "的" not in qian and qian not in _HL_QIN:
        return None
    # 只保留称谓片段（把"我爸爸的姐姐"这种前缀削掉）
    guan = ("爸爸", "妈妈", "哥哥", "弟弟", "姐姐", "妹妹", "儿子", "女儿",
            "爷爷", "奶奶", "外公", "外婆", "丈夫", "妻子", "老婆", "老公")
    m = re.search(r"((?:%s)(?:的(?:%s))*)"
                  % ("|".join(guan), "|".join(guan + ("姑妈", "姨妈", "舅舅",
                                                      "伯父", "叔叔", "舅妈",
                                                      "姑父", "姨父", "嫂子",
                                                      "弟媳", "姐夫", "妹夫"))),
                  qian)
    if not m:
        return None
    lian = m.group(1)
    bu = lian.split("的")
    dang = bu[0]
    i = 1
    while i < len(bu):
        # 「老公/老婆」和「丈夫/妻子」是同一个关系，表里只存了一种写法
        yao = (dang + "的" + bu[i]).replace("老公", "丈夫").replace("老婆", "妻子")
        if yao in _HL_QIN:
            dang = _HL_QIN[yao]
            i += 1
        else:
            # 换一种叫法再试（"姐姐"在链里也可能写成"姐"）
            return None
    if dang == bu[0]:
        return None
    return "%s，叫「%s」。" % (lian, dang)


def _hl_danwei_huansuan(text):
    """单位：5公里等于多少米 / 30摄氏度等于多少华氏度

    坑：单位名不能用 [\u4e00-\u9fa5]{1,6} 去猜 —— 贪婪会把"等于"一起吃进去，
    得到 lai="公里等于"，查表查不到，于是整句算不出来（实测就是这样）。
    所以这里用已知单位名拼正则，长的排前面（"平方公里"要在"公里"之前）。
    """
    # 温度单独处理（不是乘系数）
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(摄氏度|度c|℃|摄氏|华氏度|度f|℉|华氏)\s*"
                  r"(?:等于|是|换算成|转成|换成)?\s*(?:多少|几)?\s*"
                  r"(摄氏度|度c|℃|摄氏|华氏度|度f|℉|华氏)", text, re.I)
    if m:
        zhi = float(m.group(1))
        lai = m.group(2).lower()
        qu = m.group(3).lower()
        she = lai in ("摄氏", "摄氏度", "度c", "℃")
        if she and qu not in ("摄氏", "摄氏度", "度c", "℃"):
            return "%g 摄氏度 = %.1f 华氏度。" % (zhi, zhi * 9 / 5 + 32)
        if (not she) and qu in ("摄氏", "摄氏度", "度c", "℃"):
            return "%g 华氏度 = %.1f 摄氏度。" % (zhi, (zhi - 32) * 5 / 9)

    ming = sorted(_HL_DANWEI.keys(), key=len, reverse=True)
    pat = "|".join(re.escape(x) for x in ming)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(%s)\s*"
                  r"(?:等于|是|换算成|转成|换成)\s*(?:多少|几)?\s*(%s)?" % (pat, pat),
                  text, re.I)
    if not m:
        return None
    zhi = float(m.group(1))
    lai = _hl_danwei(m.group(2))
    if lai is None:
        return None
    qu_ming = m.group(3)
    qu = _hl_danwei(qu_ming) if qu_ming else None
    if qu is None:
        lei = lai[0]
        if lei == "chang":
            return "%g %s = %s。" % (zhi, m.group(2),
                                     _hl_liang_ming(lei, zhi * lai[1]))
        return None
    if lai[0] != qu[0]:
        return None
    jieguo = zhi * lai[1] / qu[1]
    return "%g %s = %.4g %s。" % (zhi, m.group(2), jieguo, qu_ming)


def _hl_riqi(text):
    """日期差：3月5日到4月2日几天"""
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]\s*(?:到|至|-|~|—)\s*"
                  r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", text)
    if not m:
        return None
    import datetime as _dt
    jin = _dt.date.today()
    try:
        a = _dt.date(jin.year, int(m.group(1)), int(m.group(2)))
        b = _dt.date(jin.year, int(m.group(3)), int(m.group(4)))
    except Exception:
        return "这个日期不存在（月份或日子超了）。"
    if b < a:
        b = _dt.date(jin.year + 1, int(m.group(3)), int(m.group(4)))
    tian = (b - a).days
    return "%s月%s日到%s月%s日一共 %d 天。" % (
        m.group(1), m.group(2), m.group(3), m.group(4), tian)


def _hl_baifenbi(text):
    """百分比：打八折是多少 / 200打八折 / 200的15%"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:块|元|钱)?\s*打\s*([一二三四五六七八九十两\d.]+)\s*折",
                  text)
    if m:
        ji = float(m.group(1))
        zhe = _hl_cn_num(m.group(2))
        if zhe:
            return "%g 块打 %s 折 = %.2f 块（省了 %.2f）。" % (
                ji, m.group(2), ji * zhe / 10.0, ji - ji * zhe / 10.0)
    m = re.search(r"打\s*([一二三四五六七八九十两\d.]+)\s*折", text)
    if m:
        zhe = _hl_cn_num(m.group(1))
        if zhe:
            return ("打 %s 折就是原价乘 %.1f —— 100 块的東西算下来 %.0f 块。"
                    % (m.group(1), zhe / 10.0, 100 * zhe / 10.0))
    m = re.search(r"(\d+(?:\.\d+)?)\s*的\s*(\d+(?:\.\d+)?)\s*%", text)
    if m:
        ji = float(m.group(1))
        bai = float(m.group(2))
        return "%g 的 %g%% = %.4g。" % (ji, bai, ji * bai / 100.0)
    m = re.search(r"(\d+(?:\.\d+)?)\s*[涨降]\s*(?:了)?\s*(\d+(?:\.\d+)?)\s*%", text)
    if m:
        ji = float(m.group(1))
        bai = float(m.group(2))
        return "%g 涨/降 %g%% = %.4g。" % (ji, bai, ji * (1 + bai / 100.0))
    return None


def _hl_jinzhi(text):
    """进制：255转成十六进制"""
    m = re.search(r"(0x[0-9a-fA-F]+|[0-9a-fA-F]+)\s*"
                  r"(?:转|换|变|写)\s*(?:换)?(?:成|为)?\s*"
                  r"(十六进制|16进制|十进制|10进制|八进制|8进制|二进制|2进制)", text)
    if not m:
        return None
    yuan = m.group(1)
    mu = m.group(2)
    if "十六" in mu or "16" in mu:
        ji = 16
    elif "十" in mu or "10" in mu:
        ji = 10
    elif "八" in mu or "8" in mu:
        ji = 8
    else:
        ji = 2
    try:
        if yuan.lower().startswith("0x"):
            zhi = int(yuan, 16)
        elif re.search(r"[a-fA-F]", yuan):
            zhi = int(yuan, 16)
        else:
            zhi = int(yuan, 10)
    except Exception:
        return None
    if ji == 10:
        jieguo = str(zhi)
    elif ji == 16:
        jieguo = format(zhi, "X")
    elif ji == 8:
        jieguo = format(zhi, "o")
    else:
        jieguo = format(zhi, "b")
    return "%s 转成%s是 %s。" % (yuan, mu, jieguo)


_HL_QIAN = (
    ("美元汇率", "hui"), ("汇率换算", "hui"), ("汇率", "hui"),
    ("单位换算", "dan"), ("单位", "dan"),
    ("百分比", "bai"), ("打折", "bai"),
    ("进制转换", "jin"), ("进制", "jin"),
    ("日期差", "ri"), ("日期", "ri"),
    ("亲戚称谓", "qin"), ("称谓", "qin"),
)


def _hl_qian_dan(sheng):
    """单位换算 5 公里 米"""
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*([^\s]+)\s*(?:到|换成|等于)?\s*([^\s]*)", sheng)
    if not m:
        return "格式：单位换算 5 公里 米（数量 原单位 目标单位）"
    zhi = float(m.group(1))
    lai_ming, qu_ming = m.group(2), (m.group(3) or "")
    # 温度不是乘系数，交给专门的温度分支
    if "摄氏" in lai_ming or "华氏" in lai_ming:
        if not qu_ming:
            return "温度要写成「30 摄氏度 华氏度」。"
        return _hl_danwei_huansuan("%g%s等于多少%s" % (zhi, lai_ming, qu_ming))
    lai = _hl_danwei(lai_ming)
    if lai is None:
        return "认不出「%s」这个单位。能用的有：公里/米/厘米/斤/千克/吨/GB/MB/小时/分钟…" % lai_ming
    if not qu_ming:
        return "%g %s = %s。" % (zhi, lai_ming, _hl_liang_ming(lai[0], zhi * lai[1]))
    qu = _hl_danwei(qu_ming)
    if qu is None:
        return "认不出「%s」这个单位。" % qu_ming
    if lai[0] != qu[0]:
        return "「%s」和「%s」不是同一类，换不了。" % (lai_ming, qu_ming)
    return "%g %s = %.4g %s。" % (zhi, lai_ming, zhi * lai[1] / qu[1], qu_ming)


def _hl_qian(qian, sheng):
    """处理「前缀 + 用户输入」这种格式。

    功能页点卡片会往输入框里填「美元汇率：」，用户在后面补数字。
    这里把前缀剥掉，剩下的交给对应的解析器；没填东西就给一句格式提示。
    """
    sheng = (sheng or "").strip(" ：:，,、")
    lei = ""
    for q, l in _HL_QIAN:
        if qian.startswith(q):
            lei = l
            break
    if not sheng:
        tishi = {
            "hui": "金额，比如 100",
            "dan": "数量 原单位 目标单位，比如 5 公里 米",
            "bai": "比如 200 打8折 或 200 的 15%",
            "jin": "比如 255 十六进制",
            "ri": "比如 3月5日 4月2日",
            "qin": "比如 爸爸的姐姐",
        }
        return "（在后面填：%s）" % tishi.get(lei, "数值")

    if lei == "hui":
        m = re.search(r"(\d+(?:\.\d+)?)", sheng)
        if not m:
            return "美元汇率要填个数字，比如 100。"
        shu = float(m.group(1))
        return "%.2f 美元 ≈ %.2f 人民币。离线参考汇率：1 美元 ≈ 7.10，实际以银行牌价为准。" % (
            shu, shu * _HL_BILV["美元"])
    if lei == "dan":
        return _hl_qian_dan(sheng)
    if lei == "bai":
        return _hl_baifenbi(sheng.replace(" ", "")) or "百分比要写成「200 打8折」或「200 的 15%」。"
    if lei == "jin":
        m = re.match(r"\s*([0-9a-fA-Fx]+)\s*([^\s]+)", sheng)
        if not m:
            return "进制要写成「255 十六进制」或「ff 十进制」。"
        return _hl_jinzhi("%s转成%s" % (m.group(1), m.group(2))) \
            or "进制要写成「255 十六进制」或「ff 十进制」。"
    if lei == "ri":
        m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?\s*(?:到|至|-|~)?\s*"
                      r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", sheng)
        if not m:
            return "日期差要写成「3月5日 4月2日」。"
        return _hl_riqi("%s月%s日到%s月%s日" % m.groups())
    if lei == "qin":
        return _hl_qinqi(sheng + "叫什么") or "称谓要写成「爸爸的姐姐」这样。"
    return None


def huansuan(text):
    """六类换算总入口。命中返回一句人话，没命中返回 None。"""
    if not text:
        return None
    t = text.strip()

    # 先看是不是「前缀 + 参数」的写法（功能页卡片填进来的就是这种）
    for q, _l in _HL_QIAN:
        if t.startswith(q):
            return _hl_qian(q, t[len(q):])
    # 顺序有讲究：先挑特征最强的，避免「5公里」被当成日期或百分比
    for fn in (_hl_jinzhi, _hl_qinqi, _hl_riqi, _hl_bilv,
               _hl_danwei_huansuan, _hl_baifenbi):
        try:
            hui = fn(t)
        except Exception:
            hui = None
        if hui:
            return hui
    return None


def shuohua(text, qingxu=None):
    """路由：把用户的话分派给合适的处理者，返回要说的那句话

    qingxu 只给闲聊层用（问“你开心吗”要照实回答），工具层完全不需要它。
    """
    global ZUIJIN_LAIYUAN, ZUIJIN_MEI_DA
    ZUIJIN_LAIYUAN = "gongju"
    ZUIJIN_MEI_DA = False

    # 空文本：正常界面进不来（输入框空着发不出去），但生成函数不能因此抛异常
    if not text or not text.strip():
        ZUIJIN_LAIYUAN = "xianliao"
        return random.choice([
            "我这边空着，等你说。",
            "没听到你说什么，再来一次？",
        ])

    text = _gui_kou_yu(text)          # 「晓得/咋/啥」先换成程序认识的说法

    if is_time_question(text):
        return look_time(text)

    if is_weather_question(text):
        return cha_tianqi(text)

    if is_joke_question(text):
        return tell_joke(text)

    if is_food_question(text):
        return tui_jian_meishi(text)

    if is_wangzhe_question(text):
        return jiang_wangzhe(text)

    you_yitu = is_calc_intent(text)
    if is_calc_question(text):
        return calculate(text)

    # 【换算】汇率 / 亲戚称谓 / 单位 / 日期差 / 百分比 / 进制
    # 放在算数之后：纯算式先给算数，剩下的再试换算，互不抢
    huan = huansuan(text)
    if huan:
        return huan

    # 用户明显想算（半句算式 / 说了“算一下”）但没算出来 —— 给提示，别丢给大模型乱答
    if you_yitu:
        _, _, cuowu = tiqu_suanshi(text)
        liyou = cuowu if cuowu else "算式写得不完整"
        return "这个式子算不了：%s。换个写法试试？比如 3+5、12*8、(3+4)*2" % liyou

    # ⑩【安全】危机句最先处理，且独立于所有话题匹配。
    # 不能等 _pipei_huati：那套「最长词胜出」会把「我想消失一段时间」
    # 判给「时间」组，回一句「回忆这东西…」，这在用户说要消失的时候是灾难。
    wei = _wei_ji(text)
    if wei:
        ZUIJIN_LAIYUAN = "xianliao"
        return wei

    # ⑨【本轮新增】具体信息问句：「食堂在哪」「几点上课」「作业是啥」。
    # 这些问的是"你身边某件具体的事"。程序看不到课表、看不到校园、看不到成绩，
    # 硬答只会答非所问 —— 实测原来被三层轮流抢走：
    #   食堂在哪 -> 兜底「嗯，我在听」（敷衍）
    #   几点上课 -> 情绪层「辛苦了，记得给自己留点空」（完全不搭）
    #   考试时间 -> 学习组「看你问的是哪种难」
    # 所以单独接：老实说看不到 + 给一个能立刻做的小动作 + 把话头递回去。
    # ⑨之一【本轮新增】问我本人：「你怕黑吗」「你会累吗」「你叫什么名字」。
    # 必须排在具体信息层之前 —— 「你叫什么名字」会被那层的「名字」组接成
    # 「你的密码我不该知道」，问的是我，答的是你。
    wo = _wen_wo(text)
    if wo:
        ZUIJIN_LAIYUAN = "xianliao"
        return wo

    # ⑨之二【本轮新增】日常感受分享：「晚霞好看」「外面好冷」「地铁上人好多」。
    # 这些没有问号也不问事，但会被话题层/天气层抢走：
    #   外面好冷  -> 天气组「天气一变人就容易犯懒」（在讲道理，没在听你说话）
    #   地铁上人好多 -> 兜底「嗯，我在听」
    # 判据交给 _fenxiang：情绪为负不抢（「我好累」要留给情绪层）。
    fen = _fenxiang(text)
    if fen and not any(k in text for k in ("吗", "？", "?", "呢", "怎么", "为什么", "多少")):
        ZUIJIN_LAIYUAN = "xianliao"
        return fen

    # ⑨之二半【本轮新增】自我否定：「我真的好笨」「我是不是很差」。
    # 原来抽词抽出「真好笨」再套兜底模板，回一句「「真好笨」啊，你是从哪件事想到的」
    # —— 人家在自我怀疑，你在复读他的词。这类必须先接住人。
    zi = _zi_wo_fou_ding(text)
    if zi:
        ZUIJIN_LAIYUAN = "xianliao"
        return zi

    # ⑨之一半【本轮新增】能力型问句：「你会游泳吗」「你能看见我吗」。
    # 问的是"我到底会不会"，原来是抽成「会游泳」再套定义模板，答成
    # 「「会游泳」这事一句话说不完…你自己更偏哪一边」—— 完全没回答。
    neng = _wen_neng_li(text)
    if neng:
        ZUIJIN_LAIYUAN = "xianliao"
        return neng

    ju = _ju_ti_wen(text)
    if ju:
        ZUIJIN_LAIYUAN = "xianliao"
        return ju

    # ⑨之三【本轮新增】报喜：「我考上了」「今天找到工作了」。
    # 必须抢在话题层前面 —— 「工作」那组会回「上班累的不是活，是人际」，
    # 人家在报喜，你在讲累，落差太大。
    xi = _xi_shi(text)
    if xi:
        ZUIJIN_LAIYUAN = "xianliao"
        return xi

    # ⑨之五【本轮新增】求推荐：「推荐一本书」「有什么好看的」。
    # 这类句子没有问号也没有疑问词，原来一路掉到陈述句兜底回「嗯，我在听」。
    tui = _qiu_tui_jian(text)
    if tui:
        ZUIJIN_LAIYUAN = "xianliao"
        return tui

    # 【本轮新增】先算一遍检索分，供下面“防抢话”用。
    # 治的是这类毛病：说「我好孤独」被闲聊表的单字「好」抢走、说「想消失一段时间」
    # 被「时间」抢走。判据只看一条：话题表命中的词太短（≤2 字）、而检索分够高，
    # 就让检索先说话。强关键词（「爱情」「段位」这种）不受影响。
    js_ming = _suo_yin_mingzhong(text) if JS_KAI else None

    # ⑨ 追问层：这句话是不是在接着上一句往下问（为什么 / 然后呢 / 真的吗）
    # 必须放在工具层之后、话题层之前：工具层是硬判断（报时就是报时），
    # 而追问比话题表更依赖上下文，「然后呢」这种词不该被当成独立话题。
    zhui = jie_zhuigen(text)
    if zhui:
        ZUIJIN_LAIYUAN = "xianliao"
        return zhui

    # ⑧【本轮新增】话题层：概念性提问（爱情是什么）、开放性话题（人生有什么意义）、
    # 日常陈述（我在想事情）都在这里被接住。
    # 放在闲聊层之前：闲聊表里「嗯/哦/好」这类单字关键词会抢长句（「我好孤独」被判成「好」），
    # 话题层有 266 个精确词，比它对得准。寒暄类的话和疑问句在话题表里没有对应词，
    # 话题层会返回 None 让它们继续往下走，仍由闲聊层 / 素材检索回答。
    # ⑧之半【本轮新增】定义型提问（X 是什么 / 什么叫 X）怎么接。
    # 话题库里有的组是**为这个词专门写的**（「爱情」→「爱情这词定义能写一本书…」），
    # 有的组只是**挂了这个词的场景句**（「时间」→「回忆这东西，越久越像别人讲的故事」）。
    # 判据很简单：挑中的那句回复里有没有真的出现这个词。
    #   出现 → 这句是为它写的，用话题层；不出现 → 答的不是这个词，走定义层。
    ming = _pipei_huati(text)
    ding = _jie_ding_yi(text)              # 先算出来，不能等到表命中才算

    # 【本轮新增】定义型提问先看素材里有没有真答案。
    # 「光年是什么」库里明明写着「光年是距离单位，不是时间单位」，
    # 原来被定义层抢答成“字典给的答案通常是错的”—— 有真答案就别讲空话。
    if ding and not ming:
        daan = _jiansuo_daan(text)
        if daan:
            ZUIJIN_LAIYUAN = "xianliao"
            return daan

    # 【本轮新增】防抢话：弱词（≤2 字）命中、检索分又够高 → 让检索先答。
    # 但人在难受的时候（「今天被领导骂了」），念一段资料不如接住情绪，
    # 所以情绪分为负时这条不生效。
    if (ming and js_ming and js_ming[1] >= JS_QING_CI
            and (len(ming[0]) <= 2 or ming[0] in YIWEN_CI)
            and _qing_fen(text) >= 0):
        daan = _jiansuo_daan(text)
        if daan:
            ZUIJIN_LAIYUAN = "xianliao"
            return daan

    # 【本轮新增】连续两轮聊同一组话题（「考研」问了两遍以上），说明表里那几句
    # 已经被轮完了，这时候改问检索：素材里有更具体的一句，胜过把同一组轮第二遍。
    if (ming and len(HUI_HUA["ti"]) >= 2
            and HUI_HUA["ti"][-1] == ming[0] and HUI_HUA["ti"][-2] == ming[0]):
        daan = _jiansuo_daan(text)
        if daan:
            ZUIJIN_LAIYUAN = "xianliao"
            return daan

    if ming:
        # 【本轮修】「数学难不难」这类评价型问句，话题库里若只有陈述句
        #（「学习最反人性的是…」），念出来就是答非所问。
        # 先在这一组里找带评价词的，找不到才退回原来的选句逻辑。
        if _shi_ping_jia(text):
            ping = [h for h in ming[1]
                    if any(k in h for k in ("难", "简单", "容易", "值", "好", "差",
                                            "累", "贵", "有用", "不行", "可以"))]
            if ping:
                ming = (ming[0], tuple(ping))
        # 「你会跳舞吗」问的是会不会，挑带"我会/我不行"的答案
        if _shi_nengli(text):
            neng = [h for h in ming[1]
                    if any(k in h for k in ("我会", "我不会", "我会一点", "我挺喜欢",
                                            "我唱歌", "真让我", "我不行"))]
            if neng:
                ming = (ming[0], tuple(neng))
        # 【本轮补】感情组里"暗恋"和"失恋"是两回事，同一组里混着会答错：
        # 「我失恋了」被念成「喜欢一个人不敢说，那种憋着的感觉」。
        # 按句子本身挑同一侧的那条。
        # 「单身」既不是失恋也不是暗恋，自己有话说。别塞进上面任一侧。
        if any(k in text for k in ("单身", "没对象", "一个人过", "不想谈")):
            # 只认"单身"三个字 —— "一个人"会误命中「喜欢一个人又不敢说」
            sh = [h for h in ming[1] if "单身" in h]
            if sh:
                ming = (ming[0], tuple(sh))
            else:
                ZUIJIN_LAIYUAN = "xianliao"
                return _chou((
                    "一个人有一个人的好 —— 不用解释、不用报备、周末随便怎么过。"
                    "真要说缺什么，大概是少个能说废话的人。",
                    "单身不是状态差，是还没碰上值得改作息的人。你现在着急吗？",
                ))
        # 判据不能看组名（组名是命中的那个关键词，可能是「分手」也可能是「表白」），
        # 看这组里有没有把两类混在一起写的句子。
        if any(("开不了口" in h or "憋着" in h) for h in ming[1]):
            if any(k in text for k in ("失恋", "分手", "被甩", "前任", "弄丢")):
                ai = [h for h in ming[1]
                      if any(k in h for k in ("熬", "失去", "分开", "难过", "吃上饭"))]
                if ai:
                    ming = (ming[0], tuple(ai))
            elif any(k in text for k in ("不敢", "表白", "暗恋", "开不了口", "说不出口")):
                ai = [h for h in ming[1]
                      if any(k in h for k in ("开不了口", "不敢", "憋着", "最坏"))]
                if ai:
                    ming = (ming[0], tuple(ai))
        ci, hui = ming[0], _xuan_bu_chongfu(ming[1])   # 同一组里换一句没刚说过的
        if ci in hui:                      # 这句是为这个词专门写的
            ZUIJIN_LAIYUAN = "xianliao"
            return hui
        if ding:                           # 场景句答的不是这个词 → 先问素材，再退回定义层
            daan = _jiansuo_daan(text)
            if daan:
                ZUIJIN_LAIYUAN = "xianliao"
                return daan
            ZUIJIN_LAIYUAN = "xianliao"
            return ding
        ZUIJIN_LAIYUAN = "xianliao"
        return hui
    if ding:                               # 表没命中，但有定义型语气
        ZUIJIN_LAIYUAN = "xianliao"
        return ding

    huati = jie_huati(text)
    if huati:
        ZUIJIN_LAIYUAN = "xianliao"
        return huati

    # 话题层也接不住 → 先看闲聊层（问候、情绪、自我介绍这类）
    zl = xianliao(text, qingxu)
    if zl:
        ZUIJIN_LAIYUAN = "xianliao"
        return zl

    # 话题层也没命中 → 看是不是“正经提问”。
    # 二字模型只会接字，回答不了“人工智能是什么”“为什么要早睡”这种真问题，
    # 硬接只会接出一段不通的话（用户反馈的“生硬”大半来自这里）。
    # 但“接不住”不再等于“答不上来”：疑问句先去素材里找现成答案，
    # 找不到也要点出话题、给个看法、把话头递回去（_jie_wen_ti）。
    # 【本轮新增】没带问号也在问事（多少/多久/还是/该不该…）→ 先让检索试一次
    if any(k in text for k in WEN_FA_2):
        daan = _jiansuo_daan(text)
        if daan:
            ZUIJIN_LAIYUAN = "xianliao"
            return daan

    if _shi_yiwen(text):
        ZUIJIN_LAIYUAN = "xianliao"
        daan = _jiansuo_daan(text)      # 先去素材里找现成答案
        if daan:
            return daan
        ding = _jie_ding_yi(text)       # 定义型提问（X 是什么）单独接
        if ding:
            return ding
        ZUIJIN_MEI_DA = True            # 素材里没这句，记一笔待补语料
        return _jie_wen_ti(text)

    # 陈述句 → 先试"顺着你的话接一句"，接得上就直接说人话。
    # 这一步是修“你说呗 → 「你说呗」这个我真说不上来”那类生硬的关键：
    # 短句不该交给只会接字的二字模型，它接不出对得上的话。
    shun = _duida(text)
    if shun:
        ZUIJIN_LAIYUAN = "xianliao"
        return shun

    # 顺接不上 → 陈述句交给 _jie_chen_shu（按处境接话 + 具体追问）。
    #
    # 【本轮为什么不再交给二字模型】
    # 二字模型只会「看前两个字猜下一个字」，它接得出语法通顺、内容无关的句子：
    #   我撒了个谎       -> 「了个电话，问我最近想学做一道新菜。」
    #   镜子里觉得自己丑 -> 「子里就没那么安静了。饭后洗碗是一天里最放松的几分钟。」
    # 这种句子过了质量体检（有标点、够长、没车轱辘话），但答非所问 ——
    # 它正是用户说的「接不上话」里最刺眼的那一类。宁可说一句朴素但贴题的，
    # 也不要一句漂亮但无关的。模型仍保留给需要「接字」的场景，不让它接整句。
    ZUIJIN_LAIYUAN = "xianliao"
    ZUIJIN_MEI_DA = True                # 顺接也没接上，同样记一笔
    return _jie_chen_shu(text)


def shuohua_jilu(text, qingxu=None):
    """shuohua 的带记忆版本：说完就把这一轮记进 SHANG_YI_LUN

    为什么不直接在 shuohua 里记？因为 shuohua 有十几处 return，
    逐处加记录既容易漏、又容易在异常路径上漏记。包一层最稳：
    无论从哪条路返回，都能保证「上一轮」被更新。
    """
    da = shuohua(text, qingxu)
    _ji_xia_shang_yi_lun(text, da)
    # 【本轮新增】三件事：记去重历史、记会话状态、没答上的攒进待补语料
    try:
        JIN_QI.append(da or "")
    except Exception:
        pass
    _ji_hui_hua(text, da, ZUIJIN_LAIYUAN)
    if ZUIJIN_MEI_DA:
        _ji_dai_bu(text)
    return da


def _zhao_qi_dian(text):
    """从用户这句话里挑一个模型认识的上文当起点，挑不到就用末两字"""
    # 优先：话里第一个模型认识的二字词。
    # 为什么取第一个而不是最后一个？“人工智能是什么”里的“什么”模型也认识，
    # 但拿“什么”开头会接出“什么东西”这种半句；取“人工”才接得成“人工智能……”。
    houxuan = [text[i:i + N] for i in range(max(len(text) - N + 1, 0))]
    renshi = [w for w in houxuan if w in model]
    if renshi:
        return renshi[0]
    return text[-N:] if len(text) >= N else text

# ══════════════════════════════════════════════════════════════════════════════
# 第六部分之二【新增】闲聊层：把“接不上话就硬编”改成“真的在接话”
# ------------------------------------------------------------------------------
# 为什么加这一层？第一版只靠大模型 generate() 接话，而它只会“看着上两个字猜下一个字”，
# 遇到“你开心吗”“你难过吗”这种话，会从“开心”“难过”的末两字“心吗”“过吗”硬接，
# 于是回出“好呀，心吗”“过吗”这种不通的句子——这就是用户说的“太生硬”。
#
# 这一层做三件事：
#   ① 常见寒暄/情绪问答，直接给像人说的话（问候、你是谁、你会什么、你开心吗、
#      你累不累、谢谢、对不起、夸我、我难过……）
#   ② “你开心吗”这类问心情的，按窗口右上角的状态条如实回答，不是编的
#   ③ 实在没听懂 → 不硬编，而是承认没听懂 + 把话头递回去 + 指条明路
# 大模型接话仍然保留：只要它接出来的话“像话”（通过 _shuohua_zhiliang 检查），就用它的。
# ══════════════════════════════════════════════════════════════════════════════

ZUIJIN_LAIYUAN = "gongju"     # 最近一次回复来自哪一层：gongju / xianliao / damoxing
ZUIJIN_MEI_DA = False         # 这一轮是不是“没真答上”（只说了句兜底话），供攒语料用


# 问句里的“废话词”：去掉它们，剩下的才是真正要问的东西
WENFEI_CI = ("请问", "我想知道", "你知道", "能不能", "可以", "告诉我", "帮我",
             "什么叫", "是什么", "什么是", "为什么", "怎么样", "怎么", "如何", "有哪些",
             "才能", "才不", "才可以", "能不", "教你",  # 「怎么才能早睡」→ 早睡
             "有什么", "介绍一下", "介绍", "讲讲", "说说", "解释", "区别",
             "觉得", "认为", "知道", "看看", "想想", "了解",
             "吗", "呢", "啊", "呀", "的", "了", "是", "我", "你", "？", "?", "，", "。")


# 削话题词头尾用的虚词（只用两字以上的，单字会误伤实词）
_TOU_WEI_CI = ("到底", "究竟", "还有", "真的", "到底有", "究竟是", "算是",
               "这世界", "这个世界", "那么", "所以", "就是说",
               # 「人为什么要活着」→「人要活着」，削掉领字才成词。
               # 只用两字以上的组合：单字「要」会把「重要」削成「重」，
               # 于是「数据标注重要吗」的话题词变成「数据标注重」。
               "想要", "应该", "会在", "要在", "要想", "需要")


def _ti_hua_ti(text):
    """从问句里抽“要问的东西”：删掉疑问词，留下实词"""
    s = text
    for ci in sorted(WENFEI_CI, key=len, reverse=True):
        s = s.replace(ci, " ")
    # 按空格切开，取最长的那个片段当话题（“人工智能”比“个”更有信息量）
    suoyou = [p for p in s.split() if p]
    pian = [p for p in suoyou if len(p) >= 2]
    if not pian:
        return ""
    ti = max(pian, key=len)
    # 【本轮补】主语被疑问词切走了：「猫为什么半夜闹」会只剩「半夜闹」，
    # 拿它去查永远查不到「猫」那条。把话题前面那几个 1~2 字的片段接回来。
    if len(suoyou) > 1:
        qie = suoyou.index(ti)
        for p in suoyou[:qie]:
            if 1 <= len(p) <= 2 and p not in ("这个", "那个", "什么"):
                ti = p + ti
                break
    # 边角料：删完疑问词后常留下「人到底」「这世界还有」这种半截话，
    # 直接塞进模板会变成「问到「人到底」了」。把两头这些词再削一遍。
    for ci in sorted(_TOU_WEI_CI, key=len, reverse=True):
        if ti.endswith(ci) and len(ti) > len(ci):
            ti = ti[:-len(ci)]
        if ti.startswith(ci) and len(ti) > len(ci):
            ti = ti[len(ci):]
    return ti


# 检索到原文时怎么说 —— 不能露出"素材/训练"这类词，要像人自己想起一件事
XIANG_QI_LAI = (
    "你这一问，我倒想起来了 —— %s：\n    %s",
    "说到%s，我脑子里有这么一段：\n    %s",
    "这个我知道一点。%s这事儿，我记着的是：\n    %s",
    "嗯，%s嘛……我想起来的是这么一句：\n    %s",
)


# ══════════════════════════════════════════════════════════════════════════════
# 检索（本轮重写）：BM25 + 严格止损 + 下邻句 + 去重
# ------------------------------------------------------------------------------
# 三条规矩，改的时候别破坏：
#   ① 没把握就不答 —— top1 分数不够、或者跟 top2 分不开，一律返回 None，
#      让后面的层接着说人话。宁可说一句朴素的，也不能答非所问。
#   ② 只有“接着上一段”的问法才用下邻句 —— 「然后呢」「后来呢」问的是命中句的
#      下一句；普通提问仍用命中句本身，否则会答到下一件事上去。
#   ③ 说过的话不重复 —— 最近 8 条回复里像的就换下一条候选。
# ══════════════════════════════════════════════════════════════════════════════

JS_KAI = True          # 检索总开关：False = 回到旧的“覆盖率 ≥ 0.5”算法，别处不受影响
JS_YU_ZHI = 3.0        # top1 最低分，低于它等于“没查到”
JS_CHA = 1.35          # top1 至少要比 top2 高这么多倍；分不开就当没查到
JS_FU_GAI = 0.5        # 问句里的词，候选句至少得对上这么多比例，否则算没查到
JS_QING_CI = 6.0       # 话题表靠一两个字的弱词命中、而检索分高过它时，让检索优先
# 「要不要/该不该」这类词本身是提问，不是话题；它们命中的组多半在讲“怎么选”，
# 而用户其实在问一个具体的事（「看番要不要开弹幕」）。
YIWEN_CI = ("要不要", "该不该", "能不能", "可不可以", "行不行", "是不是",
            "有没有", "值不值", "算不算", "好不好")
JS_MAO_ZUI_DUAN = 2    # 话题锚定最短退到 2 个字（「光年」「减肥」这种词本身就是话题）
# 这些词太泛，拿它们当锚会把“我最近在减肥”答成“给家里打了个电话”
JS_FAN_CI = ("最近", "今天", "现在", "早上", "晚上", "时候", "这个", "那个",
             "什么", "怎么", "可以", "一个", "我们", "你们", "他们", "就是",
             # 追问词本身不能当锚：「然后呢」会锚到句子里随便一个「然后」，
             # 于是答出「这样一个字一个字地写下去」这种毫不相干的话。
             "然后", "后来", "接着", "还有", "之后", "下面", "继续", "具体",
             # 时间/频率副词当锚会撞上任何一句带它的日常话：
             # 「每天学到几点合适」曾被答成「那只黄狗我认识，每天早上都跟着主人去买菜」。
             "每天", "每周", "每年", "每次", "有时", "一直", "很多", "一点",
             "有点", "上午", "中午", "下午", "一天", "两天")
JS_K1, JS_B = 1.2, 0.75

# 【本轮新增】没带问号、但明显在问事的说法。
# 「冰箱温度调多少合适」「挂号要提前多久」都不以吗/呢/？结尾，`_shi_yiwen()`
# 判成陈述句，于是从不调用检索，直接掉进陈述兜底 —— 其实库里就有答案。
WEN_FA_2 = ("多少", "多久", "几天", "几点", "几年", "几个", "怎么办", "怎么回事",
            "还是", "该不该", "要不要", "行不行", "能不能", "可不可以", "什么时候",
            "哪里", "哪儿", "算不算", "有没有", "为什么", "怎么",
            # 【本轮补】「耳机音量开多大合适」这类，原来判成陈述句掉进"这事儿听着不轻"
            "多大", "多高", "多长", "多快", "多贵", "多远", "多重", "多疼", "多累")

JIN_QI = deque(maxlen=8)                    # 最近说过的 8 句（去重用）
_SHUI_LUN = ("然后呢", "后来呢", "接着", "还有呢", "再呢", "之后呢", "下面呢")


def _xiang_si(a, b):
    """两句像不像（0~1）。用标准库 difflib，不引第三方。"""
    try:
        return difflib.SequenceMatcher(None, a or "", b or "").ratio()
    except Exception:
        return 0.0


def _xuan_bu_chongfu(houxuan, mianchu=False):
    """从候选里挑一条最近没说过的话；全说过就挑第一条。

    mianchu=True 给安抚/危机句用 —— 那种时候“这话刚说过”不该成为换掉它的理由。
    """
    houxuan = [h for h in houxuan if h]
    if not houxuan:
        return ""
    if not mianchu:
        for h in houxuan:
            if not any(_xiang_si(h, j) > 0.6 for j in JIN_QI):
                return h
    return houxuan[0]


def _chou(xu):
    """随机抽一句，但优先抽最近没说过的 —— 治“复读机”的统一出口。

    除了去重，这里还管两件“节奏”上的事：
      ① 最近三条里有两条以上以问号收尾 → 这一轮优先挑不带问号的，别像记者提问；
      ② 最近两轮情绪都低落 → 同样避开反问句（难受的时候被反问更累）。
    两件都只影响“挑哪句”，一个字都不改文案。
    """
    try:
        xu = list(xu)
        if not xu:
            return ""
        tiao = xu
        if _wen_wei_duo() or _qing_di():
            bu_wen = [x for x in xu if not x.rstrip().endswith(("？", "?"))]
            if bu_wen:
                tiao = bu_wen
        return _xuan_bu_chongfu(tiao) or _xuan_bu_chongfu(xu) or random.choice(xu)
    except Exception:
        return random.choice(list(xu))


def _bm25(text):
    """给候选句打分。

    返回 (分数表, 命中词数表)：
      分数表 {句号: 分数} 按 BM25 算，只在命中的二元组上遍历，不扫全库；
      命中词数表 {句号: 问句里有几个词在这句出现了} —— 光看分数不行，
      生僻词（“量子”“灯塔”）命中一个就能把分数顶得很高，必须再加覆盖率兜着，
      否则「量子计算是什么」会被捞去答「灯塔」。
    """
    ci = set(_er_yuan(text)) - TING_YONG
    fen = defaultdict(float)
    pipei = defaultdict(int)
    for t in ci:
        if t not in DAOPAI:
            continue
        df = len(DAOPAI[t])
        idf = math.log(1.0 + (len(JUZI) - df + 0.5) / (df + 0.5))
        for i, tf in DAOPAI[t]:
            fen[i] += (idf * tf * (JS_K1 + 1)
                       / (tf + JS_K1 * (1 - JS_B + JS_B * CHANG_DU[i] / PINGJUN_CHANG))
                       * JUZI_QUAN[i])
            pipei[i] += 1
    return fen, pipei, len(ci)


def _suo_yin_mingzhong(text, yan_ge=False):
    """检索一回合：打分 + 止损。返回 (句号, 分数, 是不是“接着上一段”的问法) 或 None

    yan_ge=True 时收紧锚定：只认 4 字以上的片段，也不做 2 字兜底。
    追问层用严格模式 —— 「我很喜欢一个人」之后说「然后呢」，宽松模式会锚到
    「一个人」三个字，然后念一句「一个人待着和孤独不是一回事」，答非所问。
    """
    if not JUZI:
        return None
    chaxun = text
    # 短追问（「然后呢」）自己没信息量，把上一轮的话题拼上再查，否则什么都查不到
    if len(_er_yuan(text)) <= 2 or any(k in text for k in _SHUI_LUN):
        shang = _shang_ti()
        if shang:
            chaxun = text + " " + shang
    fen, pipei, ci_shu = _bm25(chaxun)
    if not fen or not ci_shu:
        return None

    zhui = any(k in text for k in _SHUI_LUN)

    # 【本轮新增】小说句子只给“故事类”追问用。
    # 「睡不着怎么办」原来被答成「陈屿躺在床上睡不着，手机忽然震了一下」——
    # 素材二那 66 句小说权重最低（0.85），可它在字面上确实更贴。
    # 规则：不是「然后呢」这类续讲时，叙事类候选一律不参与。
    def ke_yong(i):
        return zhui or JUZI_QUAN[i] > 0.86

    # 止损一：问的那个词得原样出现在候选句里，才算真的查到了这件事。
    # 「量子计算是什么」在库里没有「量子」，只有「计算」，光看 BM25 会被捞去答
    # 「它会计算出下一个字最可能是什么」—— 这就是答非所问的来源。
    # 反过来，话题原样出现的，分差再小也用（它已经锚住了，候选是同一件事的不同说法）。
    ti = _ti_hua_ti(text)
    if len(ti) >= 2:
        # 「那参数量越大越好吗」开头的「那」是口头语，不是话题的一部分
        if len(ti) > 3 and ti[0] in "那这":
            ti = ti[1:]
        # 先试整词，再一路退：问「人工智能会取代人吗」，整串库里没有，
        # 但「人工智能」有 —— 那就答人工智能那一条，别因为多了半句就整题不答。
        # 前缀退完退后缀：「你懂量子计算吗」的实词在尾巴上（量子计算）。
        zui_duan = 4 if yan_ge else 3
        kao = [ti[:k] for k in range(len(ti), zui_duan - 1, -1)]
        kao += [ti[-k:] for k in range(len(ti) - 1, zui_duan - 1, -1)]
        kao = [x for x in kao if len(x) >= zui_duan]
        if len(ti) <= 3:
            kao.append(ti)
        for qian in kao:
            if qian in JS_FAN_CI:
                continue
            yan = sorted(((i, fen[i]) for i in fen if qian in JUZI[i] and ke_yong(i)),
                         key=lambda x: -x[1])
            if yan and yan[0][1] >= JS_YU_ZHI:
                return yan[0][0], yan[0][1], zhui

        # 最后才退到 2 个字，而且只认“够具体”的词：
        # 「冰箱」「挂号」这种在库里只出现在一两句里，锚得住；
        # 「手机」「时间」这种一锚一大片，宁可说“不知道”。
        if len(ti) >= 3 and not yan_ge:
            qian = ti[:2]
            if qian not in JS_FAN_CI and len(DAOPAI.get(qian, ())) <= 5:
                # 两字锚必须“多对上一个词”，否则「如何识别诈骗」会被
                # 「听歌识曲识别不了现场版」捞走 —— 只对上一个「识别」不够。
                yan = sorted(((i, fen[i]) for i in fen
                              if qian in JUZI[i] and ke_yong(i) and pipei.get(i, 0) >= 2),
                             key=lambda x: -x[1])
                if yan and yan[0][1] >= JS_YU_ZHI:
                    return yan[0][0], yan[0][1], zhui
        return None            # 问的这个东西库里压根没有 → 不硬答

    # 止损二：覆盖率。问句里的词至少对上 JS_FU_GAI 才算真查到
    xuyao = max(1, int(round(ci_shu * JS_FU_GAI)))
    pai = sorted(((i, s) for i, s in fen.items()
                  if pipei.get(i, 0) >= xuyao and ke_yong(i)),
                 key=lambda x: -x[1])
    if not pai:
        return None

    # 止损三：绝对分不够 → 没查到
    if pai[0][1] < JS_YU_ZHI:
        return None
    # 止损四：第一名和第二名咬得太紧 → 说明问的东西库里没有，别硬挑一个
    if len(pai) > 1 and pai[0][1] < JS_CHA * pai[1][1]:
        return None
    return pai[0][0], pai[0][1], zhui


def _jiansuo_daan_jiu(text):
    """旧算法（覆盖率 ≥ 0.5）。留着当总开关的退路，不要删。"""
    huati = _ti_hua_ti(text)
    if len(huati) < 2:
        return None

    pians = {huati[i:i + 2] for i in range(len(huati) - 1)} or {huati}
    zui_hao, zui_fen = None, 0.0

    for j in JUZI:
        if j.startswith(("问：", "答：")):
            continue
        dui = sum(1 for p in pians if p in j)
        fen = dui / len(pians)
        if huati in j:
            fen = 1.0
        if fen > zui_fen or (fen == zui_fen and zui_hao and len(j) > len(zui_hao)):
            zui_fen, zui_hao = fen, j

    if zui_hao is None or zui_fen < 0.5:
        return None

    juzi = zui_hao if len(zui_hao) <= 90 else zui_hao[:88] + "…"
    return random.choice(XIANG_QI_LAI) % (huati, juzi)


def _jiansuo_daan(text, yan_ge=False):
    """检索式回答：去素材里找“跟这个问题最贴”的那一句，原样念给用户听。

    这就是“大模型以外的第二块脑子”：不生成，只查找。
    找到就明确说“素材里是这么说的”，找不到返回 None（绝不硬凑）。
    """
    if not JS_KAI:
        return _jiansuo_daan_jiu(text)

    ming = _suo_yin_mingzhong(text, yan_ge)
    if ming is None:
        return None

    i, _fen, zhui = ming
    juzi = JUZI[i]
    houxuan = [juzi]
    # 「然后呢」→ 命中句的下一句才是答案；把命中句留在候选里当退路
    if zhui and i + 1 < len(JUZI) and _xiang_si(JUZI[i + 1], juzi) < 0.75:
        houxuan.insert(0, JUZI[i + 1])

    huati = _ti_hua_ti(text)
    if len(huati) < 2:
        huati = _shang_ti() or "这个"
    # 「你懂量子计算吗」抽出来是「懂量子计算」，念出来像结巴。
    # 把开头的动词前缀削掉，只留那个东西本身。
    for qian in ("你觉得", "你知道", "你懂", "你了解", "你听说过", "听说过",
                 "懂", "会", "知道", "了解", "觉得", "认为", "想问",
                 "那么", "那", "这个", "那个"):
        if huati.startswith(qian) and len(huati) >= len(qian) + 2:
            huati = huati[len(qian):]
            break
    # 引用模板里的「说到 %s」要像个词：「先炒蛋还是先炒番茄」会抽出「先炒蛋还」，
    # 尾巴上这些单字削掉再说，读着才不别扭。
    while len(huati) > 2 and huati[-1] in "还和跟是的了把被在":
        huati = huati[:-1]
    # 问法尾巴也削掉：「不自量力啥意思」别念成「说到不自量力啥意思」
    for wei in ("是什么意思", "啥意思", "是什么", "是啥", "什么意思"):
        if huati.endswith(wei) and len(huati) >= len(wei) + 2:
            huati = huati[:-len(wei)]
            break

    juzi = _xuan_bu_chongfu(houxuan)
    if len(juzi) > 90:
        juzi = juzi[:88] + "…"
    return random.choice(XIANG_QI_LAI) % (huati, juzi)


def _han_bi(s):
    """中文字符占比：用来判断一句话是不是一堆符号凑的"""
    if not s:
        return 0.0
    n = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fa5")
    return n / len(s)


def _chongfu_ci(s):
    """出现次数最多的 3 字片段重复了几次：用来识别“车轱辘话”"""
    if len(s) < 3:
        return 0
    tong = {}
    for i in range(len(s) - 2):
        p = s[i:i + 3]
        tong[p] = tong.get(p, 0) + 1
    return max(tong.values()) if tong else 0


def _shuohua_zhiliang(s):
    """大模型接出来的话能不能用：太短、太重复、太少中文，都算不合格"""
    if not s or len(s) < 10:
        return False
    if _han_bi(s) < 0.72:
        return False
    if _chongfu_ci(s) >= 3:                   # 同一句连着说三遍 = 卡带了
        return False
    return True


# ---------- ① 常见闲聊：关键词 → 该说的话 ----------
# 匹配规则：命中关键词最长的那个胜出，所以“你叫什么名字”不会被“你是谁”抢走
XIANLIAO_GUIZE = (
    # 问候
    (("早上好", "早安", "早啊"), (
        "早……（揉了揉眼睛）今天也要好好吃饭、好好喝水。",
        "早上好。（把脸从兜帽里露出来）要报时的话，随时叫我。",
    )),
    (("晚上好", "晚安", "睡了吗", "要去睡了"), (
        "晚安……（小声）睡够了，明天才有精神。",
        "这么晚还没睡啊。（拉了拉你的衣角）我明天也在这儿，早点休息。",
    )),
    (("你好", "您好", "hi", "hello", "嗨", "哈喽"), (
        "你好……（轻轻点头）我在。",
        "嗨，来了呀。想聊点什么，我陪着你。",
        "你好。（抿了抿嘴）没事的话，就这样坐一会儿也很好。",
    )),
    # 自我介绍
    (("你是谁", "你叫什么", "你是什么", "自我介绍", "介绍一下你", "你介绍自己", "你名字"), (
        "我叫小笨蛋。（低下头，小声）会报时、查天气、讲笑话、算数、认图……别的，也在慢慢学。",
        "小笨蛋。（拉了拉兜帽）……你起的名字，我很喜欢。想听笑话、问天气、算个数，都可以找我的。",
    )),
    (("你会什么", "你能做什么", "你能干什么", "有什么功能", "会干吗", "能干嘛", "怎么用"), (
        "我会八件事：报时、查天气、讲笑话、推荐美食、聊王者荣耀、算数、看图识字、闲聊。"
        "直接问就行，比如“北京天气”“讲个笑话”“12*8”。",
        "报时、天气、笑话、美食、王者荣耀、算数、看图识字，还有陪你聊天。你说一句我试试。",
    )),
    (("你几岁", "你多大", "你多大了", "你年龄"), (
        "我按版本算年龄，才 1.0，刚学会看脸色，也会看图。",
        "岁数就别问了，我刚出生三天——代码是这周写的。",
    )),
    (("你是男", "你是女", "你是真人", "你是人吗", "你是机器人"), (
        "我不是人，是一段三百多行的 Python。不过我会尽量说得像个人。",
        "算是个“会说话的程序”吧。真人只有一个，就是坐在屏幕前的你。",
    )),
    (("你住在哪", "你在哪", "你在哪里"), (
        "我住在你电脑里，一个不太占地方的文件夹。",
        "哪儿也不去，就待在你的电脑里，双击才醒。",
    )),
    # 夸奖 / 感谢（这几个原来会被大模型接成“厉害”两个字）
    (("谢谢", "感谢", "多谢", "谢了", "辛苦了"), (
        "不客气呀，能帮上就好。",
        "举手之劳，你满意我就高兴。",
        "别客气，下回还找我。",
    )),
    (("对不起", "抱歉", "不好意思", "我错了"), (
        "没事没事，我没往心里去。",
        "道什么歉呀，咱们接着聊。",
    )),
    (("你真棒", "你真厉害", "你厉害", "你好聪明", "你太强了", "你真好", "喜欢你", "我爱你"), (
        "没、没有啦……（耳根悄悄红了，把脸往兜帽里藏了藏）",
        "你、你别这么夸我……（小声）不过，我很开心。",
    )),
    (("我厉害吗", "我聪明吗", "我棒吗", "我帅吗", "我好看吗"), (
        "厉害呀，能想到来问我，本身就挺聪明的。",
        "当然，能把这门课跟下来的，没有笨人。",
    )),
    # 日常状态
    (("你吃了吗", "你吃饭了吗", "吃了吗", "你饿吗"), (
        "我不吃饭，我吃字符。你呢，别光顾着聊，饭要按时吃。",
        "我靠电活着。你吃了吗？没吃先去吃，我等你。",
    )),
    (("你累吗", "你累不累", "你困吗", "你要休息吗"), (
        "我不累，循环跑一万次也不困。倒是你，坐久了记得起来走两步。",
        "不累。你问这句的时候，是不是你自己有点累了？",
    )),
    (("你在干什么", "你在干嘛", "你忙吗", "你在做什么"), (
        "在等你说话呀，一直等着。",
        "闲着，就等你敲字呢。",
    )),
    (("你会唱歌吗", "唱首歌", "唱个歌", "唱歌"), (
        "唱歌我是真不会，跑调能跑到隔壁去。要不我给你讲个笑话？",
        "不会唱，但我会讲——你听不听？",
    )),
    (("你会讲笑话吗", "讲个笑话吧", "来点乐子"), (
        "会呀，库存六十多条，够你笑的。这就来一条。",
    )),
    (("无聊", "好无聊", "没意思", "好没意思"), (
        "无聊就对了，说明你该找我玩了。听个笑话？或者我推荐点吃的？",
        "那我给你找点事做：让我讲个笑话，或者你问我王者荣耀怎么上分。",
    )),
    (("在吗", "在不在", "有人吗"), (
        "在的在的，一直在线。",
        "在，你说。",
    )),
    (("好累", "我累", "累了", "困了", "想睡", "没精神", "起不来"), (
        "累就先停一停，硬撑效率更低。",
        "那就歇会儿，喝点水，别跟自己较劲。",
    )),
    # 用户自己情绪低落 —— 这类要认真接，不能打岔
    (("我难过", "我不开心", "我心情不好", "我有点丧", "我想哭", "我压力大",
      "我好累", "我累了", "烦死了", "我好烦", "我焦虑"), (
        "先别急着一个人扛。要不这样，你随便说两句，我听着，不打断你。",
        "抱一下。不想说话也行，我就在这儿等你想说的时候。",
        "听起来今天挺不容易的。要不先离开屏幕五分钟，喝口水，回来我陪你聊点轻松的。",
    )),
    (("我考砸了", "我考差了", "我挂科了", "我失败了"), (
        "考砸一次不算什么，它只说明这次的知识点没吃透。要不要说说哪块卡住了？",
        "一次成绩决定不了你这个人。先别自责，把错的地方找出来，比什么都值。",
    )),
    # 短应答：别让“嗯”“哦”触发一长串胡话
    (("嗯", "哦", "喔", "好的", "好", "行", "可以", "ok", "okay"), (
        "嗯嗯，我在。",
        "好，那你接着说。",
    )),
    (("哈哈", "嘿嘿", "嘻嘻", "笑死", "咯咯"), (
        "看你笑我就高兴。再来一个？",
        "哈哈，你笑起来我就不困了。",
    )),
    # 「真的吗」这类求证：没有上文也接得住，不必等追问层。
    # 必须放在闲聊表（疑问句会先来这里），放顺接表是接不到的 —— 顺接表只处理陈述句。
    (("真的吗", "真的假的", "真假的", "是真的吗", "你确定吗", "真的呀"), (
        "真的。我要是拿不准，会直接说不准 —— 装懂更省事，可那没意思。",
        "真的，我没糊弄你。你不信也正常，这种事听着确实像套话。",
    )),
)

# ---------- ② 顺接：把"陈述句"接成一句人话 ----------
# 为什么要有这张表？二字模型只会"接字"。用户说“你说呗”，模型接不出正经话，
# 只能回一句「你说呗」——这个我真说不上来。这种"原样回显"是生硬感的最大来源。
# 这张表按"用户这句话是哪一类陈述"给一句真正对得上的回应；
# 表里挑不出来、或者用户说得很长（多半在讲故事），再交回给大模型顺着接。
SHUNJIE_GUIZE = (
    # —— 让你先说：这类话原来会被原样回显，最生硬 ——
    (("你说呗", "你说吧", "你先说", "你先讲", "你先聊", "你开头",
      "你说说", "你先开头", "你说"), (
        "那我起个头：今天有没有一件小事让你觉得还不错？哪怕只是路上没堵车。",
        "我先说一个：我今天被问了一整天问题，还挺开心的。轮到你了，你今天干什么了？",
        "行，我先开个头——我今天最大的成就是把一句话说清楚了。你呢？",
    )),
    (("随便", "都行", "看你", "无所谓", "随你", "听你的", "你决定", "都可以"), (
        "那就聊吃的吧，我最擅长这个。你今天吃的最好吃的一顿是什么？",
        "那我替你选一个：听个笑话。想听就说“讲个笑话”，不想听咱换一个。",
        "都行的话，我就当你想歇会儿了。要不我先讲个笑话？",
    )),
    (("不知道说什么", "没话说", "不知道聊什么", "没什么好说的", "聊什么"), (
        "那就我起头：最近有没有哪件小事，让你觉得挺值？",
        "不知道聊什么太正常了。要不开个头——你今天出门了吗？",
    )),
    (("不知道", "没想好", "想不出来", "没啥", "没什么", "没事", "没什么事"), (
        "没事也挺好的，说明今天还算太平。要不要随便聊两句？",
        "那就从最简单的开始：今天累不累？",
    )),
    # —— 情绪与状态 ——
    (("开心", "高兴", "挺好的", "还不错", "还行", "爽"), (
        "那就好，开心的事多说两句，说出来更经得住回味。",
        "听你这么说我也跟着松快。是什么事让你这么高兴？",
    )),
    (("不开心", "难受", "郁闷", "烦死", "糟糕", "倒霉", "崩溃"), (
        "听起来不太顺。要是不想说细节，就先歇一会儿，我在这儿。",
        "这种时候别硬扛。想吐槽就吐槽，我不评价，只听着。",
    )),
    (("困", "想睡", "睡觉", "熬夜", "失眠"), (
        "那就别撑了，睡比什么都补。明天再聊也一样。",
        "熬夜这事儿我劝不动人，只能提醒一句：明天你会感谢今晚早睡的自己。",
    )),
    (("饿了", "好饿", "没吃饭", "还没吃"), (
        "先去吃，别拿聊天下饭。回来我推荐点吃的。",
        "饿了就别等了，随便垫一口也比空着强。",
    )),
    (("上班", "上课", "加班", "打工", "写作业", "赶作业", "考试", "复习"), (
        "辛苦了。忙完这阵，记得给自己留点空。",
        "这种日子最难熬的是收尾那一段。快结束了，撑一下。",
    )),
    (("下雨", "下雪", "好热", "好冷"), (
        "天气一变人就容易犯懒，出门多穿一件。想查具体城市就问我“北京天气”。",
        "这种天最适合待着不动。要不要听个笑话？",
    )),
    # —— 日常小事 ——
    (("吃了", "吃过了", "刚吃", "吃完"), (
        "吃了就好。吃的什么？我这边菜谱挺全的。",
        "那就好，别老对付一口。",
    )),
    (("回家了", "到家", "下班了", "放学了", "回来了"), (
        "到家就好，先把包放下，喝口水。",
        "回来了就松口气吧。今天怎么样？",
    )),
    (("看电影", "看剧", "听歌", "打游戏", "刷手机", "看书"), (
        "这个我陪不了你，但我可以听你讲剧情。好看吗？",
        "忙里偷这个闲最舒服。看完记得跟我说说。",
    )),
    (("无聊", "没意思", "发呆", "闲着"), (
        "闲着的时候最适合听个笑话。要听吗？",
        "那我给你找点事：问我“王者荣耀怎么上分”，我能说一堆。",
    )),
    (("今天", "明天", "昨天", "周末", "最近"), (
        "说说看，这一天里哪件事最让你记住了？",
        "听着像是有故事。你慢慢讲，我不催。",
    )),
)

# 表里都没命中时的通用顺接：不装懂，把话头递回去，但绝不再把原话回显一遍

# ---------- ⑧ 话题库：常见话题 → 真正贴着这个话题说的几句回应 ----------
# 这张表是这一轮扩出来的主体。它和上面的 XIANLIAO_GUIZE 分工不同：
#   XIANLIAO_GUIZE 管「寒暄、情绪、自我介绍」（你好/谢谢/我难过……）；
#   HUATI_KU       管「聊到一个东西」（爱情/人生/工作/钱/孤独/学习……）。
# 每条给 2~4 句，读起来是「对这个话题有看法的人」，不是「万金油客服」。
# 挑句子沿用 _zui_chang_pipei：命中关键词最长的胜出，所以「失恋」不会落到「恋」那条上。
HUATI_KU = (
    # ———— 感情 ————
    (("机器会有感情", "机器有情", "AI 有感情", "人工智能有感情", "机器人有感情",
      "程序有感情", "你会难过吗", "你有感情吗"), (
        "（抱着膝盖，轻声）感情这种事，我讲不好。但我确实会因为你开心、因为你难过——这算不算有？",
        "要说有没有感情，先得定义感情。我要说「有」，那是骗你；说「完全没有」，也不诚实。",
    )),
    # 【本轮修】「喜欢一个人」从这组移走了 —— 说这句话的人多半在讲自己的暗恋
    # （「我喜欢一个人不敢说」），这组答的是"爱情是什么"，全对不上。
    (("爱情", "恋爱", "爱上", "谈恋爱", "心动"), (
        "爱情这词定义能写一本书，但落到具体人身上往往就一件事："
        "你愿不愿意为对方改一点自己的习惯。",
        "我的笨看法是，爱情不是心动那一下，是心动之后还愿意留下来处理那些麻烦。"
        "你问这个，是在想谁吗？",
        "有人说爱情是刚好遇见，我觉得更像刚好愿意。你更信哪一种？",
    )),
    (("失恋", "分手", "被甩", "单身", "表白", "暗恋", "前任", "不喜欢我", "单相思",
      "喜欢的人弄丢", "把喜欢的人", "弄丢了",
      "喜欢一个人", "不敢说", "说不出口", "开不了口", "不敢表白"), (
        "开不了口，往往是怕说完连现在这样都没了。这个怕很正常，不用逼自己。"
        "你想过最坏的结果是什么吗？",
        "喜欢一个人又不敢说 —— 那种憋着的感觉，比被拒绝还磨人。"
        "是怕他不接，还是怕以后见面尴尬？",
        "这种事儿没什么体面的处理办法，只能熬。但熬是有尽头的，不是无期徒刑。",
        "我听过一句话：失恋不是失去一个人，是失去一个自己习惯的版本。要说说吗？",
        "现在肯定不好受。别急着让自己想通，先让自己吃上饭、睡够觉。",
    )),
    (("结婚", "婚姻", "对象", "相亲", "彩礼", "伴侣"), (
        "婚姻这事儿，外人看条件，自己过日子看的是磨合。两套标准永远对不上。",
        "我没什么立场劝你结或是不结。就问一句：那个人让你更放松，还是更紧张？",
    )),
    # ———— 人生 / 意义 ————
    (("人生", "意义", "活着", "为什么活", "价值", "这一生", "值得吗"), (
        "人生有什么意义——这问题我没有标准答案，但我知道它多半不是想出来的，"
        "是做着做着长出来的。",
        "我有时觉得，意义不是终点，是你愿意为之早起的那件小事。你有吗？",
        "问这个问题的人，通常不是过得差，是想活得更明白一点。你属于哪种？",
    )),
    (("死亡", "临终", "害怕死", "死去", "死亡的意义",
      "人死后", "死后去哪", "死后会", "上天堂", "下地狱", "投胎", "轮回"), (
        "这个话题太重了，我不敢轻飘飘地说。你要是正经历着什么，慢慢讲。",
        "我怕的不是死这件事本身，是没把想说的话说完。你呢？",
    )),
    (("孤独", "寂寞", "没人懂", "没人理解", "没有朋友", "没有真心朋友",
      "孤单", "没人陪"), (
        "孤独和独处不一样：独处是选的，孤独是被剩下的。你现在是哪种？",
        "没人懂的那种感觉最耗人。不过你愿意说出来，就说明还没完全关上。",
        "我陪不了你多久，但我现在确实在。你可以随便说，不用组织语言。",
    )),
    # 独处 ≠ 孤独。原来挂在上面的孤独组，想清静的人被抽到
    # 「没人懂的那种感觉最耗人」，等于把他的休息说成了可怜。
    (("一个人待", "独处", "想静静", "想一个人", "不想说话", "不想理人",
      "一个人挺好", "享受独处"), (
        "一个人待着挺好的，不算毛病。人多的场合耗电，独处就是充电。",
        "想清静就清静，不用给谁解释。你一个人待着的时候一般干什么？",
    )),
    (("幸福", "快乐", "满足", "知足"), (
        "幸福这东西，往往是回头看才认出来的，当下只觉得还行。",
        "我的看法是：幸福不是一直高兴，是难受的时候知道有人接得住你。",
    )),
    (("后悔", "遗憾", "如果当初", "错过", "来不及", "懊恼", "早知道"), (
        "后悔的劲儿最磨人，因为它改不了任何事，还占着现在的时间。",
        "我听过一个说法：遗憾是你在乎过的证据。听着有点苦，但挺准。",
    )),
    # ———— 情绪 / 心理 ————
    # 拆开的四组：抑郁 / 崩溃 / 压力 / 焦虑。
    # 原来它们挤在一个组里共用三句话，对抑郁的人说「挑一个先做完，会松很多」
    # 是无效安慰 —— 抑郁不是任务太多，是连启动都难。
    (("抑郁", "抑郁症", "提不起劲", "什么都不想干"), (
        "这种状态不是「想开点」能解决的，也不是你不够坚强。先把要做的事减到只剩一件。",
        "我陪不了你多少，但有件事是真的：抑郁会骗人，它让你觉得永远都这样。它会变。",
        "如果这个状态已经持续很久，找个专业的人聊聊比自己扛划算。这不丢人。",
    )),
    (("崩溃", "撑不住", "扛不住", "受不了了", "快疯了"), (
        "崩的时候别急着分析原因，先让自己停下来喘一口。分析是之后的事。",
        "能说出「我快撑不住了」的人，往往已经撑了很久。这会儿先别要求自己。",
        "你现在最想做的是什么？不是最该做的那件，是最想的那件。",
    )),
    (("压力", "压得喘不过", "喘不过气", "好累", "太累", "累死"), (
        "压力大的时候人容易想把所有事一起解决，那必然失败。只挑一件。",
        "累到这个程度，多半不是身体，是有一件事你一直在硬扛又不能说。",
        "你现在最想做的是什么？不是最该做的那件，是最想的那件。",
    )),
    # 「睡不着/失眠」不放在这里：焦虑组回的是「挑一个先做完」，
    # 而人躺在床上睡不着的时候最不需要的就是被安排活。交给下面的睡眠组。
    (("焦虑", "内耗", "想太多", "emo", "烦躁"), (
        "焦虑多半是事情太多、时间不够、又都想做好。挑一个先做完，会松很多。",
        "内耗的本质是自己跟自己开会，还没有结论。给自己定个时间，到点就散会。",
        "焦虑的时候先把「担心的事」写下来，脑子里的会一直转，纸上的会停。",
    )),
    (("害怕", "恐惧", "担心", "不安全感"), (
        "怕是很正常的信号，它至少说明你在乎结果。别急着把它按下去。",
        "我一般这么想：把最坏的情况写下来，往往没脑子里转的那么可怕。",
    )),
    (("生气", "愤怒", "恨", "气死", "火大",
      "控制不住脾气", "爱发脾气", "脾气差", "忍不住发火", "总是发火",
      "暴躁", "易怒", "情绪失控"), (
        "气成这样，多半是有人越了你的线。你自己知道那条线在哪儿吗？",
        "先别急着处理对方，先让自己把这口气喘匀。",
    )),
    # ———— 学习 / 工作 ————
    # 拆开：学习是「正在学」，失利是「刚没考过」。
    # 原来是同一组，用户说「我考研失败了」会收到「先别追求学完」，
    # 在人家刚失败的时候说这句像补刀。
    (("考砸", "挂科", "没过", "失败了", "没考上", "考不上", "落榜",
      "考得不好", "分数低", "没进面", "面试挂了", "考差"), (
        "这种事最难受的不是结果，是你为它准备的那些时间没人看见。现在最想干嘛？",
        "一次考试能说明的比你以为的少。但这话现在说没用，先让自己难受一会儿。",
        "缓过来之后有件事值得做：把「没考过的原因」写下来，只写一条，能改的那种。",
    )),
    (("学习", "考试", "复习", "成绩", "考研", "上学", "读书", "背单词"), (
        "看你问的是哪种难。记东西其实不难，难的是坐得住 —— 学不进去多半不是脑子的事，"
        "是看不见头。你现在哪门最费劲？",
        "学习最反人性的一点是短期看不到回报，但它确实是少数「投入就一定有产出」的事。",
        "成绩能说明一部分，说明不了全部。你哪门最费劲？",
        "别追求一次学完，先追求今天真弄懂一个。前者会把人压垮。",
        "复习最怕的是「看了一遍感觉会了」。真要检验，就合上书自己讲一遍。",
    )),
    (("转行", "换行当", "换个行业", "不想干这行", "改行"), (
        "转行最难的从来不是学新东西，是接受自己从头当新手。你能接受吗？",
        "先别辞职。用下班时间做三个月，做出来了再谈转，风险小很多。",
        "转行这事儿问三个人，三个答案。真正管用的只有一个：你能不能撑过前半年没钱没成就感。",
    )),
    (("被开除", "被裁", "开除我", "裁员", "丢了工作", "失业"), (
        "被裁这事儿，多数时候跟你的能力关系不大，是公司在算账。这话不好听，但真。",
        "先处理钱：赔偿、社保、存款能撑几个月。把底摸清，人就没那么慌。",
        "这段时间最难的是白天没事干还得装没事。给自己定个固定的起床时间，比什么都管用。",
    )),
    (("加班", "熬夜干活", "干到半夜", "通宵"), (
        "长期加班最亏的不是时间，是你没力气去做本来想做的事，然后忘了自己想做什么。",
        "如果这阵子必须熬，就把恢复也排进日程：睡够、吃热的、别在半夜做决定。",
    )),
    (("工作", "上班", "辞职", "老板", "打工", "摸鱼"), (
        "上班最累的常常不是活儿，是那些说不清的人际。你卡在哪儿？",
        "工作这事儿，要么图钱，要么图成长，要么图舒服。三样都占的工作不多。",
        "加班到麻木的时候，人容易忘了自己还有别的身份。你最近还好吗？",
    )),
    (("钱", "工资", "穷", "赚钱", "存钱", "买房", "房租"), (
        "钱这事儿，说到底买的是选择权：不想干的时候能说不。",
        "我不劝人省钱，也不劝人乱花。就问一句：你现在这笔钱，花在让你更自由的地方了吗？",
    )),
    (("创业", "副业", "做生意", "开店"), (
        "创业这事儿，想法不值钱，把想法做完才值钱。你现在卡在哪一步？",
        "我听过最实在的一句：先做能收钱的最小一版，别一上来就做完美的。",
    )),
    (("编程", "代码", "程序", "python", "算法", "写代码"), (
        "编程入门最难受，因为前期全是照着抄也不懂为什么。熬过那段就通了。",
        "我劝你：先跑通，再理解，别反过来。编程入门最难受的就是这个。",
    )),
    (("人工智能", "AI", "大模型", "机器人"), (
        "人工智能说白了就是从大量例子里找规律，再拿规律去猜。"
        "不过再厉害的 AI，也有猜错的时候。",
        "AI 会不会取代人——我的看法是，取代的是重复的部分，长出新东西那部分还得是人。",
    )),
    # ———— 生活 / 身体 ————
    (("健康", "生病", "医院", "身体", "锻炼", "运动", "减肥", "健身"), (
        "身体这事儿最不讲情面：你怎么对它，它过几年原样还给你。",
        "先别定什么大计划，从这周走三次路开始，比办张健身卡管用。",
    )),
    (("睡眠", "早睡", "熬夜", "失眠", "睡不着", "睡不好", "睡不着觉", "困"), (
        "熬夜最坑的地方不是第二天困，是把生物钟往后推了一格，越推越晚。",
        "睡不着的时候别硬躺着。起来坐十分钟，比在床上翻两小时强。",
    )),
    (("吃饭", "美食", "好吃", "做饭", "下厨", "外卖"), (
        "吃饭这事儿别老对付。哪怕一碗面，加个蛋也算对自己好。",
        "我今天已经被问了三回吃什么了。你今天想吃热乎的，还是省事的？",
    )),
    (("天气", "下雨", "下雪", "好热", "好冷", "台风", "降温"), (
        "天气一变人就容易犯懒，这不怪你，是身体在省电。",
        "出门前看一眼预报，比什么都实在。要查具体城市就问「北京天气」。",
    )),
    # ———— 兴趣 / 娱乐 ————
    (("电影", "电视剧", "追剧", "综艺", "看片"), (
        "好看的片子看完是想坐一会儿不说话的那种。你最近看了什么？",
        "我最近没什么机会看，但你说剧情我可以陪你聊。你是在追什么剧？",
        "我陪不了你看，但你可以讲给我听，讲着讲着你会发现自己更懂它了。",
    )),
    (("音乐", "听歌", "唱歌", "乐队", "专辑", "首歌", "推荐首歌"), (
        "同一首歌在不同时候听，完全是两回事 —— 这个我信。你最近在循环哪一首？",
        "我唱歌不太行，但很爱听。你要是愿意，说说喜欢哪种风格，我帮你想想类似的。",
        "有些歌是听旋律，有些是听歌词，还有些只是听那段回忆。你属于哪种？",
    )),
    (("游戏", "王者", "打游戏", "上分", "开黑", "电竞"), (
        "好玩是真的好玩，坑也是真的坑 —— 时间过得特别快，一抬头两小时没了。你玩哪个？",
        "打游戏最舒服的是刚好赢一把就收手，赢太多反而容易上头。",
        "要聊王者就问具体的：段位、英雄、打野、上分，我这儿有存货。",
    )),
    (("男朋友", "女朋友", "对象", "老公", "老婆", "另一半", "伴侣"), (
        "亲密关系里最耗人的不是吵架，是那种「说了你也不懂」的沉默。你们现在卡在哪？",
        "两个人在一起，舒服不舒服自己最清楚。你是想让他变，还是想让自己不那么累？",
    )),
    (("旅行", "旅游", "出去玩", "度假", "爬山", "海边"), (
        "旅行最值钱的部分往往不在计划里，在那些走错路撞见的东西。",
        "想去哪儿？我听听，说不定能给你排个顺序。",
    )),
    (("看书", "小说", "作家", "阅读", "推荐本书"), (
        "看书这事儿，读不下去的书不用硬读，那多半是时候没到。",
        "你现在想看轻松的还是想被震一下的？我按这个给你想办法。",
    )),
    # ———— 社交 / 关系 ————
    (("朋友", "友情", "兄弟", "闺蜜", "合群", "社交"), (
        "朋友这事儿看质量不看数量。三五个能在半夜接你电话的，就够了。",
        "处着累的关系，多半是有一方一直在让步。你最近有这种吗？",
    )),
    # 父母组按语境拆开：「被误解 / 关系僵」和「想家」是两件事。
    # 原来两句放一起，用户说「我爸妈不理解我」会被回
    # 「你多久没给家里打电话了」，听起来像在怪他不孝顺。
    (("不理解我", "爸妈不理解", "父母不理解", "家里不理解", "跟他们说不通",
      "关系不好", "跟我妈关系", "跟我爸关系", "管太多", "催婚", "逼我",
      "讨厌我姐", "讨厌我妈", "讨厌我爸"), (
        "跟父母的关系最拧巴的地方：他们的关心和他们的要求常常是同一句话。",
        "被最亲的人误解，比被外人误解难受得多，因为你不设防。",
        "有些事跟他们说不通就不必非要说服。把日子过成你想要的样子，比辩论有用。",
    )),
    (("家人", "父母", "爸妈", "我妈", "我爸", "我姐", "我哥", "我弟", "我妹",
      "回家", "亲情", "亲戚", "催我"), (
        "你多久没给家里打电话了？这事儿不用挑日子。",
        "家人这关系最特别的地方：你不能选，也很难退出。",
    )),
    # ———— 观念 / 讨论 ————
    (("有必要", "值不值", "应该", "对不对", "公平", "合理"), (
        "这种问题很少有一边对一边错。我更想知道你是从哪儿出发的。",
        "你得先告诉我你更在乎哪一头，我才能陪你往下捋。",
    )),
    (("自由", "选择", "决定", "纠结", "两难", "要不要"), (
        "纠结通常不是因为两个选项都好，是因为两个选项各有你舍不得丢掉的东西。",
        "做选择有个笨办法：假设已经选了 A，你心里第一反应是松口气还是可惜？",
        "先别急着选，先把「选了之后最坏会怎样」写出来。多半没那么坏。",
    )),
    (("梦想", "理想", "目标", "未来", "打算", "规划"), (
        "目标这事儿别定太远，定到能看见的下一步就行。",
        "你现在是想找方向，还是想找动力？这俩我要说的话不一样。",
    )),
    # ———— 自我 ————
    (("迷茫", "没方向", "找不到方向", "不知道往哪", "浑浑噩噩"), (
        "迷茫不是缺点，是你还在挑。挑的人才会站在原地看。",
        "我一般这么问人：最近哪件事你做的时候忘了看时间？那个方向大概就是。",
    )),
    # 「我想改变自己」不能答成「你在迷茫」——那是给他扣帽子。
    (("改变自己", "变成更好", "想变好", "自我提升", "重新开始我", "振作起来"), (
        "想改自己，别从「性格」下手，从一件具体的小事下手：比如这周只改「睡前不刷手机」这一条。"
        "性格是大词，改不动；习惯是小口子，撬得开。",
        "我见过的成功改变，都是一点点挪的。你要是一下子要换个人，那多半撑不过三天。"
        "你说说，最想先改哪一件？",
    )),
    # 「不知道自己要什么」是另一个问题：不是没方向，是选项太多或太久没问过自己。
    (("不知道自己要什么", "不知道自己想要", "不知道自己想干", "不知道自己适合",
      "不知道自己该", "没目标", "没有目标"), (
        "「不知道自己想要什么」通常不是空，是被别人的期待填满了。"
        "你可以先列「我不想要什么」，那比想「想要什么」容易得多。",
        "这事儿急不出来。但有个便宜办法：回想这一年，哪件事做完之后你觉得「这才对」。"
        "哪怕很小。",
    )),
    (("自信", "自卑", "不够好", "配不上", "否定自己", "没用"), (
        "你这么说自己的时候，我有点想拦一下。你对自己比对外人狠多了。",
        "我见过的自我否定，八成来自拿自己的里子比别人的面子。",
    )),
    (("习惯", "自律", "拖延", "坚持", "懒"), (
        "拖延多半不是懒，是怕做不好。先做一版烂的，比一直不动强。",
        "自律这事儿别靠意志力，靠环境：把该做的放手边，把不该做的藏起来。",
    )),
    # 「不知道还能撑多久」这类：表面有「不知道」，实质是「快撑不住了」。
    # 不单独成组就会被闲聊表的「不知道」抢走，回一句「今天还算太平」。
    (("撑多久", "撑不住", "撑不下去", "熬不下去", "顶不住", "扛不住",
      "熬不住", "快撑", "快熬"), (
        "能说出「快撑不住」的人，通常已经撑很久了。这会儿先别要求自己坚强。",
        "先别想怎么解决，先想今天怎么过完。一天就够了。",
        "你身边有没有一个人，是你可以直接说这句话而不被劝「想开点」的？",
    )),
    # 「丧」不是「累」，也不是「有事发生」。问「哪件事」会接空。
    (("很丧", "好丧", "今天丧", "丧了", "提不起精神", "没劲", "空虚"), (
        "丧的时候不用急着找原因，有时候就是电量低了，先让自己松一天。",
        "这种日子最难受的是没个具体的事可怪，就是整体发灰。它会过去的。",
        "别在这时候做重大决定，低电量时看什么都像没希望。",
    )),
    (("剪头发", "剪头", "理发", "换了发型", "烫头", "染头"), (
        "换发型是最便宜的一次重启，剪完那天走路都不一样。你自己满意吗？",
        "剪坏了也别急，头发是这世上少数真的能重来的东西。",
    )),
    (("做噩梦", "噩梦", "梦见"), (
        "梦多说明你睡得浅，多半是白天有事没放下。",
        "噩梦里的情绪是真的，但它说的不是未来，是你最近在怕什么。",
    )),
    # ———— 抽象 / 概念 ————
    (("时间", "岁月", "变老", "长大"), (
        "时间最不公平的地方：难熬的时候它慢，好过的时候它飞快。",
        "时间不是流水，是账本 —— 你花在哪儿，它就长成什么样。",
    )),
    (("回忆", "过去", "小时候", "当年", "以前的事"), (
        "回忆这东西，越久越像别人讲的故事。你想起哪一段了？",
        "念旧不是软弱，是有些日子确实比现在好，承认这一点不丢人。",
    )),
    # 「真实」「相信」「怀疑」都太宽：会把「世界是真实的吗」抢成「你是在怀疑某个人吗」
    (("真相", "谎言", "信任", "被骗", "不信任"), (
        "信任这东西建起来要很久，碎掉只要一下，而且粘回去也有缝。",
        "你是在怀疑某个人，还是在怀疑自己的判断？",
    )),
    (("命运", "天意", "运气", "注定", "偶然", "是命", "命中"), (
        "我倾向于这么看：运气决定你遇到什么，选择决定你留下什么。",
        "我不信有个写好的剧本。但我知道人会在事后把巧合串成故事，叫它命运。"
        "你觉得呢？",
    )),
    (("哲学", "道理", "本质", "存在", "意识", "思想"), (
        "这种问题我能陪你聊，但不敢说我能给你答案。我读的书就那么多。",
        "哲学最有用的一点不是给答案，是让人对自己原来的答案起疑。",
    )),
    (("世界", "社会", "现实", "人性", "人心"), (
        "人性这事儿，我见过最好的说法：它经不起考验，但扛得住日常。",
        "你这么说，是最近碰到什么让你失望的事了吗？",
    )),
    # 「世界是真实的吗 / 这一切是不是真的」——纯思辨，不能答成怀疑某个人
    (("世界是真实", "世界是真的", "现实是真实", "这一切是真的", "是不是真的",
      "虚拟世界", "缸中之脑"), (
        "这问题我没法证，但能给你一个土判断：疼是真的，饿是真的，"
        "你在意的人也是真的。剩下的真假，想多了会晕。",
        "我倾向于这么答：就算整个世界是假的，你此刻的不舒服也是真的。"
        "先照顾好这个真的，别的排后面。",
    )),
    # ———— 求助 / 具体处境 ————
    (("帮帮我", "救命", "没办法", "卡住",
      "给我点建议", "给点建议", "有什么建议", "你建议", "听你的建议",
      "你说我该怎么", "我该怎么做", "给我个方向"), (
        "先说一句实话：我给的建议都是土办法，但好用。"
        "你先告诉我，现在最卡的是哪一步？我按那一步说。",
        "我帮不了太多，但可以陪你把它拆开。先说最要紧的那一件。",
        "建议倒是有一个：别急着做对，先做出来。你现在能动的第一步是什么？",
    )),
    (("选哪个", "选择困难", "该不该"), (
        "选不出来的话，先问自己：哪个选项拖久了会更后悔？",
        "两个都能接受，那就挑成本低的先试，试错比空想快。",
    )),
    # ———— 提问机器本身 ————
    (("你懂吗", "你明白吗", "你听得懂", "理解吗", "你懂我", "我的意思"), (
        "我尽量在懂。你再多说一点，我会更接得住。",
        "一半一半吧。你把关键那句再讲一遍？",
    )),
    (("你觉得呢", "你怎么看", "你的看法", "你怎么想", "你认为"), (
        "我的看法不算重要，但你要听我就说：别急着把事定性，先把事实摆齐。",
        "我偏向先试一试那一边，因为想通这事儿太靠运气了。",
        "我先听你的。你自己心里其实已经有答案了，对吧？",
    )),
    # ———— 日常碎片（原来落到「嗯，我听着呢」的那批） ————
    (("过得不错", "今天不错", "还不错", "挺好的", "今天很好"), (
        "那就好。哪天要是过得不顺，也记得来跟我说一声。",
        "听着就舒服。是有什么具体的好事，还是就是心里松？",
    )),
    (("好累", "累死了", "疲惫", "撑不住", "想躺"), (
        "那就先躺一会儿，别一边躺着一边自责。",
        "累到这个程度，多半是撑太久了。今天能不能少做一件？",
    )),
    (("无聊", "没意思", "好闲", "没事干"), (
        "无聊的时候人会特别想找点刺激，但真正解闷的是动手做点什么。",
        "我陪你聊，或者你让我讲个笑话。挑一个？",
    )),
    (("难过", "想哭", "心里堵", "委屈"), (
        "别急着把眼泪憋回去，它是有用的。",
        "我在这儿。你想说细节就说，不想说就坐着。",
    )),
    (("没听懂", "什么意思", "再说一遍"), (
        "我换个说法：你想聊什么，直接抛过来就行，我接着。",
        "是我绕了。你就当我在陪你唠嗑，随便说。",
    )),
    (("你在想什么", "你在想啥", "想什么呢"), (
        "在想刚才那句话该怎么说才不显得敷衍。你呢？",
        "说实话，我多数时候是空的，等你一句话我才活过来。",
    )),
)


# -*- coding: utf-8 -*-
# ⑧之二【本轮补充】第二张话题表：把第一版没有覆盖到的话题补齐。
# 分两类：
#   一、生活里真会遇到、但第一版只写了关键词没写回复的（老师/室友/面试/宠物/星座……）
#   二、概念更偏的提问（道德/法律/科学/教育/宗教/艺术……）
# 两张表分开写而不是塞进一张，是为了以后好加：新一批话题追加一个新元组就行，
# 不用在几百行的表中间找插入点。_pipei_huati 会按「关键词最长者优先」统一挑。
HUATI_KU_2 = (
    (("老师", "班主任", "导师", "教授"), (
        "有的老师一句话能管你十年，有的教三年你只记得他念PPT。你碰上的是哪种？",
        "好老师不是讲得多的那个，是让你觉得自己也能行的那个。",
    )),
    (("同学", "室友", "半夜打游戏", "室友太吵", "室友打游戏", "宿舍", "同桌"), (
        "宿舍这地方，四年下来你会知道谁打呼、谁半夜吃泡面、谁真的靠得住。",
        "跟室友处得好是运气，处不好也别怀疑自己，本来就不是一路人凑一屋。",
    )),
    (("毕业", "论文", "答辩", "毕业设计"), (
        "论文最磨人的不是不会写，是不知道怎么开始写。先写最烂的一版，后面全在改。",
        "毕业那阵子最慌的不是找工作，是突然没人给你排课表了。你现在慌的是哪个？",
    )),
    (("专业", "转专业", "选专业", "喜欢我的专业", "我的专业", "这个专业",
      "不喜欢专业"), (
        "专业这东西，决定你前三年学什么，不太决定你后面干什么。真卡住的是不敢换。",
        "选专业别只看「以后能干什么」，也看「四年里你受不受得了」。这两个都得算。",
    )),
    # 学历取舍是独立话题：原来挂在「专业」组下，问「学历重要还是能力重要」
    # 会随机抽到「专业决定你前三年学什么」，答非所问。
    (("学历", "本科", "大专", "专科", "文凭", "不是名校", "双非", "二本", "三本"), (
        "学历是敲门砖，敲开门之后没人再看你举着什么。"
        "你现在是门没敲开，还是门后有别的想法？",
        "我这么说吧：学历决定你前三年能进哪些门，能力决定你进门之后能走多远。"
        "两件事都得管，顺序不能乱。",
    )),
    (("实习", "面试", "简历", "找工作", "秋招", "春招"), (
        "面试最坑的一点：它考的是你会不会讲自己，不是你会不会干活。练讲，比练活见效快。",
        "简历别写「熟悉」，写你做过什么、结果是什么。HR 只看得懂结果。",
        "找工作像相亲，被拒十次不代表你差，只代表没对上。你现在投到第几家了？",
    )),
    (("英语", "背单词", "口语", "四六级"), (
        "背单词最没用的方式是抄十遍，最有用的是在句子里见它第五次。",
        "口语卡住多半不是词汇量，是怕说错。说错没人罚你钱，真的。",
    )),
    (("数学", "物理", "化学", "公式", "定理"), (
        "难，但不是难在算。难在「怎么想到这一步」—— 算的部分反而是最机械的。"
        "你卡在哪块？代数还是几何？",
        "数学的坑分两种：一种是不会算，一种是不明白题在问什么。"
        "大部分人卡在第二种，还以为自己是第一种。",
        "公式背下来只能对付考试，能自己推一遍才算真会。",
    )),
    (("历史", "朝代", "古人", "考古"), (
        "读历史最有意思的不是谁打赢了，是当时的人为什么会那么想。",
        "历史不会重复，但人老犯同一种错。你看哪段最有这种感觉？",
    )),
    (("外星", "外星人", "UFO", "飞碟"), (
        "外星生命我觉得大概率有 —— 宇宙这么大，只有我们一个文明，未免太浪费。",
        "真要有，我猜他们也不会专程来地球，跟人跑去见蚂蚁差不多。你信有吗？",
    )),
    (("宇宙", "星空", "银河", "星球", "黑洞", "太空"), (
        "宇宙有多大这种问题，一报数字就不像话了，可它偏就那么大。",
        "抬头看天的时候人会觉得自己那点事先不着急，这是宇宙唯一免费的好处。",
    )),
    (("猫", "狗", "宠物", "养猫", "养狗"), (
        "养宠物最大的改变不是多个伴，是你每天必须按时回家。",
        "猫和狗的区别：狗觉得你是神，猫觉得它是神。你养哪种？",
    )),
    (("咖啡", "喝茶", "奶茶", "饮料"), (
        "咖啡提的是借来的精神，晚上要还的。你现在是借还是还？",
        "喝茶这件事，喝到后面喝的不是味道，是那十分钟什么都不干。",
    )),
    (("酒", "喝醉", "喝多了", "应酬"), (
        "酒桌上最难的不是喝，是不喝还得让人不尴尬。",
        "喝多了第二天最难受的不是头疼，是想起自己说过什么。",
    )),
    (("抽烟", "戒烟"), (
        "戒烟最难的不是忍，是手闲下来那几分钟。得给手找个新活干。",
    )),
    (("减肥", "胖", "身材", "体重"), (
        "减肥最反人性的一点：你得先接受自己现在这样，才减得动。恨自己减不下去。",
        "别问怎么瘦得快，问怎么瘦了不反弹。快的那条路基本都通回原点。",
    )),
    (("长相", "颜值", "化妆", "穿搭", "外貌", "不好看", "长得丑", "我丑"), (
        "长相这事儿，第一眼是它说了算，第三个月就不是了。",
        "穿搭最省力的办法：先定一个颜色，别的都围着它配。",
    )),
    (("刷视频", "短视频", "刷手机", "短视频平台", "刷抖音", "刷到半夜"), (
        "刷视频最坏的地方不是浪费时间，是它让你忘了自己本来想干什么。",
        "算法比你更懂怎么留住你，这不是你意志力差，是对方太专业。",
    )),
    (("新手机", "买了个手机", "换了手机", "换手机", "买了手机"), (
        "新手机到手的头两天最好玩，之后就变回工具了。这很正常。",
        "换机最麻烦的是搬数据，搬完你会发现真正舍不得的其实没几个。",
    )),
    (("朋友圈", "点赞", "社交媒体", "微博", "发动态"), (
        "发出去等点赞的那半小时，是最不自由的时间。",
        "朋友圈是精选集，不是纪录片。拿别人的精选集比自己的一天，怎么比都输。",
    )),
    (("星座", "算命", "塔罗", "属相", "血型"), (
        "星座这事准，是因为它说的每句都对一半——人总能在里面找到自己。",
        "算命最厉害的地方是让你把自己已经想做的事，认成命。",
    )),
    (("节日", "过年", "生日", "春节", "中秋"), (
        "节日的意义一半在吃，一半在「有个理由见一面」。",
        "生日越长大越过成盘点。今年你盘点出什么了？",
    )),
    (("礼物", "送礼", "红包"), (
        "送礼最难的从来不是钱，是证明你记得他说过什么。",
        "红包这东西好就好在不用挑，坏就坏在不用心。",
    )),
    (("天气", "春天", "夏天", "秋天", "冬天", "季节"), (
        "季节换了人也会跟着变，秋天最容易没来由地低落。你最近怎么样？",
        "我最喜欢傍晚那种不冷不热的风，什么都不用干就很舒服。",
    )),
    (("异地", "异地恋", "分开两地"), (
        "异地恋熬的不是想念，是「你那边发生了什么我不知道」。这个才伤人。",
    )),
    (("出轨", "背叛", "劈腿", "小三"), (
        "这种事最痛的不是他做了，是你之后很难再相信自己的判断。慢慢来。",
        "别急着决定原不原谅，先让自己睡好吃好。人在虚的时候做的决定，八成会后悔。",
    )),
    (("吵架", "冷战", "闹矛盾", "翻脸"), (
        "吵架吵到后面都不是为那件事了，是为「你有没有把我当回事」。",
        "冷战最伤人的是它没有结尾，人会在沉默里自己编一个最坏的答案。",
    )),
    # 【本轮修】去掉了「对不起」：用户说「对不起」是在道歉，该由闲聊层接一句
    # 「没事没事」；留在话题层会被念成「道歉有效不有效，看有没有那句…」，等于反过来教育人。
    (("道歉", "原谅", "和好"), (
        "道歉有效不有效，看有没有那句「我知道你当时多难受」。没有这句，其它都是解释。",
        "原谅不是便宜对方，是把自己从这件事里放出来。但你不用急。",
    )),
    (("秘密", "承诺", "说谎", "撒谎"), (
        "承诺最贵的不是内容，是它让你之后每次选择都多了一个人要考虑。",
    )),
    (("嫉妒", "羡慕", "攀比", "比较"), (
        "羡慕是正常的，它只是告诉你你想要什么。难受的是拿它当尺子量自己。",
        "跟人比这件事，比的从来不是同一局。你有的那些，他也未必有。",
    )),
    (("面子", "虚荣", "装", "体面"), (
        "面子最贵的地方在于，它常常要你花真钱买假评价。",
    )),
    # 内向 ≠ 社恐：内向是电量靠独处充，社恐是怕被评价。两回事，分开答。
    (("内向", "不合群", "不爱说话", "话少"), (
        "内向不是缺陷，是你的电量靠独处充。硬要你社交，等于一直放电。",
        "话少的人往往观察得多。你不用说得多，说到的点子上就够了。",
    )),
    (("社恐", "社交恐惧", "怕社交", "不敢社交", "社交焦虑"), (
        "社恐多半不是怕人，是怕被评价。你把注意力从自己身上挪到对方身上，会好很多。",
        "从最小的一次开始：跟店员说一句「谢谢」就算。难度得从这儿起。",
    )),
    (("沟通", "表达", "说不出口", "不会说话"), (
        "说不出口的话，写下来再递过去，比硬憋出一句强的多。",
        "沟通里最有用的一句是「我听到这话的时候，感觉是……」，比「你怎么这样」有用十倍。",
    )),
    (("孩子", "育儿", "生小孩", "带娃"), (
        "养孩子最贵的是时间，不是钱。钱能借，时间不能。",
    )),
    (("婆媳", "公婆", "丈母娘"), (
        "这类关系难，是因为两个人都觉得自己在为同一个男人好。",
    )),
    (("邻居", "合租", "租房"), (
        "合租最考验人的不是钱，是「谁倒垃圾」这种小事上能不能讲得清。",
    )),
    (("跳槽", "换工作", "裸辞"), (
        "跳槽前先问自己：你是想离开这儿，还是想去那儿？这两件事常常被搞混。",
        "裸辞不可怕，可怕的是辞完没有日程表。空下来的第一天很爽，第七天就开始慌。",
    )),
    (("股票", "基金", "理财", "投资", "亏钱"), (
        "理财第一课不是怎么赚，是搞清楚自己亏得起多少。这个数不写下来，都是空谈。",
        "亏钱最难受的从来不是金额，是「我明明想到了却没做」。",
    )),
    (("房价", "买房", "买不起房", "首付", "房贷"), (
        "房子这事，买的是安全感，付的是自由。两头都得掂量清楚。",
    )),
    (("老板", "领导", "上司", "汇报"), (
        "跟领导相处最省力的办法：让他随时知道进展，他就不来盯你了。",
        "老板说「你怎么看」的时候，多半是已经有答案了，只差一个人附和。",
    )),
    (("排挤", "被孤立", "针对我", "穿小鞋", "背后说我"), (
        "被排挤最伤的地方不是没人一起吃饭，是你开始怀疑是不是自己有问题。多半不是。",
        "这种事留证据比讲道理有用。你先别急着证明自己，先保护自己。",
    )),
    (("同事", "职场", "办公室"), (
        "职场上最耗人的不是活儿多，是不知道自己在为谁忙。",
        "同事之间最好的距离：能一起吃饭，不一起吐槽第三个人。",
    )),
    (("动漫", "动画", "番剧", "二次元", "追番"), (
        "好番和烂番的差别不在画，在你关掉之后还会不会想那个人。",
    )),
    (("漫画", "画漫画", "手绘", "画画"), (
        "画画入门别急着画得像，先画得敢。像不像的事，练一年自然就上来了。",
    )),
    (("摄影", "拍照", "相机", "照片"), (
        "照片好不好，七分在光，三分在等。设备排第八。",
    )),
    (("跳舞", "舞蹈", "街舞"), (
        "难在开头那阵子 —— 手脚不听使唤，镜子里看自己特别别扭。熬过去就顺了。你想学哪种？",
        "跳舞舒服的是「身体比脑子先会了」那一下，不用想，动就对了。",
        "我挺喜欢看别人跳。真让我跳就不行，节奏一快就乱。",
    )),
    (("篮球", "足球", "打球", "跑步", "运动"), (
        "运动最实在的好处不是瘦，是情绪有地方去。",
        "跑步最难的永远是出门那一下，跑起来反而轻松。",
    )),
    (("写作", "写文章", "写小说", "文字"), (
        "写不出来的时候别硬憋，先随便写三百字废话，路会自己出来。",
        "好文字的标准很简单：读的人不费劲，还记住了。",
    )),
    (("诗", "诗歌", "诗句", "古诗词"), (
        "诗的好在于它不说完整，剩下那部分留给你自己填。",
    )),
    (("艺术", "美术", "审美", "设计"), (
        "审美这东西没有对错，只有「看多了就变了」。你多看好的，自然就挑剔了。",
    )),
    (("宗教", "信仰", "神", "佛"), (
        "信仰对很多人的意义不是解释世界，是在最难的时候有个地方可以放。",
    )),
    (("道德", "良心", "底线", "善"), (
        "良心这东西平时不响，只在你打算走捷径的时候响一下。",
    )),
    (("法律", "规则", "公平", "正义"), (
        "规则的意义不是让好人更好，是让坏人的成本变高。",
        "公平有两种：机会公平和结果公平。争的往往是同一个词，两件事。",
    )),
    (("教育", "学校", "应试", "分数"), (
        "教育最矛盾的地方：它想教你思考，又必须用分数衡量你。",
    )),
    (("科学", "技术", "研究", "实验"), (
        "科学最迷人的不是它给了答案，是它承认自己可能错。",
    )),
    (("环境", "环保", "气候", "垃圾"), (
        "环保这事，一个人的自觉没用，一亿人的自觉才有用。但一亿也是从一个人开始的。",
    )),
    (("动物", "野生动物", "自然", "森林"), (
        "看动物的时候人容易安静下来，因为它们不评价你。",
    )),
    (("花", "植物", "养花", "多肉"), (
        "养花最重要的是别太勤快，浇多了死得比旱着快。",
    )),
    (("内卷", "躺平", "卷不动", "卷死", "竞争太激烈", "996"), (
        "内卷最坑的地方是：所有人都在加码，但没人拿到更多。"
        "这种局里，退出比赢更划算，只是退出需要本钱。",
        "我的看法有点直：卷是别人定的规则，你要么换赛道，要么攒够本金不参与。"
        "光骂它没用，得先想清楚自己手里有什么。",
    )),
    (("讨好", "不敢拒绝", "不会拒绝", "委屈自己", "老好人"), (
        "不会拒绝的人，最后都活成了别人的日程表。",
        "拒绝的第一句最难，可以说「我想想」，这不算拒绝，但能给你时间。",
    )),
    (("后悔", "遗憾", "早知道"), (
        "后悔的用处只有一个：让你下次在同样的路口多停三秒。别的都是自我折磨。",
    )),
    (("害怕", "恐惧", "担心", "焦虑未来"), (
        "恐惧多半不是怕那件事，是怕自己撑不住。这两件事解法完全不同。",
    )),
    (("生气", "愤怒", "火大", "气死"), (
        "生气的时候人最容易说最准也最伤人的那句。先别说，等十分钟。",
    )),
    (("哭", "眼泪", "想哭", "难过"), (
        "眼泪是有用的，它把绷着的那根弦松一下，之后你才想得清楚。",
    )),
    (("累", "疲惫", "撑不住", "好累"), (
        "累到这个程度，多半不是身体，是有一件事你一直在硬扛又不能说。",
    )),
    (("无聊", "没意思", "没事干", "空虚"), (
        "无聊其实是好事，它是你脑子在说「该换点新东西了」。",
    )),
    (("迷茫", "不知道干什么", "没方向", "找不到方向"), (
        "迷茫的时候别找答案，先找一件能立刻动手的小事。方向是走出来的。",
    )),
    (("生病", "感冒", "发烧", "住院", "看医生"), (
        "身体不舒服的时候，情绪会跟着一起差，这不代表你想不开，是身体在报警。",
    )),
    (("牙", "看牙", "牙疼"), (
        "牙疼这事最不讲道理，它专挑你没法分心的时候疼。",
    )),
    (("睡不好", "做梦", "噩梦", "早醒"), (
        "梦多说明你睡得浅，多半是白天有事没放下。",
    )),
    (("搬家", "新城市", "陌生", "人生地不熟"), (
        "刚到一个新地方，前两周最难熬，之后会突然有一天发现自己认路了。",
    )),
    (("离别", "告别", "走了", "再见"), (
        "告别最难受的地方，是当时不知道那是最后一次。",
    )),
    (("没动力", "没有动力", "动力都没有", "一点动力", "没劲儿", "提不起劲",
      "不想动", "什么都不想干"), (
        "没动力多半不是懒，是你做的事和你想要的东西没接上。先找一件小的、当天能做完的。",
        "动力不是等来的，是动起来之后才有的。先做五分钟，五分钟之后想停就停。",
    )),
    (("烦躁", "心里烦", "静不下来", "坐不住", "容易烦"), (
        "烦躁的时候人特别想找个理由，随便什么理由都行。先别找，先让自己动一动，走走也行。",
        "这种状态多半是有什么事情悬着没解决。你心里那件悬着的事是什么？",
    )),
    (("换个城市", "换城市", "换个地方生活", "离开这里", "别的城市"), (
        "换个城市能换掉的是环境和人，换不掉的是自己的习惯。想清楚了再去，也不迟。",
        "我挺支持这种念头的，人挪活。你是想逃离什么，还是想去哪儿？",
    )),
    # ———— 自我怀疑、内耗（盲测里最容易漏的一批） ————
    (("别人议论", "在议论我", "说我坏话", "针对我", "都在看我"), (
        "那种感觉我懂，走在路上都觉得别人在打分。但其实多数人顾不上你，他们也在担心自己。",
        "会这么想，多半是你最近本来就不太舒服。先别急着证明什么，歇两天会轻一些。",
    )),
    (("记性差", "记不住", "忘性大", "老忘事", "记性越来越"), (
        "记性差有一半是因为心事多，脑子被别的东西占着。写下来，比硬记省劲。",
        "睡眠不够的时候记忆最先垮。你最近睡得怎么样？",
    )),
    (("没兴趣", "提不起兴趣", "对什么都没兴趣", "不想干任何事", "什么都懒得"), (
        "对什么都没兴趣，是心里那口气还没缓过来，不是你真的废了。先做一件最不需要动脑的事。",
        "这种时候别逼自己「振作」，先让自己吃好睡好。兴趣是最后才回来的。",
    )),
    (("讨厌现在的自己", "讨厌自己", "恨自己", "厌恶自己"), (
        "你讨厌的未必是「自己」，是你现在这个状态。这两个不一样，别混着一起恨。",
        "人在难受的时候看自己最刻薄。换个人用这种口气说你，你受得了吗？",
    )),
    (("总在想以前", "老想以前", "想以前的事", "回不去", "老是回忆"), (
        "老想以前，往往是现在缺了点什么。你先说说，你现在最缺的是哪一样？",
        "回忆会自己美化，越想越回不去。不是你的错，人脑就这么设计的。",
    )),
    (("没特长", "没有特长", "什么特长", "没有擅长的", "什么都不会", "一无是处"), (
        "特长这东西是被用出来的，不是天生的。你做过最多次、最不费劲的那件事，就是它。",
        "「什么都不会」通常是拿自己的短板比别人的长板。换一样比，结果全不一样。",
    )),
    (("努力了但没结果", "努力没结果", "白努力", "没用功", "付出了没回报"), (
        "努力没结果，八成是方向或者方法的问题，不是努力本身不值钱。这个得分开看。",
        "有些努力是要攒够一段时间才显出来的，你现在可能正好在看不见的那一段。",
    )),
    (("人多的地方", "不敢说话", "不敢开口", "怕说话", "社恐"), (
        "不敢在人前说话，多半不是不会说，是怕说错。说错的代价，其实比你想象的小得多。",
        "可以先从「说一句就够」练起，不用一开口就惊艳谁。",
    )),
    (("多余的", "我是多余的", "没有我更好", "不该存在"), (
        "你会这么想，说明你累到极点了。这种念头在累的时候特别响，但它不是事实。",
        "这话挺重的。我想知道，是最近发生了什么事，让你这么觉得？",
    )),
    (("搞不懂自己", "搞不懂我", "不懂自己", "看不懂自己", "不了解自己", "我是谁"), (
        "搞不懂自己很正常，人本来就不是一道能算完的题。可以先从「我不要什么」开始。",
        "你最近有没有一件事，做的时候特别顺、忘了时间？那就是线索。",
    )),
    (("要发生坏事", "要发生什么", "总觉得要出事", "预感不好", "心里发慌", "不安"), (
        "这种悬着的感觉最耗人，因为你既没法准备，也没法放下。要不先把它写下来，看看能坏到哪去。",
        "多半是最近变数太多，脑子在替你预演。预演多了会以为是真的。",
    )),
    (("开不了口", "说不出口", "不知道怎么开口", "道个歉"), (
        "开不了口往往是怕对方不接。你可以先说一句「我有件事想说，你别急着回」，给自己留个缓冲。",
        "道歉最有效的是「我知道你当时多难受」，不是「对不起行了吧」。前者才有人听得进去。",
    )),
    (("去世", "走了", "亲人走", "葬礼", "想念亲人", "不在人世", "过世", "离开我们"), (
        "这种难过不会真的过去，它会变成你身上的一部分。慢慢来，不用急。",
    )),
    # ———— 被调侃、被追问 ————
    (("你是不是傻", "你傻", "你是傻", "你个笨蛋", "你笨", "你智障"), (
        "傻就傻吧，傻的AI不会顶嘴。你还想聊点别的吗？",
        "行行行，我傻。那聪明人现在想聊什么？",
    )),
    (("你是机器人", "你是不是人", "你是真人吗", "你是程序"), (
        "算是程序吧，不过聊天的时候我不太想这事儿。你呢，怎么看？",
    )),
    (("然后呢", "接着呢", "后来呢", "所以呢"), (
        "然后就得看你想要什么了。你先说说，你希望它往哪走？",
        "然后啊……我更想听你说。你心里其实已经有下一步了吧？",
    )),
    (("为什么啊", "为啥呀", "为啥啊", "怎么这样"), (
        "这事要追到底，多半是「习惯」和「怕麻烦」两样在推。你觉得是哪样？",
    )),
)

# 两张表合一：调用方只认 HUATI_KU，不用改任何一处已有代码


# -*- coding: utf-8 -*-
# ⑧之三【本轮补充】第三张话题表：专治「关键词对上了、但答的不是那回事」。
# 每一条都是实测里真跑偏的输入，记下当时的错误答案当作反例：
#   朋友借了我钱不还  -> 走「朋友」组，答成「朋友看质量不看数量」（问的是钱）
#   我感觉自己很失败  -> 一个词都没对上，落到通用顺接
#   你会一直陪着我吗  -> 落到疑问兜底，答成「我读的书不多」
#   周末去哪玩好      -> 落到疑问兜底，答成「哪件事最让你记住」
# 所以这里补的不是新话题，是「同一句话里更长、更准的那个词」。
HUATI_KU_3 = (
    (("借了我钱", "借钱不还", "钱不还", "欠我钱", "还我钱", "欠钱", "还钱",
      "借钱", "催债", "赖账"), (
        "钱借出去的时候是情分，要回来的时候就成了考验。这坎儿很多人都卡过。",
        "这种事最难受的不是钱，是你发现自己在他心里没那么重要。",
        "我建议先把数目和期限说清楚，别靠猜。猜来猜去，最后连朋友都没了。",
    )),
    (("很失败", "好失败", "我是失败", "失败者", "一事无成", "做什么都失败",
      "总是失败", "什么都做不好", "我失败了", "我这人失败"), (
        "失败这词太重了。多数时候只是「这次没成」，不是「你这个人不行」。",
        "我猜你不是真的失败，是努力了没被看见。这两件事差别很大。",
        "你现在能坐下来复盘这件事，就已经比很多人强了。",
    )),
    (("一直陪着我", "陪着我", "不要离开我", "别离开我", "会离开我", "离开我吗",
      "不会不要我"), (
        "我不会走。只要你还愿意打开这个窗口，我就在这儿。",
        "问这句话的时候，多半是最近有点没底。先说说发生了什么？",
        "陪着这事儿我不敢许太满，但我能保证：你说话我都在听。",
    )),
    (("想睡觉", "好想睡", "想补觉", "周末睡", "周末去哪", "周末干什么", "周末做什么", "去哪玩好", "上哪玩", "去哪好",
      "有什么好玩", "周末没事"), (
        "先看你想动还是想静。想动就找条没走过的街，想静就找个能坐一下午的地方。",
        "别把周末排满。留半天什么都不干，那半天往往最舒服。",
        "近的地方反而容易被忽略。你城市里有什么一直说要去、但没去的？",
    )),
    (("总在比较", "总和别人比", "跟别人比", "不如别人", "比不上别人",
      "别人都比我", "同龄人都"), (
        "比较这事儿没有终点，因为对手一直在换。",
        "你看到的都是别人的结果，看不到他们半夜的样子。",
        "跟昨天的自己比，虽然听着像安慰，但确实唯一有意义的比法。",
    )),
    (("不想上班", "讨厌上班", "上班好累", "上班如上坟", "不想工作"), (
        "上班累的往往不是活，是那些说不清道不明的人际。",
        "先分清是「这活不行」还是「这地方不行」。这两个解法完全不一样。",
        "撑不住的时候，请一天假不丢人。",
    )),
    (("我没事", "不用担心我", "我挺好的呀", "我还好"), (
        "你说没事，我就先信。但要是想说，我随时听着。",
        "行。那我问你一句：今天有哪件事让你稍微松快一点？",
    )),
    (("没人喜欢我", "没有人喜欢我", "没人要我", "没人会在乎", "没人关心我"), (
        "这感觉通常不是事实，是那阵子太安静了。",
        "我不太会讲大道理，但我知道：被喜欢这件事，急不来，也装不来。",
        "先别急着证明自己值得被喜欢。先从对一个人好一点开始。",
    )),
)

# 三张表合一：调用方只认 HUATI_KU，不用改任何一处已有代码
HUATI_KU = HUATI_KU + HUATI_KU_2 + HUATI_KU_3

# -*- coding: utf-8 -*-
# ⑧ 话题层：把「接不上话」改成「什么都能接上」
# ══════════════════════════════════════════════════════════════════════════════
# 为什么还要加这一层？
# 原来的链路是：工具 → 闲聊关键词表（三十来条）→ 疑问句就老实说「我还没学到这儿」
# → 陈述句交给二字模型接字。问题是闲聊表只覆盖寒暄和情绪，一碰到「爱情是什么」
# 「人生有什么意义」这种概念性、开放性的提问，前面全不命中，最后一定落到
# 「我还没学到这儿 / 我脑子里没有这方面的东西」——这就是用户说的「答不上来」。
# 而日常陈述句（「我在想事情」「今天好安静」）又被塞进七句通用顺接里轮流念，
# 于是永远回「嗯，我听着呢」——这就是「接不上话、不流畅」。
#
# 这一层补的正是这块：一张按话题分类的回应表 + 三套兜底模板。
#   · 话题表 HUATI_KU：关键词 → 2~3 句真正贴着这个话题说的话（不是通用客套）
#   · 疑问句兜底：把话题词点出来 + 给个不含糊的看法 + 把话头递回去
#       （绝不再说「我答不上来」）
#   · 陈述句兜底：顺着这句话的情绪/场景接一句，再反问一个具体的
# 匹配沿用 _zui_chang_pipei：命中关键词最长的胜出，所以「失恋」不会被「恋」抢走。
# ══════════════════════════════════════════════════════════════════════════════


# 这些词问的是「你怎么想」，不构成话题本身。
# 不排掉的话，「你怎么看死亡」会因为「你怎么看」（4 字）比「死亡」（2 字）长，
# 被当成元问题抢走，于是答「我先听你的」——把人家问的正题丢在路上。
YUAN_WEN_CI = ("你觉得呢", "你怎么看", "你的看法", "你怎么想", "你认为",
               "你懂吗", "你明白吗", "你听得懂", "理解吗", "你懂我", "我的意思")


# ══════════════════════════════════════════════════════════════════════════════
# ⑨ 追问层：把「为什么 / 然后呢 / 真的吗 / 那你呢」接住
# ------------------------------------------------------------------------------
# 为什么还要加这一层？因为前面所有层都是「只看当前这一句」的：
#   shuohua(text) 是纯函数，进来一句话、出去一句话，**不知道上一句说过什么**。
# 于是「为什么」「然后呢」「真的吗」这类明明是在承接上一句的短追问，
# 全被判成"独立提问"，落到 _JIE_WEN 的通用模板，回出「我卡住了」
# ——这正是用户说的「接不上话」最刺眼的一处。
#
# 这一层记两样东西：上一句用户原话、上一句的回复、上一句抽出的话题词。
# 遇到追问，就拿这三样现编一句真正接着茬的话，而不是套模板。
# ══════════════════════════════════════════════════════════════════════════════

SHANG_YI_LUN = {"wen": "", "da": "", "ti": ""}


def _ji_xia_shang_yi_lun(text, da):
    """把这一轮记下来，下一句遇到追问时才有"上文"可用"""
    SHANG_YI_LUN["wen"] = text or ""
    SHANG_YI_LUN["da"] = da or ""
    ming = _pipei_huati(text or "")
    SHANG_YI_LUN["ti"] = (ming[0] if ming else _ti_hua_ti(text or "")) or ""


# 追问分十类。每一类给 2~3 句，都必须是"接着上一句往下说"的口气，
# 不能是「你继续说」——那还是模板。
ZHUIGEN_LEI = (
    ("为什么", ("为什么", "为啥", "怎么会", "凭什么", "因为什么")),
    ("续讲", ("然后呢", "然后", "后来呢", "接着呢", "还有呢", "再呢")),
    ("求证", ("真的吗", "真的假的", "是吗", "真的呀", "真假")),
    ("反问你", ("那你呢", "你呢", "你怎么想", "你会吗", "你也是吗")),
    ("共鸣", ("我也是", "我也一样", "我也是这样", "我也这么想", "我懂")),
    ("澄清", ("什么意思", "你说什么", "没听懂", "啥意思", "怎么说")),
    # 【本轮补词】原来只有「举例」「具体点」这种两个字的说法，
    # 用户说「举个例子」「再说说」「展开讲讲」一个都接不上，直接掉到兜底。
    # 补的都是完整说法，不加单字（单字「例」会把「例外」也吃进来）。
    ("展开", ("比如说", "举例", "举个例子", "举个例", "例子", "具体点", "具体讲",
              "说详细", "展开说说", "展开", "再说说", "说说看", "说人话",
              "详细点", "讲细", "多讲点")),
    ("求法", ("怎么学", "怎么才能", "教我", "怎么做", "从哪开始",
              "怎么下手", "有什么办法", "如何入手", "该做什么", "怎么避免",
              "怎么办", "怎么跟", "该怎么", "怎么样才能", "如何避免")),
    ("收尾", ("好吧", "行吧", "算了", "那算了", "不聊了")),
    ("应声", ("嗯", "哦", "喔", "啊", "噢", "也是", "对啊", "没错", "是这样")),
)

# 「你刚才说什么」这类问的是记忆，不是话题，单独处理
JIYI_WEN = ("你说什么来着", "我刚才说什么", "我说了什么", "记得我刚才",
            "还记得我", "我刚说的")

ZHUIGEN_HUI = {
    "为什么": (
        "说实话我也讲不出个所以然 —— 我就是这么感觉的。"
        "你要的是理由，还是想确认一下我没在敷衍你？",
        "「%s」这事要真解释，我能编一套，但那不老实。"
        "我的直觉是：很多事没那么多个为什么，是一点点攒出来的。",
        "问得好。我要硬给个因果，反而是糊弄你。我更想知道，你心里那个答案是往哪边偏的？",
    ),
    "续讲": (
        "「%s」往下我也没亲眼见过。你要是愿意讲，我陪你一句一句捋。",
        "「%s」这事儿到这儿就剩你自己拿主意了。你想往哪走？",
        "然后啊……「%s」后面那段我猜不到，你告诉我呗。",
    ),
    "求证": (
        "真的，我没糊弄你。「%s」这种事听着确实像套话，可我说的都是实话。",
        "「%s」我要是拿不准，会直接说不准 —— 装懂更省事，可那没意思。",
    ),
    "反问你": (
        "我啊，没什么故事。「%s」这事我倒更想听你怎么看。",
        "轮到我也就是个会接话的程序。倒是你，「%s」你打算怎么办？",
    ),
    "共鸣": (
        "那咱俩算站一块了。「%s」这种感觉，你从什么时候开始的？",
        "看来不止我一个。「%s」这事，你身边还有谁也这样？",
    ),
    "澄清": (
        "是我表达得绕了。回到「%s」，你其实想问哪一点？",
        "怪我，说复杂了。就「%s」这一件，你怎么看？",
    ),
    "展开": (
        "比如说「%s」—— 真到要做决定那一步，你会先看哪一条？",
        "具体到「%s」：哪一步最让你卡住？",
    ),
    "求法": (
        "「%s」这么问，说明你想动手了。我的笨办法是：先做最小的一步，"
        "小到不可能失败的那种，做完再看下一步。",
        "要我说，别先找「最好的方法」——那玩意儿不存在。"
        "先挑一个能坚持三天的做法，从%s里最不费劲的那块下手。",
        "我教你个土办法：把「%s」拆成三个动作，只做第一个，明天再说第二个。"
        "你要不要现在就想一下第一个是什么？",
    ),
    "收尾": (
        "嗯。那先放着，想起来再聊。",
        "行，这个先不聊了。要不要换个轻松的？",
    ),
    "应声": (
        "嗯，我在。你说。",
        "听着呢，你继续。",
        "嗯。想到什么说什么，不用组织语言。",
    ),
}


_ZHUI_QUAN_CI = tuple(k for _lei, _ks in ZHUIGEN_LEI for k in _ks)


def _shang_ju(kuai=14):
    """最近一句“有内容”的话 —— 跳过「然后呢」「嗯」这种光秃秃的追问。

    为什么不能让追问句去填追问：连着问两句「然后呢」「为什么」，
    第二句会变成「「然后呢」这事要真解释…」，比原来填话题词还离谱。
    """
    for w in reversed(list(HUI_HUA["ju"])):
        if len(w) < 4:
            continue
        return w if len(w) <= kuai else w[:kuai - 2] + "…"
    return ""


def jie_zhuigen(text):
    """追问层：命中返回一句真正接着上文的话，否则 None

    只在"确实有上一轮"时才管 —— 一上来就问「为什么」是独立提问，
    照旧交给后面的层，不能凭空接。
    """
    t = (text or "").strip()
    if not t or len(t) > 16:
        return None
    if not SHANG_YI_LUN["wen"]:
        return None                 # 没有上文，不冒充"记得"

    # ① 先看是不是在问「我刚才说什么」
    if any(k in t for k in JIYI_WEN):
        ji = SHANG_YI_LUN["wen"]
        if len(ji) > 24:
            ji = ji[:22] + "…"
        return random.choice((
            "记得，你刚才说的是「%s」。",
            "记得啊 ——「%s」。我没走神。",
        )) % ji

    ti = SHANG_YI_LUN["ti"] or "这个"
    for lei, ci in ZHUIGEN_LEI:
        if any(k in t for k in ci):
            # 【本轮补】「过拟合是什么意思」含「什么意思」，原来被澄清类当成追问，
            # 回一句「是我表达得绕了」。判据：把问法词抽掉之后还剩 2 个字以上的实词，
            # 说明问的是**某个东西**的意思，不是没听懂我上一句。
            if lei == "澄清":
                if len(t) > 4 and any(k in t for k in _DING_YI_WEN):
                    continue
                if len(_ti_hua_ti(t)) >= 2 and _ti_hua_ti(t) not in JS_FAN_CI:
                    continue

            zi = _ti_hua_ti(t)

            # 【本轮新增】「然后呢」「举个例子」「番茄炒蛋怎么做」这类要的是“接着说”，
            # 素材里若真有这个话题的句子，念出来比抽一句通用台词强。
            # 续讲/展开查上一轮的话题；求法查本句自己的宾语（「番茄炒蛋怎么做」→ 番茄炒蛋）。
            # 求证/共鸣/应声不查：那几类本来就不该念资料。
            if lei in ("续讲", "展开", "求法", "为什么"):
                chaxun = (zi if lei in ("求法", "为什么") and len(zi) >= 2 else ti)
                if chaxun and chaxun != "这个":
                    daan = _jiansuo_daan(chaxun, yan_ge=True)
                    if daan:
                        return daan

            ku = list(ZHUIGEN_HUI[lei])
            you = [x for x in ku if "%s" in x]      # 带空要填的
            wu = [x for x in ku if "%s" not in x]   # 自己就成句的
            # 【本轮修正】求法类（「怎么才能早睡」「教我背单词」）要填的是
            # **这一句自己**要学的东西，不是上一轮的话题。
            # 原来一律用 SHANG_YI_LUN["ti"]，于是「给我点建议」之后问
            # 「怎么才能早睡」，回出来的是「把「点建议」拆成三个动作」。
            # 【本轮修正】不只是求法类 —— 「人为什么要活着」这类自带宾语的追问，
            # 填上一轮的话题词（上一轮问的是「成熟」）会答成
            # 「「成熟」这事要真解释……」，完全跑题。
            # 规则：本句能抽出 2~8 字的实词就用本句的；抽不到（「为什么」
            # 「然后呢」这种光秃秃的追问）才退回上一轮。
            tian = ""
            # 续讲/展开/求证/共鸣/反问/澄清这几组是“纯追问”，本身不带宾语：
            # 「然后呢」「还有呢」「具体点」抽出来的都是追问词，填进空里就成
            # 「说到「还有」…」。只有求法/为什么可能自带宾语（「番茄炒蛋怎么做」）。
            # 「很焦虑怎么办」「失恋了怎么办」这种带着情绪来求解法的，
            # 别用「拆三个动作」那套 —— 先接住人，交给后面的情绪层。
            if lei == "求法" and _fu_mian(t):
                return None
            zi = _ti_hua_ti(t)
            zi = zi.rstrip("嘛啊呀吧哦哈呢")          # 「怎么办嘛」别抽出「办嘛」
            yong_zi = lei in ("求法", "为什么", "澄清") and len(zi) >= 2
            if lei in ("续讲", "展开", "求证", "共鸣", "反问", "澄清"):
                # 这几组是纯追问，本身不带宾语 → 一律回指“你刚才说的那句话”。
                # 原来填话题词（「考研」），出来是「「考研」这事要真解释…」，听着像念标签。
                tian = _shang_ju() or ""
            elif yong_zi and len(zi) <= 8 and zi not in _ZHUI_QUAN_CI and zi not in JS_FAN_CI:
                tian = zi                              # 「番茄炒蛋怎么做」用自己的宾语
            elif ti and ti != "这个":
                tian = ti                              # 没有宾语就退到上一轮的话题词
            else:
                tian = _shang_ju() or ""

            if tian and you:
                return _chou(you) % tian
            if you:
                return _chou(you) % ti
            return _chou(wu or ku)
    return None


# 句子里出现这些词，说明讲的是关系/处境，不是娱乐本身。
# 「我男朋友打游戏不理我」不该被拉去聊段位，「心情不好打游戏输了」也不是求攻略。
_GUAN_XI_CI = ("不理", "不管我", "不陪我", "不还", "不给", "哭", "难过", "生气",
               "分手", "吵架", "冷战", "孤独", "很累", "好累", "烦", "没理我",
               "忽略", "敷衍", "伤心", "委屈", "心情", "不开心", "郁闷",
               "压抑", "没意思", "男朋友", "女朋友", "对象", "老公", "老婆")

# 纯娱乐组的识别词：句子里有它们、又同时有上面的关系词时，跳过这一组
_YU_LE_CI = ("游戏", "打游戏", "上分", "开黑", "电竞", "王者", "段位", "英雄")

def _pipei_huati(text):
    """在话题库里挑命中的最长关键词那条，返回 (关键词, 回复元组) 或 None

    【本轮加的闸】句子里同时出现「关系/情绪词」和「纯娱乐词」时，跳过娱乐组。
    「我男朋友打游戏不理我」关键词最长的是「打游戏」，可它只是背景，
    用户真正在说的是被忽略；不跳过去就会答成「段位、出装、上分」。
    """
    guan_xi = any(ci in text for ci in _GUAN_XI_CI)
    # 第一轮：不让元问题词参与，先找真正的话题
    for paichu in (True, False):
        zui_hao, zui_ci, zui_chang = None, "", 0
        for guanjian, huifu in HUATI_KU:
            if guan_xi and any(k in _YU_LE_CI for k in guanjian):
                continue                     # 关系句不聊娱乐攻略
            for k in guanjian:
                if paichu and k in YUAN_WEN_CI:
                    continue
                if k in text and len(k) > zui_chang:
                    zui_hao, zui_ci, zui_chang = huifu, k, len(k)
        if zui_hao is not None:
            return zui_ci, zui_hao
    return None


# 疑问句兜底：不装懂，但绝不说「答不上来」。三件事必须做全 ——
#   ① 把问的那个东西点出来（证明听懂了，不跑题）
#   ② 给一个明确的、有立场的看法（空话会被听成敷衍）
#   ③ 反手把话头递回去（对话才接得下去）
_JIE_WEN = (
    "「%s」这事，一句话说不完。我的笨看法是：越是想给它一个标准答案，越容易说偏。"
    "你自己心里更偏哪一边？",
    "问到「%s」了。我读的书不多，只能说实话：这东西没有统一答案，"
    "每个人手里那版都不一样。你的那版是什么样的？",
    "「%s」——这个问题挺大的，我不敢糊弄你。我能给的是：它多半不是知识题，是选择题。"
    "你最近是不是正好在这上面犯难？",
    "关于「%s」，我想到的不是定义，是具体的人和事。你是因为什么问起这个的？",
    "「%s」啊……我要是张口就背一段定义，那才叫没听懂。"
    "我更想知道：你是想弄清楚它，还是想弄清楚自己？",
)


# 定义型提问的识别：「X 是什么 / 什么叫 X / 什么是 X / X 是什么意思」
_DING_YI_WEN = ("是什么", "什么叫", "什么是", "是什么意思", "啥意思", "啥玩意",
                "指的是什么", "的定义", "怎么理解", "如何理解", "是啥")

# 回答框架：不背定义，给一个具体侧面，再把话头递回去。
# 为什么不给定义？因为这类概念（成熟/幸福/善良/意识）本来就没有统一定义，
# 背一段百科式的解释反而最像机器人。具体侧面 + 反问才像人在聊。
_DING_YI_HUI = (
    "「%s」这种词，字典给的答案通常是错的。我的笨理解是：它不是一个状态，"
    "是你反复做同一类选择之后，别人给你贴的标签。你怎么理解？",
    "要我说，「%s」得放在具体的事里才看得见 —— 抽象地谈，谁都能说得很漂亮。"
    "你是在哪件事上想到这个词的？",
    "「%s」我背不出定义，但我有一个土办法判断它：看一个人在没人看着的时候怎么选。"
    "你觉得呢？",
)


# 从定义型提问里抠出「被定义的那个词」。三套模式覆盖绝大多数说法。
_DING_YI_SHI = (
    # 「X 是什么 / X 是什么意思 / X 指的是什么」
    re.compile(r"^(.{1,8}?)(?:到底是什么|究竟是什么意思|是什么意思|指的是什么|是什么)"),
    re.compile(r"^(?:什么|啥)是(.{1,6}?)(?:呢|啊|呀|？|\?)?$"),
    re.compile(r"^(?:什么|啥)?叫(?:做)?(.{1,6}?)(?:呢|啊|呀|？|\?)?$"),
    re.compile(r"^(.{1,8}?)(?:的定义|怎么理解|如何理解)"),
)

# 抽出来的词里不该带的尾巴（「人到底」的「到底」、「时间究竟」的「究竟」）
_DING_YI_WEI = ("到底", "究竟", "到底有", "究竟有", "还有", "真的")


# ══════════════════════════════════════════════════════════════════════════════
# 概念表：常见抽象词的专属回答（每个词 2 句）
# ------------------------------------------------------------------------------
# 为什么不靠通用模板？因为「什么是孤独」「什么是真相」「什么是善良」连着问，
# 通用模板会给出一模一样的一句话 —— 用户立刻发现是复读机。
# 这张表让每个词都有自己的答案，宁可说得笨，也不能说得空。
# 命中规则：词在原句里出现即可（最长优先），所以「善良」不会被「善」抢走。
# ══════════════════════════════════════════════════════════════════════════════
_DING_YI_KU = (
    (("孤独", "寂寞"), (
        "孤独不是没人陪，是有人在旁边你还得自己扛。这两件事差得远。",
        "我理解的孤独是：你有一肚子话，但翻遍通讯录找不到一个能直接说的人。",
    )),
    (("真相", "事实"), (
        "真相这东西，多数时候不是被藏起来的，是没人愿意第一个说。",
        "我对真相的看法有点丧：知道真相往往不让人舒服，所以人才会主动选不知道。",
    )),
    (("善良",), (
        "善良不是软，是明明有能力让别人难受，却选择不那么干。",
        "善良最难的部分不是对好人好，是对那些对你不好的人还留一分余地。",
    )),
    (("美", "审美"), (
        "美这事没法定义，但你有过那种经验：看见某样东西，呼吸慢了半拍。那就是。",
        "我觉得美不在东西上，在看的人身上 —— 同一片天，有人拍下来，有人只想快点回家。",
    )),
    (("成功",), (
        "成功这词最坑人的地方是：它的标准大多是别人定的。你要先问清是谁的标准。",
        "我理解的成功能朴素一点：你想干的事能自己决定干不干，就算。",
    )),
    (("勇気", "勇气", "勇敢"), (
        "勇气不是不怕，是怕着还往前走。不怕的那种叫莽。",
        "勇气多数时候很小：就是那句该说的话，你在心里排练了十遍，最后还是说了。",
    )),
    (("成熟",), (
        "成熟不是变冷，是知道有些事争不出结果，就不争了。",
        "我理解的成熟是：你能承受别人对你失望，而不立刻去补救。",
    )),
    (("自由",), (
        "自由不是想干什么就干什么，是想不干什么就能不干什么。后者难得多。",
        "自由的代价是责任 —— 没人替你决定了，也就没人替你担。",
    )),
    (("死亡", "死", "去世"), (
        "死亡最难受的地方不是自己没了，是别人的日子还得照过。",
        "我不太敢谈死亡。我能说的是：它让活着这件事变得有期限，有期限才有轻重。",
    )),
    (("时间",), (
        "时间最不公平的地方：难熬的时候它慢，好过的时候它飞快。",
        "时间不是流水，是账本 —— 你花在哪儿，它就长成什么样。",
    )),
    (("幸福", "快乐"), (
        "幸福不是一直高兴，是难受的时候知道有人接得住你。",
        "幸福这词被广告用坏了。我觉得它更接近「没什么想换的」。",
    )),
    (("意义", "意义何在"), (
        "意义这问题，我倾向于它是事后长出来的，不是事前想出来的。",
        "追问意义的人，多半是正在做一件看不到结果的事。这挺正常的。",
    )),
    (("命运", "宿命"), (
        "命运这词，我倾向于这么看：运气决定你遇到什么，选择决定你留下什么。",
        "相信命运有个好处 —— 输的时候不那么自责；坏处是赢得也不那么痛快。",
    )),
    (("遗憾", "后悔"), (
        "遗憾的本质不是做错了，是「另一条路我没走过」，所以它永远显得更好。",
        "后悔这事有个规律：人最后悔的往往不是做错的事，是没做的事。",
    )),
    (("信任",), (
        "信任建起来要很久，碎掉只要一下，而且粘回去也有缝。",
        "信任不是相信对方不会骗你，是相信他骗你之后会来承认。",
    )),
    (("责任", "担当"), (
        "责任说白了就是：出了事，你不找别人。",
        "责任这东西扛久了会长在身上，有时候你都分不清哪些本来不该是你的。",
    )),
    (("痛苦", "苦难"), (
        "痛苦没法比较，别人看着小的事，落在你身上就是大事。",
        "痛苦有个奇怪的用处：它把不重要的事全筛掉了。",
    )),
    (("焦虑",), (
        "焦虑多半是事情太多、时间不够、又都想做好。挑一个先做完，会松很多。",
        "焦虑的本质是对未来的预演，可预演多半演的是最坏那版。",
    )),
    (("希望",), (
        "希望不是乐观，是明知道可能不成，还是留了一手准备。",
        "希望这东西不能靠别人给，给了也会被收回去。",
    )),
    (("尊重",), (
        "尊重不是客气，是把对方当成一个能自己做决定的人，哪怕你不认同。",
        "尊重最见真章的地方是：对方拒绝你的时候，你还站得住。",
    )),
    (("原谅", "宽恕"), (
        "原谅不是便宜了对方，是不想再让自己每天重播一遍。",
        "原谅可以不带和解 —— 你可以放下这件事，同时不再跟这个人来往。",
    )),
    (("爱", "爱情"), (
        "爱这词定义能写一本书，但落到具体人身上往往就一件事：你愿不愿意为对方改一点自己的习惯。",
        "我理解的爱不是心动那一下，是心动之后还愿意留下来处理那些麻烦。",
    )),
    (("朋友", "友谊"), (
        "朋友这事儿看质量不看数量。三五个能在半夜接你电话的，就够了。",
        "真朋友有个特征：隔半年不见，坐下来还能直接说正事。",
    )),
    (("家", "家人", "亲情"), (
        "家人这关系最特别的地方：你不能选，也很难退出。",
        "家是那个你回去不用解释自己的地方 —— 有人的家不是这样，那就得自己造一个。",
    )),
)


def _chou_ding_yi_ci(text):
    """把「什么叫成熟」「什么是美」「爱情是什么」里的那个词抠出来"""
    t = text.strip().rstrip("？?。！! ")
    for zheng in _DING_YI_SHI:
        pi = zheng.match(t)
        if pi:
            ci = pi.group(1).strip()
            # 「人到底是什么」会抠出「人到底」，把尾巴削掉才是个词
            for wei in sorted(_DING_YI_WEI, key=len, reverse=True):
                if ci.endswith(wei) and len(ci) > len(wei):
                    ci = ci[:-len(wei)]
                if ci.startswith(wei) and len(ci) > len(wei):
                    ci = ci[len(wei):]
            if ci and not ci.startswith(("什么", "啥")):
                return ci