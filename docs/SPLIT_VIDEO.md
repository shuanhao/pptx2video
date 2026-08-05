# 把匯出的 MP4 依換頁邊界切成多段

> 這份文件是給「Step 10 匯出的單一 MP4 太長，想切成幾段」的情境看的選用功能說明。不需要分段的話可以略過，回到 [README.md](../README.md)。

deck 頁數多、講稿長的時候，Step 10 匯出的單一 MP4 可能長達數小時，不方便觀看/上傳/分享。PowerPoint 的匯出 API（`Presentation.CreateVideo()`）**沒有任何「只匯出某個頁面範圍」的參數**——每次呼叫一定是匯出整份簡報，如果為了分段而重跑 Step 10 三次，等於要付出三倍的匯出時間。

`scripts/split_video_by_slides.py` 改成對**已經匯出好的單一 MP4** 事後切割，並重用跟 `regenerate_srt_from_export.py` 校正字幕時同一套「真實起始時間」量測，保證切點精準落在換頁的地方，不會切在講稿講到一半。

## 基本用法

自動平均分段（例如分成 3 段，長度盡量平均）：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3
```

或指定要在哪幾頁之後切（例如切成第 1~7 頁、第 8~14 頁、第 15 頁~結尾 三段）：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --split-after-slides 7 14
```

會在 `output/segments` 底下產生 `segment_1.mp4`、`segment_2.mp4`、`segment_3.mp4`。

⚠️ **強烈建議加上 `--global-scale-correction`**（見 [CALIBRATION.md](CALIBRATION.md)）：字幕時間軸差個零點幾秒觀眾未必有感，但切點沒校正好，可能會把下一頁narration的開頭一小段切掉、或留在上一段的結尾。用法跟 `regenerate_srt_from_export.py` 一樣：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3 --global-scale-correction 1.001221
```

實際切割預設用 ffmpeg 的 `-c copy`（stream copy，不重新編碼），速度快，但切點會吸附到該時間點之前最近的關鍵影格；如果切出來的片段開頭偶爾閃一下前一頁畫面的尾巴，那就是關鍵影格間距造成的，加上 `--reencode` 可以改成重新編碼、取得影格精準的切點（速度慢很多，長影片請預留足夠時間）。

## 字幕也要一起切嗎？加 `--subtitles` 就會

只切影片、不處理字幕的話，`output/captions.srt` 還是整份 deck 的時間軸，直接搭配 `segment_2.mp4`、`segment_3.mp4` 播放時間會完全對不上（因為 `segment_2.mp4` 是從整支影片的中間某個時間點開始重新算 00:00:00，但 `captions.srt` 裡的時間戳沒有跟著歸零）。

加上 `--subtitles`（指向 Step 10 產生的、已經是真實起始時間對齊版本的 `captions.srt`），這個工具就會在切每一段影片的同時，也把字幕切成對應的 `segment_1.srt`、`segment_2.srt`、`segment_3.srt`，各自從 `00:00:00` 重新算起：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3 --global-scale-correction 1.001221 --subtitles output/captions.srt
```

這裡刻意**重用跟切影片時完全相同的切點時間戳**，而不是另外重新量一次——這樣才能保證每一段影片跟它自己的 `.srt` 對「時間 0 秒」的認定完全一致，不會因為兩次量測結果有些微差異而讓字幕跟畫面對不齊。落在切點之外的字幕行會整行捨棄；理論上不會有字幕行剛好橫跨切點（因為切點本來就選在某一頁narration 的真正起點，那一頁的字幕自然是從那個時間點才開始），但如果真的出現極小的誤差橫跨到切點，這個工具會把該行**裁切**到所在那一段的範圍內，而不是整行丟掉或整行重複塞進兩段。

⚠️ 注意：`--subtitles` 吃的必須是**真實起始時間對齊版本**的 `captions.srt`（Step 10 把 `--subtitles-output` 跟 `--export-video` 寫在同一行時產生的版本，或用 `regenerate_srt_from_export.py` 事後重新產生的版本）——如果拿 Step 8 單獨執行、還沒匯出影片時的「預測版」字幕來切，時間戳本身就跟實際匯出的 `output/deck.mp4` 對不準，切出來的分段字幕自然也不會準。
