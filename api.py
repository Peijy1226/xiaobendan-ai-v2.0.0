# -*- coding: utf-8 -*-
"""api.py —— 前后端桥（第二阶段：接真逻辑）

设计三条：
  ① 前端只管"要一段话 + 心情 + 表情 + 状态"，不关心背后是规则引擎还是灵光
  ② 慢操作（联网 / 天气）由 pywebview 自己丢进子线程（见 webview/util.py
     的 js_bridge_call 用 Thread 起），这里不再套一层
  ③ 返回值形状固定；以后换实现，前端一行不用改

【命名铁律】所有实例属性以下划线开头。
pywebview 启动时遍历 js_api 的公开属性并递归检查是否是方法，
`self._chuang = window` 带下划线会被跳过；写成 `self.chuang` 就会递归进
COM 对象栈溢出，表现为窗口出来了但 start() 永不返回。
"""
import os
import sys
import threading

_JI = os.path.dirname(os.path.abspath(__file__))
if _JI not in sys.path:
    sys.path.insert(0, _JI)

# 【必须在 import 之前设】core/luoji.py 里的 DIR 是 import 时就定下来的，
# 之后在模块级算出一堆路径常量（SUCAI_MU / CUNDANG_LU / TOU_LU ...）。
# 所以只能靠环境变量在 import 前告诉它素材在哪。
os.environ.setdefault("XBD_DIR", os.path.join(_JI, "ui"))

import webview              # noqa: E402

from core import luoji      # noqa: E402
from core import shitu      # noqa: E402
from core import zhengli    # noqa: E402
from core import xiezuo     # noqa: E402


class Qiao:
    """暴露给 JS 的对象：window.pywebview.api.xxx()"""

    def __init__(self):
        self._chuang = None
        self._suo = threading.Lock()
        self._qingxu = luoji.Qingxu()
        self._hui = []                  # [(who, text, title)]，和旧版存档格式一致
        self._lingguang = False
        self._pei = {}
        self._nuo_qi = [0, 0]
        self._shang_ci = None           # 上次存档时的内容指纹（没变就不写盘）
        self._cang_zhe = False          # 窗口是否藏在托盘（主动消息据此决定弹不弹通知）

    def gua_chuang(self, chuang):
        self._chuang = chuang
        self.chong_du_peizhi()

    def chong_du_peizhi(self):
        """重读 API.txt，顺便把灵光开关跟钥匙对齐

        【为什么要"跟钥匙对齐"】钥匙填了但开关是关的，用户会以为联网坏了。
        旧版的设计是「填了钥匙 = 默认开」（API.txt 里 默认开启=1）。
        这里照做：有钥匙就开，没钥匙就关 —— 用户在界面上再手动关也行。
        """
        try:
            self._pei = luoji.du_api_peizhi()
            you = bool(luoji.api_youxiao(self._pei))
            mo = str(self._pei.get("默认开启", "1")).strip()
            if you:
                self._lingguang = mo not in ("0", "false", "False")
            else:
                self._lingguang = False
        except Exception as e:
            print("[api] 读 API 配置失败：%s" % e)
            return {"ok": False, "cuo": str(e)}
        return {"ok": True, "kai": self._lingguang,
                "you_yao": bool(self._pei.get("api_key"))}

    # ══════════════════════════════════════════════════════════════════
    #  一 · 对话
    #      hui_fu（含联网分流） / _lianwang_hui / _zhuan_lishi / _pan_gongju
    # ══════════════════════════════════════════════════════════════════
    def hui_fu(self, wenben):
        """发一句，返回 {wen, tou, biao, xinqing, haogan, lunshu, lianren}"""
        wenben = (wenben or "").strip()
        if not wenben:
            return self._bao("")

        with self._suo:
            da = ""
            # 【联网优先】灵光开着就先走大模型 —— 这是第二阶段漏掉的：
            # _lingguang 只拿去挑表情了，对话根本没走模型，一直是离线规则引擎。
            # 分流顺序照旧版 _fasong_zaiwang：
            #   报时 / 算数 留本地（有确定答案，绕网络反而容易错）
            #   天气 单独走实时接口，拿到数据再让模型用自己的口气说
            #   其余（闲聊/问事/笑话/美食/王者）交给模型
            if self._lingguang:
                try:
                    da = self._lianwang_hui(wenben)
                except Exception as e:
                    import traceback
                    print("[api] 联网对话失败，退回离线：%s" % e)
                    traceback.print_exc()
                    da = ""

            if not da:
                try:
                    da = luoji.shuohua_jilu(wenben, self._qingxu)
                except Exception as e:
                    print("[api] shuohua 异常：%s" % e)
                    da = "……我这边好像卡了一下。"

            # 【记忆】说完就记 —— 这是"陪伴"和"聊天"的分界线。
            # 规则抽取是同步的、免费的、零延迟；规则抽不到才丢给模型补。
            # 模型那一步放后台线程：不能让用户多等 1 秒才知道她说了什么。
            新记 = []
            try:
                新记 = luoji.ti_zhongyao(wenben) or []
            except Exception as e:
                print("[api] 规则记忆失败：%s" % e)
            if not 新记:
                threading.Thread(
                    target=self._ji_yi_bu_chong, args=(wenben,), daemon=True
                ).start()

            try:
                self._qingxu.gengxin(wenben, da)
            except Exception as e:
                print("[api] 情绪更新失败：%s" % e)

            tou = ""
            try:
                chang = luoji.bq_changjing(wenben, self._qingxu.lianren)
                p = luoji.bq_xuan(self._qingxu.dangqian, self._qingxu.lianren,
                                  self._lingguang, chang)
                if p:
                    tou = os.path.basename(p)
            except Exception as e:
                print("[api] 表情挑选失败：%s" % e)

            biao = self._biao_ti()
            self._ji(wenben, da, biao)

        return self._bao(da, tou, biao)

    def _lianwang_hui(self, wenti):
        # 注意：这个函数 return 的地方很多，但记忆提取放在 hui_fu 里、
        # 在这一步之后统一做 —— 不能放这儿，否则早退路径会漏记。
        """联网那一路。返回一段话，失败返回空串（调用方自动退回离线）。

        分流顺序和旧版 _fasong_zaiwang 一样：
          报时 / 算数 → 本地算，快且准
          天气       → 先查实时接口，拿到数据再让模型用自己的口气说
          笑话/美食/王者/换算 → 先取本地素材，再让模型"用自己的口气讲"
          其余       → 直接问模型
        """
        # ---- ① 先判断会落到哪个工具 ----
        gongju = self._pan_gongju(wenti)
        if gongju in ("报时", "算数"):
            return ""                    # 留本地，走 shuohua

        pei = self._pei or luoji.du_api_peizhi()
        lishi = self._zhuan_lishi()
        haogan = self._qingxu.haogan
        dangqian = self._qingxu.dangqian

        # ---- ② 天气：先拿数据 ----
        if gongju == "天气":
            try:
                tq_wen, tq_cuo, you = luoji.tianqi_chaxun(
                    wenti, pei.get("默认城市", "北京"))
            except Exception as e:
                tq_wen, tq_cuo, you = "", str(e), False
            if not you:
                # 绝不编一个温度糊过去
                return ("天气没查上：%s。\n网络通了再问我一次，"
                        "我把实时温度和未来几天都给你。"
                        % (tq_cuo or "接口没回话"))
            gao, cuo = luoji.diaoyong_llm(
                wenti + "\n\n" + tq_wen, lishi, haogan, dangqian, pei,
                xitong=luoji._renshe_wen(haogan, dangqian) + luoji.TQ_WEATHER_RULE)
            # 模型改了数字/换了城市 → 用接口原文，宁可不那么像人话
            if gao and self._tq_shuo_dui(gao, tq_wen):
                return gao
            return tq_wen

        # ---- ③ 有本地素材的工具：先取答案 ----
        ziliao, daan_gongju = "", ""
        if gongju not in ("", "灵光"):
            try:
                _m, daan_gongju = luoji.gongju_daan(wenti)   # (工具名, 答案)
                if daan_gongju:
                    ziliao = "\n\n【%s工具给的内容】\n%s" % (gongju, daan_gongju)
            except Exception:
                ziliao, daan_gongju = "", ""

        # ---- ④ 问模型 ----
        if ziliao:
            # 有工具资料：让模型"用自己的口气把这事说出来"，
            # 而不是纯聊天 —— 否则人设里那句"我不玩游戏"会赢
            da, cuo = luoji.diaoyong_llm(
                wenti + ziliao, lishi, haogan, dangqian, pei,
                xitong=luoji._renshe_wen(haogan, dangqian) + luoji.GONGJU_YUE)
            if cuo or not da:
                return daan_gongju or ""
            return da

        da, cuo = luoji.diaoyong_llm(wenti, lishi, haogan, dangqian, pei)
        if cuo:
            print("[api] 模型没回：%s" % cuo)
            return ""
        return da or ""

    def _ji_yi_bu_chong(self, wenben):
        """规则抽不到时，后台让模型补一遍（不阻塞对话）"""
        try:
            新 = luoji.ti_zhongyao_llm(wenben, self._pei)
            if 新:
                print("[api] 模型补记了 %s" % (新,))
                # 推给界面，让「记忆」那页能立刻看到
                try:
                    if self._chuang:
                        self._chuang.evaluate_js(
                            "setTimeout(function(){"
                            "if(window.GongNeng&&GongNeng.在开&&GongNeng.在开())"
                            "document.dispatchEvent(new Event('jiyi-gengxin'));"
                            "}, 30)")
                except Exception:
                    pass
        except Exception as e:
            print("[api] 模型补记失败：%s" % e)

    def _zhuan_lishi(self):
        """把存档格式 [who, text, title] 转成模型要的 [(role, content)]

        【为什么必须转】存档里 who 是 "wo"/"ta"（旧版就这么存的，方便渲染），
        而 _zuzhuang_xiaoxi 要的是 OpenAI 的 "user"/"assistant"。
        直接传过去会在 for 解包时崩：too many values to unpack (expected 2, got 3)。
        """
        out = []
        for t in self._hui[-10:]:
            if not t or len(t) < 2:
                continue
            who, wen = t[0], t[1]
            if not wen:
                continue
            out.append(("user" if who == "wo" else "assistant", str(wen)[:1200]))
        return out

    def _pan_gongju(self, wenti):
        """这句话会交给哪个工具 —— 判断顺序必须和 shuohua 里一模一样"""
        try:
            if luoji.is_time_question(wenti):
                return "报时"
            if luoji.is_weather_question(wenti):
                return "天气"
            if luoji.is_joke_question(wenti):
                return "笑话"
            if luoji.is_food_question(wenti):
                return "美食"
            if luoji.is_wangzhe_question(wenti):
                return "王者荣耀"
            if luoji.is_calc_question(wenti) or luoji.is_calc_intent(wenti):
                return "算数"
        except Exception:
            pass
        return ""

    @staticmethod
    def _tq_shuo_dui(gao, yuanwen):
        """模型这段话说得对不对：数字必须和接口原文一致

        为什么只查数字：模型最爱"顺手"把 24% 说成"大概三成"、
        把 3~8℃ 说成"十几度"。数字一变，用户就白问了。
        """
        import re
        shu_yuan = set(re.findall(r"\d+(?:\.\d+)?", yuanwen or ""))
        shu_gao = set(re.findall(r"\d+(?:\.\d+)?", gao or ""))
        if not shu_yuan:
            return True
        # 模型说的话里，接口给的数字得占大多数
        return len(shu_yuan & shu_gao) >= max(1, len(shu_yuan) // 2)

    def _bao(self, wen, tou="", biao=None):
        q = self._qingxu
        return {
            "wen": wen,
            "tou": tou,                  # 表情文件名，如 "开心.png"，空串=不贴
            "biao": biao or self._biao_ti(),
            "xinqing": q.dangqian,
            "haogan": q.haogan,
            "lunshu": q.lunshu,
            "lianren": q.lianren,
            "xin": luoji.xin_shu(q.haogan),
            "zhuangtai": q.zhuangtai(),
        }

    def _biao_ti(self):
        """气泡上方那行：小笨蛋 （-__-） 平静（旧版 _biaoti，12720 行）"""
        q = self._qingxu
        if q.lianren:
            return "小笨蛋 %s 恋人" % luoji.QINGXU_LIANREN["lian"]
        pei = luoji.QINGXU_BIAO.get(q.dangqian) or luoji.QINGXU_BIAO["平静"]
        return "小笨蛋 %s %s" % (pei["lian"], q.dangqian)

    def _ji(self, wen, da, biao):
        """记一条，最多 200 条（存档格式：[who, text, title]）"""
        self._hui.append(["wo", wen, ""])
        self._hui.append(["ta", da, biao or ""])
        if len(self._hui) > 200:
            del self._hui[:-200]

    # ══════════════════════════════════════════════════════════════════
    #  二 · 开场与状态
    #      kai_chang / zhuang_tai / cun_dang / qing_kong
    # ══════════════════════════════════════════════════════════════════
    def kai_chang(self):
        """开场：有存档就接上次，没有就让前端补开场白

        返回 {duihua, zhuangtai, kai, kaichang}
        kai=True 表示没有存档 —— 前端自己摆一句 TTS_KAI_CHANG + 一张表情。
        """
        try:
            cun = luoji.du_cundang()
        except Exception:
            cun = None

        if cun and cun.get("对话"):
            try:
                self._qingxu.haogan = int(cun.get("好感度", 55))
                self._qingxu.lunshu = int(cun.get("轮数", 0))
                self._qingxu.dangqian = cun.get("心情") or "平静"
                self._qingxu.lianren = self._qingxu.haogan >= 100
                self._hui = [list(x) for x in cun["对话"] if len(x) >= 3]
            except Exception as e:
                print("[api] 读存档失败：%s" % e)
            return {"duihua": self._hui, "zhuangtai": self.zhuang_tai(),
                    "kai": False}

        # 【首次引导】没有存档 AND 记忆档案也空 = 真·第一次。
        # 这时候不能只丢一句开场白 —— 谁知道该说什么、谁知道要去填 API 钥匙。
        # 返回一个 yin_dao 标记，前端摆一张引导卡。
        第一次 = True
        try:
            第一次 = not bool(luoji.du_zhongyao())
        except Exception:
            pass
        you_yao = False
        try:
            you_yao = not bool(luoji.api_youxiao(self._pei or {}))
        except Exception:
            pass

        jie = {"duihua": [], "zhuangtai": self.zhuang_tai(), "kai": True,
               "kaichang": luoji.TTS_KAI_CHANG}
        if 第一次:
            jie["yin_dao"] = {
                "yao_ming": True,        # 要不要问名字
                "yao_yao": you_yao,      # 要不要引导填钥匙
                "wen": luoji._chou((
                    "（把兜帽往后推了推，露出眼睛）……你是新来的吧。\n"
                    "我叫小笨蛋。你叫什么？",
                    "（从屏幕角落探出头）啊，有人打开我了。\n"
                    "我叫小笨蛋——你叫什么名字？",
                )) if hasattr(luoji, "_chou") else
                "（把兜帽往后推了推）……你是新来的吧。我叫小笨蛋。你叫什么？",
            }
        return jie

    def zhuang_tai(self):
        """顶栏：五颗心（1~5）+ 状态字"""
        q = self._qingxu
        return {
            "xin": luoji.xin_shu(q.haogan),
            "zhuangtai": q.zhuangtai(),
            "haogan": q.haogan,
            "lunshu": q.lunshu,
            "lianren": q.lianren,
        }

    def cun_dang(self):
        """存档：每轮结束写一次。

        【为什么去掉节流】原来是 6 秒节流，想着"别那么频繁"。实测出问题：
        用户连着聊四五句（每句 1～2 秒），全被节流挡掉，只有第一轮落盘 ——
        关掉重开只剩第一句。存档是几百字节的小文件，人手打字的速度根本
        谈不上频繁，节流是过早优化。
        防抖仍有：内容没变就不写（见 _cun_nei_rong）。
        """
        with self._suo:
            zhuang = (len(self._hui), self._qingxu.haogan,
                      self._qingxu.lunshu, self._qingxu.dangqian)
            if zhuang == self._shang_ci:
                return {"ok": True, "bian": False}
            self._shang_ci = zhuang
        try:
            ok = luoji.xie_cundang(self._hui, self._qingxu.haogan,
                                   self._qingxu.lunshu, self._qingxu.dangqian)
            return {"ok": bool(ok), "bian": True}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def qing_kong(self):
        """忘记我吧：清空对话 + 删存档（旧版 shan_cundang）"""
        with self._suo:
            self._hui = []
            self._qingxu = luoji.Qingxu()
            try:
                luoji.shan_cundang()
            except Exception:
                pass
        return {"ok": True, "zhuangtai": self.zhuang_tai()}

    # ══════════════════════════════════════════════════════════════════
    #  三 · 数据持久化（气泡样式 / 灵光配置 / 天气）
    # ══════════════════════════════════════════════════════════════════
    def du_yang(self):
        """读上次用的气泡样式（0 猫耳 / 1 圆角 / 2 透光）"""
        try:
            return int(luoji.du_qipao_yang())
        except Exception:
            return 0

    def cun_yang(self, n):
        """存气泡样式（写 个性化/气泡.txt，和旧版同一个文件）"""
        try:
            luoji.cun_qipao_yang(int(n))
        except Exception as e:
            print("[api] 存气泡样式失败：%s" % e)
        return True

    # ================= 灵光（联网） =================
    def ling_guang(self):
        return {
            "kai": self._lingguang,
            "you_yao": bool(self._pei.get("api_key")),
            "moxing": self._pei.get("model", ""),
        }

    def she_ling_guang(self, kai):
        self._lingguang = bool(kai)
        return {"kai": self._lingguang, "you_yao": bool(self._pei.get("api_key"))}

    def wen_tianqi(self, chengshi):
        """真实天气。js_api 调用本身在子线程，直接阻塞也没事。"""
        chengshi = (chengshi or "北京").strip()
        try:
            wen, cuo, ok = luoji.tianqi_chaxun("%s天气" % chengshi, chengshi)
            return {"wen": wen, "cuo": cuo, "ok": ok}
        except Exception as e:
            return {"wen": "", "cuo": str(e), "ok": False}

    # ================= 窗口控制 =================
    def nuo_chuang(self, dx, dy):
        """按偏移量挪窗口（无边框窗口唯一的拖动方案，见 README 坑 3）"""
        try:
            import ctypes
            if self._chuang is None:
                return False
            hwnd = self._chuang.native.Handle.ToInt32()
            x = self._nuo_qi[0] + int(dx)
            y = self._nuo_qi[1] + int(dy)
            # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
            ctypes.windll.user32.SetWindowPos(hwnd, None, x, y, 0, 0,
                                              0x0001 | 0x0004 | 0x0010)
            return True
        except Exception as e:
            print("[api] 挪窗失败 %s" % e)
            return False

    def nuo_qi_dian(self):
        """记录拖动起点（窗口当前左上角，物理像素）"""
        try:
            import ctypes
            import ctypes.wintypes as wt
            if self._chuang is None:
                return False
            hwnd = self._chuang.native.Handle.ToInt32()
            r = wt.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
            self._nuo_qi = [r.left, r.top]
            return [r.left, r.top]
        except Exception as e:
            print("[api] 记拖动起点失败 %s" % e)
            return False

    def zui_xiao_hua(self):
        try:
            if self._chuang is not None:
                self._chuang.minimize()
        except Exception as e:
            print("[api] 最小化失败 %s" % e)
        return True

    def guan_bi(self):
        """关闭：先存档，再销毁（旧版 _guan_bi 也是这个顺序）"""
        try:
            luoji.xie_cundang(self._hui, self._qingxu.haogan,
                              self._qingxu.lunshu, self._qingxu.dangqian)
        except Exception:
            pass
        try:
            if self._chuang is not None:
                self._chuang.destroy()
        except Exception as e:
            print("[api] 关闭失败 %s" % e)
        return True

    # ══════════════════════════════════════════════════════════════════
    #  五 · 功能页 13 项
    #      ②识图 ③写一篇 ④整理助手 ⑤打赏 ⑥壁纸 ⑩记忆 ⑨灵光 ⑧个性化
    # ══════════════════════════════════════════════════════════════════

    # ---------- ② 识图 ----------
    def xuan_tu(self):
        """弹系统文件对话框选一张图，返回 {ok, lu, url, ming, w, h}

        【两套路径】lu 给 Python 侧识图用（本地绝对路径），
        url 给前端 <img> 用（http 服务相对路径）——
        因为它们不是一回事：浏览器读不到 C 盘绝对路径，Python 也读不了 http URL。
        """
        import shutil
        import time as _t
        try:
            r = self._chuang.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=False,
                file_types=('图片 (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.tif;*.tiff)',
                            '所有文件 (*.*)'))
        except Exception as e:
            return {"ok": False, "cuo": "打不开文件对话框：%s" % e}
        if not r:
            return {"ok": False, "cuo": ""}          # 用户取消，不算错
        lu = r[0]
        try:
            from PIL import Image
            im = Image.open(lu)
            w, h = im.size
        except Exception as e:
            return {"ok": False, "cuo": "读不了这张图：%s" % e}

        # 复制到 ui/识图/ 下，前端才取得到（http 服务只能访问 ui/ 里的东西）
        mu = os.path.join(luoji.DIR, "识图")
        try:
            os.makedirs(mu, exist_ok=True)
            ming = "yt_%d%s" % (int(_t.time() * 1000),
                                os.path.splitext(lu)[1].lower())
            dst = os.path.join(mu, ming)
            shutil.copy2(lu, dst)
        except Exception as e:
            return {"ok": False, "cuo": "复制图片失败：%s" % e}

        return {"ok": True, "lu": dst, "url": "识图/" + ming,
                "ming": os.path.basename(lu), "w": w, "h": h}

    def shi_tu(self, zenme, lu):
        """识图。zenme = 提字 / 认人 / 认物 / 看穿搭

        dev 版优先走多模态大模型：它能看懂画面，说得出"这个人在做什么、
        穿什么颜色"，本地模型只会画框和认类别。
        没有钥匙 / 没网 / 大模型挂了，才退本地三个模型（RapidOCR + YuNet + YOLOX）。
        """
        import cv2
        import numpy as np
        # OpenCV 在 Windows 上读不了中文路径，统一走 imdecode
        try:
            buf = np.fromfile(lu, dtype=np.uint8)
            im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception as e:
            return {"ok": False, "cuo": "读不了图：%s" % e}
        if im is None:
            return {"ok": False, "cuo": "这张图打不开（格式不支持或已损坏）"}

        # ---- 先试大模型 ----
        # 提字和看穿搭靠大模型就够了（它读字比 OCR 会断行，看穿搭本地根本不会说人话）。
        # 认人 / 认物不一样：需要精确的框坐标，大模型给不了 ——
        # 所以那两项仍走本地出框，只在末尾附一句大模型的描述（有钥匙才有）。
        if zenme in ("提字", "看穿搭"):
            wen = self._kan_tu_llm(lu, zenme)
            if wen:
                return {"ok": True, "wen": wen, "kuang": [], "laiyuan": "联网大模型"}

        # ---- 本地 ----
        if zenme == "提字":
            try:
                jieguo, cuo = shitu.tiqu_wenzi(im)
            except Exception as e:
                return {"ok": False, "cuo": "提字失败：%s" % e}
            if cuo:
                return {"ok": False, "cuo": cuo}
            wen = []
            for kuang, zi, fen in jieguo:
                if zi.strip():
                    wen.append(zi.strip())
            if not wen:
                return {"ok": True, "wen": "（这张图里没认出文字）",
                        "kuang": [], "laiyuan": "本地 RapidOCR"}
            return {"ok": True, "wen": "\n".join(wen), "kuang": [],
                    "laiyuan": "本地 RapidOCR"}

        if zenme == "认人":
            try:
                kuang, cuo = shitu.zhao_renlian(im)
            except Exception as e:
                return {"ok": False, "cuo": "认人失败：%s" % e}
            if cuo:
                return {"ok": False, "cuo": cuo}
            if not kuang:
                return {"ok": True, "wen": "（没找到人脸）", "kuang": [],
                        "laiyuan": "本地 YuNet"}
            hua = [{"x": int(a), "y": int(b), "w": int(c), "h": int(d),
                    "ming": "人脸 %.0f%%" % (f * 100), "ren": True}
                   for a, b, c, d, f in kuang]
            wen = "找到 %d 张脸。" % len(kuang)
            buchong = self._kan_tu_llm(lu, "描述")
            if buchong:
                wen += "\n\n" + buchong
                return {"ok": True, "wen": wen, "kuang": hua,
                        "laiyuan": "本地 YuNet + 大模型描述"}
            return {"ok": True, "wen": wen, "kuang": hua,
                    "laiyuan": "本地 YuNet"}

        if zenme == "认物":
            try:
                kuang, cuo = shitu.zhao_wuti(im)
            except Exception as e:
                return {"ok": False, "cuo": "认物失败：%s" % e}
            if cuo:
                return {"ok": False, "cuo": cuo}
            if not kuang:
                return {"ok": True,
                        "wen": "（没认出东西。可以试试主体更清楚的图）",
                        "kuang": [], "laiyuan": "本地 YOLOX"}
            hua, ming = [], []
            for a, b, c, d, lei, f in kuang:
                zw = shitu._zhongwen(lei)
                ming.append("%s %.0f%%" % (zw, f * 100))
                hua.append({"x": int(a), "y": int(b), "w": int(c), "h": int(d),
                            "ming": zw, "ren": lei == "person"})
            wen = "认出 %d 样：\n· %s" % (len(hua), "\n· ".join(ming))
            buchong = self._kan_tu_llm(lu, "描述")
            if buchong:
                wen += "\n\n" + buchong
                return {"ok": True, "wen": wen, "kuang": hua,
                        "laiyuan": "本地 YOLOX + 大模型描述"}
            return {"ok": True, "wen": wen, "kuang": hua,
                    "laiyuan": "本地 YOLOX"}

        if zenme == "看穿搭":
            # 【必须先认出人和物，再把框交给它】
            # 第一版传了三个 None，miaoshu_chuanda 一看 ren_wu 是空就直接
            # 返回空列表 —— 于是"看不出什么"。它不是自己会找人的。
            try:
                lian, _ = shitu.zhao_renlian(im)
                wuti, _ = shitu.zhao_wuti(im)
            except Exception as e:
                return {"ok": False, "cuo": "先认人认物时失败：%s" % e}

            # wuti 是 6 元组 (x,y,w,h,类别,分数)，只挑 person
            ren = [(int(a), int(b), int(a + c), int(b + d), "person", f)
                   for a, b, c, d, lei, f in (wuti or []) if lei == "person"]
            # 没有 person 框但有脸 → 用脸推一个身体框（旧版也是这么兜的）
            if not ren and lian:
                fx, fy, fw, fh, ff = lian[0]
                ren = [(int(fx - fw * 1.6), int(fy - fh * 0.6),
                        int(fx + fw * 2.6), int(fy + fh * 6.0), "person", ff)]

            if not ren:
                wen = "（这张图里没找到人）"
                buchong = self._kan_tu_llm(lu, "看穿搭")
                if buchong:
                    return {"ok": True, "wen": buchong, "kuang": [],
                            "laiyuan": "联网大模型"}
                return {"ok": True, "wen": wen, "kuang": [],
                        "laiyuan": "本地配色分析"}

            try:
                jie, cuo = shitu.miaoshu_chuanda(im, ren, wuti, lian)
            except Exception as e:
                return {"ok": False, "cuo": "看穿搭失败：%s" % e}
            if cuo:
                return {"ok": False, "cuo": cuo}
            wen = "\n".join(jie) if jie else "（看不出什么）"
            hua = [{"x": int(a), "y": int(b), "w": int(c - a), "h": int(d - b),
                    "ming": "人", "ren": True} for a, b, c, d, _, _ in ren]
            buchong = self._kan_tu_llm(lu, "看穿搭")
            if buchong:
                return {"ok": True, "wen": wen + "\n\n" + buchong,
                        "kuang": hua, "laiyuan": "本地配色 + 大模型描述"}
            return {"ok": True, "wen": wen, "kuang": hua,
                    "laiyuan": "本地配色分析"}

        return {"ok": False, "cuo": "不认识这个操作：%s" % zenme}

    def _kan_tu_llm(self, lu, zenme):
        """让多模态大模型看图。没有钥匙 / 没网 / 不支持视觉，都返回空串。

        为什么单开一个函数：这是个"有就用、没有就算"的增强，
        不该跟主流程纠缠。失败一律静默返回空串，调用方自然退回本地模型。
        """
        import base64
        import json
        import urllib.request
        try:
            pei = luoji.du_api_peizhi()
            key = str(pei.get("api_key", "")).strip()
            if not key:
                return ""
            # 图太大就缩一下：视觉接口按像素计费，2000px 长边足够
            try:
                from PIL import Image
                im = Image.open(lu).convert("RGB")
                if max(im.size) > 2000:
                    bi = 2000.0 / max(im.size)
                    im = im.resize((int(im.width * bi), int(im.height * bi)),
                                   Image.LANCZOS)
                buf = os.path.join(os.path.dirname(lu), "_tmp_kan.jpg")
                im.save(buf, "JPEG", quality=86)
                with open(buf, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                try:
                    os.remove(buf)
                except Exception:
                    pass
            except Exception:
                with open(lu, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")

            if zenme == "提字":
                wenda = ("把这张图里的文字全部照原样抄下来，不要翻译、不要解释、"
                         "不要加任何说明。没字就回「没有文字」。")
            elif zenme == "描述":
                wenda = ("用两句中文说这张图里有什么：谁、在做什么、什么东西。"
                         "口语一点，不要分点，不要客套，不要提「图片」这个词。")
            else:
                wenda = ("用中文详细描述这张图里这个人的穿着打扮：上装、下装、鞋子、"
                         "配饰、颜色、风格。两三句话，口语一点，不要分点，不要客套。")

            ti = {
                "model": str(pei.get("model", "deepseek-flash")),
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": wenda},
                        {"type": "image_url",
                         "image_url": {"url": "data:image/jpeg;base64," + b64}},
                    ],
                }],
                "max_tokens": 700,
                "stream": False,
            }
            req = urllib.request.Request(
                str(pei.get("base_url", "https://api.deepseek.com")).rstrip("/")
                + "/chat/completions",
                data=json.dumps(ti, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=40) as r:
                jie = json.loads(r.read().decode("utf-8", "replace"))
            return (jie["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            # 静默降级：可能在控制台看一眼原因，用户看不到
            print("[api] 大模型看图失败（退回本地）：%s" % e)
            return ""

    # ---------- ③ 写一篇 ----------
    def xie_yi_pian(self, timu, ticai):
        """写作文。联网走大模型，没网套模板。

        返回 {ok, wen, zi, laiyuan}
        """
        timu = (timu or "").strip()
        if not timu:
            return {"ok": False, "cuo": "先填个题目。"}
        ticai = ticai or "随便"

        pei = luoji.du_api_peizhi()
        if luoji.api_youxiao(pei):
            try:
                hui, cuo = luoji.diaoyong_llm(
                    "体裁：%s\n题目：%s\n请写一篇 100~200 字的作文。" % (ticai, timu),
                    [], self._qingxu.haogan, self._qingxu.dangqian, pei,
                    xitong=xiezuo.xiezuo_xitong(200), yao_jian_cha=False)
                if hui:
                    wen, zi = xiezuo.xiezuo_zhengli(hui, 200)
                    return {"ok": True, "wen": wen, "zi": zi, "laiyuan": "联网大模型"}
                print("[api] 写作文失败：%s" % cuo)
            except Exception as e:
                print("[api] 写作文异常：%s" % e)

        wen, zi = xiezuo.xiezuo_lixian(timu, ticai)
        return {"ok": True, "wen": wen, "zi": zi,
                "laiyuan": "离线模板（没联网或钥匙没填）"}

    # ---------- ④ 整理助手 ----------
    def zhengli_kai_guan(self, kai=None):
        """开关。不传就当"查状态"。

        【为什么不给默认开】这是全程序唯一会移动用户文件的功能。
        旧版也是默认关着，点「开启」才生效 —— 这条规矩不能松。
        """
        try:
            if kai is not None:
                zhengli.zl_xie_kai(bool(kai))
            return {"kai": bool(zhengli.zl_du_kai()),
                    "jia": zhengli.zl_yanshi_lu(),
                    "shangxian": "%d 个 / %d MB"
                                % (zhengli.ZL_ZUI_DUO,
                                   zhengli.ZL_ZUI_DA // 1048576)}
        except Exception as e:
            return {"kai": False, "jia": "", "cuo": str(e)}

    def zhengli_sao(self, leixing="全部"):
        """扫演示夹。没开开关 / 夹子是空的，都返回一句人话，不报错。"""
        try:
            if not zhengli.zl_du_kai():
                return {"ok": False, "cuo": "整理助手现在关着。先点「开启整理助手」。"}

            # 夹子空的时候造几个演示文件 —— 旧版 zl_zhunbei_yanshi 就是这个用途
            if zhengli.zl_yanshi_kong():
                ok, xinxi = zhengli.zl_zhunbei_yanshi()
                if not ok:
                    return {"ok": False, "cuo": xinxi}

            dong = zhengli.zl_lie(zhengli.zl_yanshi_lu(), leixing or "全部")
            zong = sum(x["da"] for x in dong)
            if len(dong) > zhengli.ZL_ZUI_DUO:
                dong = dong[:zhengli.ZL_ZUI_DUO]
                tishi = ("文件比 %d 个多，这次只列前 %d 个。"
                         % (zhengli.ZL_ZUI_DUO, zhengli.ZL_ZUI_DUO))
            else:
                tishi = ""
            return {"ok": True,
                    "dong": [{"lu": x["lu"], "ming": x["ming"],
                              "daxiao": x["da"]} for x in dong],
                    "zong": zong, "tishi": tishi}
        except Exception as e:
            return {"ok": False, "cuo": "扫不了：%s" % e}

    def zhengli_zhi_xing(self, wenjian):
        """执行移动（到回收站）。

        【只在用户明确点了确认之后才调到这里】前端那一步是"点了按钮"，
        不是"打开页面"。所以这里不再二次确认 —— 但函数内部仍会走
        zl_weixian 的四道闸（快捷方式 / 程序自己 / 系统目录 / 白名单）。
        """
        try:
            if not zhengli.zl_du_kai():
                return {"ok": False, "cuo": "整理助手现在关着。"}
            if not wenjian:
                return {"ok": False, "cuo": "没选文件。"}
            hao, huai, shuo = zhengli.zl_zhi_xing(list(wenjian))
            if shuo:
                return {"ok": False, "cuo": shuo}
            beizhu = ""
            if huai:
                beizhu = "跳过 %d 个：\n%s" % (
                    len(huai),
                    "\n".join("· %s  %s" % (os.path.basename(p), li)
                              for p, li in huai[:5]))
            return {"ok": True, "cheng": len(hao), "beizhu": beizhu}
        except Exception as e:
            return {"ok": False, "cuo": "执行失败：%s" % e}

    def zhengli_da_kai(self):
        """打开演示夹（资源管理器）"""
        try:
            zhengli.zl_dakai_mulu(zhengli.zl_yanshi_lu())
            return True
        except Exception as e:
            print("[api] 打开演示夹失败 %s" % e)
            return False

    # ---------- ⑤ 打赏 ----------
    def da_shang(self, dang):
        """打赏一档。只加好感度，不连任何支付。

        返回 {ok, wen, haogan, biao, tou, zhuangtai}
        """
        import random
        from core import dashang as ds
        try:
            zhi = None
            for shu, biao, jia, hui in ds.DASHANG_DANG:
                if biao.split()[0] == str(dang) or str(shu) == str(dang):
                    zhi = (shu, biao, jia, hui)
                    break
            if not zhi:
                return {"ok": False, "cuo": "没有这个档位。"}

            shu, biao, jia, hui = zhi
            with self._suo:
                qian = self._qingxu.haogan
                self._qingxu._jia_haogan(jia)
                zeng = self._qingxu.haogan - qian
                tidu = ds.DASHANG_TAIDU.get(shu, ("", ""))
                xiao = random.choice([x for x in tidu if x])
                wen = "%s\n%s" % (hui, xiao)
                if zeng == 0:
                    wen += "\n（好感度已经满了）"
                self._ji("[打赏] " + biao, wen, self._biao_ti())

            # 收礼就该是一张"开心/害羞"的脸，别用当前的平静。
            # 第一版传了 changjing="love"，结果挑到「恋人.png」——
            # 好感 63 就贴恋人图，不合时宜。
            tou = ""
            try:
                p = luoji.bq_xuan("开心", self._qingxu.lianren,
                                  self._lingguang, "")
                if p:
                    tou = os.path.basename(p)
            except Exception:
                pass
            return {"ok": True, "wen": wen, "haogan": self._qingxu.haogan,
                    "biao": self._biao_ti(), "tou": tou,
                    "zhuangtai": self.zhuang_tai()}
        except Exception as e:
            return {"ok": False, "cuo": "没打赏成：%s" % e}

    # ---------- ⑥ 壁纸 ----------
    def dang_qian_bi_zhi(self):
        """现在用的壁纸。前端启动时问一次，好把网格里的选中态对上。"""
        try:
            lu = luoji._du_bizhi() if hasattr(luoji, "_du_bizhi") else None
        except Exception:
            lu = None
        return {"lu": (lu or "素材/壁纸/xiaobendan.mp4"),
                "lei": "img" if (lu or "").lower().endswith(
                    (".jpg", ".jpeg", ".png", ".bmp", ".webp")) else "video"}

    def huan_bi_zhi(self, lu, shi_shi_pin):
        """换壁纸：记下来（下次打开还是它）+ 前端自己换 <video>/<img>。"""
        try:
            if hasattr(luoji, "_ji_bizhi"):
                luoji._ji_bizhi(lu)
        except Exception as e:
            print("[api] 记壁纸失败 %s" % e)
        return {"ok": True}

    def xuan_bi_zhi(self):
        """选一个视频或图片当壁纸，复制进 ui/素材/壁纸/"""
        import shutil
        import time as _t
        try:
            r = self._chuang.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=False,
                file_types=('视频 (*.mp4;*.webm;*.mov;*.mkv;*.avi)',
                            '图片 (*.png;*.jpg;*.jpeg;*.bmp;*.webp)',
                            '所有文件 (*.*)'))
        except Exception as e:
            return {"ok": False, "cuo": "打不开对话框：%s" % e}
        if not r:
            return {"ok": False, "cuo": ""}
        lu = r[0]
        ext = os.path.splitext(lu)[1].lower()
        mu = os.path.join(luoji.DIR, "素材", "壁纸")
        try:
            os.makedirs(mu, exist_ok=True)
            ming = "bz_%d%s" % (int(_t.time() * 1000), ext)
            shutil.copy2(lu, os.path.join(mu, ming))
        except Exception as e:
            return {"ok": False, "cuo": "复制失败：%s" % e}
        shipin = ext in (".mp4", ".webm", ".mov", ".mkv", ".avi")
        return {"ok": True, "lu": "素材/壁纸/" + ming, "url": "素材/壁纸/" + ming,
                "ming": os.path.basename(lu),
                "lei": "video" if shipin else "img"}

    # ---------- ⑩ 记忆 ----------
    def ji_yi(self):
        """她记住的东西（记忆_重要的事.json）"""
        try:
            d = luoji.du_zhongyao() or {}
            return {"ok": True, "dong": d}
        except Exception as e:
            return {"ok": False, "dong": {}, "cuo": str(e)}

    def qing_ji_yi(self):
        """清空记忆档案（不动对话）"""
        try:
            luoji.xie_zhongyao({})
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    # ---------- ⑨ 灵光钥匙 ----------
    def cun_yao_shi(self, kai):
        """存钥匙（写 ui/API.txt），顺手试一次看通不通"""
        kai = (kai or "").strip()
        if not kai:
            return {"ok": False, "cuo": "钥匙是空的。"}
        try:
            pei = luoji.du_api_peizhi()
            luoji.xie_api_peizhi({"api_key": kai})
            self._pei = luoji.du_api_peizhi()
            shi = False
            try:
                ok, _shuo = luoji.ce_lingguang(
                    kai, pei.get("base_url"), pei.get("model"), 12)
                shi = bool(ok)
                if ok:
                    self._lingguang = True
            except Exception:
                pass
            return {"ok": True, "shi": shi}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def da_kai_ge_xing_hua(self):
        """打开 ui/个性化/（放她的头像）"""
        try:
            mu = os.path.join(luoji.DIR, "个性化")
            os.makedirs(mu, exist_ok=True)
            os.startfile(mu)
            return True
        except Exception as e:
            print("[api] 打开个性化失败 %s" % e)
            return False

    # ---------- ⑧ 个性化：双头像 ----------
    def xuan_tou(self, shui):
        """选一张图当头像。shui = "ta"（她）或 "wo"（我）

        存成 256×256 的 PNG（tou_cun 做居中裁方 + LANCZOS 缩放）。
        【为什么必须裁方】头像是圆形蒙版，不裁方的话长图会被拉扁。
        """
        try:
            r = self._chuang.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=False,
                file_types=('图片 (*.png;*.jpg;*.jpeg;*.bmp;*.webp)',))
        except Exception as e:
            return {"ok": False, "cuo": "打不开对话框：%s" % e}
        if not r:
            return {"ok": False, "cuo": ""}
        try:
            shui = "ta" if shui == "ta" else "wo"
            # 【返回值是元组】tou_cun 返回 (True, 路径) 或 (False, 原因)，
            # 直接 if not ok 恒为假（元组非空就是真），解包才对。
            jieguo = luoji.tou_cun(r[0], shui)
            cheng = jieguo[0] if isinstance(jieguo, tuple) else bool(jieguo)
            if not cheng:
                li = jieguo[1] if isinstance(jieguo, tuple) and len(jieguo) > 1 else ""
                return {"ok": False, "cuo": "存不下这张图%s"
                        % ("：" + str(li) if li else "（格式或权限问题）")}
            return {"ok": True, "shui": shui,
                    "url": "个性化/%s?v=%d" % (
                        luoji.TOU_MING[shui], int(__import__("time").time()))}
        except Exception as e:
            return {"ok": False, "cuo": "存头像失败：%s" % e}

    def tou_zhuang_tai(self):
        """两个头像现在是什么状态：有没有自定义图、URL 带时间戳防缓存"""
        import time as _t
        out = {}
        for shui in ("ta", "wo"):
            you = False
            try:
                you = bool(luoji.tou_you(shui))
            except Exception:
                pass
            out[shui] = {
                "you": you,
                "url": ("个性化/%s?v=%d" % (luoji.TOU_MING[shui],
                                            int(_t.time()) if you else 0))
                       if you else "",
            }
        return out

    def shan_tou(self, shui):
        """删掉自定义头像，退回画的猫脸"""
        try:
            shui = "ta" if shui == "ta" else "wo"
            luoji.tou_shan(shui)
            return {"ok": True, "shui": shui}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    # ---------- 七 · 语音 ----------
    def yin_zhuang_tai(self):
        """语音开着没。默认关 —— 突然说话会吓人。"""
        try:
            return {"kai": bool(luoji.tts_du_kai()),
                    "you": self._you_tts()}
        except Exception:
            return {"kai": False, "you": False}

    def kai_yin(self, kai):
        try:
            luoji.tts_xie_kai(bool(kai))
            return {"ok": True, "kai": bool(kai), "you": self._you_tts()}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def nian(self, wenben):
        """合成一句语音，返回可以给 <audio> 播的相对 URL

        【为什么返回 URL 而不是直接播】合成要 3~4 秒（edge-tts 走网络），
        在这边播会卡住接口。交给浏览器的 <audio> 播，主线程不堵。
        """
        import time as _t
        wenben = (wenben or "").strip()
        if not wenben:
            return {"ok": False, "cuo": "没有要念的字。"}
        try:
            lu, cuo = luoji.tts_hecheng(wenben, 20, self._qingxu.dangqian)
            if not lu:
                return {"ok": False, "cuo": cuo or "合成失败"}
            # 缓存目录在 ui/语音缓存/，转成 http 相对路径
            xiang = os.path.relpath(lu, luoji.DIR).replace("\\", "/")
            return {"ok": True, "url": xiang + "?v=%d" % int(_t.time())}
        except Exception as e:
            return {"ok": False, "cuo": "念不出来：%s" % e}

    @staticmethod
    def _you_tts():
        try:
            import edge_tts  # noqa: F401
            return True
        except Exception:
            return False

    # ---------- 七·一 · 功能页玻璃参数（可调） ----------
    # 存成 ui/个性化/玻璃.txt，一行一个值：模糊|饱和|亮度|底色透明度
    # 【默认值为什么从 42px 降到 22px】
    # 42px 是第七阶段按"面板内亮度和面板外的差值"选出来的 ——
    # 那个指标只衡量"透不透"，没衡量"糊不糊"。
    # 用户第一句反馈就是"模糊程度还是太高了"。
    # 重新量了五档（帮助页文字做靶）：
    #   blur 42 底0.19 → 透亮度 4.4  文字对比 18297   ← 太糊，字发虚
    #   blur 24 底0.19 →  5.7       18562
    #   blur 22 底0.26 →  5.8       20271         ← 取这组
    #   blur 20 底0.30 →  5.9       22431
    #   blur 18 底0.34 →  6.1       23762         ← 更清楚，但底部开始像块板
    # 22px + 0.26 底：透亮度比 42px 高 32%，文字对比高 11%，还不像板。
    _BOLI_MOREN = (22, 175, 112, 26)     # 22px / 1.75 / 1.12 / 0.26

    def _boli_lu(self):
        return os.path.join(luoji.DIR, "个性化", "玻璃.txt")

    def du_bo_li(self):
        """读玻璃参数。返回 {mo, bao, liang, di}（都是整数，前端自己格式化）"""
        mo, bao, liang, di = self._BOLI_MOREN
        try:
            with open(self._boli_lu(), encoding="utf-8") as f:
                hang = (f.read() or "").replace("\n", " ").split()
            if len(hang) >= 4:
                mo = max(0, min(80, int(float(hang[0]))))
                bao = max(100, min(260, int(float(hang[1]))))
                liang = max(70, min(140, int(float(hang[2]))))
                di = max(0, min(80, int(float(hang[3]))))
        except Exception:
            pass
        return {"mo": mo, "bao": bao, "liang": liang, "di": di}

    def cun_bo_li(self, mo, bao, liang, di):
        """存玻璃参数。范围在服务端再夹一次 —— 前端滑块被改也不怕"""
        try:
            mo = max(0, min(80, int(mo)))
            bao = max(100, min(260, int(bao)))
            liang = max(70, min(140, int(liang)))
            di = max(0, min(80, int(di)))
            mu = os.path.join(luoji.DIR, "个性化")
            os.makedirs(mu, exist_ok=True)
            with open(self._boli_lu(), "w", encoding="utf-8") as f:
                f.write("%d %d %d %d\n" % (mo, bao, liang, di))
            return {"ok": True, "mo": mo, "bao": bao, "liang": liang, "di": di}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def bo_li_chong_zhi(self):
        """恢复默认（实测选出来的那组）"""
        mo, bao, liang, di = self._BOLI_MOREN
        return self.cun_bo_li(mo, bao, liang, di)

    # ---------- 七·二 · 语音输入 ----------
    def yin_shu_zhuang_tai(self):
        """语音输入能不能用：模型在不在、麦克风有没有"""
        try:
            from core import yuyin_shuru as ys
        except Exception as e:
            return {"ke": False, "cuo": "模块加载失败（%s）" % e}
        lu = ys.mogen_zai()
        if lu:
            return {"ke": True, "mo": os.path.basename(lu), "yao_mo": False}
        # 没模型，看看库在不在
        try:
            import sounddevice  # noqa: F401
            import vosk          # noqa: F401
            return {"ke": False, "yao_mo": True,
                    "cuo": "还差语音模型（42 MB，要去下）"}
        except Exception as e:
            return {"ke": False, "yao_mo": True,
                    "cuo": "还差语音库（%s）" % e}

    def yin_shu_kai(self):
        """按下说话：开始录音"""
        try:
            from core import yuyin_shuru as ys
            return ys.kai_shi()
        except Exception as e:
            return {"ok": False, "cuo": "开不了录音（%s）" % e}

    def yin_shu_ting(self):
        """松开说话：停止录音并返回识别结果 {ok, wen, cuo}"""
        try:
            from core import yuyin_shuru as ys
            return ys.ting_zhi()
        except Exception as e:
            return {"ok": False, "cuo": "收不了（%s）" % e}

    def xia_yu_yin_mo(self):
        """下载语音模型（42 MB）。带进度，后台跑。

        用户点一下才开始下 —— 不偷偷占带宽。
        """
        import threading as _t
        if getattr(self, "_zai_xia", False):
            return {"ok": True, "zhengzai": True}
        self._zai_xia = True
        self._xia_bf = 0

        def _pao():
            import urllib.request
            import zipfile
            try:
                from core import yuyin_shuru as ys
                mu = ys.MOGEN_MU
                os.makedirs(mu, exist_ok=True)
                URL = ("https://alphacephei.com/vosk/models/"
                       "vosk-model-small-cn-0.22.zip")
                zip_lu = os.path.join(mu, "_m.zip")
                for _ in range(20):
                    have = os.path.getsize(zip_lu) if os.path.exists(zip_lu) else 0
                    try:
                        req = urllib.request.Request(
                            URL, headers={"Range": "bytes=%d-" % have} if have else {})
                        with urllib.request.urlopen(req, timeout=120) as r:
                            zong = int(r.headers.get("Content-Length") or 0) + have
                            mode = "ab" if have and r.status == 206 else "wb"
                            with open(zip_lu, mode) as f:
                                while True:
                                    b = r.read(262144)
                                    if not b:
                                        break
                                    f.write(b)
                                    if zong:
                                        self._xia_bf = min(
                                            99, int(os.path.getsize(zip_lu) * 100 / zong))
                        break
                    except Exception:
                        continue
                with zipfile.ZipFile(zip_lu) as z:
                    z.extractall(mu)
                os.remove(zip_lu)
                self._xia_bf = 100
            except Exception as e:
                self._xia_cuo = str(e)
            finally:
                self._zai_xia = False

        self._xia_cuo = ""
        _t.Thread(target=_pao, daemon=True).start()
        return {"ok": True, "zhengzai": True}

    def yu_yin_mo_jin_du(self):
        return {"zai": bool(getattr(self, "_zai_xia", False)),
                "baifen": int(getattr(self, "_xia_bf", 0)),
                "cuo": getattr(self, "_xia_cuo", "")}

    # ---------- 七·五 · 托盘主动说话 ----------
    def zhu_dong_shuo(self, qiang_zhi=False):
        """她主动说一句话（托盘「让她说句话」用）

        走旧版 luoji.zhu_dong_na()：按当前时段/上次说话时间/好感，
        从 ZHU_HUA 里挑一句（久别 / 深夜 / 想 / 无聊 / 关心）。
        返回 {wen, biao, changjing}

        【qiang_zhi 是什么】zhu_dong_na 有节奏限制（一天 6 次、间隔 40 分钟）。
        用户手动点「让她说句话」时不该被这个限制挡住 —— 那是自动推送的规矩。
        所以 qiang_zhi=True 时直接自己挑一句，不走限制。
        """
        try:
            if qiang_zhi:
                # 手动触发：按当前时段挑场景，但要轮着来 ——
                # 每次都是「今天累不累」用户会以为坏了
                import random
                xs = __import__("datetime").datetime.now().hour
                if xs >= 23 or xs < 4:
                    场 = "深夜"
                elif not self._hui:
                    场 = "久别"          # 从没聊过 → 就当久别重逢
                else:
                    场 = random.choice(("想", "无聊", "关心"))
                池 = list(luoji.ZHU_HUA[场])
                上 = getattr(self, "_shang_ju", "")
                if len(池) > 1 and 上 in 池:
                    池.remove(上)
                句 = random.choice(池)
                self._shang_ju = 句
                jie = (场, 句)
            else:
                jie = luoji.zhu_dong_na()
            if not jie:
                return {"wen": "", "biao": ""}
            # zhu_dong_na 返回 (场景, 句子) 或 None
            chang, wen = (jie if isinstance(jie, tuple) else ("", jie))
            wen = str(wen or "").strip()
            if not wen:
                return {"wen": "", "biao": ""}
            with self._suo:
                biao = self._biao_ti()
                self._ji("", wen, biao)     # 记进对话历史（用户那句空，渲染时跳过）
                try:
                    # 没有"单独更新情绪"的方法（Qingxu 只有 gengxin(问,答)），
                    # 主动说话时把空问题传进去 —— 它只看回答就会更新脸色
                    self._qingxu.gengxin("", wen)
                except Exception:
                    pass
            return {"wen": wen, "biao": biao, "changjing": chang}
        except Exception as e:
            print("[api] 主动说话失败 %s" % e)
            return {"wen": "", "biao": ""}

    def ji_ming_zi(self, ming):
        """首次引导里用户填的名字 —— 直接写进记忆档案

        【为什么要单独一个接口】ti_zhongyao 认的是"我叫X"这种句式，
        引导卡里用户只填一个词（"小裴"），没有句式可抽。
        这里直接写，跳过规则。
        """
        ming = str(ming or "").strip()
        if not ming or len(ming) > 20:
            return {"ok": False, "cuo": "名字不像名字"}
        try:
            ji = luoji.du_zhongyao()
            ji["名字"] = ming
            ji["更新"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
            luoji.xie_zhongyao(ji)
            return {"ok": True, "ming": ming}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def ji_zhu_dong(self, wen, biao=""):
        """把主动说的一句话记进对话（窗口藏着、只发了通知时用）

        为什么不复用 zhu_dong_shuo：那个函数会重新挑一句。
        这里是把**已经挑好的那句**补记进历史，不然用户点开窗口看不到。
        """
        try:
            with self._suo:
                self._ji("", str(wen or ""), biao or self._biao_ti())
                try:
                    self._qingxu.gengxin("", str(wen or ""))
                except Exception:
                    pass
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "cuo": str(e)}

    def chuang_ke_jian(self):
        """窗口现在可见吗 —— 主动消息用它决定是推气泡还是发通知"""
        # pywebview 6.x 的 Window 没有 is_visible()，只有 show/hide。
        # 所以自己记账：隐藏时打个标记，显示时清掉。
        try:
            if self._chuang is None:
                return True
            return not bool(getattr(self, "_cang_zhe", False))
        except Exception:
            return True

    def ji_cang_zhe(self, cang):
        """界面/托盘隐藏或显示时调一下，让主动消息知道该不该弹通知"""
        self._cang_zhe = bool(cang)
        return {"ok": True, "cang": self._cang_zhe}

    # ---------- 八 · 关于 ----------
    def guan_yu(self):
        """版本与环境，全是真的（不写死）"""
        import platform
        neng = []

        def shi(ming, biao):
            try:
                return {"ming": ming, "you": bool(biao())}
            except Exception:
                return {"ming": ming, "you": False}

        neng.append(shi("灵光（联网大模型）", lambda: luoji.api_youxiao(self._pei)))
        neng.append(shi("识图·本地 OCR", lambda: __import__("rapidocr_onnxruntime")))
        neng.append(shi("识图·人脸/物体",
                        lambda: os.path.exists(shitu.FACE_MOGEN)
                        and os.path.exists(shitu.WUTI_MOGEN)))
        neng.append(shi("整理助手",
                        lambda: os.path.isdir(zhengli.zl_yanshi_lu())))
        neng.append(shi("语音", lambda: __import__("edge_tts")))

        return {
            "python": "%s (%s)" % (platform.python_version(), platform.architecture()[0]),
            "webview2": self._webview2_ban(),
            "dabao": bool(getattr(sys, "frozen", False)),
            "nenli": neng,
        }

    @staticmethod
    def _webview2_ban():
        """从注册表读 WebView2 版本（读不到就返回 '?'）"""
        try:
            import winreg
            for lu in (r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
                       r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
                       r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
                       r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"):
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, lu) as k:
                        v, _ = winreg.QueryValueEx(k, "pv")
                        if v:
                            return str(v)
                except Exception:
                    continue
        except Exception:
            pass
        return "?"

    # ══════════════════════════════════════════════════════════════════
    #  九 · 自己检查（给第五阶段的验收用）
    # ══════════════════════════════════════════════════════════════════

    def zi_jian(self):
        """把关键能力过一遍，返回逐项结果。

        为什么放在 api 而不是测试脚本里：用户双击 exe 之后，
        想自己看一眼"哪样能用"时，从功能页「关于」就能调到这里。
        返回的形状和界面上的展示一致，不为了测试另造一套。
        """
        out = []

        def 项(ming, fn, shuo_bai=""):
            try:
                ok, xi = fn()
            except Exception as e:
                ok, xi = False, "异常：%s" % e
            out.append({"ming": ming, "ok": bool(ok), "xi": xi or shuo_bai})

        # ① 灵光
        def _ling():
            kai = bool(self._lingguang)
            有 = bool(luoji.api_youxiao(self._pei))
            return (kai and 有,
                    "开着" if kai else "关着（没钥匙或手动关了）")
        项("灵光（联网对话）", _ling)

        # ② 识图三件
        def _ocr():
            import rapidocr_onnxruntime  # noqa: F401
            return True, "RapidOCR 就绪"
        项("识图·提字", _ocr)

        def _ren():
            return (os.path.exists(shitu.FACE_MOGEN),
                    os.path.basename(shitu.FACE_MOGEN))
        项("识图·认人", _ren)

        def _wu():
            return (os.path.exists(shitu.WUTI_MOGEN),
                    os.path.basename(shitu.WUTI_MOGEN))
        项("识图·认物", _wu)

        # ③ 语音
        def _yin():
            return (self._you_tts(), "edge-tts 就绪")
        项("语音", _yin)

        # ④ 托盘 —— pystray 装在 vendor/ 里，不在系统 site-packages，
        #    所以这里要先把 vendor 塞进 sys.path 才 import 得到
        def _tuo():
            try:
                vd = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "vendor")
                if not os.path.isdir(vd):
                    vd = os.path.join(getattr(sys, "_MEIPASS", ""), "vendor")
                if os.path.isdir(vd) and vd not in sys.path:
                    sys.path.insert(0, vd)
                import pystray  # noqa: F401
                return True, "pystray 就绪"
            except Exception as e:
                return False, "没装（%s）" % e
        项("托盘", _tuo)

        # ④b 语音输入（和"语音输出"是两件事，分开列）
        def _yinshu():
            try:
                from core import yuyin_shuru as ys
                lu = ys.mogen_zai()
                if not lu:
                    return False, "还没下模型（点输入框右边的麦克风可以下）"
                return True, os.path.basename(lu)
            except Exception as e:
                return False, "模块加载失败（%s）" % e
        项("语音输入（按住说话）", _yinshu)

        # ⑤ 素材
        def _su():
            n = len(luoji.JUZI) if hasattr(luoji, "JUZI") else 0
            return (n > 100, "%d 句语料" % n)
        项("聊天语料", _su)

        def _bq():
            mu = os.path.join(luoji.DIR, "表情", "灵光")
            n = len([x for x in os.listdir(mu) if x.endswith(".png")]) \
                if os.path.isdir(mu) else 0
            return (n >= 10, "%d 张表情" % n)
        项("表情", _bq)

        # ⑥ 存档
        def _cd():
            lu = getattr(luoji, "CUNDANG_LU", "")
            return (bool(lu) and os.path.isdir(os.path.dirname(lu)),
                    os.path.basename(lu) if lu else "路径未知")
        项("存档", _cd)

        return {"ok": all(x["ok"] for x in out), "xiang": out}
