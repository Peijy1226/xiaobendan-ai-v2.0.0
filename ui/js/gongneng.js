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
