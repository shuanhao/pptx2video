# 把匯出的 MP4 依換頁邊界切成多段

> 這份文件是給「Step 10 匯出的單一 MP4 太長，想切成幾段」的情境看的選用功能說明。不需要分段的話可以略過，回到 [README.md](../README.md)。

deck 頁數多、講稿長的時候，Step 10 匯出的單一 MP4 可能長達數小時，不方便觀看/上傳/分享。PowerPoint 的匯出 API（`Presentation.CreateVideo()`）**沒有任何「只匯出某個頁面範圍」的參數**——每次呼叫一定是匯出整份簡報，如果為了分段而重跑 Step 10 三次，等於要付出三倍的匯出時間。

`scripts/split_video_by_slides.py` 對既有 MP4 分段，共用音訊定位邏輯。旁白起點不必然等於畫面換頁；prepared 定位退回會影響可用切點，切割後仍需檢查每段開頭與結尾。

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

預設校正係數維持 1.0；只有獨立核對確認有比例偏差時才校準，不能把歷史的 1.001221 當通用設定。以下為 1.0 範例：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3 --global-scale-correction 1.0
```

實際切割預設用 ffmpeg 的 `-c copy`（stream copy，不重新編碼），速度快，但切點會吸附到該時間點之前最近的關鍵影格；如果切出來的片段開頭偶爾閃一下前一頁畫面的尾巴，那就是關鍵影格間距造成的，加上 `--reencode` 可以改成重新編碼、取得影格精準的切點（速度慢很多，長影片請預留足夠時間）。

## 字幕也要一起切嗎？加 `--subtitles` 就會

只切影片、不處理字幕的話，`output/captions.srt` 還是整份 deck 的時間軸，直接搭配 `segment_2.mp4`、`segment_3.mp4` 播放時間會完全對不上（因為 `segment_2.mp4` 是從整支影片的中間某個時間點開始重新算 00:00:00，但 `captions.srt` 裡的時間戳沒有跟著歸零）。

加上 `--subtitles` 指向人工確認同步的 SRT（可為 initial 或其他候選），工具會依相同切點裁切字幕並將各段時間歸零：

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3 --global-scale-correction 1.0 --subtitles output/captions.srt
```

這裡刻意**重用跟切影片時完全相同的切點時間戳**，而不是另外重新量一次——這樣才能保證每一段影片跟它自己的 `.srt` 對「時間 0 秒」的認定完全一致，不會因為兩次量測結果有些微差異而讓字幕跟畫面對不齊。落在切點之外的字幕行會整行捨棄；理論上不會有字幕行剛好橫跨切點（因為切點本來就選在某一頁narration 的真正起點，那一頁的字幕自然是從那個時間點才開始），但如果真的出現極小的誤差橫跨到切點，這個工具會把該行**裁切**到所在那一段的範圍內，而不是整行丟掉或整行重複塞進兩段。

注意：字幕必須與這份 MP4 實際同步，不能單憑 captions／initial 檔名判定。分段不會修復原本不同步的字幕。

## 想把字幕直接燒進畫面（硬字幕）？

上面 `--subtitles` 產生的 `segment_N.srt` 是「軟字幕」——一個獨立的字幕檔，播放器可以自己選擇要不要顯示。如果想把字幕直接燒進影片畫面（不管在哪個播放器打開都看得到，適合上傳到不一定會顯示字幕軌的平台），有兩種用法：

**方式一：切分段的同時順便燒字幕**（`--subtitles` + `--burn-subtitles`）

```powershell
python scripts/split_video_by_slides.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output-dir output/segments --num-segments 3 --global-scale-correction 1.0 --subtitles output/captions.srt --burn-subtitles
```

會在切出 `segment_N.mp4`、`segment_N.srt` 之後，緊接著多產生一個 `segment_N_burned.mp4`——原本的 `segment_N.mp4`（未燒字幕）跟 `segment_N.srt`（軟字幕）還是照樣保留，方便之後只想調整字幕樣式時，不用重新切影片、只要重跑燒字幕那一步就好。

**方式二：只燒某一個 `.mp4`/`.srt` 配對，不切分段**（`scripts/burn_subtitles.py`，獨立工具）

如果只是想燒完整版 `deck.mp4`、或想重燒已經切好的某一段而不重新切影片，用這個獨立工具：

```powershell
python scripts/burn_subtitles.py --video output/deck.mp4 --srt output/captions.srt --output output/deck_burned.mp4
```

兩種用法背後呼叫的是同一套燒字幕邏輯（`src/subtitle_burner.py`），不會因為走不同工具而出現不一致的結果。

燒字幕使用固定黑條加白字，黑條尺寸由下節 auto／fixed／手動值決定。FontSize 與 MarginV 為 ASS 座標值，不是輸出像素。改變字型或斷句寬度後仍需檢查長句版面。

⚠️ 燒字幕一定要重新編碼影片本身（`libx264`，因為是把文字畫進每一幀的像素），比純切割（`-c copy`）慢很多；音軌完全沒被動到，一律用 `-c:a copy` 直接複製。


## Stage 5：字幕黑條自動縮放

人工確認 SRT 後獨立執行：
```powershell
python scripts/burn_subtitles.py --video output/deck.mp4 --srt output/captions_initial.srt --output output/deck_burned.mp4
```

預設 `--bar-scale-mode auto` 使用 ffprobe 的實際影片尺寸：1280×720 採 650／38／40；1920×1080 採 975／57／60（黑條寬／高／底部至頂邊距離）。FontSize=15、MarginV=1 不縮放，兩者為 ASS 樣式座標值，不是直接輸出像素。

三個幾何參數可逐項覆寫為最終像素；1080p 加 `--bar-width 900` 得到 900／57／60。`--bar-scale-mode fixed` 使用舊有 650／38／40 預設，也允許覆寫。1080p 未指定尺寸的預設效果因此有意改變。

auto 僅支援無旋轉、方形像素的上述尺寸；其他影片需 fixed 或完整三個手動值。黑條須位於畫面內，高度不可大於底部 offset。所有模式均需 ffprobe 驗證，失敗停止、不猜測尺寸。輸出不得與輸入影片或字幕同一路徑。

分段入口 `scripts/split_video_by_slides.py --burn-subtitles` 支援相同選項，共用 `src/subtitle_burner.py` 的 probe／resolve 邏輯。第一階段不自動選字幕或燒錄，不需重跑 TTS 或 PowerPoint。
