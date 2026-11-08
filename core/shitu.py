# -*- coding: utf-8 -*-
"""shitu.py —— 识图（提取文字 / 认人 / 认物 / 描述穿搭）

从旧版第九部分的第 14238-15300 行整段搬来，**一个字没改**（只补了 TUPIAN_GE 和
MOGEN_DIR 的路径来源，见下）。

三件事都是本地模型，不联网：
  1. 提取图里的文字      -> RapidOCR（自带中英文模型）
  2. 认出人并画框        -> YuNet 人脸检测 + YOLOX 的 person 类
  3. 认出物体并画框      -> YOLOX（COCO 80 类，640 输入）

模型文件在 core/models/，40 MB，跟着程序走。
没有它们时本模块 import 不会崩 —— 只在真正识图时返回一句"模型缺了"。

【联网优先】dev 版里 shitu_llm() 走多模态大模型（见 api.py 的 kan_tu_llm），
本模块是**降级方案**：没填钥匙 / 没网 / 模型缺了，才退回这里。
"""
import os
import sys

# 模型目录跟着**本文件**走（core/models/），不跟 DIR ——
# DIR 是"用户素材目录"（ui/），模型是程序自带的，两者不该混。
_ZHEN = os.path.dirname(os.path.abspath(__file__))

DIR = os.environ.get("XBD_DIR") or os.path.dirname(_ZHEN)

# 第九部分：识图（提取文字 / 认人 / 认物 / 描述穿搭）
# ----------------------------------------------------------------------
# 用户要的三件事，分别由三个离线模型完成：
#   1. 提取图里的文字      → RapidOCR（自带中英文模型，装在包里，不用联网）
#   2. 认出图里的人并画框  → YuNet 人脸检测 + NanoDet 的 person 类，两者叠起来
#   3. 认出图里的物体并画框 → NanoDet（COCO 80 类，杯子/手机/键盘这些）
#
# 三条"不影响主程序"的规矩：
#   · 模型全部在用的时候才加载（第一次点识图才 import opencv、才读 onnx），
#     所以没装库、没放模型文件时，程序照样能启动、照样聊天。
#   · 任何一种识别失败，只在这个识图窗口里写一行错误提示，不抛到外面。
#   · 识别放在子线程里跑，界面不会卡死；跑完再用 root.after 回到主线程刷界面。
# ======================================================================

import threading

# 允许选的图片格式（tkinter 的文件对话框用它筛）
TUPIAN_GE = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")

# 三个 onnx 模型放在程序旁边的 models 文件夹里
MOGEN_DIR = os.path.join(_ZHEN, "models")
FACE_MOGEN = os.path.join(MOGEN_DIR, "face_detection_yunet_2023mar.onnx")

# 物体检测：主用 YOLOX（640 输入，准得多），NanoDet 留作降级备份。
# 为什么换？原来的 NanoDet 只有 0.9M 参数、416 输入，在暗光/大动作的图上
# 会把月亮认成飞机、把随手一块布料认成人，误检一堆。YOLOX 大 40 倍，
# 同一个位置只给一个框，蜘蛛侠那张图从「3 个人」变成「1 个人」。
WUTI_MOGEN = os.path.join(MOGEN_DIR, "object_detection_yolox_2022nov.onnx")
WUTI_MOGEN_BEI = os.path.join(MOGEN_DIR, "object_detection_nanodet_2022nov.onnx")

# 检测参数（这三个数是拿 messi5 / basketball1 / lena / fruits / 蜘蛛侠
# 五张图逐一扫出来的，不是随手定的，理由见各变量注释）
WUTI_CHICUN = 640      # 输入边长。640 比 416 多留一倍细节，大物体框得更贴
WUTI_YUZHI = 0.25      # 分数阈值。0.15 会冒出「船/马桶」这种瞎猜，0.25 刚好干净
WUTI_ZUIXIAO = 0.015   # 面积下限：小于整图 1.5% 的当细节，忽略不报
#                        （用户要求"细节可以忽略，大物件一定要识别出来"）

# NanoDet 输出的 80 个类别名（COCO 数据集顺序，不能改）
COCO_LEI = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "?", "stop sign", "parking meter",
    "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear",
    "zebra", "giraffe", "?", "backpack", "umbrella", "?", "handbag", "tie",
    "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "?", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog",
    "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "?",
    "dining table", "?", "?", "toilet", "?", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "?", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush")

# 常见的几类给个中文名，没列到的就显示英文原名
COCO_ZHONG = {
    "person": "人", "bicycle": "自行车", "car": "汽车", "motorcycle": "摩托车",
    "bus": "公交车", "train": "火车", "truck": "卡车", "boat": "船",
    "bird": "鸟", "cat": "猫", "dog": "狗", "horse": "马",
    "backpack": "背包", "umbrella": "雨伞", "handbag": "手提包", "tie": "领带",
    "suitcase": "行李箱", "frisbee": "飞盘", "sports ball": "球",
    "bottle": "瓶子", "wine glass": "酒杯", "cup": "杯子", "fork": "叉子",
    "knife": "刀", "spoon": "勺子", "bowl": "碗", "banana": "香蕉",
    "apple": "苹果", "sandwich": "三明治", "orange": "橙子", "pizza": "披萨",
    "donut": "甜甜圈", "cake": "蛋糕", "chair": "椅子", "couch": "沙发",
    "potted plant": "盆栽", "bed": "床", "dining table": "桌子", "toilet": "马桶",
    "tv": "电视", "laptop": "笔记本电脑", "mouse": "鼠标", "remote": "遥控器",
    "keyboard": "键盘", "cell phone": "手机", "microwave": "微波炉",
    "oven": "烤箱", "toaster": "面包机", "sink": "水槽", "refrigerator": "冰箱",
    "book": "书", "clock": "钟表", "vase": "花瓶", "scissors": "剪刀",
    "teddy bear": "毛绒玩具", "hair drier": "吹风机", "toothbrush": "牙刷",
    # 这一批原来没翻，屏幕上会直接蹦英文（bench 被念成"bench"）
    "airplane": "飞机", "traffic light": "红绿灯", "fire hydrant": "消防栓",
    "stop sign": "停止牌", "parking meter": "停车计时器", "bench": "长椅",
    "sheep": "羊", "cow": "牛", "elephant": "大象", "bear": "熊",
    "zebra": "斑马", "giraffe": "长颈鹿", "skis": "滑雪板",
    "snowboard": "单板滑雪板", "kite": "风筝", "baseball bat": "棒球棒",
    "baseball glove": "棒球手套", "skateboard": "滑板",
    "surfboard": "冲浪板", "tennis racket": "网球拍", "broccoli": "西兰花",
    "carrot": "胡萝卜", "hot dog": "热狗",
}

# 三个模型/库的单例，第一次用到才创建；_cuo 里存"为什么没建成"，给界面显示
_se_ocr = None
_se_ocr_cuo = ""
_se_wuti = None
_se_wuti_cuo = ""
_se_wuti_leixing = ""      # "yolox" 还是 "nanodet"，决定后面怎么解码
_se_face_cuo = ""
_se_kai_suo = threading.Lock()

# 框的颜色：人物红、物体绿、文字橙
SE_RENWU = "#e53935"
SE_WUTI = "#43a047"
SE_WENZI = "#fb8c00"


# ---------------------- 1. 提取文字 ----------------------
# 【第二轮】三个阈值从默认（0.5/0.5/1.6）调低。
# 起因：成绩单那张图里「89」整个漏掉。实测原因是检测框分数 0.45 上下，
# 被 box_thresh=0.5 直接筛掉了，识别模型其实认得出。调到 0.30 之后
# 42 条变 43 条，多出来的正好是那个 89，而且没有多出垃圾条目。
# unclip_ratio 从 1.6 提到 1.8：数字行很窄，外扩多一点才不会把上下边切掉。
OCR_BOX_YUZHI = 0.30      # 文本框的检测分数下限
OCR_WEN_YUZHI = 0.30      # 文字识别的置信度下限
OCR_UNCLIP = 1.80         # 检测框外扩比例
OCR_ZUI_CHANG = 2200      # 送进 OCR 前先把长边缩到这个尺寸（大图提速十倍）


def _yao_ocr():
    """第一次调用时把 OCR 引擎建起来；失败就把原因记在 _se_ocr_cuo 里"""
    global _se_ocr, _se_ocr_cuo
    with _se_kai_suo:
        if _se_ocr is not None or _se_ocr_cuo:
            return _se_ocr
        try:
            from rapidocr_onnxruntime import RapidOCR
        except Exception:
            _se_ocr_cuo = ("没装识别文字用的库 rapidocr-onnxruntime。\n"
                           "在命令行里运行这一句装上就行：\n"
                           "  pip install rapidocr-onnxruntime -i "
                           "https://pypi.tuna.tsinghua.edu.cn/simple")
            return None
        try:
            _se_ocr = RapidOCR()
        except Exception as e:
            _se_ocr_cuo = "识别文字用的模型加载失败：%s" % e
            _se_ocr = None
        return _se_ocr


def _kuang_zhong(kuang):
    """四点框 → (中心 x, 中心 y, 高)"""
    try:
        xs = [float(p[0]) for p in kuang]
        ys = [float(p[1]) for p in kuang]
    except Exception:
        return 0.0, 0.0, 0.0
    return (sum(xs) / len(xs), sum(ys) / len(ys), max(ys) - min(ys))


def _pai_hang(out):
    """把识别结果按"从上到下、同一行从左到右"重排（第二轮新增）

    为什么必须排：模型输出的是"检测框的原始顺序"，看起来是乱的 ——
    成绩单那张图里 99 后面跟着课程名，再隔几行才是 92，用户对着图看很费劲。
    排序规则：先按中心 y 分行（同一行的判定容差取该行字高的一半），
    行内再按中心 x 从左到右。
    """
    if not out:
        return out
    dai = []
    for i, (kuang, wen, fen) in enumerate(out):
        cx, cy, h = _kuang_zhong(kuang)
        dai.append((cy, cx, max(1.0, h), i))
    dai.sort(key=lambda t: t[0])
    hang = []
    for cy, cx, h, i in dai:
        if hang:
            _y, _h, _lie = hang[-1]
            if abs(cy - _y) <= max(6.0, min(h, _h) * 0.55):
                _lie.append((cx, i))
                hang[-1] = ((_y * len(_lie) + cy) / (len(_lie) + 1),
                            max(_h, h), _lie)
                continue
        hang.append((cy, h, [(cx, i)]))
    jieguo = []
    for _y, _h, lie in hang:
        lie.sort(key=lambda t: t[0])
        for _cx, i in lie:
            jieguo.append(out[i])
    return jieguo


def _wen_you_xiao(wen):
    """这段文字有没有"内容"：纯符号、纯空白的当成噪声丢掉"""
    for ch in wen:
        if ch.isalnum():
            return True
        if "\u4e00" <= ch <= "\u9fa5":
            return True
    return False


def _ocr_pao(ocr, tu):
    """跑一次识别，返回原始结果（老版本不认关键字时退回默认参数）"""
    try:
        j, _ = ocr(tu, box_thresh=OCR_BOX_YUZHI, text_score=OCR_WEN_YUZHI,
                   unclip_ratio=OCR_UNCLIP)
        return j
    except TypeError:
        j, _ = ocr(tu)
        return j


def _kuang_suo(jieguo, bi):
    """把框的坐标乘一个系数（放大/缩小图之后换算回原图坐标）"""
    if not jieguo or bi == 1.0:
        return jieguo
    out = []
    for h in jieguo:
        try:
            kuang = [[float(pt[0]) * bi, float(pt[1]) * bi] for pt in h[0]]
            out.append([kuang, h[1], h[2] if len(h) > 2 else 0.0])
        except Exception:
            continue
    return out


def tiqu_wenzi(tupian):
    """识别整张图里的文字。返回 (结果列表, 错误说明)
    结果列表每一项是 (四个角点, 文字, 置信度)，已按阅读顺序排好。"""
    ocr = _yao_ocr()
    if ocr is None:
        return [], _se_ocr_cuo

    # 【第二轮】大图先缩到 2200。检测模型内部只按 736 的短边工作，拿 7898px
    # 的原图去跑纯属浪费：实测那张 23MB 的图要 15.8 秒，缩完 2 秒内出结果，
    # 文字一个不少。
    gong, bi = _suo_xiao(tupian, OCR_ZUI_CHANG)
    try:
        jieguo = _ocr_pao(ocr, gong)
    except Exception as e:
        return [], "识别文字时出错了：%s" % e

    # 小图/小字兜底：一条都没检出、或只检出零星几条时放大一倍再试一次
    if not jieguo or len(jieguo) < 5:
        try:
            import cv2
            gao, kuan = gong.shape[:2]
            if max(gao, kuan) <= 1400:
                da = cv2.resize(gong, None, fx=2.0, fy=2.0,
                                interpolation=cv2.INTER_CUBIC)
                jieguo2 = _ocr_pao(ocr, da)
                if jieguo2 and (not jieguo or len(jieguo2) > len(jieguo)):
                    jieguo = _kuang_suo(jieguo2, 0.5)
        except Exception:
            pass

    if not jieguo:
        return [], ""
    if bi != 1.0:
        jieguo = _kuang_suo(jieguo, 1.0 / bi)

    out = []
    for hang in jieguo:
        # rapidocr 返回 [框的四点坐标, 文字, 分数]
        kuang = hang[0]
        wen = str(hang[1]).strip()
        fen = float(hang[2]) if len(hang) > 2 else 0.0
        if wen and _wen_you_xiao(wen):
            out.append((kuang, wen, fen))
    return _pai_hang(out), ""


# ---------------------- 1.5 模型路径兜底（中文路径 · OpenCV 读不了） ----------------------
# 为什么需要这个？
#   cv2.dnn.readNet / cv2.FaceDetectorYN 都是 OpenCV 的 C++ 侧在开文件，
#   它不认非 ASCII 路径。实测同一份模型：
#     ...\Ge\1\models\face_detection_yunet_2023mar.onnx   → 成功
#     ...\Desktop\Pei\小笨蛋\models\同文件              → Can't read ONNX file
#   而这个程序自己（用 PIL 读图）是认中文的，所以只有模型这一路会挂。
# 办法：
#   ① 能走内存的（cv2.dnn）直接喂字节，压根不碰路径；
#   ② 只能给路径的（YuNet），把文件复制到 %LOCALAPPDATA%\XiaoBenDan\models，
#      那个目录保证是 ASCII，再把这个路径交给它。
# 打包换目录、换盘符都不受影响，第一次会多花几十毫秒复制，之后直接命中。
MOGEN_YINGWEN = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "XiaoBenDan", "models")


def _yingwen_mogen(lu):
    """给一个 onnx 路径，返回一个「OpenCV 一定能打开」的路径。

    本来就是纯英文路径就原样返回；否则复制到 MOGEN_YINGWEN 下。
    复制失败就退回原路径，让调用方照常报错，不至于整个功能哑掉。
    """
    try:
        lu.encode("ascii")
        return lu                      # 纯英文，直接用
    except UnicodeEncodeError:
        pass
    try:
        if not os.path.isdir(MOGEN_YINGWEN):
            os.makedirs(MOGEN_YINGWEN, exist_ok=True)
        mubiao = os.path.join(MOGEN_YINGWEN, os.path.basename(lu))
        # 已经复制过、大小也一致，就不再重复复制
        if not (os.path.exists(mubiao)
                and os.path.getsize(mubiao) == os.path.getsize(lu)):
            shutil.copyfile(lu, mubiao)
        return mubiao
    except Exception:
        return lu                      # 兜不住就交回原路径


# ---------------------- 1.9 大图先缩小再检测 ----------------------
# 为什么：检测模型自己会把图缩到 640/416，但**缩放这一步本身**是按原图
# 像素量算的；7898×5924 的手机原图光这一步就要 3 秒，而结果和先缩到
# 1600 再检测完全一样（缩到 640 之前的信息早就丢光了）。
# 所以统一"进门先缩"，识别完再把坐标按比例放大回去。
JIANCE_ZUI_CHANG = 1600


def _suo_xiao(tupian, zui_chang=JIANCE_ZUI_CHANG):
    """把长边超过 zui_chang 的图缩小，返回 (图, 缩放比)。没缩就返回 1.0"""
    try:
        import cv2
        gao, kuan = tupian.shape[:2]
        chang = max(gao, kuan)
        if chang <= zui_chang:
            return tupian, 1.0
        bi = float(zui_chang) / float(chang)
        xiao = cv2.resize(tupian, (max(1, int(kuan * bi)), max(1, int(gao * bi))),
                          interpolation=cv2.INTER_AREA)
        return xiao, bi
    except Exception:
        return tupian, 1.0


# ---------------------- 2. 认人 ----------------------
def zhao_renlian(tupian):
    """YuNet 找人脸，返回 ([(x,y,w,h,分数)], 错误说明)"""
    global _se_face_cuo
    if _se_face_cuo:
        return [], _se_face_cuo
    try:
        import cv2
    except Exception:
        _se_face_cuo = "没装 opencv，认不出人脸。\n装法：pip install opencv-python"
        return [], _se_face_cuo
    if not os.path.exists(FACE_MOGEN):
        _se_face_cuo = ("找不到人脸模型文件：\n  %s\n"
                        "把 face_detection_yunet_2023mar.onnx 放进 models 文件夹即可。"
                        % FACE_MOGEN)
        return [], _se_face_cuo
    try:
        # 大图先缩到 1600 再检测：YuNet 在这个尺寸上够准，速度快一个量级
        xiao, bi = _suo_xiao(tupian)
        gao, kuan = xiao.shape[:2]
        # YuNet 只收路径，先摊到纯英文目录，否则中文路径下必然读不出来
        jian = cv2.FaceDetectorYN.create(
            _yingwen_mogen(FACE_MOGEN), "", (kuan, gao), 0.6, 0.3, 5000)
        _, lian = jian.detect(xiao)
    except Exception as e:
        _se_face_cuo = "人脸检测初始化失败：%s" % e
        return [], _se_face_cuo
    out = []
    if lian is not None:
        for f in lian:
            x, y, w, h = f[:4]
            if bi != 1.0:                       # 坐标换回原图
                x, y, w, h = x / bi, y / bi, w / bi, h / bi
            out.append((int(x), int(y), int(w), int(h), float(f[-1])))
    return out, ""


# ---------------------- 3. 认物体 ----------------------
def _yao_wuti():
    """第一次调用时把物体检测模型读进来（YOLOX 优先，NanoDet 兜底）"""
    global _se_wuti, _se_wuti_cuo, _se_wuti_leixing
    with _se_kai_suo:
        if _se_wuti is not None or _se_wuti_cuo:
            return _se_wuti
        try:
            import cv2
        except Exception:
            _se_wuti_cuo = "没装 opencv，认不出物体。\n装法：pip install opencv-python"
            return None

        # 先试 YOLOX
        if os.path.exists(WUTI_MOGEN):
            try:
                _se_wuti = cv2.dnn.readNet(
                    _yingwen_mogen(WUTI_MOGEN), engine=cv2.dnn.ENGINE_CLASSIC)
                _se_wuti_leixing = "yolox"
                return _se_wuti
            except Exception as e:
                # 读不成就退回 NanoDet，不让整个识图功能废掉
                _se_wuti = None
                _se_wuti_leixing = ""

        # 退路：NanoDet
        if os.path.exists(WUTI_MOGEN_BEI):
            try:
                # NanoDet 必须用经典引擎，且输入写死 416，否则 Reshape 层报错
                _se_wuti = cv2.dnn.readNet(
                    _yingwen_mogen(WUTI_MOGEN_BEI), engine=cv2.dnn.ENGINE_CLASSIC)
                _se_wuti_leixing = "nanodet"
                return _se_wuti
            except Exception as e:
                _se_wuti_cuo = "物体模型加载失败：%s" % e
                _se_wuti = None
                return None

        _se_wuti_cuo = ("找不到物体模型文件，两个都没找到：\n  %s\n  %s\n"
                        "把 object_detection_yolox_2022nov.onnx 放进 models 文件夹即可。"
                        % (WUTI_MOGEN, WUTI_MOGEN_BEI))
        return None


def _jie_nanodet(fenlei, huikuang, buju, chizi, reg_max=7):
    """把 NanoDet 的两个输出（80 类分数 + 32 维框分布）解成像素框
    32 维 = 4 条边 × 8 个 bin，先 softmax 再加权求和得到"离中心多远\""""
    import numpy as np
    bian = chizi // buju
    fen = fenlei[0]
    kuang = huikuang[0].reshape(-1, 4, reg_max + 1)
    kuang = kuang - kuang.max(axis=2, keepdims=True)
    e = np.exp(kuang)