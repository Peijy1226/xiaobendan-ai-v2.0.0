/* ============================================================================
   chat.js —— 聊天区渲染（第二阶段：接真逻辑）

   渲染结构照旧版 _hua_mao（7963 行）：
     · 她这一条上面有小字（小笨蛋 （-__-） 平静）
     · 头像顶边与气泡顶边齐平
     · 三套气泡共用一套 DOM，只换 class，几何细节全在 chat.css

   数据来自 Python 的 api.hui_fu()，返回形状固定：
     {wen, tou, biao, xinqing, haogan, lunshu, lianren}
   ========================================================================== */

(function () {
  'use strict';

  var 区 = document.getElementById('liao-tian');
  var 当前样式 = 0;          /* 0 猫耳 / 1 圆角 / 2 透光 */
  var 表情根 = "表情/灵光/";

  /* 情绪表（QINGXU_BIAO，5272 行）：七种，颜文字原样 */
  var 情绪 = {
    平静: '（-__-）',
    开心: '（＾▽＾）',
    兴奋: '（★▽★）',
    得意: '（•̀ω•́）',
    委屈: '（；ω；）',
    困惑: '（・_・?）',
    关心: '（´･ω･`）'
  };

  function 标题(心情) {
    if (心情 === '恋人') return '小笨蛋 （◍•ᴗ•◍） 恋人';
    return '小笨蛋 ' + (情绪[心情] || 情绪.平静) + ' ' + 心情;
  }

  /* 头像：有自定义头像图就用，没有就画猫脸

     【两边的默认不同】
       她（ta）→ 个性化/她的头像.png（默认那张是从壁纸里裁的脸）
       我（wo）→ 个性化/我的头像.png（默认是几何人形，不是猫脸）
     两张都可能在，也可能被用户删掉 —— 404 就退回猫脸，不留破图标。
     为什么不再用"猫脸当默认"：用户说太幼稚了。 */
  /* 【头像缓存】文件名 → 时间戳。
     为什么要缓存这个：换头像后浏览器还拿着旧图（同一个 URL）。
     必须在 URL 后面挂 ?v=时间戳 才强制重取。

     【之前为什么"换完只有下一条变、再下一条又变回去"】
     造头像() 里根本没读 头像缓存 —— 它写的是固定路径
     `个性化/她的头像.png`，永远没有 ?v=。
     于是：
       · 刷头像() 把已有气泡换成带时间戳的新 URL —— 变了
       · 但下一条新消息走 造头像()，又用回裸路径 —— 浏览器给旧缓存
     两个函数各写一套 URL 拼法，必然分家。
     解法：URL 只在一个地方拼（这里），刷头像 和 造头像 都调它。 */
  var 头像缓存 = {};          /* 'ta'/'wo' → 时间戳 */

  function 头像地址(是我) {
    var 名 = 是我 ? '我的头像.png' : '她的头像.png';
    var v = 头像缓存[是我 ? 'wo' : 'ta'];
    return '个性化/' + encodeURIComponent(名) + (v ? '?v=' + v : '');
  }

  function 记头像时间戳(st) {
    /* st 是后端 tou_zhuang_tai() 的返回：{ta:{you,url}, wo:{...}} */
    if (!st) return;
    ['ta', 'wo'].forEach(function (k) {
      var x = st[k];
      if (!x) return;
      if (x.you && x.url) {
        /* 后端 url 形如 个性化/她的头像.png?v=1763...，把 v 抠出来 */
        var m = /[?&]v=(\d+)/.exec(x.url);
        头像缓存[k] = m ? m[1] : String(Date.now());
      } else {
        delete 头像缓存[k];       /* 没有自定义图 → 回到裸路径（走 onerror 出猫脸） */
      }
    });
  }

  function 造头像(是我) {
    var k = document.createElement('div');
    k.className = 'tou-xiang';
    k.dataset.shui = 是我 ? 'wo' : 'ta';

    var im = document.createElement('img');
    im.alt = '';
    im.src = 头像地址(是我);
    im.onerror = function () {
      im.remove();
      if (!k.querySelector('.mao-lian')) k.appendChild(猫脸(是我));
    };
    im.onload = function () {
      /* 换上新图之后把旧的猫脸撤掉 */
      var mao = k.querySelector('.mao-lian');
      if (mao) mao.remove();
    };
    k.appendChild(im);
    return k;
  }

  /* 外部（个性化页）换完头像调一次，把已画出来的全部刷新。
     顺带把时间戳记进 头像缓存 —— 这样**之后新来的消息**也用新图，
     不然会出现"这条换了、下一条又变回去"。 */
  function 刷头像(st) {
    st = st || {};
    记头像时间戳(st);
    var 所有 = document.querySelectorAll('#liao-tian .tou-xiang');
    for (var i = 0; i < 所有.length; i++) {
      var 是我 = (所有[i].dataset.shui || 'ta') === 'wo';
      var x = st[是我 ? 'wo' : 'ta'] || {};
      /* 清空重画，走和 造头像() 完全一样的路径，避免两套逻辑又不一致 */
      所有[i].innerHTML = '';
      if (x.you && x.url) {
        var im = document.createElement('img');
        im.alt = '';
        im.src = 头像地址(是我);
        im.onerror = function () {
          /* 用闭包变量会有循环引用问题，这里靠 dataset 反查 */
        };
        所有[i].appendChild(im);
      } else {
        所有[i].appendChild(猫脸(是我));
      }
    }
  }

  function 猫脸(是我) {
    var lian = document.createElement('div');
    lian.className = 'mao-lian';
    lian.innerHTML =
      '<div class="lian"></div>' +
      '<div class="er zuo"></div><div class="er you"></div>' +
      '<div class="yan zuo"></div><div class="yan you"></div>' +
      '<div class="zui"></div>';
    return lian;
  }

  /* 造一条消息 */
  function 造消息(kind, wenben, biaoti) {
    var hang = document.createElement('div');
    hang.className = 'xiao-xi ' + kind;
    if (biaoti) hang.classList.add('you-biao-ti');

    if (biaoti) {
      var t = document.createElement('div');
      t.className = 'biao-ti';
      t.textContent = biaoti;
      hang.appendChild(t);
    }

    /* 自定义头像：她那张可能不存在，浏览器 404 时自动退回猫脸 */
    hang.appendChild(造头像(kind === 'wo'));

    var pao = document.createElement('div');
    pao.className = 'qi-pao ' + 样式类(当前样式, kind);

    /* 三层：耳朵/爪子（z0）→ 身子（z1）→ 文字（z2） */
    var er1 = 造耳朵('zuo');
    var er2 = 造耳朵('you');
    var zhua1 = document.createElement('span');
    zhua1.className = 'qp-zhua zuo';
    var zhua2 = document.createElement('span');
    zhua2.className = 'qp-zhua you';
    var shen = document.createElement('div');
    shen.className = 'qp-shen';
    var wen = document.createElement('span');
    wen.className = 'qp-wen';
    wen.textContent = wenben;

    pao.appendChild(er1);
    pao.appendChild(er2);
    pao.appendChild(zhua1);
    pao.appendChild(zhua2);
    pao.appendChild(shen);
    pao.appendChild(wen);

    hang.appendChild(pao);
    return hang;
  }

  /* 一只耳朵：26×14 的 SVG。
     路径不是手画的 —— 是把旧版 qipao_tu() 那 6 个控制点按 Tk 的
     smooth=True（二次 B 样条）数学转换成的贝塞尔。
     Tk 的平滑规则：相邻两点的中点之间走曲线、原控制点作把手。 */
  function 造耳朵(ce) {
    var s = document.createElement('span');
    s.className = 'qp-er ' + ce;

    var lu = 'M -11.20 -4.06 ' +
      'Q -8.12 -8.12 -4.48 -10.92 ' +
      'Q -0.84 -13.72 1.54 -13.79 ' +
      'Q 3.92 -13.86 5.88 -10.85 ' +
      'Q 7.84 -7.84 10.78 -3.92 ' +
      'Q 13.72 0.00 -0.28 0.00 ' +
      'Q -14.28 0.00 -11.20 -4.06 Z';

    /* 内耳：旧版是硬三角（没走 smooth），掺 52% 白 */
    var nei = 'M -8.12 -2.20 L 1.40 -7.70 L 7.56 -2.20 Z';

    var fan = (ce === 'zuo') ? '' : ' transform="scale(-1,1)"';
    s.innerHTML =
      '<svg viewBox="-15 -15 30 16" width="26" height="14" ' +
      'style="overflow:visible;display:block">' +
      '<path class="er-wai" d="' + lu + '"' + fan + '/>' +
      '<path class="er-nei" d="' + nei + '"' + fan + '/>' +
      '</svg>';
    return s;
  }

  function 样式类(n, kind) {
    var ji = ['mao', 'yuan', 'tou-guang'][n] || 'mao';
    return ji + (kind === 'wo' ? ' wo' : ' ta');
  }

  /* 表情图：不套气泡，靠左贴一条（旧版 BQ_GAO=148） */
  function 造表情(文件) {
    if (!文件) return null;
    var d = document.createElement('div');
    d.className = 'biao-qing';
    var img = document.createElement('img');
    img.src = 表情根 + 文件;
    img.alt = '';
    img.onerror = function () { d.remove(); };
    d.appendChild(img);
    return d;
  }

  /* ---------------- 对外 ---------------- */
  function 加消息(kind, wenben, biaoti) {
    var el = 造消息(kind, wenben, biaoti || '');
    区.appendChild(el);
    滚到底();
    return el;
  }

  /* 表情图：不套气泡，靠左贴一条（旧版 BQ_GAO=148） */
  function 加表情(文件) {
    var d = 造表情(文件);
    if (d) {
      区.appendChild(d);
      滚到底();
    }
  }

  function 滚到底() {
    /* 下一帧再滚，等图片解码完高度才准 */
    requestAnimationFrame(function () {
      区.scrollTop = 区.scrollHeight;
    });
  }

  function 清空() {
    区.innerHTML = '';
  }

  function 换样式(n) {
    当前样式 = n;
    var 所有 = 区.querySelectorAll('.qi-pao');
    for (var i = 0; i < 所有.length; i++) {
      var p = 所有[i];
      var 是wo = p.classList.contains('wo');
      p.className = 'qi-pao ' + 样式类(n, 是wo ? 'wo' : 'ta');
    }
    if (n === 2) 算透光字色();
    Qiao.存样式(n);
  }

  /* 旧版 _di_wen_se：取气泡身后那块的平均亮度，>108 用深字。
     新版没法跨域取像素，改用整窗平均亮度预判（壁纸是同一张）。 */
  function 算透光字色() {
    var 所有 = 区.querySelectorAll('.qi-pao.tou-guang');
    /* 实测这张壁纸对话区亮度 78 < 108 → 浅字。写死比每次猜稳。 */
    for (var i = 0; i < 所有.length; i++) {
      所有[i].classList.remove('liang');
    }
  }

  /* ---------------- 启动 ---------------- */
  function 启动() {
    当前样式 = Qiao.读样式();
    同步样式按钮();

    /* 【先拉头像状态】否则 头像缓存 是空的，开场那几条用裸路径；
       用户换过头像又重启程序时，历史消息会显示旧图（浏览器缓存）。 */
    try {
      Promise.resolve(Qiao.头像状态()).then(function (st) {
        记头像时间戳(st);
        /* 已经画出来的（开场那几条）用新时间戳重画一遍 */
        刷头像(st || {});
      });
    } catch (e) {
      console.warn('[chat] 拉头像状态失败', e);
    }

    /* 问 Python 要开场：有存档就恢复，没有就摆开场白 */
    Promise.resolve(Qiao.开场()).then(function (r) {
      if (!r) {
        加消息('ta', '（拉了拉深色的兜帽）……你来了。', 标题('平静'));
        return;
      }
      if (r.duihua && r.duihua.length) {
        /* 恢复历史：每条 [who, text, title] */
        for (var i = 0; i < r.duihua.length; i++) {
          var x = r.duihua[i];
          加消息(x[0] === 'wo' ? 'wo' : 'ta', x[1], x[2] || '');
        }
      } else if (r.kai) {
        /* 第一次打开：她说引导语（问名字），下面挂一张引导卡。
           不是弹窗 —— 弹窗会挡住界面，而且用户第一反应是找关闭按钮。 */
        var 引导 = r.yin_dao;
        加消息('ta', (引导 && 引导.wen) || r.kaichang || '……你来了。',
               标题('平静'));
        加表情('平静.png');
        if (引导) 摆引导卡(引导);
      }
      if (r.zhuangtai) 刷顶栏(r.zhuangtai);
    }).catch(function (e) {
      console.error('[chat] 开场失败', e);
      加消息('ta', '（拉了拉深色的兜帽）……你来了。', 标题('平静'));
    });
  }

  /* ================= 首次引导卡 =================
     两件事要一次问清：他叫什么（记忆的种子）、有没有填 API 钥匙。
     不做成弹窗：弹窗会挡住界面，用户第一反应是找关闭按钮，
     而不是读内容。做成聊天区里的一张卡，跟着对话走。 */
  function 摆引导卡(引导) {
    var 卡 = document.createElement('div');
    卡.className = 'yin-dao';

    var 内 = '<div class="yd-biao">先认识一下</div>';

    if (引导.yao_ming) {
      内 += '<div class="yd-shuo">告诉我你叫什么，我记着 —— ' +
            '以后不用每次重新自我介绍。</div>' +
            '<div class="yd-hang">' +
            '<input class="yd-in" id="yd-ming" maxlength="12" ' +
            'placeholder="比如：小裴">' +
            '<button class="yd-an" id="yd-ming-qu">好</button>' +
            '</div>';
    }

    if (引导.yao_yao) {
      内 += '<div class="yd-fen"></div>' +
            '<div class="yd-shuo">' +
            '现在的我只会背台词。填一个 API 钥匙（DeepSeek，几毛钱能用很久），' +
            '我才能真正跟你聊天、看书、写东西。<br>' +
            '<span class="yd-xiao">在「☰ 功能 → 灵光」里填，也可以先跳过。</span></div>' +
            '<div class="yd-hang"><button class="yd-an ci" id="yd-qu-lingguang">' +
            '去填钥匙</button></div>';
    }

    卡.innerHTML = 内;
    区.appendChild(卡);
    滚到底();

    var 名框 = 卡.querySelector('#yd-ming');
    var 名钮 = 卡.querySelector('#yd-ming-qu');

    function 交名字() {
      var v = (名框 && 名框.value || '').trim();
      if (!v) return;
      Promise.resolve(Qiao.记名字(v)).then(function () {
        卡.querySelector('.yd-biao').textContent = '记住了';
        卡.querySelector('.yd-shuo').textContent =
          '好，' + v + '。以后我就这么叫你。';
        名框.remove();
        名钮.remove();
        加消息('ta', '（把这个名字在心里念了一遍）' + v + '……嗯，记住了。',
               标题('平静'));
      });
    }
    if (名框) {
      名框.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') 交名字();
      });
    }
    if (名钮) 名钮.addEventListener('click', 交名字);

    var 去钮 = 卡.querySelector('#yd-qu-lingguang');
    if (去钮) {
      去钮.addEventListener('click', function () {
        if (window.GongNeng) GongNeng.开('lingguang');
      });
    }
  }

  /* 顶栏：五颗心 + 状态字（旧版 _buju_ding 那两样） */
  function 刷顶栏(z) {
    if (!z) return;
    var xin = document.querySelectorAll('#xin-zu i');
    var n = z.xin || 1;
    for (var i = 0; i < xin.length; i++) {
      var man = i < n;
      xin[i].classList.toggle('man', man);
      xin[i].textContent = man ? '♥' : '♡';
    }
    var el = document.getElementById('zhuang-tai');
    if (el && z.zhuangtai) el.textContent = z.zhuangtai;
    document.getElementById('xin-zu').title =
      '好感度 ' + z.haogan + '/100';
  }

  function 同步样式按钮() {
    var 钮 = document.querySelectorAll('#yang-shi button');
    for (var i = 0; i < 钮.length; i++) {
      钮[i].classList.toggle('on', parseInt(钮[i].dataset.yang, 10) === 当前样式);
    }
  }

  /* ---------------- 导出 ---------------- */
  window.LiaoTian = {
    加消息: 加消息,
    加表情: 加表情,
    清空: 清空,
    换样式: 换样式,
    滚到底: 滚到底,
    刷顶栏: 刷顶栏,
    刷头像: 刷头像,
    标题: 标题,
    取样式: function () { return 当前样式; }
  };

  Qiao.就绪后(启动);
})();
