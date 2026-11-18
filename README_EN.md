# 小笨蛋 (Little Dummy)

**English** · [中文](README.md)

[![release](https://img.shields.io/github/v/release/Peijy1226/xiaobendanV2.0.0?cacheSeconds=3600)](https://github.com/Peijy1226/xiaobendanV2.0.0/releases)
[![license](https://img.shields.io/github/license/Peijy1226/xiaobendanV2.0.0)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4)](#)

A character who lives on your computer. Close the window and she stays in the system tray. Leave her alone long enough and she'll come find you.

![demo](docs/demo.gif)

## Install

One zip in [Releases](https://github.com/Peijy1226/xiaobendanV2.0.0/releases). Unzip, double-click `小笨蛋.exe`. No Python, no runtime needed.

First launch she asks your name. She remembers it after that.

Works without an API key — 515 canned lines cover time, arithmetic, jokes, OCR, and file sorting. Add a DeepSeek key and she actually talks. Costs pennies for thousands of messages.

## Why this exists

I wanted a character who lives on the computer. Not an assistant, not a toolbox.

Every chat app I tried felt like a tool — ask, answer, forget. I wanted: you mention you're working late, and the next day she asks how late you slept.

So memory got the most work; everything else grew around it. Two layers: rules extract synchronously (name, pets, likes, job, city — 10ms), anything missed goes to the model in the background (1.2s). If the rules got it, the model isn't called — otherwise every message costs an extra cent and a second.

## What she does

**Chat.** Real replies when online, 515 canned lines offline. Time, arithmetic, jokes, unit conversion, OCR, file sorting all work without a key — only free-form conversation needs one.

**Remember you.** Your name, your cat, what you like, what you do, where you live. Across sessions. Mention you're working late and she might ask the next day how late you actually slept.

**Speak up.** Goes quiet for a while and she'll chime in. Hidden in the tray, she can't talk, so she sends a system notification instead.

**Read aloud, and listen.** The 🔊 in the title bar reads her lines out with edge-tts, splitting on punctuation and downloading while playing — first sound in under a second. The 🎤 next to the input is hold-to-talk, recognized locally by Vosk. No network, nothing uploaded.

**Look at images.** Hand her a picture: she pulls the text out, counts the faces, tells you what the object is. Large images get downscaled before detection, so a 7000-pixel photo won't blow up memory.

**Write.** Narrative, argumentative, expository, letters. Prompts shift by length tier — 300 words and 3000 words aren't the same task.

**Sort files.** Point her at a folder, she groups by file type. Anything outside the whitelist stays put.

**Change the wallpaper.** Video wallpapers keep playing — not a still frame. Drop your own into `ui/素材/壁纸/`.

**Tune the UI.** Font size 12–20, three bubble styles, four blur sliders on the features panel — drag and see it live.

## Where she goes when you close the window

Into the system tray. Doesn't take up space, timers and proactive messages keep running. Double-click the icon to bring her back; right-click → "let her say something" and she'll pipe up on her own.

The tray icon is registered locally and remounts itself after Explorer restarts. If it ever goes missing from the corner, Features → About has a "Quit completely" button that doesn't depend on the tray at all.

## Three bubble styles

Cat ears, rounded, and frosted glass.

The frosted one uses real `backdrop-filter` — the wallpaper moves and it moves with it, not a flat image.

The cat-ear ears are SVG. The path isn't hand-drawn: the 6 control points from the Tkinter version's `create_polygon(smooth=True)` were converted to Béziers via quadratic B-spline — six curves per ear.

## Tuning the UI

Features → Personalize, four sliders:

- **Blur**: 0–80 px
- **Saturation**: 1.0–2.0
- **Brightness**: 0.70–1.40
- **Tint opacity**: 0–0.80

Live while dragging, saved on release. Stored in `ui/个性化/玻璃.txt` as four integers.

The default — blur 22, tint 0.26, brightness 1.12 — came from measuring against the help page text: transparency 5.8, text contrast 20,271. The panel lets the wallpaper through without losing the letters.

## Stack

| Layer | What |
|---|---|
| UI | Plain HTML/CSS/JS + WebView2 |
| Window | pywebview 6.2, custom frameless title bar + DWM rounded corners |
| Imaging | OpenCV 5 + onnxruntime + RapidOCR |
| Speech out | edge-tts |
| Speech in | Vosk Chinese small model (42 MB, local, offline) |
| Tray | pystray |
| Packaging | PyInstaller |

**Why not Electron**: an Electron shell starts at 150 MB, and this program's bulk is models and OpenCV anyway. WebView2 ships with Windows — free.

---

# Dev notes

## Layout

```
main.py              Entry: window, DWM rounded corners, tray, idle timer
api.py               Frontend bridge, 53 methods
core/
  luoji.py           Logic, 7,700 lines: chat, mood, memory, wallpaper
  shitu.py           Vision: OCR + face + object
  zhengli.py         File organizer
  xiezuo.py          Writing
  dashang.py         Tips
  tuopan.py          System tray
  zhu_dong.py        Proactive messages + notifications
  yuyin_shuru.py     Speech input (Vosk)
  models/            onnx models (not in repo — run 下载模型.py)
ui/
  index.html
  css/               base / titlebar / chat / input / gongneng
  js/                bridge / bishu / chat / gongneng / input
                     / yuyin (her voice) / yuyin_shuru (your voice)
  素材/              Wallpaper, icons, sample material
  表情/              29 reaction images named by mood
  语料/              515 offline lines
  个性化/            Avatars, bubble preference
  人设.txt           ← her personality
  API.txt            ← your key (gitignored)
下载模型.py
打包.spec
```

Three layers: page (HTML/CSS/JS) → bridge (every `api.py` method maps to one `Qiao.xxx()` on the frontend) → logic (`core/luoji.py`).

## Running locally

```bash
pip install -r requirements.txt
python 下载模型.py
python main.py
```
