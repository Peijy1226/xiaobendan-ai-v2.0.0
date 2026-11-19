/* ============================================================================
   bishu.js —— 壁纸（视频 / 静图 / 纯色底）

   旧版的做法（DongTaiBeiJing，小笨蛋.py 5814 行）：
     后台线程解码 → 缩放 → 压暗 → 界面线程每帧贴图
     一帧 60~130ms，被硬压到 8~12fps，播什么都是慢放。

   新版交给浏览器 <video>：
     硬件解码 + 合成器直出，60fps 不占 CPU，且和页面共用一个时钟，
     气泡的 backdrop-filter 跟着视频每一帧自动重算 —— 旧版做不到这点。

   还多了个旧版没有的好处：视频播到哪一帧，毛玻璃就是哪一帧的模糊，
   不需要"_boli_shua 每 0.6 秒刷一次气泡底图"那套补丁。
   ========================================================================== */

(function () {
  'use strict';

  var shi = document.getElementById('bi-shi');   // video
  var zhen = document.getElementById('bi-zhen'); // 首帧垫底图

  /* 视频一能播出画面就把垫底图淡出。
     loadeddata = 首帧已解码、能画在屏幕上，比 canplay 更早一点点。 */
  var yi_liang = false;
  function liang() {
    if (yi_liang) return;
    yi_liang = true;
    if (zhen) zhen.classList.add('ming');
    console.log('[bishu] 视频就绪，垫底图淡出');
  }

  if (shi) {
    if (shi.readyState >= 2) {
      liang();
    } else {
      shi.addEventListener('loadeddata', liang);
      /* 兜底：视频加载失败（文件被删 / 编码不支持）就永远停在首帧图上，
         不让用户看到黑屏。旧版也是这么退的（换不了壁纸就留着上一张）。 */
      shi.addEventListener('error', function () {
        console.warn('[bishu] 视频加载失败，保留首帧图', shi.error);
        if (zhen) zhen.classList.remove('ming');
      });
    }

    /* Chromium 允许静音视频自动播放，但某些策略下仍会被拦。
       这里兜一次：被拦就当用户点过页面再播。 */
    var p = shi.play();
    if (p && p.catch) {
      p.catch(function (e) {
        console.warn('[bishu] 自动播放被拦，等用户第一次点击', e);
        var qi = function () {
          shi.play().catch(function () { });
          window.removeEventListener('mousedown', qi);
        };
        window.addEventListener('mousedown', qi);
      });
    }

    /* 窗口最小化时浏览器会自动暂停视频（省电），恢复后要接着播。
       WebView2 也会暂停，所以这里显式接一下。 */
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && shi.paused) {
        shi.play().catch(function () { });
      }
    });
  }

  /* ---------------- 对外 ---------------- */
  window.BiShu = {
    /* 换壁纸：第二阶段接"个性化 → 壁纸"时用。传文件路径（相对 ui/ 或绝对）。 */
    换: function (lujing, shi_fou_shi_pin) {
      if (!shi) return false;
      if (shi_fou_shi_pin) {
        shi.src = lujing;
        shi.load();
        shi.play().catch(function () { });
        if (zhen) zhen.classList.remove('ming');
      } else {
        /* 静图：直接让垫底图显示新图，视频停掉藏起来 */
        if (zhen) {
          zhen.src = lujing;
          zhen.classList.remove('ming');
        }
        shi.pause();
      }
      return true;
    },

    视频就绪: function () { return yi_liang; },

    播: function () { if (shi) shi.play().catch(function () { }); },
    停: function () { if (shi) shi.pause(); },

    当前帧: function () { return shi ? shi.currentTime : 0; }
  };
})();
