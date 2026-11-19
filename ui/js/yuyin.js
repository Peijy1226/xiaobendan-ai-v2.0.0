/* ============================================================================
   yuyin.js —— 让她说话（边缘 TTS）

   【为什么是"念一句、播一句"】
   edge-tts 走网络，合成一句要 3~4 秒。如果等她说完再播，用户会以为卡住了。
   所以策略是：
     · 合成完先入库（ui/语音缓存/），同一个文本第二次是零延迟
     · 播的时候用 <audio>，不占 Python 主线程
     · 一句话播完不打断下一句（队列）

   【为什么默认关】
   电脑突然出声会吓人。而且用户可能正在开会。所以只在顶栏点开才说话。
   ========================================================================== */

(function () {
  'use strict';

  var 开 = false;
  var 队 = [];                 /* 待播的文本 */
  var 在播 = false;
  var 音频 = new Audio();
  var 按钮 = document.getElementById('niu-yin');

  音频.volume = 0.92;

  function 刷钮() {
    if (!按钮) return;
    按钮.textContent = 开 ? '🔊' : '🔇';
    按钮.title = 开 ? '她说话中（点一下关）' : '让她说话（点一下开）';
    按钮.classList.toggle('kai', 开);
  }

  /* 【必须在 bridge 就绪之后再问状态】
     第一版直接同步调 Qiao.语音状态()。那时 pywebview 还没注入
     window.pywebview.api，bridge 走兜底返回 {kai:false, you:false} ——
     于是 `you === false` 把按钮 disabled 了，点一辈子也没反应。
     实测：log 里第一行就是 "disabled=true"。
     解法：用 bridge 的 就绪后()，它会在 pywebviewready 之后才执行。 */
  function 初始化() {
    Qiao.就绪后(function () {
      Promise.resolve(Qiao.语音状态()).then(function (r) {
        开 = !!(r && r.kai);
        if (r && r.you === false) {
          按钮.disabled = true;
          按钮.title = '没装 edge-tts（第五阶段才完整支持）';
        }
        刷钮();
      });
    });
  }

  /* 点开关：只切状态。
     【为什么不做"开启时先念一句"】合成一句要 3~4 秒，用户点完会觉得
     "按钮没反应"。状态切换应该是瞬时的，说话交给下一条回复。 */
  var 忙 = false;
  按钮 && 按钮.addEventListener('click', function () {
    if (忙) return;
    忙 = true;
    var 要开 = !开;
    Promise.resolve(Qiao.开语音(要开)).then(function (r) {
      忙 = false;
      if (!r || r.ok === false) {
        /* 后端说不行（没装 edge-tts / 写不了文件）→ 按钮保持原样，给人一句提示 */
        按钮.title = (r && r.cuo) || '语音打不开';
        return;
      }
      开 = 要开;
      刷钮();
      if (!开) {
        队.length = 0;
        音频.pause();
      }
    }).catch(function () {
      忙 = false;
      按钮.title = '语音打不开';
    });
  });

  /* ---- 队列：一次合成一句，播完再下一句 ---- */
  function 说(wen) {
    if (!开 || !wen) return;
    var t = String(wen).replace(/\s+/g, ' ').trim();
    if (!t) return;
    队.push(t);
    if (!在播) 下一句();
  }

  function 下一句() {
    if (!队.length) {
      在播 = false;
      return;
    }
    在播 = true;
    var t = 队.shift();
    Promise.resolve(Qiao.念(t)).then(function (r) {
      if (!r || !r.ok) {
        在播 = false;
        下一句();
        return;
      }
      音频.src = r.url;
      var 收尾 = function () {
        音频.onended = null;
        音频.onerror = null;
        下一句();
      };
      音频.onended = 收尾;
      音频.onerror = 收尾;
      音频.play().catch(function () {
        /* 浏览器策略可能拦自动播放（WebView 里一般不会），拦了就跳过这句 */
        收尾();
      });
    }).catch(function () {
      在播 = false;
      下一句();
    });
  }

  window.YuYin = {
    说: 说,
    在开: function () { return 开; },
    /* 她说一句之前先清掉旧的 —— 用户连着发几句时，不要念一串过期的 */
    清队: function () { 队.length = 0; }
  };

  初始化();
})();
