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
    p = e / e.sum(axis=2, keepdims=True)
    juli = (p * np.arange(reg_max + 1)).sum(axis=2) * buju
    ys, xs = np.meshgrid(np.arange(bian), np.arange(bian))
    # 网格中心间距为 stride，第一个中心在 stride/2 处
    zx = (xs.reshape(-1) * buju + 0.5 * (buju - 1))[:, None]
    zy = (ys.reshape(-1) * buju + 0.5 * (buju - 1))[:, None]
    x1 = zx - juli[:, 0:1]
    y1 = zy - juli[:, 1:2]
    x2 = zx + juli[:, 2:3]
    y2 = zy + juli[:, 3:4]
    return np.hstack([x1, y1, x2, y2]), fen.max(axis=1), fen.argmax(axis=1)


def _zhengli_tupian(tupian, chizi):
    """把任意尺寸的图等比缩到 chizi×chizi 的方框里，居中补灰边（不变形）"""
    import numpy as np
    import cv2
    gao, kuan = tupian.shape[:2]
    suofang = min(chizi / kuan, chizi / gao)
    xin_kuan, xin_gao = int(round(kuan * suofang)), int(round(gao * suofang))
    hua = np.full((chizi, chizi, 3), 114, dtype=np.uint8)   # 114 是 YOLO 惯例的灰边
    shang, zuo = (chizi - xin_gao) // 2, (chizi - xin_kuan) // 2
    hua[shang:shang + xin_gao, zuo:zuo + xin_kuan] = cv2.resize(tupian, (xin_kuan, xin_gao))
    return hua, suofang, zuo, shang


def _jie_yolox(shuchu, chizi, suofang, zuo, shang, kuan, gao, yuzhi):
    """把 YOLOX 的 (N, 85) 解成原图上的框
    YOLOX 的排列：cx cy w h obj cls×80，三个尺度依次拼起来（8/16/32），
    前 4 列是相对本网格的偏移量，要乘 stride 再加网格坐标才是像素。"""
    import numpy as np
    import cv2
    a = np.asarray(shuchu).reshape(-1, 85)
    hua_kuang, hua_fen, hua_lei = [], [], []

    idx = 0
    for buju in (8, 16, 32):
        g = chizi // buju
        seg = a[idx:idx + g * g]
        idx += g * g
        if len(seg) == 0:
            continue
        gy, gx = np.meshgrid(np.arange(g), np.arange(g), indexing="ij")
        gx = gx.reshape(-1).astype(np.float32)
        gy = gy.reshape(-1).astype(np.float32)

        fen = seg[:, 4:5] * seg[:, 5:]        # 目标置信度 × 类别分数
        zuihao = fen.max(axis=1)
        liu = zuihao > yuzhi
        if not liu.any():
            continue
        s = seg[liu]
        cx = (s[:, 0] + gx[liu]) * buju
        cy = (s[:, 1] + gy[liu]) * buju
        bw = np.exp(s[:, 2]) * buju            # YOLOX 的宽高是 exp() 出来的
        bh = np.exp(s[:, 3]) * buju
        for i in range(len(s)):
            x1 = (cx[i] - bw[i] / 2 - zuo) / suofang
            x2 = (cx[i] + bw[i] / 2 - zuo) / suofang
            y1 = (cy[i] - bh[i] / 2 - shang) / suofang
            y2 = (cy[i] + bh[i] / 2 - shang) / suofang
            x1 = max(0.0, min(kuan - 1.0, x1))
            x2 = max(0.0, min(kuan - 1.0, x2))
            y1 = max(0.0, min(gao - 1.0, y1))
            y2 = max(0.0, min(gao - 1.0, y2))
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue
            hua_kuang.append([float(x1), float(y1), float(x2 - x1), float(y2 - y1)])
            hua_fen.append(float(zuihao[liu][i]))
            hua_lei.append(int(np.argmax(s[i, 5:])))
    return hua_kuang, hua_fen, hua_lei


def _fangda_kuang(jieguo, bi, kuan, gao):
    """把"缩小图上算出来的框"按比例换回原图坐标（bi 是缩小时的比例）"""
    if bi == 1.0 or not jieguo:
        return jieguo
    out = []
    for (x, y, w, h, lei, fen) in jieguo:
        x, y, w, h = x / bi, y / bi, w / bi, h / bi
        x = max(0.0, min(kuan - 1.0, x))
        y = max(0.0, min(gao - 1.0, y))
        w = min(w, kuan - x)
        h = min(h, gao - y)
        if w < 2 or h < 2:
            continue
        out.append((x, y, w, h, lei, fen))
    return out


def _hou_chuli(kuang, fen, lei, kuan, gao, yuzhi):
    """NMS 去重 + 丢掉小目标 + 大件排前面
    这里做两遍 NMS：
      · 先按类别各自去重（同类的一个东西只留一个框）
      · 再跨类去重（同一块地方被认成两种东西时，只留分数高的那个）
    跨类那一步是治「一个东西报了三遍」的关键。"""
    import numpy as np
    import cv2
    if not kuang:
        return []

    # 第一遍：同类 NMS
    by = {}
    for i, l in enumerate(lei):
        by.setdefault(l, []).append(i)
    di_yi = []
    for l, idxs in by.items():
        bx = [kuang[i] for i in idxs]
        sc = [fen[i] for i in idxs]
        keep = cv2.dnn.NMSBoxes(bx, sc, yuzhi, 0.45)
        if len(keep) == 0:
            continue
        for k in np.array(keep).reshape(-1):
            j = idxs[int(k)]
            di_yi.append((kuang[j], fen[j], lei[j]))

    # 第二遍：跨类 NMS（按分数从高到低扫，压住重叠的低分框）
    di_yi.sort(key=lambda o: -o[1])
    liu = []
    for item in di_yi:
        a = item[0]
        chong = False
        for b_item in liu:
            b = b_item[0]
            ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
            iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
            jiao = ix * iy
            if jiao <= 0:
                continue
            bing = a[2] * a[3] + b[2] * b[3] - jiao
            if bing > 0 and jiao / bing > 0.55:      # 重叠过半就认为说的是同一个东西
                chong = True
                break
        if not chong:
            liu.append(item)

    # 丢小目标 + 分级门槛：用户说"细节可以忽略，大物件一定要识别出来"。
    # 所以不是一刀切一个阈值，而是面积越小、要求分数越高 ——
    # 大件只要到 WUTI_YUZHI 就收；小件必须非常自信才留下，
    # 否则那些 1% 出头的碎框会把真正的大物件淹掉。
    zong = float(kuan * gao)
    jieguo = []
    for (k, f, l) in liu:
        zhan = k[2] * k[3] / zong
        if zhan < WUTI_ZUIXIAO:
            continue
        if zhan >= 0.05:              # 大件：整图 5% 以上，放宽
            menkan = yuzhi
        elif zhan >= 0.02:            # 中等：2%~5%，要求比大件更自信
            menkan = max(yuzhi, 0.36)
        else:                          # 小件：1.5%~2%，要求很自信
            menkan = max(yuzhi, 0.45)
        if f < menkan:
            continue
        # COCO 里有几个类别名是占位符 "?"（数据集里被删掉的类），
        # 命中它们只会在结果区显示一个问号，直接丢掉
        if COCO_LEI[l] == "?":
            continue
        # 还有一个反方向的坑：整张图一个框全包住（占 90% 以上），
        # 那是模型「把整幅画糊成一坨」的典型表现，不是真有一个物体
        if zhan > 0.90 and f < 0.60:
            continue
        jieguo.append((int(k[0]), int(k[1]), int(k[2]), int(k[3]),
                       COCO_LEI[l], float(f)))

    # 大件排前面：面积大的先说，这是"大物件优先"的直接体现
    jieguo.sort(key=lambda o: -(o[2] * o[3]))
    return jieguo


def zhao_wuti(tupian, yuzhi=None):
    """找出图里能认出来的物体，返回 ([(x,y,w,h,类别,分数)], 错误说明)
    大物件优先：返回的列表按面积从大到小排好，界面顺序就是"先大的后小的"。"""
    import numpy as np
    import cv2
    if yuzhi is None:
        yuzhi = WUTI_YUZHI
    wang = _yao_wuti()
    if wang is None:
        return [], _se_wuti_cuo

    # 大图先缩到 1600：模型本来就要把图缩到 640，先缩一次只是把"缩放这一步"
    # 从几千万像素降到两三百万像素，结果一样，速度差好几倍
    xiao, bi = _suo_xiao(tupian)
    gao, kuan = xiao.shape[:2]
    chizi = WUTI_CHICUN if _se_wuti_leixing == "yolox" else 416
    hua, suofang, zuo, shang = _zhengli_tupian(xiao, chizi)

    # 注意两者的预处理不一样：
    #   YOLOX 是「减均值除方差」的归一化，且不缩放像素值
    #   NanoDet 是 1/57.375 的缩放 + ImageNet 均值
    if _se_wuti_leixing == "yolox":
        blob = cv2.dnn.blobFromImage(hua, 1.0, (chizi, chizi), (0, 0, 0),
                                     swapRB=True, crop=False)
    else:
        blob = cv2.dnn.blobFromImage(hua, 1 / 57.375, (chizi, chizi),
                                     (103.53, 116.28, 123.675),
                                     swapRB=True, crop=False)
    try:
        wang.setInput(blob)
        mingzi = wang.getUnconnectedOutLayersNames()
        shuchu = wang.forward(mingzi)
    except Exception as e:
        return [], "物体识别推理失败：%s" % e

    if _se_wuti_leixing == "yolox":
        kuang, fen, lei = _jie_yolox(shuchu[0], chizi, suofang, zuo, shang,
                                     kuan, gao, yuzhi)
        jieguo = _fangda_kuang(_hou_chuli(kuang, fen, lei, kuan, gao, yuzhi),
                               bi, tupian.shape[1], tupian.shape[0])
        return _jiuzheng_lingdai(tupian, jieguo), ""

    # ---------------- 以下只给 NanoDet 兜底用 ----------------
    shuchu = dict(zip(mingzi, shuchu))
    kuang_all, fen_all, lei_all = [], [], []
    for buju, ming_fen, ming_kuang in ((8, "792", "795"), (16, "814", "817"),
                                       (32, "836", "839")):
        if ming_fen not in shuchu or ming_kuang not in shuchu:
            continue
        k, f, l = _jie_nanodet(shuchu[ming_fen], shuchu[ming_kuang], buju, chizi)
        kuang_all.append(k)
        fen_all.append(f)
        lei_all.append(l)
    if not kuang_all:
        return [], "物体模型的输出对不上，可能是模型版本不对。"

    kuang_all = np.vstack(kuang_all)
    fen_all = np.concatenate(fen_all)
    lei_all = np.concatenate(lei_all)
    liu = fen_all > yuzhi
    kuang_all, fen_all, lei_all = kuang_all[liu], fen_all[liu], lei_all[liu]

    daiban_k, daiban_f, daiban_l = [], [], []
    for i in range(len(kuang_all)):
        x1 = (kuang_all[i, 0] - zuo) / suofang
        x2 = (kuang_all[i, 2] - zuo) / suofang
        y1 = (kuang_all[i, 1] - shang) / suofang
        y2 = (kuang_all[i, 3] - shang) / suofang
        x1 = max(0, min(kuan - 1, x1))
        x2 = max(0, min(kuan - 1, x2))
        y1 = max(0, min(gao - 1, y1))
        y2 = max(0, min(gao - 1, y2))
        if x2 - x1 < 3 or y2 - y1 < 3:
            continue
        daiban_k.append([float(x1), float(y1), float(x2 - x1), float(y2 - y1)])
        daiban_f.append(float(fen_all[i]))
        daiban_l.append(int(lei_all[i]))

    jieguo = _fangda_kuang(
        _hou_chuli(daiban_k, daiban_f, daiban_l, kuan, gao, yuzhi),
        bi, tupian.shape[1], tupian.shape[0])
    return _jiuzheng_lingdai(tupian, jieguo), ""


def _zhongwen(lei):
    return COCO_ZHONG.get(lei, lei)


# ----------------------------------------------------------------------
# 3.5 领带纠偏（第二轮新增）
# ----------------------------------------------------------------------
# 问题：正装照里那条领带被认成「雨伞」。
# 为什么模型会这样：COCO 80 类里有 tie，但这一类在训练集里占比极小，
# 权重给的分很低；而"竖着的一条深色窄长物"在特征上确实和收起的伞很像。
# 换模型不现实（39MB 已经不小了），所以按几何 + 亮度做一次纠偏：
#   · 它整个落在某个「人」的框里（是穿戴在人身上的东西，不是独立道具）
#   · 又窄又长：高宽比 ≥ 1.35，宽度不到人宽的 40%，长度不到人高的 42%
#   · 位置在躯干上部：中心落在人框的 18%~72% 高度之间
#   · 而且偏暗（领带绝大多数是深色，伞面一般亮）
# 四条全中才改判成「领带」—— 宁可少改，也不能把真伞说成领带。
_LINGDAI_KE_GAI = ("umbrella", "handbag", "backpack", "suitcase",
                   "kite", "vase", "bottle", "tie", "book")


def _kuai_liangdu(tupian, x, y, w, h):
    """一小块的平均亮度（0~255）。取不到就返回 255，让调用方放弃改判"""
    try:
        gao, kuan = tupian.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(kuan, int(x + w)), min(gao, int(y + h))
        if x2 - x1 < 3 or y2 - y1 < 3:
            return 255.0
        kuai = tupian[y1:y2:2, x1:x2:2]        # 隔行隔列取，够用又快
        return float(kuai.mean())
    except Exception:
        return 255.0


def _jiuzheng_lingdai(tupian, jieguo):
    """把"穿在人身上、被认成雨伞/包"的窄长深色物改判成领带

    阈值是拿这张正装照实测调出来的：模型给的框是 (721,1839) 起、233×667，
    底部比人框还多出 30px。所以判定要允许一点点溢出（人高的 6%），
    并且中轴必须贴着人身（领带一定在正中间，挎包/伞把不会）。
    """
    if not jieguo:
        return jieguo
    ren = [(o[0], o[1], o[2], o[3]) for o in jieguo if o[4] == "person"]
    if not ren:
        return jieguo
    out = []
    for (x, y, w, h, lei, fen) in jieguo:
        if lei in _LINGDAI_KE_GAI and lei != "person":
            for (px, py, pw, ph) in ren:
                rong = max(6.0, ph * 0.06)            # 允许溢出一点
                if not (x >= px - rong and y >= py - rong
                        and x + w <= px + pw + rong
                        and y + h <= py + ph + rong):
                    continue
                if h / max(1.0, w) < 1.35:            # 不够长条
                    continue
                if w > pw * 0.40 or h > ph * 0.58:    # 太大，是别的东西
                    continue
                # 中轴要落在人身上中间那 50% 里：领带/领结才这么正
                cx = x + w / 2.0
                if abs(cx - (px + pw / 2.0)) > pw * 0.25:
                    continue
                # 垂直位置：脖子以下、腰以上（人框含肩以上，故此区间偏中上）
                cy = y + h / 2.0
                if not (py + ph * 0.14 <= cy <= py + ph * 1.00):
                    continue
                if _kuai_liangdu(tupian, x, y, w, h) > 140:
                    continue                          # 太亮，不像深色领带
                lei = "tie"
                break
        out.append((x, y, w, h, lei, fen))
    return out


# ----------------------------------------------------------------------
# 3.6 穿搭描述（第二轮新增）
# ----------------------------------------------------------------------
# 没有训练过任何一个"服装分类"模型，也不联网，所以这里不装作认得牌子，
# 只做一件老实的事：**按身体分带取主色，再把主色翻译成中文说法**。
#   头肩带 → 发色（顺带判断是不是深色头发）
#   躯干带 → 左右两侧（外套）+ 中间窄条（内搭/衬衫）
#   下装带 → 裤子/裙子的主色
# 再加上物体检测已经认出来的领带，拼成"深色外套 + 白色内搭 + 领带"这种话。
# 判断不了的一律写"看不出"，绝不编。
def _zhuse(kuai, qu_se=None, qu_fu=False):
    """一块 BGR 图的主色（最密的那一档），返回 (r, g, b)

    qu_se 是"背景色"：给了就把接近它的像素剔掉。证件照/影棚图里人框
    很宽，两侧混进大片背景（蓝色背景 → 黑西装被说成"蓝上装"）。
    qu_fu 是"剔掉肤色"：脖子、手会混进领口那一带，不剔会把衬衫读成
    "橙内搭"（实测就踩过）。
    """
    if kuai is None or getattr(kuai, "size", 0) == 0:
        return None
    try:
        import numpy as np
        x = kuai.reshape(-1, 3)
        if len(x) > 4000:                 # 采样即可，别为一块布算几万像素
            x = x[::max(1, len(x) // 4000)]
        if qu_fu and len(x):
            r_ = x[:, 2].astype(np.int32)
            g_ = x[:, 1].astype(np.int32)
            b_ = x[:, 0].astype(np.int32)
            fu = (r_ > 95) & (g_ > 40) & (b_ > 20) & (r_ > g_) & (r_ > b_) \
                & ((r_ - g_) > 18)
            liu = ~fu
            if int(liu.sum()) >= max(24, int(len(x) * 0.10)):
                x = x[liu]
        if qu_se is not None and len(x):
            cha = np.abs(x[:, ::-1].astype(np.int32)
                         - np.array(qu_se, dtype=np.int32)).sum(axis=1)
            liu = cha > 70
            # 只剩一点点就别剔了 —— 那说明这块本来就接近背景色，
            # 硬剔完会算出个乱七八糟的平均色
            if int(liu.sum()) >= max(24, int(len(x) * 0.12)):
                x = x[liu]
        # 【量化粒度必须是 32】每通道 8 档 = 3 bit，三个通道拼成一个整数当
        # 桶号。写成 x//24 会得到 0~10 一共 11 档，塞不进 3 bit，桶号会互相
        # 踩踏（白色 245 被算成"青"，就是这一处错位导致的）。
        q = (x // 32).astype(np.int32)
        key = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
        vals, counts = np.unique(key, return_counts=True)
        k = int(vals[int(counts.argmax())])
        # 注意通道顺序：tupian 是 cv2 的 BGR，q[:,0] 是 B，不是 R。
        b = (k // 64) * 32 + 16
        g = ((k // 8) % 8) * 32 + 16