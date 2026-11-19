/* ============================================================================
   bridge.js —— 前端与 Python 之间唯一的通道

   第二阶段接口（全部由 api.py 实现）：
     hui_fu(文本)      -> {wen, tou, biao, xinqing, haogan, lunshu, lianren}
     kai_chang()       -> {duihua, zhuangtai, kai, kaichang}
     zhuang_tai()      -> {xin, zhuangtai, haogan, lunshu, lianren}
     cun_dang()        -> {ok, tiao}
     qing_kong()       -> {ok, zhuangtai}
     du_yang() / cun_yang(n)
     ling_guang() / she_ling_guang(kai) / chong_du_peizhi()
     wen_tianqi(chengshi)
     nuo_qi_dian() / nuo_chuang(dx,dy) / zui_xiao_hua() / guan_bi()

   为什么单独一层：浏览器里直接打开 index.html 调样式时 window.pywebview
   不存在，这里退化成假回复，不用为了看界面去启动 exe。
   ========================================================================== */

(function () {
  'use strict';

  var 已就绪 = false;
  var 待办 = [];

  function 检查就绪() {
    if (window.pywebview && window.pywebview.api) {
      已就绪 = true;
      var 队列 = 待办;
      待办 = [];
      队列.forEach(function (fn) { fn(); });
      return true;
    }
    return false;
  }

  if (!检查就绪()) {
    window.addEventListener('pywebviewready', 检查就绪);
    var 次 = 0;
    var 轮 = setInterval(function () {
      if (检查就绪() || ++次 > 50) clearInterval(轮);
    }, 100);
  }

  function 就绪后(fn) {
    if (已就绪) { fn(); return; }
    待办.push(fn);
    setTimeout(function () {
      var i = 待办.indexOf(fn);
      if (i >= 0) {
        待办.splice(i, 1);
        fn();
      }
    }, 2000);
  }

  function 调用(方法名, 参数, 兜底) {
    if (已就绪 && window.pywebview.api[方法名]) {
      try {
        return window.pywebview.api[方法名].apply(null, 参数 || []);
      } catch (e) {
        console.warn('[bridge] 调用失败，走兜底', 方法名, e);
      }
    }
    return Promise.resolve(兜底 ? 兜底.apply(null, 参数 || []) : null);
  }

  /* 【启动就套一次】玻璃参数存在 Python 那边（ui/个性化/玻璃.txt）。
     第一版只在打开「个性化」那页时才改变量 —— 结果用户不动滑块，
     功能页永远用 CSS 里的兜底值 42px，改什么都"没生效"。
     放到这里：bridge 一就绪就套，跟哪个页面开没开无关。 */
  就绪后(function () {
    try {
      Promise.resolve(调用('du_bo_li', [], null)).then(function (v) {
        if (!v) return;
        var r = document.documentElement.style;
        r.setProperty('--boli-mo', (v.mo || 22) + 'px');
        r.setProperty('--boli-bao', ((v.bao || 175) / 100).toFixed(2));
        r.setProperty('--boli-liang', ((v.liang || 112) / 100).toFixed(2));
        r.setProperty('--boli-di', ((v.di || 26) / 100).toFixed(2));
      });
    } catch (e) {
      console.warn('[bridge] 玻璃参数套用失败', e);
    }
  });

  window.Qiao = {
    就绪后: 就绪后,
    可用: function () { return 已就绪; },

    /* ---- 对话 ---- */
    回复: function (文本) {
      return 调用('hui_fu', [文本], function (t) {
        return {
          wen: '（浏览器调试模式，Python 没连上）你说的是「' + t + '」。',
          tou: '', biao: '小笨蛋 （・_・?） 困惑',
          xinqing: '困惑', haogan: 55, lunshu: 0, lianren: false
        };
      });
    },

    开场: function () {
      return 调用('kai_chang', [], function () {
        return {
          duihua: [], kai: true,
          kaichang: '（拉了拉深色的兜帽，脸颊微红）你来了……小笨蛋今天也在这里等你哦。',
          zhuangtai: {
            xin: 1, haogan: 55, lunshu: 0, lianren: false,
            zhuangtai: '（-__-） 平静　好感度 55/100 · 第 0 轮'
          }
        };
      });
    },

    存档: function () {
      return 调用('cun_dang', [], function () { return { ok: true }; });
    },
    清空: function () {
      return 调用('qing_kong', [], function () { return { ok: true }; });
    },

    /* ---- 气泡样式 ---- */
    读样式: function () {
      var v = localStorage.getItem('qipao_yang');
      return v === null ? 0 : parseInt(v, 10) || 0;
    },
    存样式: function (n) {
      localStorage.setItem('qipao_yang', String(n));
      return 调用('cun_yang', [n], null);
    },

    /* ---- 灵光 ---- */
    灵光状态: function () {
      return 调用('ling_guang', [], function () {
        return { kai: false, you_yao: false, moxing: '' };
      });
    },
    开灵光: function (kai) {
      return 调用('she_ling_guang', [kai], function () {
        return { kai: false, you_yao: false };
      });
    },

    /* ---- 功能页接口 ---- */
    选图: function () { return 调用('xuan_tu', [], function () { return { ok: false, cuo: '浏览器里选不了图。' }; }); },
    识图: function (zenme, lu) { return 调用('shi_tu', [zenme, lu], function () { return { ok: false, cuo: '浏览器里没有识图。' }; }); },
    写一篇: function (timu, ticai) { return 调用('xie_yi_pian', [timu, ticai], function () { return { ok: false, cuo: '浏览器里没有大模型。' }; }); },

    整理开关: function (kai) {
      return 调用('zhengli_kai_guan', kai === undefined ? [null] : [kai],
        function () { return { kai: false, jia: '' }; });
    },
    整理扫: function (lei) { return 调用('zhengli_sao', [lei], function () { return { ok: false, cuo: '浏览器里扫不了。' }; }); },
    整理执行: function (lu) { return 调用('zhengli_zhi_xing', [lu], function () { return { ok: false, cuo: '浏览器里不能动文件。' }; }); },
    整理打开夹: function () { return 调用('zhengli_da_kai', [], null); },

    打赏: function (dang) { return 调用('da_shang', [dang], null); },

    当前壁纸: function () { return 调用('dang_qian_bi_zhi', [], function () { return { lu: '素材/壁纸/xiaobendan.mp4', lei: 'video' }; }); },
    换壁纸: function (lu, shi) { return 调用('huan_bi_zhi', [lu, !!shi], null); },
    选壁纸: function () { return 调用('xuan_bi_zhi', [], function () { return { ok: false }; }); },

    记忆: function () { return 调用('ji_yi', [], function () { return { dong: {} }; }); },
    清记忆: function () { return 调用('qing_ji_yi', [], function () { return { ok: true }; }); },

    存钥匙: function (k) { return 调用('cun_yao_shi', [k], function () { return { ok: false, cuo: '浏览器里存不了。' }; }); },

    打开个性化: function () { return 调用('da_kai_ge_xing_hua', [], null); },

    /* ---- 语音 ---- */
    语音状态: function () { return 调用('yin_zhuang_tai', [], function () {
      return { kai: false, you: false }; }); },
    开语音: function (kai) { return 调用('kai_yin', [!!kai], function () {
      return { ok: false }; }); },
    念: function (wen) { return 调用('nian', [wen], function () {
      return { ok: false, cuo: '浏览器里没有语音。' }; }); },

    /* ---- ⑧ 个性化：双头像 ---- */
    选头像: function (shui) { return 调用('xuan_tou', [shui], function () {
      return { ok: false, cuo: '浏览器里选不了图。' }; }); },
    头像状态: function () { return 调用('tou_zhuang_tai', [], function () {
      return { ta: { you: false, url: '' }, wo: { you: false, url: '' } }; }); },
    删头像: function (shui) { return 调用('shan_tou', [shui], function () {
      return { ok: true }; }); },

    /* ---- 功能页玻璃（可调模糊） ---- */
    读玻璃: function () { return 调用('du_bo_li', [],
      function () { return { mo: 22, bao: 175, liang: 112, di: 26 }; }); },
    存玻璃: function (mo, bao, liang, di) {
      return 调用('cun_bo_li', [mo, bao, liang, di],
        function () { return { ok: false }; });
    },
    重置玻璃: function () { return 调用('bo_li_chong_zhi', [],
      function () { return { ok: false }; }); },

    /* ---- 语音输入 ---- */
    语音输入状态: function () { return 调用('yin_shu_zhuang_tai', [],
      function () { return { ke: false, yao_mo: false }; }); },
    开始录音: function () { return 调用('yin_shu_kai', [],
      function () { return { ok: false, cuo: '浏览器里不能录。' }; }); },
    停止录音: function () { return 调用('yin_shu_ting', [],
      function () { return { ok: false, cuo: '浏览器里不能录。' }; }); },
    下语音模型: function () { return 调用('xia_yu_yin_mo', [],
      function () { return { ok: false }; }); },
    语音模型进度: function () { return 调用('yu_yin_mo_jin_du', [],
      function () { return { zai: false, baifen: 0 }; }); },

    记名字: function (ming) { return 调用('ji_ming_zi', [ming], function () {
      return { ok: false }; }); },

    自检: function () { return 调用('zi_jian', [], function () {
      return { ok: false, xiang: [] }; }); },

    关于: function () { return 调用('guan_yu', [], function () {
      return { python: '?', webview2: '?', dabao: false, nenli: [] };
    }); },

    /* ---- 窗口控制 ---- */
    窗原点: function () {
      return 调用('nuo_qi_dian', [], null);
    },
    挪窗口: function (dx, dy) {
      return 调用('nuo_chuang', [dx, dy], null);
    },
    最小化: function () {
      return 调用('zui_xiao_hua', [], null);
    },
    关闭: function () {
      return 调用('guan_bi', [], null);
    }
  };
})();
