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