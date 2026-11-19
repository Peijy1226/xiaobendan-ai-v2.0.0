/* ============================================================================
   gongneng.js —— 功能页 13 项

   旧版是 PIL 画在 Canvas 上再贴过去（GongNengYe，3939 行），
   因为 Tk 的控件做不出毛玻璃。新版是 DOM，毛玻璃、动画、滚动条全是浏览器
   原生能力，代码量从 3939 行降到 400 行上下。

   13 项照旧版 GN_NEI_RONG 的顺序，一个字没改：
     计算与换算 / 识图 / 写一篇 / 整理助手 / 打赏 / 壁纸 / 字体大小 /
     个性化 / 灵光 / 记忆 / 忘记我吧 / 帮助 / 关于
   ========================================================================== */

(function () {
  'use strict';

  var 面板 = document.getElementById('gong-neng');
  var 菜单 = document.getElementById('gn-cai-dan');
  var 内容 = document.getElementById('gn-ye');
  var 标题 = document.getElementById('gn-biao');
  var 副标题 = document.getElementById('gn-fu');

  var 当前 = 'jisuan';
  var 状态 = {};          /* 各页的临时状态（输入框内容、选中的档位…） */

  /* ---------------- 13 项定义 ----------------
     副标题照旧版 GN_NEI_RONG 的说明写。图标用内联 SVG，不引外部字体。 */
  /* 13 个描边图标。全部 17×17 viewBox，stroke 由 CSS 统一给（1.55px）。
     为什么不用字体图标：那要引外部字体，打包多一份风险；
     为什么不用 emoji：颜色不受控、各家渲染还不一样。 */
  var TU = {
    jisuan:
      '<svg viewBox="0 0 20 20"><rect x="3.5" y="2.5" width="13" height="15" rx="2.6"/>' +
      '<path d="M6.6 6.2h6.8"/><path d="M7 10h.01"/><path d="M10 10h.01"/>' +
      '<path d="M13 10h.01"/><path d="M7 13.4h.01"/><path d="M10 13.4h.01"/>' +
      '<path d="M13 13.4h.01"/></svg>',
    shitu:
      '<svg viewBox="0 0 20 20"><rect x="2.6" y="4" width="14.8" height="12" rx="2.4"/>' +
      '<circle cx="7.1" cy="8.2" r="1.35"/>' +
      '<path d="M2.9 13.9l3.5-3.1a1.6 1.6 0 0 1 2.1 0l4.9 4.4"/>' +
      '<path d="M12.2 11.4l1.7-1.5a1.6 1.6 0 0 1 2.1 0l1.4 1.3"/></svg>',
    xiezuo:
      '<svg viewBox="0 0 20 20"><path d="M13.4 3.1l3.5 3.5"/>' +
      '<path d="M14.9 1.6a1.7 1.7 0 0 1 2.4 2.4L7.5 13.8 3 15.3l1.5-4.5z"/>' +
      '<path d="M3.4 17.2h13.2"/></svg>',
    zhengli:
      '<svg viewBox="0 0 20 20"><path d="M2.7 6.2a2 2 0 0 1 2-2h2.3l1.6 2h6.7a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H4.7a2 2 0 0 1-2-2z"/>' +
      '<path d="M7 11.6h6"/></svg>',
    dashang:
      '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7.2"/>' +
      '<path d="M10 5.9l1.4 2.8 3.1.45-2.25 2.2.53 3.1L10 13l-2.78 1.45.53-3.1L5.5 9.15l3.1-.45z"/></svg>',
    beijing:
      '<svg viewBox="0 0 20 20"><rect x="2.6" y="3.4" width="14.8" height="13.2" rx="2.2"/>' +
      '<path d="M2.9 12.6l3.8-3.4a1.6 1.6 0 0 1 2.1 0l3.4 3"/>' +
      '<circle cx="13.6" cy="7.3" r="1.3"/></svg>',
    ziti:
      '<svg viewBox="0 0 20 20"><path d="M3.6 15.6L9 4.4l5.4 11.2"/>' +
      '<path d="M6 11.6h6"/><path d="M16.2 15.6h2"/>' +
      '<path d="M17.2 11.6v8"/></svg>',
    gexinghua:
      '<svg viewBox="0 0 20 20"><path d="M10 2.8l1.9 4.1 4.5.55-3.3 3.1.85 4.45L10 12.9l-3.95 2.1.85-4.45-3.3-3.1 4.5-.55z"/>' +
      '<circle cx="10" cy="10" r="1.1" class="dian"/></svg>',
    lingguang:
      '<svg viewBox="0 0 20 20"><path d="M10 2.4v3"/><path d="M10 14.6v3"/>' +
      '<path d="M2.4 10h3"/><path d="M14.6 10h3"/>' +
      '<path d="M4.9 4.9l2.1 2.1"/><path d="M13 13l2.1 2.1"/>' +
      '<path d="M15.1 4.9L13 7"/><path d="M7 13l-2.1 2.1"/>' +
      '<circle cx="10" cy="10" r="3.1"/></svg>',
    jiyi:
      '<svg viewBox="0 0 20 20"><path d="M17.2 9.4a7 7 0 0 1-7.5 6.9 7.6 7.6 0 0 1-2.5-.5L3 17.2l1.5-3.9A6.8 6.8 0 0 1 3 9.6a7 7 0 0 1 7-6.8 7 7 0 0 1 7.2 6.6z"/>' +
      '<path d="M7.2 9.6h5.6"/></svg>',
    qingkong:
      '<svg viewBox="0 0 20 20"><path d="M3.5 5.6h13"/>' +
      '<path d="M8 5.6V3.9a1.3 1.3 0 0 1 1.3-1.3h1.4A1.3 1.3 0 0 1 12 3.9v1.7"/>' +
      '<path d="M5.2 5.6l.8 10.1a2 2 0 0 0 2 1.9h4a2 2 0 0 0 2-1.9l.8-10.1"/>' +
      '<path d="M8.4 9v5.4"/><path d="M11.6 9v5.4"/></svg>',
    bangzhu:
      '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7.4"/>' +
      '<path d="M7.9 7.7a2.2 2.2 0 1 1 2.9 2.1c-.5.2-.8.7-.8 1.2v.7"/>' +
      '<circle cx="10" cy="14.3" r="0.9" class="dian"/></svg>',
    guanyu:
      '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7.4"/>' +
      '<path d="M10 9.2v5.1"/><circle cx="10" cy="6.2" r="0.95" class="dian"/></svg>'
  };

  var 项 = [
    { jian: 'jisuan', ming: '计算与换算', fu: '算数、单位、进制', tu: TU.jisuan },
    { jian: 'shitu', ming: '识图', fu: '提字、认人、认物、看穿搭', tu: TU.shitu },
    { jian: 'xiezuo', ming: '写一篇', fu: '记叙 / 议论 / 写景 / 书信', tu: TU.xiezuo },
    { jian: 'zhengli', ming: '整理助手', fu: '只移到回收站，默认关着', tu: TU.zhengli },
    { jian: 'dashang', ming: '打赏', fu: '七个档位，都是 token', tu: TU.dashang },
    { jian: 'beijing', ming: '壁纸', fu: '视频 / 图片 / 纯色', tu: TU.beijing },
    { jian: 'ziti', ming: '字体大小', fu: '无级调节，立刻生效', tu: TU.ziti },
    { jian: 'gexinghua', ming: '个性化', fu: '气泡样式、头像', tu: TU.gexinghua },
    { jian: 'lingguang', ming: '灵光', fu: '联网大模型，填钥匙即可', tu: TU.lingguang },
    { jian: 'jiyi', ming: '记忆', fu: '她记住的你', tu: TU.jiyi },
    { jian: 'qingkong', ming: '忘记我吧', fu: '清空对话和好感', tu: TU.qingkong },
    { jian: 'bangzhu', ming: '帮助', fu: '会什么、怎么用', tu: TU.bangzhu },
    { jian: 'guanyu', ming: '关于', fu: '版本与环境', tu: TU.guanyu }
  ];

  function 建菜单() {
    菜单.innerHTML = '';
    项.forEach(function (x) {
      var d = document.createElement('div');
      d.className = 'gn-xiang' + (x.jian === 当前 ? ' on' : '');
      d.dataset.jian = x.jian;
      d.innerHTML = '<span class="gn-tu">' + x.tu + '</span><span>' + x.ming + '</span>';
      d.addEventListener('click', function () { 切页(x.jian); });
      菜单.appendChild(d);
    });
  }

  function 切页(jian) {
    当前 = jian;
    var x = 项.filter(function (y) { return y.jian === jian; })[0] || 项[0];
    标题.textContent = x.ming;
    副标题.textContent = x.fu;
    var 全部 = 菜单.querySelectorAll('.gn-xiang');
    for (var i = 0; i < 全部.length; i++) {
      全部[i].classList.toggle('on', 全部[i].dataset.jian === jian);
    }
    内容.innerHTML = '';
    var 造 = 页[jian];
    if (造) 造(内容);
  }

  /* ---------------- 工具 ---------------- */
  function 造(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function 行() {
    var d = 造('div', 'gn-hang');
    for (var i = 0; i < arguments.length; i++) d.appendChild(arguments[i]);
    return d;
  }

  function 说明(html) { return 造('div', 'gn-shuo', html); }

  function 输入(占位, 值) {
    var i = 造('input', 'gn-in');
    i.type = 'text';
    i.placeholder = 占位 || '';
    if (值) i.value = 值;
    return i;
  }

  function 按钮(字, 点击, cls) {
    var b = 造('button', 'gn-an' + (cls ? ' ' + cls : ''), 字);
    if (点击) b.addEventListener('click', 点击);
    return b;
  }

  function 分段(选项, 当前值, 改) {
    var d = 造('div', 'gn-duan');
    选项.forEach(function (o) {
      var v = typeof o === 'string' ? o : o.v;
      var t = typeof o === 'string' ? o : o.t;
      var b = 造('button', v === 当前值 ? 'on' : '', t);
      b.dataset.v = v;
      b.addEventListener('click', function () {
        var 全 = d.querySelectorAll('button');
        for (var i = 0; i < 全.length; i++) 全[i].classList.toggle('on', 全[i] === b);
        改(v);
      });
      d.appendChild(b);
    });
    return d;
  }

  function 结果(父, 文, 类) {
    var d = 父.querySelector('.gn-jie');
    if (!d) {
      d = 造('div', 'gn-jie');
      父.appendChild(d);
    }
    d.className = 'gn-jie' + (类 ? ' ' + 类 : '');
    d.textContent = 文 || '';
    return d;
  }

  function 忙(父, 文) {
    var d = 父.querySelector('.gn-jie');
    if (!d) {
      d = 造('div', 'gn-jie');
      父.appendChild(d);
    }
    d.className = 'gn-jie';
    d.innerHTML = '<span class="gn-mang"></span>' + (文 || '处理中…');
    return d;
  }

  /* ================================================================
     ① 计算与换算
     旧版是把输入框填好、光标放过去，让用户按发送（走 shuohua 的算数路由）。
     新版同样：点「算」就直接把算式发给聊天，保持一致。
     ================================================================ */
  var 页 = {};

  页.jisuan = function (父) {
    父.appendChild(说明(
      '直接写算式就行，支持中文数字、括号、π、开方、阶乘、百分比。' +
      '单位换算和进制转换也在这条路上。'));

    var i = 输入('试试：128 * 7 + 根号 81，或者 2的10次方', 状态.jisuan || '');
    i.addEventListener('input', function () { 状态.jisuan = i.value; });
    i.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') 算();
    });

    function 算() {
      var t = i.value.trim();
      if (!t) return;
      发到聊天(t);
      关();
    }

    父.appendChild(行(i, 按钮('算', 算)));

    父.appendChild(说明(
      '也能直接问她：<code>1+1等于几</code> <code>帮我算 365 乘 24</code> ' +
      '<code>100 华氏度是多少摄氏度</code>'));
  };

  /* ================================================================
     ② 识图
     dev 版优先走多模态大模型（能看懂画面），没钥匙才退本地三个模型。
     ================================================================ */
  页.shitu = function (父) {
    父.appendChild(说明(
      '选一张图，能干四件事：<b>提字</b>（中英文都认）、' +
      '<b>认人</b>（画框）、<b>认物</b>（COCO 80 类）、<b>看穿搭</b>（描述衣着配色）。<br>' +
      '联网时优先让大模型看整张图；本地模型（RapidOCR + YuNet + YOLOX）作为降级。'));

    var 图框 = 造('div', 'gn-hang');
    var 左 = 造('div');
    左.style.cssText = 'display:flex;gap:9px;flex-wrap:wrap';
    图框.appendChild(左);
    父.appendChild(图框);

    var 预览 = 造('div');
    预览.id = 'gn-yu-lan';
    预览.innerHTML = '<div style="position:relative;display:inline-block">' +
      '<img alt=""><div id="gn-kuang-ceng"></div></div>';
    父.appendChild(预览);

    var 当前图 = null;
    var 按钮组 = {};

    function 选(tag) {
      var b = 按钮(tag, function () { 做(tag); }, 'ci');
      b.style.fontSize = '12.5px';
      左.appendChild(b);
      按钮组[tag] = b;
      return b;
    }

    选('选一张图');
    选('提字').disabled = true;
    选('认人').disabled = true;
    选('认物').disabled = true;
    选('看穿搭').disabled = true;

    var 选图 = 左.querySelector('button');

    选图.addEventListener('click', function () {
      忙(父, '等你选图…');
      Promise.resolve(Qiao.选图()).then(function (r) {
        if (!r || !r.ok) {
          结果(父, r && r.cuo ? r.cuo : '没选到图。', 'ruo');
          return;
        }
        当前图 = r;
        var img = 预览.querySelector('img');
        img.onload = function () {
          /* 图片按容器宽度缩放，框要按比例算 */
          画框([], r.w, r.h);
        };
        img.src = r.url;
        预览.classList.add('kai');
        结果(父, '已选：' + r.ming + '（' + r.w + '×' + r.h + '）', 'ruo');
        按钮组['提字'].disabled = false;
        按钮组['认人'].disabled = false;
        按钮组['认物'].disabled = false;
        按钮组['看穿搭'].disabled = false;
      }).catch(function (e) {
        结果(父, '选图失败：' + e, 'cuo');
      });
    });

    function 画框(框, gw, gh) {
      var 层 = 预览.querySelector('#gn-kuang-ceng');
      var img = 预览.querySelector('img');
      层.innerHTML = '';
      if (!框 || !框.length) return;
      var w = img.clientWidth, h = img.clientHeight;
      var sx = w / gw, sy = h / gh;
      框.forEach(function (b) {
        var d = 造('div', 'gn-kuang' + (b.ren ? ' ren' : ''));
        d.style.left = (b.x * sx) + 'px';
        d.style.top = (b.y * sy) + 'px';
        d.style.width = (b.w * sx) + 'px';
        d.style.height = (b.h * sy) + 'px';
        if (b.ming) d.appendChild(造('span', '', b.ming));
        层.appendChild(d);
      });
    }

    function 做(tag) {
      if (!当前图) return;
      if (tag === '选一张图') return;
      忙(父, tag === '看穿搭' ? '正在看…' : '正在认…');
      var 起 = Date.now();
      Promise.resolve(Qiao.识图(tag, 当前图.lu)).then(function (r) {
        var 秒 = ((Date.now() - 起) / 1000).toFixed(1);
        if (!r || !r.ok) {
          结果(父, (r && r.cuo ? r.cuo : '没认出来。') +
            '\n（%s 秒 · %s）' % (秒, (r && r.laiyuan) || '未知'), 'cuo');
          return;
        }
        画框(r.kuang || [], 当前图.w, 当前图.h);
        var 尾 = '\n────\n' + 秒 + ' 秒 · ' + (r.laiyuan || '');
        结果(父, (r.wen || '（没有任何结果）') + 尾);
      }).catch(function (e) {
        结果(父, '出错了：' + e, 'cuo');
      });
    }
  };

  /* ================================================================
     ③ 写一篇
     ================================================================ */
  页.xiezuo = function (父) {
    父.appendChild(说明(
      '选体裁、填题目。联网时由大模型写，没网就套模板（能交差，但不是"写"的）。'));

    var 体 = 状态.xz_ti || '随便';
    var 题 = 输入('题目，比如「秋天的傍晚」', 状态.xz_ti_mu || '');

    var 段 = 分段(['随便', '记叙', '议论', '写景', '书信'], 体, function (v) {
      体 = v;
      状态.xz_ti = v;
    });

    父.appendChild(行(造('div', 'gn-pian', '体裁'), 段));
    父.appendChild(行(造('div', 'gn-pian', '题目'), 题,
      按钮('写', function () {
        var t = 题.value.trim();
        if (!t) {
          结果(父, '先填个题目。', 'ruo');
          return;
        }
        状态.xz_ti_mu = t;
        忙(父, '正在写…');
        Promise.resolve(Qiao.写一篇(t, 体)).then(function (r) {
          if (!r || !r.ok) {
            结果(父, (r && r.cuo ? r.cuo : '没写成。'), 'cuo');
            return;
          }
          结果(父, (r.wen || '') + '\n────\n' + r.zi + ' 字 · ' + r.laiyuan);
        }).catch(function (e) { 结果(父, '出错：' + e, 'cuo'); });
      })));
  };

  /* ================================================================
     ④ 整理助手
     危险动作，默认关着，要先开开关。
     ================================================================ */
  页.zhengli = function (父) {
    var 开 = false;
    var 说 = 说明('');

    function 刷开() {
      Promise.resolve(Qiao.整理开关()).then(function (r) {
        开 = !!(r && r.kai);
        var 夹 = (r && r.jia) || '';
        说.innerHTML = 开
          ? '已开启。<b>只会扫这个文件夹：</b><br><code>' + 夹 + '</code><br>' +
            '只动文件，不动文件夹；只移到回收站，删错了能捞回来。' +
            '单次最多 10 个、合计 200 MB。'
          : '现在关着。整理助手会移动文件，所以默认不开，你点了才生效。<br>' +
            '开启后只扫<b>演示夹</b>，别处一律不动。';
      });
    }
    刷开();

    父.appendChild(说);

    var 开钮 = 按钮('', function () {
      Promise.resolve(Qiao.整理开关(!开)).then(function () { 刷开(); });
    });

    function 刷钮() { 开钮.textContent = 开 ? '关掉它' : '开启整理助手'; 开钮.className = 'gn-an' + (开 ? ' ci' : ''); }
    var 轮 = setInterval(function () { 刷钮(); if (!面板.classList.contains('kai')) clearInterval(轮); }, 400);
    刷钮();

    父.appendChild(行(开钮, 按钮('扫一下', function () {
      if (!开) { 结果(父, '先开开关。', 'ruo'); return; }
      忙(父, '正在扫…');
      Promise.resolve(Qiao.整理扫(状态.zl_leixing || '全部')).then(显示);
    }), 按钮('打开演示夹', function () { Qiao.整理打开夹(); }, 'ci')));

    var 类型 = 状态.zl_leixing || '全部';
    父.appendChild(行(造('div', 'gn-pian', '只看'),
      分段(['全部', '安装包', '文档', '图片', '压缩包'], 类型, function (v) {
        状态.zl_leixing = v;
      })));

    function 显示(r) {
      if (!r || !r.ok) {
        结果(父, (r && r.cuo ? r.cuo : '扫不出来。'), 'cuo');
        return;
      }
      if (!r.dong || !r.dong.length) {
        结果(父, r.tishi || '这个文件夹里没有可整理的东西。', 'ruo');
        return;
      }
      var 行们 = r.dong.map(function (x, i) {
        return (i + 1) + '. ' + x.ming + '   ' + (x.daxiao / 1048576).toFixed(2) + ' MB';
      });
      结果(父,
        '找到 ' + r.dong.length + ' 个，合计 ' +
        (r.zong / 1048576).toFixed(1) + ' MB：\n\n' + 行们.join('\n') +
        '\n\n（都会移到回收站，不是真删）');

      var 确认 = 按钮('全部移到回收站', function () {
        忙(父, '正在移…');
        Promise.resolve(Qiao.整理执行(r.dong.map(function (x) { return x.lu; }))).then(function (z) {
          if (!z || !z.ok) {
            结果(父, (z && z.cuo ? z.cuo : '没执行成功。'), 'cuo');
            return;
          }
          结果(父, '移走了 ' + z.cheng + ' 个。\n' + (z.beizhu || '') +
            '\n（在回收站里，随时能还原）');
        });
      }, 'xian');
      确认.style.marginTop = '10px';
      父.appendChild(确认);
    }
  };

  /* ================================================================
     ⑤ 打赏
     七个档位照旧版 DASHANG_DANG，只有 token，不是真钱。
     ================================================================ */
  页.dashang = function (父) {
    父.appendChild(说明(
      '打赏只加好感度，<b>不花真钱</b> —— 这里没有支付，纯玩笑。' +
      '档位和加的好感照旧版：1 token 加 2 点，1M token 加 20 点。'));

    var 档 = [
      ['1', '意思一下'], ['10', '随手'], ['100', '认真了'], ['1K', '大方'],
      ['10K', '有点夸张'], ['100K', '今天高兴'], ['1M', '这个数字只会在演示里出现']
    ];

    var 网 = 造('div');
    网.id = 'gn-dang';
    档.forEach(function (d) {
      var b = 造('div', 'gn-dang',
        '<span class="jia">' + d[0] + ' token</span>' +
        '<span class="fu">' + d[1] + '</span>');
      b.addEventListener('click', function () {
        忙(父, '她收下了…');
        Promise.resolve(Qiao.打赏(d[0])).then(function (r) {
          if (!r || !r.ok) { 结果(父, (r && r.cuo) || '没收下。', 'cuo'); return; }
          结果(父, r.wen + '\n────\n好感度 ' + r.haogan + '/100');
          if (window.LiaoTian) {
            LiaoTian.加消息('ta', r.wen, r.biao);
            if (r.tou) LiaoTian.加表情(r.tou);
            LiaoTian.刷顶栏(r.zhuangtai);
          }
        });
      });
      网.appendChild(b);
    });
    父.appendChild(网);
  };

  /* ================================================================
     ⑥ 壁纸
     ================================================================ */
  页.beijing = function (父) {
    父.appendChild(说明(
      '默认那条视频就是旧版用的 <code>xiaobendan.mp4</code>。' +
      '换成静态图或纯色都行，换完立刻生效，不用重启。'));

    var 网 = 造('div');
    网.id = 'gn-bizhi';
    父.appendChild(网);

    var 现有 = [
      { ming: '视频（默认）', lei: 'video', lu: '素材/壁纸/xiaobendan.mp4' },
      { ming: '首帧静图', lei: 'img', lu: '素材/壁纸/壁纸_首帧.jpg' }
    ];

    function 刷(选中) {
      网.innerHTML = '';
      现有.forEach(function (b, i) {
        var d = 造('div', 'gn-bz' + (选中 === b.lu ? ' on' : ''));
        if (b.lei === 'video') {
          d.innerHTML = '<video src="' + b.lu + '" muted loop autoplay playsinline></video>' +
            '<div class="tik">' + b.ming + '</div>';
        } else {
          d.innerHTML = '<img src="' + b.lu + '" alt=""><div class="tik">' + b.ming + '</div>';
        }
        d.addEventListener('click', function () {
          Qiao.换壁纸(b.lu, b.lei === 'video');
          刷(b.lu);
          结果(父, '换好了：' + b.ming);
        });
        网.appendChild(d);
      });
    }

    Promise.resolve(Qiao.当前壁纸()).then(function (r) {
      刷((r && r.lu) || 现有[0].lu);
    });

    父.appendChild(行(
      按钮('选一个视频或图片…', function () {
        Promise.resolve(Qiao.选壁纸()).then(function (r) {
          if (!r || !r.ok) return;
          现有.push({ ming: r.ming, lei: r.lei, lu: r.url });
          Qiao.换壁纸(r.lu, r.lei === 'video');
          刷(r.lu);
          结果(父, '换好了：' + r.ming + '\n（放在 ui/素材/壁纸/，下次还在）');
        });
      }),
      按钮('恢复默认', function () {
        Qiao.换壁纸(现有[0].lu, true);
        刷(现有[0].lu);
        结果(父, '已经换回默认视频。');
      }, 'ci')));
  };

  /* ================================================================
     ⑦ 字体大小
     ================================================================ */
  页.ziti = function (父) {
    父.appendChild(说明('无级调，拖一下就变。改的是整个界面的基准字号，存着下次还在。'));

    var 值 = parseInt(localStorage.getItem('ziti') || '15', 10);
    var 滑 = 造('input');
    滑.type = 'range';
    滑.id = 'gn-ziti-hua';
    滑.min = '12';
    滑.max = '20';
    滑.step = '0.5';
    滑.value = String(值);

    var 样 = 造('div', 'gn-ziti-shi',
      '她说话是这个大小。晚上风凉，记得把窗关上。');
    样.style.fontSize = 值 + 'px';

    滑.addEventListener('input', function () {
      var v = parseFloat(滑.value);
      样.style.fontSize = v + 'px';
      设字号(v);
    });
    滑.addEventListener('change', function () {
      localStorage.setItem('ziti', 滑.value);
    });

    父.appendChild(行(滑));
    父.appendChild(样);
    父.appendChild(说明('范围 12 到 20，默认 15（和旧版 Tk 11 点一个大小）。'));

    var 钮 = 造('div', 'gn-hang');
    钮.style.marginTop = '14px';
    钮.appendChild(按钮('恢复 15', function () {
      滑.value = '15';
      样.style.fontSize = '15px';
      设字号(15);
      localStorage.setItem('ziti', '15');
    }, 'ci'));
    父.appendChild(钮);
  };

  function 设字号(v) {
    document.documentElement.style.setProperty('--zt', v + 'px');
    document.documentElement.style.setProperty('--hang', Math.round(v / 15 * 20) + 'px');
  }

  /* ================================================================
     ⑧ 个性化
     ================================================================ */
  页.gexinghua = function (父) {
    父.appendChild(说明('三样：气泡样式、她的头像、你的头像。改完立刻生效，不用重启。'));

    /* ---------- ① 气泡样式：三个可点的预览块 ---------- */
    父.appendChild(造('div', 'gn-pian', '气泡样式'));
    var 样式盒 = 造('div');
    样式盒.id = 'gn-yang-shi';
    父.appendChild(样式盒);

    var 名 = ['猫耳', '圆角', '透光'];
    var 当前 = LiaoTian.取样式();

    function 画样式() {
      样式盒.innerHTML = '';
      名.forEach(function (n, i) {
        var d = 造('div', 'gn-yang' + (i === 当前 ? ' on' : ''));
        d.dataset.i = i;
        /* 预览用小尺寸复刻三套真样式：猫耳有耳朵、圆角是圆块、透光是半透 */
        d.innerHTML =
          '<div class="gn-yu ' + ['mao', 'yuan', 'tou'][i] + '">' +
          '<span class="gn-yu-tou"></span>' +
          '<span class="gn-yu-pao"></span>' +
          '</div>' +
          '<span class="gn-yang-ming">' + n + '</span>';
        d.addEventListener('click', function () {
          当前 = i;
          LiaoTian.换样式(i);
          var 全 = document.querySelectorAll('#yang-shi button');
          for (var k = 0; k < 全.length; k++) {
            全[k].classList.toggle('on', parseInt(全[k].dataset.yang, 10) === i);
          }
          画样式();
        });
        样式盒.appendChild(d);
      });
    }
    画样式();

    /* ---------- ② 双头像 ---------- */
    var 头像标题 = 造('div', 'gn-pian', '头像');
    头像标题.style.marginTop = '18px';
    父.appendChild(头像标题);
    var 头盒 = 造('div');
    头盒.id = 'gn-tou-xiang';
    父.appendChild(头盒);

    function 画头像() {
      Promise.resolve(Qiao.头像状态()).then(function (r) {
        r = r || {};
        头盒.innerHTML = '';
        [['ta', '她的', '她说话时左边那个'],
         ['wo', '你的', '你说话时右边那个']].forEach(function (x) {
          var shui = x[0], biao = x[1], zhu = x[2];
          var st = r[shui] || { you: false, url: '' };

          var d = 造('div', 'gn-tou-ka');
          var 图 = 造('div', 'gn-tou-yuan');
          图.innerHTML = st.you && st.url
            ? '<img src="' + st.url + '" alt="">'
            : '<span>' + (shui === 'ta' ? '她' : '我') + '</span>';
          d.appendChild(图);

          var 右 = 造('div', 'gn-tou-you');
          右.appendChild(造('div', 'gn-tou-biao', biao + '头像'));
          右.appendChild(造('div', 'gn-tou-zhu', zhu));
          var 钮 = 造('div', 'gn-tou-niu');
          钮.appendChild(按钮('换一张', function () {
            打开选图(shui);
          }));
          if (st.you) {
            钮.appendChild(按钮('恢复默认', function () {
              Promise.resolve(Qiao.删头像(shui)).then(function () {
                画头像();
                刷新聊天头像();
              });
            }, 'ci'));
          }
          右.appendChild(钮);
          d.appendChild(右);
          头盒.appendChild(d);
        });
      });
    }

    function 打开选图(shui) {
      Promise.resolve(Qiao.选头像(shui)).then(function (r) {
        if (!r || !r.ok) {
          if (r && r.cuo) 结果(父, r.cuo, 'ruo');
          return;
        }
        画头像();
        刷新聊天头像();
        结果(父, '换好了。聊天气泡里的头像也一起变了。');
      });
    }

    /* 让聊天区已经画出来的头像也立刻换 —— 不刷新的话要等下一句才变 */
    function 刷新聊天头像() {
      Promise.resolve(Qiao.头像状态()).then(function (r) {
        if (window.LiaoTian && LiaoTian.刷头像) LiaoTian.刷头像(r);
      });
    }

    画头像();
    父.appendChild(说明(
      '建议用 1:1 的方形图，长图会自动居中裁方。' +
      '存成 256×256 放在 <code>ui/个性化/</code>。'));

    /* ---------- ③ 功能页的通透度（可调模糊） ---------- */
    var 玻璃标题 = 造('div', 'gn-pian', '功能页的通透度');
    玻璃标题.style.marginTop = '20px';
    父.appendChild(玻璃标题);

    父.appendChild(说明(
      '调的是点开「☰ 功能」时那块玻璃面板。<b>拖动立刻生效</b> —— ' +
      '先打开一次功能页，再回来拖滑块，能直接看见变化。'));

    var 玻璃盒 = 造('div', 'gn-boli');
    父.appendChild(玻璃盒);

    /* 四个滑块：模糊 / 饱和 / 亮度 / 底色浓度
       每个都是 0~100 的百分比，存到 Python 那边再换成真实单位。 */
    /* 【单位换算，别搞混】
       滑块统一 0~100（好拖），后端存的是真实单位：
         mo    0~80 px
         bao   100~260（saturate 的百分比）
         liang 70~140（brightness 的百分比）
         di    0~80（底色的百分之一，19 = 0.19）
       所以三个方向各有一对换算，写错了就会"滑到底却看不出来"。 */
    var 条 = [
      { jian: 'mo', ming: '模糊',
        bian: function (v) { return Math.round(v * 0.8) + 'px'; },
        去: function (v) { return Math.round(v * 0.8); },
        回: function (v) { return Math.min(100, Math.round(v / 0.8)); } },
      { jian: 'bao', ming: '颜色浓度',
        bian: function (v) { return (1 + v / 100).toFixed(2); },
        去: function (v) { return 100 + Math.round(v); },
        回: function (v) { return Math.max(0, Math.round(v) - 100); } },
      { jian: 'liang', ming: '亮度',
        bian: function (v) { return (0.70 + v / 100).toFixed(2); },
        去: function (v) { return 70 + Math.round(v); },
        回: function (v) { return Math.max(0, Math.round(v) - 70); } },
      { jian: 'di', ming: '底色厚度',
        bian: function (v) { return (v / 100).toFixed(2); },
        去: function (v) { return Math.round(v); },
        回: function (v) { return Math.round(v); } }
    ];

    var 默认滑块 = { mo: 28, bao: 75, liang: 42, di: 26 };

    function 去默认(i) { return 条[i].去(默认滑块[条[i].jian]); }

    function 应用到页面(值) {
      /* 变量挂在 :root 上，功能页面板读的就是它 */
      var r = document.documentElement.style;
      r.setProperty('--boli-mo', (值.mo * 0.8) + 'px');
      r.setProperty('--boli-bao', (1 + 值.bao / 100).toFixed(2));
      r.setProperty('--boli-liang', (0.70 + 值.liang / 100).toFixed(2));
      r.setProperty('--boli-di', (值.di / 100).toFixed(2));
    }

    function 画滑块(值) {
      玻璃盒.innerHTML = '';
      条.forEach(function (x) {
        var hang = 造('div', 'gn-hua-hang');
        var 左 = 造('span', 'gn-hua-ming', x.ming);
        var 值文 = 造('span', 'gn-hua-zhi', x.bian(值[x.jian]));
        var hua = document.createElement('input');
        hua.type = 'range';
        hua.min = 0;
        hua.max = 100;
        hua.value = 值[x.jian];
        hua.className = 'gn-hua';
        hua.addEventListener('input', function () {
          值[x.jian] = parseInt(hua.value, 10);
          值文.textContent = x.bian(值[x.jian]);
          应用到页面(值);
        });
        /* 松手才存盘 —— 拖动过程中每帧写文件既慢又没必要 */
        hua.addEventListener('change', function () {
          /* 传回去的是「真实单位」，不是滑块位置 */
          Qiao.存玻璃(
            条[0].去(值.mo), 条[1].去(值.bao),
            条[2].去(值.liang), 条[3].去(值.di));
        });
        hang.appendChild(左);
        hang.appendChild(hua);
        hang.appendChild(值文);
        玻璃盒.appendChild(hang);
      });

      var 钮行 = 造('div', 'gn-hua-niu');
      钮行.appendChild(按钮('打开功能页试试', function () {
        在开 = true;
        切换();
      }, 'ci'));
      钮行.appendChild(按钮('恢复默认', function () {
        Promise.resolve(Qiao.重置玻璃()).then(function (r) {
          if (r && r.ok) {
            值 = { mo: 默认滑块.mo, bao: 默认滑块.bao,
                   liang: 默认滑块.liang, di: 默认滑块.di };
            画滑块(值);
            应用到页面(值);
          }
        });
      }, 'ci'));
      玻璃盒.appendChild(钮行);
    }

    /* 读现有值 → 先套到页面上（这样老用户一进来看到的就是自己上次调的） */
    Promise.resolve(Qiao.读玻璃()).then(function (v) {
      var 原始 = {
        mo: (v && v.mo != null) ? v.mo : 去默认(0),
        bao: (v && v.bao != null) ? v.bao : 去默认(1),
        liang: (v && v.liang != null) ? v.liang : 去默认(2),
        di: (v && v.di != null) ? v.di : 去默认(3)
      };
      /* 原始单位 → 滑块位置 */
      var 值 = {
        mo: 条[0].回(原始.mo),
        bao: 条[1].回(原始.bao),
        liang: 条[2].回(原始.liang),
        di: 条[3].回(原始.di)
      };
      应用到页面(值);
      画滑块(值);
    });
  };

  /* ================================================================
     ⑨ 灵光（联网）
     ================================================================ */
  页.lingguang = function (父) {
    父.appendChild(说明(
      '开着走联网大模型，关着走本地规则引擎（也就是旧版那套）。' +
      '<b>开发版建议一直开着</b>。'));

    var 说 = 说明('');
    说.id = 'gn-yao-shi';
    var 钥 = 输入('api key（sk- 开头）', '');
    钥.type = 'password';

    function 刷() {
      Promise.resolve(Qiao.灵光状态()).then(function (r) {
        r = r || {};
        if (!r.you_yao) {
          说.innerHTML = '还没填钥匙。填上就能用，存在 <code>ui/API.txt</code>，' +
            '不会上传到任何地方。<br>' +
            '去哪拿：<code>platform.deepseek.com</code> → API keys → 创建 → 复制。';
        } else {
          说.innerHTML = '钥匙已填，模型 <code>' + (r.moxing || '?') + '</code>。' +
            '现在是<b>' + (r.kai ? '开着' : '关着') + '</b>。';
          钥.value = '';
          钥.placeholder = '要换钥匙就填新的，不换留空';
        }
      });
    }
    刷();

    父.appendChild(说);
    父.appendChild(行(钥, 按钮('保存钥匙', function () {
      var k = 钥.value.trim();
      if (!k) { 结果(父, '钥匙是空的。', 'ruo'); return; }
      忙(父, '正在试…');
      Promise.resolve(Qiao.存钥匙(k)).then(function (r) {
        if (!r || !r.ok) { 结果(父, (r && r.cuo) || '存失败。', 'cuo'); return; }
        结果(父, '存好了。' + (r.shi ? '已经试通了一次。' : ''));
        刷();
      });
    })));

    var 开钮 = 按钮('', function () {
      Promise.resolve(Qiao.灵光状态()).then(function (r) {
        Promise.resolve(Qiao.开灵光(!(r && r.kai))).then(function () { 刷(); 刷钮(); });
      });
    });
    父.appendChild(行(开钮));

    function 刷钮() {
      Promise.resolve(Qiao.灵光状态()).then(function (r) {
        开钮.textContent = (r && r.kai) ? '关掉灵光' : '开启灵光';
        开钮.className = 'gn-an' + ((r && r.kai) ? '' : ' ci');
      });
    }
    刷钮();
  };

  /* ================================================================
     ⑩ 记忆
     ================================================================ */
  页.jiyi = function (父) {
    父.appendChild(说明('她从聊天里记下来的东西。记错了可以删，删了就不再提。'));

    var 列 = 造('div', 'gn-jiyi');
    父.appendChild(列);

    function 刷() {
      Promise.resolve(Qiao.记忆()).then(function (r) {
        列.innerHTML = '';
        var d = (r && r.dong) || {};
        var 有 = false;
        /* 按"身份 → 生活 → 口味 → 其他"的顺序显示，不跟着 JSON 顺序乱跳 */
        var 顺序 = ['名字', '生日', '工作', '住处', '家人', '宠物',
                   '喜欢', '讨厌', '怕', '习惯', '重要的事'];
        var 键 = 顺序.filter(function (k) { return d[k]; })
          .concat(Object.keys(d).filter(function (k) {
            return 顺序.indexOf(k) < 0 && k !== '更新' && d[k];
          }));
        键.forEach(function (k) {
          var v = d[k];
          if (!v) return;
          /* 「更新」是内部记账字段，不是记忆 —— 显示出来会让人以为记住了日期 */
          if (k === '更新') return;
          有 = true;
          列.appendChild(造('div', 'gn-jy',
            '<span class="biao">' + k + '</span><span class="zhi">' +
            String(v).replace(/[<>&]/g, function (c) {
              return { '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c];
            }) + '</span>'));
        });
        if (!有) {
          列.appendChild(造('div', 'gn-kong',
            '还没记住什么。聊几句「我叫什么」「我喜欢什么」，她就记住了。'));
        }
      });
    }
    刷();

    /* 后台补记完会派发这个事件 —— 不用用户手动点刷新 */
    document.addEventListener('jiyi-gengxin', 刷);

    父.appendChild(行(
      按钮('刷新', 刷, 'ci'),
      按钮('清空记忆', function () {
        忙(父, '清空中…');
        Promise.resolve(Qiao.清记忆()).then(function () { 刷(); 结果(父, '清空了。'); });
      }, 'xian')));

    父.appendChild(说明(
      '她只记你<b>明确说过</b>的事（名字、宠物、喜欢什么、在做什么）。' +
      '疑问和玩笑不记 —— 记错了比不记更伤人。<br>' +
      '档案在 <code>ui/记忆_重要的事.json</code>，可以自己打开看。'));
  };

  /* ================================================================
     ⑪ 忘记我吧
     ================================================================ */
  页.qingkong = function (父) {
    父.appendChild(说明(
      '会清掉：<b>所有对话记录</b>、<b>好感度</b>、<b>轮数</b>、<b>心情</b>。<br>' +
      '不会动：你的素材、壁纸、头像、记忆档案。<br>' +
      '<b>清掉之后找不回来。</b>'));

    var 确认 = 造('input');
    确认.type = 'checkbox';
    var 标 = 造('label');
    标.style.cssText = 'font-size:13px;color:var(--se-dan);display:flex;align-items:center;gap:7px';
    标.appendChild(确认);
    标.appendChild(document.createTextNode('我知道，清掉就找不回来了'));
    父.appendChild(行(标));

    var 钮 = 按钮('忘记我吧', function () {
      if (!确认.checked) {
        结果(父, '先勾一下上面那句。', 'ruo');
        return;
      }
      Promise.resolve(Qiao.清空()).then(function () {
        LiaoTian.清空();
        结果(父, '清空了。下次打开就是第一次见面。');
      });
    }, 'xian');
    父.appendChild(行(钮));
  };

  /* ================================================================
     ⑫ 帮助
     ================================================================ */
  页.bangzhu = function (父) {
    /* 帮助页分三块：会什么 / 怎么用 / 换素材。
       全部用 <br> 排版，不靠 \n —— 靠 \n 一改 CSS 就散架。 */
    父.appendChild(说明(
      '<b>直接说话就行</b>，她接得住。下面这些会走专门的工具：'));
    父.appendChild(造('div', 'gn-shuo', (function () {
      var 行 = [
        ['报时', '现在几点 / 今天几号 / 星期几'],
        ['算数', '1+1等于几 / 帮我算 365×24 / 2的10次方'],
        ['笑话', '讲个笑话 / 来个段子'],
        ['天气', '今天天气怎么样 / 明天会下雨吗（联网时给实时数据）'],
        ['美食', '中午吃什么 / 推荐点好吃的'],
        ['王者', '射手玩什么英雄 / 打野怎么出装']
      ];
      return 行.map(function (x) {
        return '<b>' + x[0] + '</b>　' + x[1];
      }).join('<br>');
    })()));

    父.appendChild(造('div', 'gn-shuo',
      '<b>快捷键</b>　Enter 发送 · 拖标题栏移动窗口 · 最小化在右上角<br>' +
      '<b>字号</b>　「字体大小」那页能拖，12 到 20<br>' +
      '<b>气泡</b>　顶栏三颗按钮，或「个性化」那页'));

    父.appendChild(造('div', 'gn-shuo',
      '<b>她记得你</b>　说过「我叫什么」「我喜欢什么」「我养了只猫」，' +
      '她自己会记下来，下次接着提。<br>' +
      '<b>好感度</b>　她越熟越放得开。满 100 会换成另一种语气。<br>' +
      '<b>换素材</b>　<code>ui/素材/</code> 放聊天语料，<code>ui/表情/</code> 放表情图，' +
      '<code>ui/语料/</code> 放自己写的句子。'));
  };

  /* ================================================================
     ⑬ 关于
     ================================================================ */
  页.guanyu = function (父) {
    /* 先摆骨架再异步填 —— 第一版直接等 Promise，点开有半秒空白，
       验收脚本在 0.32 秒时看到的就是空的。骨架还能当"正在读环境"的提示。 */
    var 框 = 说明(
      '<b>小笨蛋</b>　产品版<br>' +
      '壳：HTML + CSS + WebView2（无边框自绘）<br>' +
      '逻辑：旧版 21,255 行里抽出来的 7,637 行<br>' +
      '壁纸：视频 1280×720 / 30fps<br><br>' +
      '<span class="gn-mang"></span>正在读运行环境…');
    父.appendChild(框);

    Promise.resolve(Qiao.关于()).then(function (r) {
      r = r || {};
      框.remove();
      父.appendChild(说明(
        '<b>小笨蛋</b>　产品版<br>' +
        '壳：HTML + CSS + WebView2（无边框自绘）<br>' +
        '逻辑：旧版 21,255 行里抽出来的 7,637 行<br>' +
        '壁纸：视频 1280×720 / 30fps<br><br>' +
        '<b>运行环境</b><br>' +
        'Python　' + (r.python || '?') + '<br>' +
        'WebView2　' + (r.webview2 || '?') + '<br>' +
        '打包　' + (r.dabao ? '是' : '否（开发模式）') + '<br><br>' +
        /* 「能力」那行删了 —— 下面的自检区已经逐项列了，
           两处重复反而让人不知道该看哪个。 */
        '作者：Pei　·　这份程序只在这台电脑上。'));

      /* 自检：逐项列出来，一眼看出哪样不能用 */
      var 自检框 = 造('div');
      自检框.style.marginTop = '18px';
      自检框.appendChild(造('div', 'gn-pian', '自检'));
      父.appendChild(自检框);

      Promise.resolve(Qiao.自检()).then(function (z) {
        z = z || { xiang: [] };
        var 列 = 造('div');
        列.style.cssText = 'margin-top:8px;display:flex;flex-direction:column;gap:5px';
        (z.xiang || []).forEach(function (x) {
          var d = 造('div', 'gn-jy');
          d.innerHTML = '<span class="biao" style="color:' +
            (x.ok ? '#8be89b' : '#ffb8b8') + '">' +
            (x.ok ? '有' : '没') + '</span>' +
            '<span class="zhi">' + x.ming +
            '<span style="color:rgba(180,196,213,.5);font-size:11.5px">　' +
            String(x.xi || '').replace(/[<>&]/g, function (c) {
              return { '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c];
            }) + '</span></span>';
          列.appendChild(d);
        });
        自检框.appendChild(列);
      });

      /* ---------- 退出 ---------- */
      /* 【为什么这里必须有个退出按钮】
         托盘图标在 explorer 重启后会失效（图标从任务栏消失），
         但进程还活着。这时候关窗口只会藏起来，托盘又点不到 ——
         用户只能开任务管理器，这是设计缺陷。
         所以留一条不依赖托盘的退出路。 */
      var 退框 = 造('div');
      退框.style.marginTop = '20px';
      退框.appendChild(造('div', 'gn-pian', '退出'));
      退框.appendChild(说明(
        '托盘图标如果不见了（右下角找不到 ⚪），' +
        '点下面的按钮可以直接结束程序。'));
      var 退行 = 造('div', 'gn-hua-niu');
      退行.style.borderTop = 'none';
      退行.appendChild(按钮('彻底退出小笨蛋', function () {
        /* 二次确认 —— 误点就把她关了，回来得重新开 */
        if (!window.confirm('要关掉小笨蛋吗？\n\n她会先存好你们的对话，' +
                            '下次打开接着聊。')) return;
        Qiao.彻底退出();
        /* 界面会给 1.5 秒后硬退，这里先把按钮置灰免得连点 */
        setTimeout(function () {
          document.body.innerHTML =
            '<div style="height:100vh;display:flex;align-items:center;' +
            'justify-content:center;color:#8fa4bb;font:14px system-ui">' +
            '（她收拾东西去了……）</div>';
        }, 120);
      }, 'ci'));
      退框.appendChild(退行);
      父.appendChild(退框);
    });
  };

  /* ================================================================
     开关
     ================================================================ */
  function 开页(哪) {
    面板.classList.add('kai');
    建菜单();
    切页(哪 || 当前);
  }

  function 关() {
    面板.classList.remove('kai');
  }

  window.GongNeng = {
    开: 开页,
    关: 关,
    切换: function () {
      if (面板.classList.contains('kai')) 关();
      else 开页();
    },
    在开: function () { return 面板.classList.contains('kai'); }
  };

  /* 点遮罩空白处关 */
  面板.addEventListener('mousedown', function (e) {
    if (e.target === 面板) 关();
  });

  document.getElementById('gn-guan').addEventListener('click', 关);

  /* Esc 关 —— 旧版没有，但这是 WebView 里的常识 */
  window.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && 面板.classList.contains('kai')) {
      e.stopPropagation();
      关();
    }
  });

  /* 发到聊天：功能页里的"算"这种，直接把话送到输入框并发送 */
  function 发到聊天(t) {
    var 框 = document.getElementById('shu-ru');
    var 钮 = document.getElementById('fa-song');
    if (框 && 钮) {
      框.value = t;
      钮.click();
    }
  }

  /* 启动时把字号读回来 */
  (function () {
    var v = localStorage.getItem('ziti');
    if (v) 设字号(parseFloat(v));
  })();
})();
