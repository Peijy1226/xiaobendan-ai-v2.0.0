# 小笨蛋 (Little Dummy)

**English** · [中文](README.md)

[![release](https://img.shields.io/github/v/release/Peijy1226/xiaobendan?cacheSeconds=3600)](https://github.com/Peijy1226/xiaobendan/releases)
[![license](https://img.shields.io/github/license/Peijy1226/xiaobendan)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4)](#)

A character who lives on your computer. Close the window and she stays in the system tray. Leave her alone long enough and she'll come find you.

![demo](docs/demo.gif)

## Install

One zip in [Releases](https://github.com/Peijy1226/xiaobendan/releases). Unzip, double-click `小笨蛋.exe`. No Python, no runtime needed.

First launch she asks your name. She remembers it after that.

Works offline too — 515 canned lines cover time, arithmetic, jokes, OCR, and file sorting. Add a DeepSeek API key and she actually talks. Costs pennies for thousands of messages.

## Why this exists

I wanted a character who lives on the computer. Not an assistant, not a toolbox.

Every chat app I tried felt like a tool — ask, answer, forget. I wanted: you mention you're working late, and the next day she asks how late you slept.

So memory got the most work; everything else grew around it. Two layers: rules extract synchronously (name, pets, likes, job, city — 10ms), anything missed goes to the model in the background (1.2s). If the rules got it, the model isn't called — otherwise every message costs an extra cent and a second.

## What she does

**Chat.** Real replies when online, 515 canned lines offline. Time, arithmetic, jokes, unit conversion, OCR, file sorting all work without a key — only free-form conversation needs one.

**Remember you.** Your name, your cat, what you like, what you do, where you live. Across sessions. Mention you're working late and she might ask the next day how late you actually slept.

**Speak up.** Goes quiet for a while and she'll chime in. Hidden in the tray, she can't talk, so she sends a system notification instead.

**Read aloud, and listen.** The 🔊 in the title bar reads her lines out, synthesized with edge-tts. The 🎤 next to the input is hold-to-talk, recognized locally — no network, nothing uploaded.

**Look at images.** Hand her a picture: she'll pull the text out, count the faces, tell you what the object is.

**Write.** Narrative, argumentative, expository, letters. Give her a topic.

**Sort files.** Point her at a folder, she groups by file type.

**Change the wallpaper.** Video wallpapers keep playing — not a still frame. Drop your own into `ui/素材/壁纸/`.

## Where she goes when you close the window

Into the system tray. Double-click the icon to bring her back; right-click → "let her say something" and she'll pipe up on her own.

**Tray icons die.** The icon registers with `explorer.exe`. When explorer restarts — installing software, or after a crash — that registration is gone: the icon vanishes from the taskbar but the process is still running. Closing the window then only hides it, and there's no tray to click.

Hit that bug. Three safeguards now:

1. A background check every 30 seconds — if the icon handle is gone, rebuild it
2. A "Quit completely" button at the bottom of Features → About, bypassing the tray entirely
3. A 1.5-second `os._exit(0)` fallback at the end of the quit path, so no background thread can hold it hostage

## Three bubble styles

Cat ears, rounded, and frosted glass. The frosted one uses real `backdrop-filter` — the wallpaper moves and it moves with it, not a flat image.

The cat-ear ears are SVG. The path isn't hand-drawn — it's the 6 control points from the Tkinter version's `create_polygon(smooth=True)`, converted to Béziers via quadratic B-spline.

I tried adding tail and ear animations to the bubbles. Six versions of the tail, every one looked like a worm. User's words: "creepy as hell." Deleted all of it.

## Tuning the UI

Features → Personalize, four sliders:

- **Blur**: 0–80 px
- **Saturation**: 1.0–2.0
- **Brightness**: 0.70–1.40
- **Tint opacity**: 0–0.80

Live while dragging, saved on release. Stored in `ui/个性化/玻璃.txt` as four integers.

It used to be hardcoded at 42px. That number came from measuring the brightness delta across the panel edge — it only measured transparency, not blur. The user said it was too blurry, so I re-measured five levels against the help page text:

| Setting | Transparency | Text contrast |
|---|---|---|
| blur 42, tint 0.19 | 4.4 | 18,297 |
| **blur 22, tint 0.26, brightness 1.12** | **5.8** | **20,271** |
| blur 18, tint 0.34, brightness 1.16 | 6.1 | 23,762 |

The new default is 32% more transparent and 11% more legible, and still doesn't look like a plank.

---

# Dev notes

For future me, who will have forgotten all of this.

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

`--debug` opens F12. `--自检` skips the window and just writes an environment report.

`vendor/` is where I installed pystray / sounddevice / vosk to keep the system site-packages clean. Not required — the code looks in both places. If you want it:

```bash
pip install --target vendor pystray sounddevice vosk srt requests tqdm
```

## Building

```bash
D:/PyThon/python.exe -m PyInstaller 打包.spec --noconfirm
```

416MB output. **Most of it isn't my code**:

| What | Size |
|---|---|
| OpenCV (`cv2.pyd`) | 82 MB |
| Vosk Chinese model | 66 MB |
| yolox onnx | 35 MB |

My code is under 1 MB total.

After building, manually `cp -r ui dist/小笨蛋/` — ui isn't bundled into the exe so users can swap wallpapers and add reaction images.

## Things that bit me

### Vosk can't read Chinese paths

```python
vosk.Model(r"E:\AI\workbuddy2\小笨蛋\...")
# Failed to create a model
```

Its C library assembles paths through ANSI APIs on Windows. Non-ASCII blows up immediately.

Tried short paths (8.3 format) and directory junctions. Only fix was copying to `%TEMP%\xbd_vosk_stt`. Checked on every launch; if the path is bad, re-copy the 66MB.

### PyInstaller can't find packages in vendor/

The spec needs this at the top:

```python
sys.path.insert(0, _VENDOR)
```

Plus adding it to `pathex`. Otherwise the build "succeeds" and the exe ImportErrors on launch.

### Tray "Quit" did nothing

`chuang.destroy()` **also fires the `closing` event**. I had `return False` in `closing` (✕ should hide to tray), so destroy got blocked by its own handler: window not destroyed, main loop still alive, process never exits.

Observed: clicking "Quit" logged one line, `closing 被触发`, then nothing.

Fix: a "really quitting" flag, set before the tray quit; `closing` returns `True` when it sees it.

### Don't build a long string to check punctuation in JS

```js
if ('，。！？、；：""''（）《》…— .,!?;:()\n\t'.indexOf(ch) >= 0)
```

That string contains Chinese curly quotes. Looks fine. But **one stray ASCII `'` closes it early and the whole file becomes a syntax error**.

Symptom: `LiaoTian is not defined`, the UI is completely dead, and nothing appears in the page console.

Replaced with an object table: `var 标点 = {'，': 1, '。': 1, ...}`, one entry at a time.

### New messages reverted to the old avatar

Two URL builders disagreeing:

- `刷头像()` used `?v=timestamp` from the backend → updated
- `造头像()` hardcoded `个性化/她的头像.png` → browser served the cached copy

Worked right after the change, reverted on the next message. Fix: build the URL in exactly one place (`头像地址()`), call it from both.

### Avatars were scaled up 26%

One CSS line:

```css
.tou-xiang img { transform: scale(1.26) translateY(2%); }
```

Intent was "crop to the face if someone uploads a full-body shot." Side effect was **every** avatar getting zoomed 26%, cropping the edges of properly square images. Looked "wrong ratio."

And `tou_cun()` already center-crops to 1:1 before saving, so the scale was redundant. Removed; `object-fit: cover` alone now.

### Deleting code? Check what references it

While removing the bubble effects I deleted `加表情()` too. It was referenced by the `window.LiaoTian` export, so the entire chat area went blank — zero bubbles.

**No error anywhere on the page**, because the exception inside the IIFE was swallowed.

Now every JS change gets verified with a fake DOM in node:

```js
const el = () => ({classList:{add(){},remove(){},toggle(){},contains(){return false}},...});
new Function('window','document','Qiao','requestAnimationFrame', src)(...);
console.log(typeof window.LiaoTian);   // must be object
```

### A leftover process wasted half an hour

Port 42001 was still held by a `小笨蛋.exe` that hadn't exited cleanly. The new test process loaded the **old process's HTTP server**.

The file on disk was updated; the page ran the old code. Took 30 minutes to notice.

Before testing:

```bash
taskkill //F //IM 小笨蛋.exe
netstat -ano | grep LISTENING   # make sure the old port is gone
```

## Magic numbers

- **22px** default blur for the features panel. Picked from the five-level measurement above
- **30s** tray icon poll interval
- **1.5s** hard-exit fallback delay
- **515** offline corpus lines
- **90** character cap for the per-character fade (that effect is gone; the number survives as trivia)

## Known issues

**Weather never answers.** `open-meteo` times out on TLS handshake from here; occasionally works on other networks. Not a code problem, that's just the endpoint.

**Speech recognition is inaccurate.** Ceiling of the Vosk small model. Clear Mandarin is fine, accents make it guess. A bigger model helps, but costs 500MB more — not worth it.

**Two instances fight.** No single-instance guard, so both processes write to the same `ui/存档.json`. A named mutex would fix it; never got around to it.

**First launch gets blocked.** Unsigned, so SmartScreen shows "unknown publisher." Click "More info" → "Run anyway." Certificates run a few hundred dollars a year, too much for a free toy.

## Wanted but didn't

- Redo the bubble layout (the more compact QQ style). Kept meaning to, but it's purely aesthetic — parked
- Single-instance guard
- Launch at login (a scheduled task would do it)

---

## License

MIT
