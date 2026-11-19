/* ============================================================================
   yuyin_shuru.js —— 按住说话（前端那半）

   【交互选型】按住说话 vs 点一下开始、点一下结束
   聊天软件的主流是"按住"（微信、QQ 都是），因为：
     · 松开就结束，不会忘了关麦
     · 手一松就知道"我说完了"，反馈明确
   但鼠标按住拖到别的窗口会丢鼠标事件 —— 所以这里加了兜底：
   如果 mouseup 没收到，超过 30 秒自动停。

   【模型没下怎么办】
   点麦克风 → 后端说"还差模型" → 弹一个内联提示条问要不要下（42 MB）。
   用户点"下"才开始。绝不偷偷下。
   ========================================================================== */

(function () {
  'use strict';

  var 钮 = document.getElementById('niu-mai');
  var 框 = document.getElementById('shu-ru');
  if (!钮 || !框) return;

  var 在录 = false;
  var 起时 = 0;
  var 超时 = null;
  var 提示条 = null;

  /* ---------------- 提示条 ---------------- */
  function 摆提示(html, 按钮们) {
    收提示();
    提示条 = document.createElement('div');
    提示条.className = 'mai-ti';
    提示条.innerHTML = '<span class="mai-ti-wen">' + html + '</span>';
    var 盒 = document.createElement('span');
    盒.className = 'mai-ti-niu';
    (按钮们 || []).forEach(function (b) {
      var e = document.createElement('button');
      e.className = 'mai-an' + (b.ci ? ' ci' : '');
      e.textContent = b.ming;
      e.addEventListener('click', b.dian);
      盒.appendChild(e);
    });
    提示条.appendChild(盒);
    /* 【挂到 body 上，不能塞进 #xia】#xia 是横排的 flex 行（输入框+按钮），
       把提示条 insertBefore(框) 会变成"横着挤在输入框左边" ——
       实测就是这样，提示文字被压成一条贴在左边。
       挂 body + position:fixed 落在输入条正上方才对。 */
    document.body.appendChild(提示条);
  }

  function 收提示() {
    if (提示条) {
      提示条.remove();
      提示条 = null;
    }
  }

  /* ---------------- 录音 ---------------- */
  function 开始() {
    if (在录) return;
    Promise.resolve(Qiao.语音输入状态()).then(function (st) {
      if (!st || !st.ke) {
        if (st && st.yao_mo) {
          摆提示('要下个语音模型（42 MB）才能听见你说话。', [
            { ming: '现在下', dian: 下模型 },
            { ming: '算了', ci: true, dian: 收提示 },
          ]);
        } else {
          摆提示((st && st.cuo) || '语音输入现在用不了。', [
            { ming: '知道了', ci: true, dian: 收提示 },
          ]);
        }
        return;
      }
      真开始();
    });
  }

  function 真开始() {
    收提示();
    在录 = true;
    起时 = Date.now();
    钮.classList.add('lu');
    钮.title = '松开就结束';
    框.placeholder = '听着呢……说完松开';
    框.disabled = true;

    Promise.resolve(Qiao.开始录音()).then(function (r) {
      if (!r || !r.ok) {
        收尾();
        摆提示((r && r.cuo) || '开不了麦克风。', [
          { ming: '知道了', ci: true, dian: 收提示 },
        ]);
      }
    });

    /* 兜底：mouseup 丢了（拖出窗口 / 切桌面）就 30 秒自动停 */
    超时 = setTimeout(function () {
      if (在录) 结束();
    }, 30000);
  }

  function 结束() {
    if (!在录) return;
    在录 = false;
    收尾();
    钮.classList.remove('lu');
    框.placeholder = '说点什么…';
    框.disabled = false;
    框.focus();

    Promise.resolve(Qiao.停止录音()).then(function (r) {
      if (!r || !r.ok) {
        if (r && r.cuo && r.cuo !== '没听清') {
          摆提示(r.cuo, [{ ming: '知道了', ci: true, dian: 收提示 }]);
        } else {
          摆提示('没听清，再说一次？', [{ ming: '好', ci: true, dian: 收提示 }]);
        }
        return;
      }
      var 文 = String(r.wen || '').trim();
      if (!文) return;
      /* 直接发出去 —— 按住说话本来就是为了少点一次 */
      框.value = 文;
      var 发 = document.getElementById('fa-song');
      if (发) 发.click();
    });
  }

  function 收尾() {
    if (超时) {
      clearTimeout(超时);
      超时 = null;
    }
  }

  /* ---------------- 下载模型 ---------------- */
  function 下模型() {
    收提示();
    Promise.resolve(Qiao.下语音模型()).then(function () {
      摆提示('<span class="mai-zai"></span>正在下 0%…', []);
      轮进度();
    });
  }

  function 轮进度() {
    if (!提示条) return;
    Promise.resolve(Qiao.语音模型进度()).then(function (r) {
      r = r || {};
      var 文 = 提示条 && 提示条.querySelector('.mai-ti-wen');
      if (!文) return;
      if (r.cuo) {
        收提示();
        摆提示('下载失败：' + r.cuo, [{ ming: '知道了', ci: true, dian: 收提示 }]);
        return;
      }
      if (!r.zai && r.baifen >= 100) {
        收提示();
        摆提示('下好了。按住麦克风就能说话。', [
          { ming: '好', ci: true, dian: 收提示 },
        ]);
        return;
      }
      文.innerHTML = '<span class="mai-zai"></span>正在下 ' +
        (r.baifen || 0) + '%…（可以先聊别的）';
      setTimeout(轮进度, 800);
    });
  }

  /* ---------------- 事件 ---------------- */
  钮.addEventListener('mousedown', function (e) {
    e.preventDefault();
    开始();
  });

  window.addEventListener('mouseup', function () {
    if (在录) 结束();
  });

  /* 鼠标离开窗口也要停 —— 拖出去松开时 mouseup 收不到 */
  window.addEventListener('mouseleave', function () {
    if (在录) 结束();
  });

  /* 键盘也能用：空格按住说（焦点不在输入框时） */
  document.addEventListener('keydown', function (e) {
    if (e.code === 'Space' && !在录 &&
        document.activeElement !== 框 &&
        document.activeElement.tagName !== 'INPUT' &&
        document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      开始();
    }
  });

  document.addEventListener('keyup', function (e) {
    if (e.code === 'Space' && 在录) 结束();
  });

  /* 启动时问一次状态：能用就把按钮做成"激活"的样子，
     不能用就灰着（但还能点，点了会引导下载）。 */
  Qiao.就绪后(function () {
    Promise.resolve(Qiao.语音输入状态()).then(function (st) {
      if (st && st.ke) {
        钮.classList.add('ke');
        钮.title = '按住说话（' + (st.mo || '') + '）';
      } else {
        钮.classList.add('que');
        钮.title = '按住说话（还差语音模型，点一下能下）';
      }
    });
  });

  window.YuYinShuRu = {
    开始: 开始,
    结束: 结束,
    在录: function () { return 在录; }
  };
})();
