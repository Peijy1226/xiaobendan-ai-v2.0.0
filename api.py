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

    def zhen_tui_chu(self):
        """界面里点「彻底退出」走这里。

        【为什么需要这个】托盘图标在重启 explorer（或者装/卸某些软件后
        explorer 崩溃重开）时会失效 —— 图标从托盘消失，但进程还在。
        用户这时既看不到窗口（藏起来了）、也点不到托盘菜单，
        只能用任务管理器 —— 这是设计缺陷。

        所以必须留一条不依赖托盘的退出路：界面里一个按钮。
        """
        import threading as _t
        import time as _ti

        def _pao():
            # ① 放行 closing（不置这个开关会被"关闭=藏托盘"拦住）
            try:
                if callable(getattr(self, "_zhen_tui", None)):
                    self._zhen_tui()
            except Exception:
                pass
            # ② 存档（和 guan_bi 同一套）
            try:
                luoji.xie_cundang(self._hui, self._qingxu.haogan,
                                  self._qingxu.lunshu, self._qingxu.dangqian)
            except Exception:
                pass
            # ③ 停托盘（停不掉也无所谓，下面会硬退）
            try:
                if callable(getattr(self, "_ting_tuo", None)):
                    self._ting_tuo()
            except Exception:
                pass
            # ④ 关窗口
            try:
                if self._chuang is not None:
                    self._chuang.destroy()
            except Exception:
                pass
            # ⑤ 1.5 秒后硬退 —— 不能因为某个 daemon 线程不听话就卡住
            _ti.sleep(1.5)
            import os as _os
            _os._exit(0)

        _t.Thread(target=_pao, daemon=True).start()
        return {"ok": True}

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