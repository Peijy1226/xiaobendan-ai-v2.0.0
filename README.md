# 小笨蛋

**[English](README_EN.md)** · 中文

[![release](https://img.shields.io/github/v/release/Peijy1226/xiaobendanV2.0.0?cacheSeconds=3600)](https://github.com/Peijy1226/xiaobendanV2.0.0/releases)
[![license](https://img.shields.io/github/license/Peijy1226/xiaobendanV2.0.0)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4)](#)

一个住在电脑里的桌面角色。关掉窗口她还在托盘里待着，过一阵子自己会来找你说句话。

![演示](docs/demo.gif)

## 装

[Releases](https://github.com/Peijy1226/xiaobendanV2.0.0/releases) 里一个 zip，解压双击 `小笨蛋.exe`。不用装 Python，不用装运行库。

第一次打开她会问你叫什么。之后她记着。

不填 API 钥匙也能用——离线有 515 句语料，报时、算数、讲笑话、识图、整理文件都能跑。填个 DeepSeek 钥匙她才会真的聊天，几毛钱能聊几千句。

## 为什么会有这个

本来想做个"住在电脑里的角色"，不是助手，不是工具箱。

试过一堆聊天软件，都太工具了——问一句答一句，聊完就没了。我要的是那种：你昨天随口说了句在加班，第二天她会问"昨天几点睡的"。

所以记忆做得最久，其他都是围着它顺手加的。分两层：一套规则同步抽（名字、宠物、喜好、工作、住处，10 毫秒出结果），抽不到再后台叫模型（1.2 秒）。规则抽到了就不调模型，不然每句话多花一分钱和 1 秒。

## 她能干什么

**聊天**。联网时真接话，离线走 515 句语料。报时、算数、讲笑话、换算、识图、整理文件这些不联网也能干，只有闲聊天要钥匙。

**记住你**。名字、养的猫、喜欢什么、干什么工作、住哪儿。跨会话。你上次说在加班，下次她可能问一句"昨天几点睡的"。

**主动说话**。一阵子没聊她冒一句。藏托盘里就说不了话，改发系统通知。

**念出来、听你说**。顶栏那个 🔊 让她把话念出来，edge-tts 合成，按标点切段边播边下，首声不到一秒。输入框右边 🎤 按住说话，Vosk 本地识别，不联网、不上传。

**看图**。给她一张图，能提字、能认人脸上有几个、能认出来是什么东西。大图先缩再检测，七千像素的照片也不会把内存吃爆。

**写东西**。记叙、议论、说明、书信，按字数档位给提示词，三百字和三千字不是一个写法。

**整理文件**。挑个文件夹，按类型分组，白名单外的目录不动。

**换壁纸**。视频壁纸会一直播，不是一张静图。自己拖进 `ui/素材/壁纸/` 也行。

**调界面**。字体 12~20，三套气泡，功能页四个模糊滑块，拖到哪看到哪。

## 关窗口她去哪了

藏到右下角托盘，不占地方，但定时的话、主动消息照常。图标双击唤回来，右键「让她说句话」会主动冒一句。

托盘是本机注册的图标，重启资源管理器之后会自动重挂一次；如果哪天右下角找不到了，「功能 → 关于」底部有个「彻底退出小笨蛋」，不走托盘也能干净退出。

## 三套气泡

猫耳、圆角、透光。

透光那套用真 `backdrop-filter`，壁纸一动它就跟着动，不是贴图。

猫耳那套的耳朵是 SVG，路径不是手画的——是把 Tkinter 版 `create_polygon(smooth=True)` 的 6 个控制点按二次 B 样条转成的贝塞尔，六条曲线拼一只耳朵。

## 界面怎么调的

功能 → 个性化，四个滑块：

- **模糊**：0~80 px
- **颜色浓度**：saturate 1.0~2.0
- **亮度**：brightness 0.70~1.40
- **底色厚度**：alpha 0~0.80

拖的时候实时生效，松手才写盘。存 `ui/个性化/玻璃.txt`，四个整数。

默认值 blur 22、底 0.26、亮 1.12 —— 这个组合是在帮助页文字上实测挑的：透亮度 5.8，文字对比度 20,271，面板既透得过壁纸又压得住字。

## 技术栈

| 层 | 用什么 |
|---|---|
| 界面 | 原生 HTML/CSS/JS + WebView2 |
| 窗口 | pywebview 6.2，无边框自绘标题栏 + DWM 系统圆角 |
| 图像 | OpenCV 5 + onnxruntime + RapidOCR |
| 语音合成 | edge-tts |
| 语音识别 | Vosk 中文小模型（42 MB，本地、不联网） |
| 托盘 | pystray |
| 打包 | PyInstaller |

**为什么没用 Electron**：一个 Electron 壳就 150 MB 起步，而这个程序的体积本来就在模型和 opencv 上。WebView2 是 Windows 自带的，零成本。

---

# 开发备忘

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
python -m PyInstaller 打包.spec --noconfirm
```

产物 416 MB。**大头不是我的代码**：

| 什么 | 多大 |
|---|---|
| opencv（`cv2.pyd`） | 82 MB |
| Vosk 中文模型 | 66 MB |
| yolox onnx | 35 MB |

我的代码加起来不到 1 MB。

打包完记得手动 `cp -r ui dist/小笨蛋/` —— ui 不打进 exe，为的是用户能自己换壁纸贴表情。

## 改她的性格

`ui/人设.txt`，改完重启生效。

里面写着：她是谁、说话什么调子、哪些话题不接、遇到不认识的怎么糊过去。提示词是按这个文件拼的，改一行就换一种人。

## 加台词

`ui/语料/*.txt`，一行一句。启动时全部读进内存，515 句现在只占几十 KB，加几千句也不卡。

## 换表情

`ui/表情/灵光/` 和 `ui/表情/离线/`，文件名就是心情：平静、开心、兴奋、得意、委屈、困惑、关心。多了会自动认，缺了就不显示。

## 发布

打 tag 推上去，GitHub Actions 会自动在 Windows 机器上编译并挂到 Release：

```bash
git tag v2.1.0
git push origin v2.1.0
```

配置在 `.github/workflows/build.yml`，约 10 分钟出包。

---

## License

MIT
