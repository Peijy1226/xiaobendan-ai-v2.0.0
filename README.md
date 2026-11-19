# 小笨蛋

**[English](README_EN.md)** · 中文

[![release](https://img.shields.io/github/v/release/Peijy1226/xiaobendan?cacheSeconds=3600)](https://github.com/Peijy1226/xiaobendan/releases)
[![license](https://img.shields.io/github/license/Peijy1226/xiaobendan)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4)](#)

一个住在电脑里的桌面角色。关掉窗口她还在托盘里待着，过一阵子自己会来找你说句话。

![演示](docs/demo.gif)

## 装

[Releases](https://github.com/Peijy1226/xiaobendan/releases) 里一个 zip，解压双击 `小笨蛋.exe`。不用装 Python，不用装运行库。

第一次打开她会问你叫什么。之后她记着。

不填 API 钥匙也能用——离线有 515 句语料，报时、算数、讲笑话、识图、整理文件都能跑。想让她真会聊天就填个 DeepSeek 钥匙，几毛钱能聊几千句。

## 为什么会有这个

本来想做个"住在电脑里的角色"，不是助手，不是工具箱。

试过一堆聊天软件，都太工具了——问一句答一句，聊完就没了。我要的是那种：你昨天随口说了句在加班，第二天她会问"昨天几点睡的"。

所以记忆做得最久，其他都是围着它顺手加的。分两层：一套规则同步抽（名字、宠物、喜好、工作、住处，10 毫秒出结果），抽不到再后台叫模型（1.2 秒）。规则抽到了就不调模型，不然每句话多花一分钱和 1 秒。

## 她能干什么

| 能力 | 说明 | 要钥匙 |
|---|---|---|
| 聊天 | 联网接话；离线走 515 句语料 | 联网要 |
| 记住你 | 名字、宠物、喜好、工作、住处，跨会话 | 不用 |
| 主动说话 | 一阵子没聊她冒一句；藏托盘时发系统通知 | 不用 |
| 念出来 | 顶栏 🔊，edge-tts 合成 | 不用 |
| 听你说 | 输入框右边 🎤，按住说话，本地识别 | 不用 |
| 看图 | 提字（OCR）、认人（人脸）、认物 | 不用 |
| 写一篇 | 记叙 / 议论 / 说明 / 书信 | 要 |
| 整理文件 | 按类型把文件夹归类 | 不用 |
| 换壁纸 | 视频壁纸会一直动 | 不用 |
| 调界面 | 字体 12~20、三套气泡、功能页模糊四滑块 | 不用 |

## 关窗口她去哪了

藏到右下角托盘。图标双击唤回来，右键「让她说句话」会主动冒一句。

**托盘图标会失效**——它向 `explorer.exe` 注册，explorer 重启（装软件、崩了重开）之后注册就没了：图标从任务栏消失，但进程还在。这时关窗口只会藏起来，托盘又点不到。

踩过这个坑，现在是三重保险：

1. 后台每 30 秒看一眼图标句柄，丢了就重建
2. 「功能 → 关于」底部有个「彻底退出小笨蛋」，不走托盘
3. 退出流程末尾 1.5 秒兜底 `os._exit(0)`，不会被后台线程卡住

## 三套气泡

猫耳、圆角、透光。透光那套用真 `backdrop-filter`，壁纸一动它就跟着动（不是贴图）。

猫耳那套的耳朵是 SVG，路径不是手画的——是把 Tkinter 版 `create_polygon(smooth=True)` 的 6 个控制点按二次 B 样条转成的贝塞尔。

试着给气泡加过尾巴和耳朵动画。做了一周，六版尾巴，每一版都像虫子，用户原话"多渗人"。全删了。

## 界面怎么调的

功能 → 个性化，四个滑块：

- **模糊**：0~80 px
- **颜色浓度**：saturate 1.0~2.0
- **亮度**：brightness 0.70~1.40
- **底色厚度**：alpha 0~0.80

拖立刻生效，松手才写盘。存 `ui/个性化/玻璃.txt`，四个整数。

原来硬编码 42px。那个数是按"面板内外亮度差"选的——只量了透不透，没量糊不糊。用户说太糊，重新用帮助页文字当靶量了五档：

| 设置 | 透亮度 | 文字对比 |
|---|---|---|
| blur 42 底 0.19 | 4.4 | 18,297 |
| **blur 22 底 0.26 亮 1.12** | **5.8** | **20,271** |
| blur 18 底 0.34 亮 1.16 | 6.1 | 23,762 |

新默认比原来透亮度高 32%、文字可读性高 11%，还不像块板。

---

# 开发备忘

下面是给自己看的，怕两周后忘了。

## 代码结构

```
main.py              入口：窗口、DWM 圆角、托盘、主动消息定时器
api.py               前后端桥，53 个方法
core/
  luoji.py           逻辑层 7,700 行：对话、情绪、记忆、壁纸
  shitu.py           识图：OCR + 人脸 + 物体
  zhengli.py         整理助手
  xiezuo.py          写一篇
  dashang.py         打赏
  tuopan.py          托盘
  zhu_dong.py        主动消息 + 系统通知
  yuyin_shuru.py     语音输入（Vosk）
  models/            onnx 模型（不进仓库，跑 下载模型.py）
ui/
  index.html
  css/               base / titlebar / chat / input / gongneng
  js/                bridge / bishu / chat / gongneng / input
                     / yuyin（她说）/ yuyin_shuru（你听）
  素材/              壁纸、图标、示例素材
  表情/              29 张，按心情命名
  语料/              515 句离线台词
  个性化/            头像、气泡偏好
  人设.txt           ← 改她的性格
  API.txt            ← 你的钥匙（.gitignore 掉了）
下载模型.py
打包.spec
```

三层：页面（HTML/CSS/JS）→ 桥（`api.py` 每个方法对应前端一个 `Qiao.xxx()`）→ 逻辑（`core/luoji.py`）。

## 本地跑

```bash
pip install -r requirements.txt
python 下载模型.py
python main.py
```

`--debug` 开 F12，`--自检` 不开窗口只写环境清单。

`vendor/` 是我把 pystray / sounddevice / vosk 单独装的地方，为了系统 site-packages 干净。不是必须的，代码两个位置都找。要用就：

```bash
pip install --target vendor pystray sounddevice vosk srt requests tqdm
```

## 打包

```bash
D:/PyThon/python.exe -m PyInstaller 打包.spec --noconfirm
```

产物 416MB。**大头不是我的代码**：

| 什么 | 多大 |
|---|---|
| opencv（`cv2.pyd`） | 82 MB |
| Vosk 中文模型 | 66 MB |
| yolox onnx | 35 MB |

我的代码加起来不到 1 MB。

打包完记得手动 `cp -r ui dist/小笨蛋/` —— ui 不打进 exe，为的是用户能自己换壁纸贴表情。

## 几个坑

### Vosk 读不了中文路径

```python
vosk.Model(r"E:\AI\workbuddy2\小笨蛋\...")
# Failed to create a model
```

它的 C 库在 Windows 上用 ANSI 接口拼路径，非 ASCII 直接炸。

短路径（8.3 格式）、目录联接都试过，只有"复制到 `%TEMP%\xbd_vosk_stt`"能解决。每次启动检查一次，路径不对就重拷 66MB。

### PyInstaller 找不到 vendor 里的包

spec 顶部必须：

```python
sys.path.insert(0, _VENDOR)
```

并且加进 `pathex`。不然打包"成功"，exe 一跑就 ImportError。

### 托盘「退出」点了没反应

`chuang.destroy()` **也会触发 `closing` 事件**。我在 `closing` 里写了 `return False`（点 ✕ 要藏托盘），于是 destroy 被自己拦住：窗口没销毁、主循环还活着、进程不退出。

实测：点「退出」后日志只有一行 `closing 被触发`，然后什么都不发生。

修法是加个"正在真退出"的开关，托盘退出前置 True，`closing` 见到 True 就 `return True` 放行。

### JS 里判断标点别拼长字符串

```js
if ('，。！？、；：""''（）《》…— .,!?;:()\n\t'.indexOf(ch) >= 0)
```

那串里有中文弯引号，看着没问题。但**只要混进一个 ASCII 的 `'` 就提前闭合，整个文件语法废掉**。

症状是 `LiaoTian is not defined`，界面完全没反应，页面上没有任何报错。

改成对象表：`var 标点 = {'，': 1, '。': 1, ...}`，一个一个列。

### 换头像后新消息又变回旧图

两套 URL 拼法打架：

- `刷头像()` 用后端返回的 `?v=时间戳` → 换了
- `造头像()` 写死裸路径 `个性化/她的头像.png` → 浏览器给旧缓存

改完当时好了，下一条消息又变回去。修法是 URL 只在一个地方拼（`头像地址()`），两个函数都调它。

### 头像被放大了 26%

CSS 里有一行：

```css
.tou-xiang img { transform: scale(1.26) translateY(2%); }
```

本意是"用户传了全身照也能裁到脸"。但副作用是**所有**头像都被放大 26%，用户按 1:1 传的好图四周被裁掉，看着就"比例不对"。

而且 `tou_cun()` 存盘前已经居中裁成 1:1 了，这里再放大多余。删掉，只留 `object-fit: cover`。

### 删代码要检查被引用的函数

清理气泡特效时把 `加表情()` 一起删了。它被 `window.LiaoTian` 导出引用，结果整个聊天区空白、气泡 0 个。

**页面上没有任何报错**，因为 IIFE 里抛了异常被吞了。

现在改完 JS 都用 node 跑一遍假 DOM：

```js
const el = () => ({classList:{add(){},remove(){},toggle(){},contains(){return false}},...});
new Function('window','document','Qiao','requestAnimationFrame', src)(...);
console.log(typeof window.LiaoTian);   // 必须是 object
```

### 测试时残留进程坑死人

端口 42001 被上一个没退干净的 `小笨蛋.exe` 占着，新起的测试进程 load 的是**旧进程的 HTTP 服务**。

磁盘上文件明明改了，页面跑的却还是旧代码。查了半小时才发现。

测试前必须：

```bash
taskkill //F //IM 小笨蛋.exe
netstat -ano | grep LISTENING   # 确认没有旧端口
```

## 几个魔数

- **22px** 功能页模糊默认值。五档实测选的，见上面那张表
- **30 秒** 托盘图标巡检间隔
- **1.5 秒** 退出兜底硬退延迟
- **515** 离线语料句数
- **90** 逐字浮现的字数上限（这个特效已删，数字留着当参考）

## 已知问题

| 问题 | 为什么没修 |
|---|---|
| 天气接口连不上 | `open-meteo` 在某些网络握手超时，不是代码问题 |
| 语音识别准确率一般 | Vosk 小模型的极限。换大模型多 500MB，不值 |
| 没有单实例保护 | 开两个会抢 `ui/存档.json`。加个命名互斥体就行，懒得弄 |
| 没有代码签名 | 证书一年几百刀，一个免费小工具不值当 |
| 没有安装包 | 绿色文件夹解压即用。要做得上 Inno Setup |

## 想改但没改

- 气泡版式重做（QQ 那种更紧凑的）。一直想做，但这是纯审美问题，先放着
- 单实例保护
- 开机自启（加个计划任务就行）

---

## License

MIT
