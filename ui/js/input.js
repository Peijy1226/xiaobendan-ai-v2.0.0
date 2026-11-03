/* ============================================================================
   input.js —— 输入、发送、窗口按钮、拖动、样式切换

   第二阶段行为（对齐旧版）：
     · Enter 发送，输入法组字时不发（e.isComposing）
     · 发出后先摆一条"正在想…"占位，回复到了原地替换
     · 每轮结束调 cun_dang 存档（Python 侧节流 6 秒一次）
     · 回复带表情就贴一张（旧版 tian_tu 也是排在气泡下面，不套气泡）
   ========================================================================== */

(function () {
  'use strict';

  var 框 = document.getElementById('shu-ru');
  var 钮 = document.getElementById('fa-song');
  var 忙 = false;

  /* ---------------- 发送 ---------------- */
  function 发送() {
    var 文本 = 框.value.trim();
    if (!文本 || 忙) return;

    框.value = '';
    忙 = true;

    LiaoTian.加消息('wo', 文本);

    /* 占位条：旧版 tian_zhan() 就是这么做的 —— 先摆一条，
       回复到了原地换掉，用户不会看到"没反应"。 */
    var 占位 = LiaoTian.加消息('ta', '……', '小笨蛋 （…） 正在想…');

    Promise.resolve(Qiao.回复(文本)).then(function (回) {
      var 文 = (回 && 回.wen) || '……';
      var 标 = (回 && 回.biao) || '小笨蛋 （・_・?） 困惑';
      占位.remove();
      LiaoTian.加消息('ta', String(文), 标);

      /* 表情：旧版是排在气泡下面单独一条，不套气泡 */
      if (回 && 回.tou) LiaoTian.加表情(回.tou);

      /* 语音：开着就念出来（只念正文，不念「正在想」这类占位） */
      if (window.YuYin && window.YuYin.在开() && 文) {
        window.YuYin.清队();          /* 上一句还没念完就算了，别堆一串 */
        window.YuYin.说(文);
      }

      /* 顶栏五颗心 + 状态字：直接用后端返回来的一整套，别在前端再算一遍 */
      if (回) LiaoTian.刷顶栏({
        xin: 回.xin || 心数(回.haogan),
        zhuangtai: 回.zhuangtai,
        haogan: 回.haogan,
        lunshu: 回.lunshu,
        lianren: 回.lianren
      });

      /* 存档：Python 侧 6 秒节流，前端每轮都叫也没事 */
      Qiao.存档();

      忙 = false;
      框.focus();
    }).catch(function (e) {
      console.error('[input] 回复失败', e);
      占位.remove();
      LiaoTian.加消息('ta', '……好像出了点问题。', '小笨蛋 （・_・?） 困惑');
      忙 = false;
    });
  }

  /* 好感度 → 五颗心（旧版 xin_shu：门槛 60/75/88/100，初始 1 颗） */
  function 心数(zhi) {
    zhi = Math.max(0, Math.min(100, parseInt(zhi, 10) || 0));
    var n = 1;
    if (zhi >= 60) n++;
    if (zhi >= 75) n++;
    if (zhi >= 88) n++;
    if (zhi >= 100) n++;
    return n;
  }

  钮.addEventListener('click', 发送);

  框.addEventListener('keydown', function (e) {
    /* 输入法组字期间回车是"上屏"，不能当发送 —— 中文输入必须判这个 */
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      发送();
    }
  });

  /* ---------------- 三套气泡切换 ---------------- */
  document.getElementById('yang-shi').addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    var n = parseInt(b.dataset.yang, 10);
    LiaoTian.换样式(n);
    var 全部 = this.querySelectorAll('button');
    for (var i = 0; i < 全部.length; i++) {
      全部[i].classList.toggle('on', 全部[i] === b);
    }
  });

  /* ---------------- 拖动标题栏 ----------------
     为什么不用 pywebview 的 .pywebview-drag-region：
     它内部发 WM_NCLBUTTONDOWN + HTCAPTION 让系统接管拖动，但那条路只对
     带系统边框的窗口有效。这扇窗是 frameless（FormBorderStyle=None），
     没有非客户区，系统收到消息直接忽略 —— 实测位移恒为 0。
     所以自己算：按下时记窗口原点 + 鼠标位置，每帧把差值交给 Python
     用 SetWindowPos 落位。rAF 节流，避免 mousemove 堆积。 */
  var tuo = { 开: false, 起X: 0, 起Y: 0, 原X: 0, 原Y: 0, 待X: 0, 待Y: 0, 排: false };

  document.getElementById('ding').addEventListener('mousedown', function (e) {
    if (e.button !== 0) return;
    if (e.target.closest('button, .ding-niu, #yang-shi')) return;
    e.preventDefault();

    tuo.开 = true;
    tuo.起X = e.screenX;
    tuo.起Y = e.screenY;

    /* 起点问 Python 要真实窗口坐标 —— screenX 在高 DPI 下和物理像素不一样 */
    Promise.resolve(Qiao.窗原点()).then(function (p) {
      if (p && p.length === 2) {
        tuo.原X = p[0];
        tuo.原Y = p[1];
      } else {
        tuo.原X = window.screenX;
        tuo.原Y = window.screenY;
      }
    });
  });

  window.addEventListener('mousemove', function (e) {
    if (!tuo.开) return;
    tuo.待X = e.screenX - tuo.起X;
    tuo.待Y = e.screenY - tuo.起Y;
    if (!tuo.排) {
      tuo.排 = true;
      requestAnimationFrame(推);
    }
  });

  function 推() {
    tuo.排 = false;
    if (!tuo.开) return;
    Qiao.挪窗口(tuo.待X, tuo.待Y);
  }

  window.addEventListener('mouseup', function () {
    tuo.开 = false;
  });

  /* ---------------- 窗口按钮 ---------------- */
  document.getElementById('niu-xiao').addEventListener('click', function (e) {
    e.stopPropagation();
    Qiao.最小化();
  });

  document.getElementById('niu-guan').addEventListener('click', function (e) {
    e.stopPropagation();
    Qiao.关闭();
  });

  /* 「☰ 功能」开功能页（13 项） */
  document.getElementById('niu-gong-neng').addEventListener('click', function () {
    window.GongNeng.切换();
  });

  /* ---------------- 启动 ---------------- */
  Qiao.就绪后(function () {
    setTimeout(function () { 框.focus(); }, 150);
  });

  /* 把窗口按钮的中心坐标暴露出去，验收脚本按真实位置点 */
  window.ChuangNiu = {
    最小化: function () {
      var r = document.getElementById('niu-xiao').getBoundingClientRect();
      return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
    },
    关闭: function () {
      var r = document.getElementById('niu-guan').getBoundingClientRect();
      return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
    },
    样式: function (n) {
      var b = document.querySelector('#yang-shi button[data-yang="' + n + '"]');
      if (!b) return null;
      var r = b.getBoundingClientRect();
      return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
    }
  };
})();
