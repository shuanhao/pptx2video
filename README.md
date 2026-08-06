# PPTX Auto Presenter (`pptx2video`)

一個基於 Python 的自動化工具，可將 PowerPoint 簡報檔（`.pptx`）自動轉換成帶旁白配音、帶字幕的 MP4 影片：解析每頁的標題與備忘稿內容 → 透過 **Edge-TTS** 生成語音（同時取得逐字時間資料）→ 把音訊插入對應投影片 → 自動呼叫 PowerPoint 匯出 MP4；備忘稿同時也會被拆成適合當字幕的短句、對齊到實際語音時間，輸出一份完整的 SRT 字幕檔。**已完成 pptx → 配音 MP4 → 字幕生成流程，並在真實 Windows + PowerPoint 環境驗證過；字幕排版仍有已知的取捨情境（極短獨立段落、純英文行寬），詳見 [TODO.md](TODO.md)**。

- 版本歷史：[CHANGELOG.md](CHANGELOG.md)
- 還沒完成的工作與已知限制：[TODO.md](TODO.md)
- 架構設計、模組職責、專案結構、PowerPoint COM 細節、測試等開發者向內容：[PROJECT_HANDOVER.md](PROJECT_HANDOVER.md)
- 字幕/切點校準：[docs/CALIBRATION.md](docs/CALIBRATION.md)；把匯出的 MP4 依換頁邊界切成多段：[docs/SPLIT_VIDEO.md](docs/SPLIT_VIDEO.md)

---

## ✨ 功能特色

- **解析 `.pptx` 投影片內容**：讀取投影片編號、標題與備忘稿，支援多頁簡報、長段落、換行與空白行，也能正確處理沒有備忘稿的頁面（例如封面/結尾頁）。
- **語音生成**：透過 `edge-tts` 把備忘稿轉成 MP3，依頁碼命名，支援語速/音高調整，失敗時有可設定次數的自動重試。
- **PowerPoint 音訊插入**：透過 `pywin32` COM 自動化把生成的 MP3 插入對應投影片，圖示縮小並移到右上角、盡量隱藏。
- **MP4 匯出自動化**：呼叫 PowerPoint「建立視訊」功能匯出 MP4，解析度/FPS/畫質/逾時秒數皆可透過 CLI 調整。
- **SRT 字幕生成**：把備忘稿依顯示寬度智慧斷行（中文用 `jieba` 斷詞避免切壞詞語，中英混排、標點、空白都有對應規則），對齊到 edge-tts 實際回報的逐字語音時間（不是估算），並依照每張投影片在最終影片裡的實際時長，合併成一份時間軸正確的完整 SRT 字幕檔。
- **完整例外分類與 Logging**：失敗情境依類型拋出對應例外，並區分「單頁跳過」與「整體中止」兩種處理策略；終端機維持簡潔輸出，log 檔案永遠保留完整 DEBUG 細節。

版本歷史與各功能導入的時間點請見 [CHANGELOG.md](CHANGELOG.md)。

---

## 🚀 快速開始（Windows）

以下步驟適合在 Windows PowerShell 中從 GitHub 下載這個專案後直接開始使用。

### 1. 下載專案

```powershell
git clone https://github.com/<your-username>/pptx2video.git
cd pptx2video
```

### 2. 建立虛擬環境

```powershell
py -3 -m venv .venv
```

### 3. 啟動虛擬環境

```powershell
.\.venv\Scripts\Activate.ps1
```

若 PowerShell 擋下執行腳本，可先執行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. 安裝依賴套件

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> `pywin32` 只會在 Windows 環境安裝（`requirements.txt` 已用 `sys_platform == "win32"` 標記），在其他作業系統上執行 `pip install` 會自動跳過它。

### 5. 生成範例簡報（可選）

```powershell
python examples/create_sample_pptx.py
```

### 6. 執行解析流程

```powershell
python src/main.py examples/sample_test.pptx --output output/slides.json
```

或使用更像套件的方式：

```powershell
python -m pptx2video examples/sample_test.pptx --output output/slides.json
```

這會讀取簡報檔，解析每頁的標題與 notes，並輸出 JSON 到 [output/slides.json](output/slides.json)。

### 7. 生成語音（TTS）

```powershell
python -m pptx2video examples/sample_test.pptx --generate-audio --audio-output-dir output/audio --voice "zh-TW-YunJheNeural" --rate=-10% --pitch="+0Hz"
```

這會把有 notes 的投影片轉成 MP3，並在 `output/audio/manifest.json` 建立對應的音訊清單。

> `edge-tts` 直接把語音服務回傳的 MP3 位元組寫入檔案，**這個階段本身不需要安裝 ffmpeg**。ffmpeg 是在下一步「產生字幕」量測每張投影片實際音檔時長時才會用到（見下方需求說明）。

> 🔧 **這一步出錯、或事後想針對某幾頁重跑時**：不用整份 deck 重新跑一次（長講稿可能要一個多小時）。加 `--slides 6,9`（逗號分隔頁碼/區間，例如 `6,8-10`）只重新生成指定頁面，其他頁面已生成好的音檔跟 `manifest.json` 紀錄不會被動到。常見情境：某頁因為網路問題生成失敗、想針對某頁換一下 `--voice`/`--rate` 重試、或下面「疑似漏講偵測」警告某一頁有問題想重新生成確認。指令範例與細節見下方「⚠️ `--generate-audio` 疑似漏講偵測」小節。

### 8. 產生字幕（SRT）

只要有跑過 `--generate-audio`（這一步會順便把每張投影片的逐字語音時間存成 `slide_XXX.wordboundaries.json`），`--subtitles-output` 就會自動用這份時間資料產生對齊過的字幕，不需要額外參數：

```powershell
python src/main.py examples/sample_test.pptx --generate-audio --audio-output-dir output/audio --subtitles-output output/captions.srt
```

**不需要每次都跟 `--generate-audio` 寫在同一行**：如果音檔已經在之前的步驟 7（或更早的某次 `--generate-audio`）生成過，`output/audio/manifest.json` 已經存在，之後單獨執行 `--subtitles-output`（不加 `--generate-audio`）一樣會自動讀取這份既有的 manifest，正確產生有內容的字幕，**不會重新呼叫 edge-tts**：

```powershell
python src/main.py examples/sample_test.pptx --audio-output-dir output/audio --subtitles-output output/captions.srt
```

只有在 `output/audio/manifest.json` 真的不存在（例如整個專案都還沒跑過 `--generate-audio`，只想先解析 JSON）時，才會寫出一個合法但空白的 `.srt` 檔案，不會報錯。

> `pydub` 需要透過 `ffmpeg` 解碼 mp3 才能量測每張投影片實際的音檔時長（用來排出每張投影片在最終影片時間軸上的位置），所以這一步需要安裝 `ffmpeg` 並加入 PATH，見下方「需求與環境」。
>
> 字幕行的斷行/合併邏輯與時間對齊的設計細節，見 `src/subtitle_segmenter.py`、`src/subtitle_alignment.py`、`src/subtitle_pipeline.py` 的模組說明；已知的取捨（極短獨立段落、純英文行寬）記錄在 [TODO.md](TODO.md)。

> ⚠️ **這一步（mp4 還沒產生時）只會寫出「預測版」字幕，還不是最終準確版**：這個階段是把每張投影片自己音檔的實際長度依序加總，猜測每頁在最終影片裡的起始時間，假設投影片是「一張接一張、中間完全沒有空隙」播放——對短 deck 通常夠準，但長 deck 可能到後面累積偏差到好幾秒（見 CHANGELOG v0.6.0）。**真正準確的版本要等 Step 10 匯出 MP4 時，把 `--subtitles-output` 跟 `--export-video` 寫在同一行才會產生**（程式會拿實際匯出的影片重新量測每頁真實起始時間，覆寫掉這裡的預測版）——細節見 Step 10 的說明，這裡先產生的版本純粹是給你先睹為快、或在還沒匯出影片前抓字幕內容有沒有問題用的。

> 🔧 **想在不重新呼叫 edge-tts 的情況下驗證字幕/漏講狀況**：`--generate-audio` 每次都會附帶重新產生字幕，而這一步會重新處理**整份** deck 既有的 manifest/wordboundaries 資料，不只是剛才用 `--slides` 重新生成的那幾頁——換句話說，就算只重生一頁，其他頁的舊資料也會被目前的程式碼重新比對一次。想單獨確認（不管是想看某幾頁有沒有漏講、或想在不跑一次 `--generate-audio` 的情況下重新檢查全部頁面）用 `scripts/check_narration_gaps.py`，純本機比對、秒級完成，細節見下方「⚠️ `--generate-audio` 疑似漏講偵測」小節。

### ⚠️ `--generate-audio` 疑似漏講偵測（`POSSIBLE DROPPED NARRATION`）

背景：實際使用中發現過一次 edge-tts **完全沒有錯誤訊息、卻悄悄漏講一整段備忘稿內容**的情況（某頁備忘稿裡連續兩個要點、約 300 字，語音直接跳過沒有唸出來，`WordBoundary` 事件的時間戳記從前一段幾乎沒有停頓就跳到下一段）。這跟「標點符號、空白沒有各自的 WordBoundary 事件」這種已知、正常的現象不同——這是語音內容本身真的少了一大段。

`--generate-audio` 現在每頁生成完音檔後，會自動比對「這一頁 WordBoundary 事件之間的時間間隔」跟「這一頁自己的平均語速」，如果某個間隔明顯短於它涵蓋的文字量該有的時間，就會印出一行警告：

```
WARNING - POSSIBLE DROPPED NARRATION - slide 9: edge-tts's audio has only 4.0s around 312.3s
where ~52s was expected for this much source text. Listen to slide_009.mp3 around 312.3s to
confirm. Skipped text: '因此，Flash 的第四個特性...（後略）'
```

看到這個警告代表**建議實際打開該頁的 mp3、跳到警告標出的時間點附近用耳朵確認**——這是啟發式判斷，不是絕對保證（依據見 [TODO.md](TODO.md) 已知限制），但目前唯一一次真實遇到的案例已驗證能準確抓到。沒有看到這個警告不代表 100% 沒問題，只是目前沒有工具能做到不需要人耳確認就 100% 保證正確；這個警告的作用是把「該去聽哪一頁、聽哪個時間點」的範圍大幅縮小，不用整份講稿逐頁逐句盲聽。

**只重新生成/檢查特定頁面**：如果只是想針對某一頁（例如收到警告的那一頁）重跑或重新檢查，不用整份 deck 重新跑一次（長講稿跑一次可能要一個多小時），有兩種情況：

- **手上還沒有這一頁的音檔/wordboundaries 資料**，或想確認 edge-tts 這次會不會又漏講：用 `--slides` 只重新生成指定頁面，不會動到其他頁面已經生成好的音檔跟 `manifest.json` 紀錄：

  ```powershell
  python src/main.py examples/sample_test.pptx --generate-audio --audio-output-dir output/audio --slides 6,9 --no-file-log
  ```

  `--slides` 接受逗號分隔的頁碼跟區間，例如 `6,9` 或 `6,8-10`。指定到 deck 裡不存在的頁碼會直接報錯中止。

- **手上已經有這一頁的音檔/wordboundaries 資料**（例如之前完整跑過一次），只是想重新跑一次疑似漏講檢查、或想用不同的敏感度門檻重新檢查：用 `scripts/check_narration_gaps.py`，完全不會呼叫 edge-tts，是純本機比對，秒級完成：

  ```powershell
  python scripts/check_narration_gaps.py --manifest output/audio/manifest.json --slides-json output/slides.json --slides 6,9
  ```

  沒有 `output/slides.json` 的話可以改用 `--pptx examples/sample_test.pptx` 直接從簡報重新抽取備忘稿文字。不加 `--slides` 就是檢查整份 deck 裡每一頁有資料可查的投影片。找到疑似漏講內容時結束代碼是 `1`，方便串進其他腳本判斷；沒問題或該頁沒有可檢查的資料則是 `0`。

### 9. 把音訊插入 PPTX（需要 Windows + PowerPoint）

```powershell
python src/main.py examples/sample_test.pptx --insert-audio --audio-output-dir output/audio --pptx-output output/deck_with_audio.pptx --verbose
```

這會透過 `pywin32` 開啟 PowerPoint，把每頁對應的 MP3 插入該投影片，圖示縮小並移到右上角，且盡量在非播放狀態隱藏。沒有音檔的頁面（例如封面/結尾頁）完全不會被更動。

> ⚠️ **重要（實測結論）**：插入後在 PowerPoint 編輯畫面裡，音訊的 Start 設定仍會顯示「按一下時」，用「投影片放映」現場播放時需要多點一下音符圖示才會出聲——這是已知限制，目前尚未解決（詳見下方「已知限制」）。**但這不影響用 PowerPoint「建立視訊」匯出 MP4**：匯出時每頁會自動依照音檔實際長度撥放並切換頁面，不需要額外設定轉場秒數（技術原因見 [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) 的 PowerPoint COM 特性說明）。

> 🔧 **如果剛才用 `--slides` 只重新生成了某幾頁的音檔**：這一步（跟下面的匯出 MP4）沒有頁面篩選機制，只要有任何一頁音檔換過，就需要對整份 `deck_with_audio.pptx` 重跑一次插入音訊；不會因為只重生一頁就漏掉，但也不能只插入那一頁——`--insert-audio` 一律是整份 deck 重新插入。

> ℹ️ **這一步不會動到字幕**：`--insert-audio` 只負責把音訊插入 pptx，跟 `captions.srt` 完全無關——不管這一步跑幾次，字幕檔都還是停在 Step 8 產生的那個版本（或更早的版本），要更新字幕請看下一步。

### 10. 匯出 MP4（已自動化，需要 Windows + PowerPoint）

> ⚠️ **這一步跟步驟 9 是接續關係，不是各自獨立的兩步驟**：`--insert-audio` 和 `--export-video` 可以在**同一行指令**裡一起下，程式會依序完成「插入音訊 → 匯出影片」。**不要把步驟 9 的指令跑完，再另外跑一次帶 `--insert-audio` 的步驟 10 指令**——那樣會讓插入音訊的動作被多做一次（重新開一次 PowerPoint、重新插一次音訊），純粹浪費時間。下面依你的情境選其中一種指令即可：

**情境 A：第一次跑，插入音訊跟匯出一次到位（跳過步驟 9，直接執行這一行就好）**

```powershell
python src/main.py examples/sample_test.pptx --insert-audio --audio-output-dir output/audio --pptx-output output/deck_with_audio.pptx --export-video --video-output output/deck.mp4 --subtitles-output output/captions.srt --verbose
```

**情境 B：已經照步驟 9 插好音訊了，只想匯出（不要再加 `--insert-audio`）**

```powershell
python src/main.py output/deck_with_audio.pptx --export-video --video-output output/deck.mp4 --subtitles-output output/captions.srt
```

兩種情境都會自動呼叫 PowerPoint「建立視訊」功能匯出 MP4（預設 720p、不使用錄製時間、沒有音訊的頁面固定顯示 5 秒），並即時印出匯出進度，例如：

```
Exporting video... status: queued
Exporting video... status: in_progress
Exporting video... status: done
Exported video to D:\...\output\deck.mp4 (42.3s)
```

已在真實 Windows + PowerPoint 環境驗證：影片可以正確產生，語音與每頁時長都對齊。

> ⚠️ `Presentation.CreateVideo()` 是非同步 API，匯出時間會依投影片數量與解析度而定，可能長達數十秒到數分鐘。程式會輪詢匯出狀態，並設有逾時保護（預設 3600 秒，可用 `--video-timeout` 調整）。

> 🔧 **同上一步的提醒**：因為 `--insert-audio` 是整份 deck 重新插入，只要走了一次（即使起因只是某一頁音檔用 `--slides` 重生），這一步（匯出 MP4）也要跟著整份重跑，才能讓影片反映最新的音檔內容；不能只匯出某幾頁。

> ⚠️ **字幕在這一步要不要一併更新，取決於這行指令有沒有加 `--subtitles-output`**：上面兩個範例都刻意加了這個參數——只有跟 `--export-video` **寫在同一行**，程式才會在匯出完成後，改用剛產生的真實 mp4 重新量測每頁起始時間，把 Step 8 的「預測版」字幕升級成「真實起始時間版」（比較準，尤其是長 deck）。如果這一步的指令沒加 `--subtitles-output`（例如只想先匯出影片，字幕晚點再說），`captions.srt` 完全不會被更新，會停留在 Step 8 產生的版本。
>
> **如果已經匯出完才想到要更新字幕，不需要重新匯出一次**，用 `scripts/regenerate_srt_from_export.py` 直接對著現有的 mp4 重新量測就好：
>
> ```powershell
> python scripts/regenerate_srt_from_export.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output output/captions.srt
> ```

### 11. 一次到底：單一指令完成整個流程

上面 1～10 是拆開一步步介紹，方便逐步理解與除錯；但實際使用時**不需要分開下指令**，所有步驟（解析 → 生成語音 → 輸出 JSON → 生成字幕 → 插入音訊 → 匯出 MP4）都可以寫在同一行指令裡，`main.py` 會依序自動完成：

```powershell
python src/main.py examples/sample_test.pptx `
  --output output/slides.json `
  --generate-audio `
  --audio-output-dir output/audio `
  --voice "zh-TW-YunJheNeural" `
  --rate=-10% `
  --pitch="+0Hz" `
  --subtitles-output output/captions.srt `
  --insert-audio `
  --pptx-output output/deck_with_audio.pptx `
  --export-video `
  --video-output output/deck.mp4 `
  --verbose
```

執行時會依序印出每個階段的進度：

```
Parsing PowerPoint file: ...
Loaded 5 slide(s)
Generating audio 1/3 (slide 2)...
Generating audio 2/3 (slide 3)...
Generating audio 3/3 (slide 4)...
Generated 3 audio file(s) in output/audio
Saved JSON to output\slides.json
Inserted audio into 3 slide(s); skipped 0. Saved to ...\deck_with_audio.pptx
Exporting video... status: queued
Exporting video... status: in_progress
Exporting video... status: done
Exported video to ...\deck.mp4 (42.3s)
Saved subtitles to output\captions.srt
```

**注意事項：**
- 生成語音需要能連上 Edge-TTS 服務（`speech.platform.bing.com`）
- 插入音訊與匯出 MP4 都需要 Windows + 已安裝 PowerPoint + `pywin32`
- 這一行指令裡 PowerPoint 實際上會被開關兩次：`--insert-audio` 用一次、`--export-video` 又用一次，不是同一個 PowerPoint session 做完兩件事。不影響結果，只是多花一點點時間（優化方向見 [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) 的「未來擴充方向」）。
- **`Saved subtitles to ...` 這一行會排在 `Exported video to ...` 之後，不是之前**：因為這一行指令同時有 `--subtitles-output` 跟 `--export-video`，程式會等影片真的匯出完成，才用真實起始時間法產生字幕（見 Step 8、10 的說明），所以字幕是整個流程的最後一步才寫出，不是預測版。這也是這一行指令（相對於分開下 Step 7～10）額外的好處：**不用像分開下指令那樣還要手動記得把 `--subtitles-output` 加進匯出那一行**，一次到底自然就是正確、最終的版本。

> 🔧 **這一行指令適合第一次跑整份 deck；事後針對個別頁面除錯或驗證，改回步驟 7～10 分開下指令**。這一行本身**沒有** `--slides` 篩選（`--slides` 只影響 `--generate-audio` 這一段），所以如果只是想重新生成/檢查某一頁，直接照這行整份重跑一次不會比較快，反而失去 `--slides` 省下重新呼叫 edge-tts 的意義。建議流程：先用步驟 7 的 `--slides` 只重生有問題的那幾頁 → 需要的話用 `scripts/check_narration_gaps.py`（步驟 8 小節）或聽 mp3 確認沒問題 → 再用步驟 9＋10（一次下也可以，兩者本來就要接續，記得帶上 `--subtitles-output` 才會一併更新成準確版）整份重新插入音訊、匯出影片。

---

## 📋 CLI 完整指令與參數說明

### 基本用法

```powershell
python src/main.py <pptx_path> [選項...]
```

或：

```powershell
python -m pptx2video <pptx_path> [選項...]
```

`<pptx_path>`（必填）：輸入的 `.pptx` 簡報檔路徑。

### 參數總表

| 參數 | 預設值 | 說明 |
|---|---|---|
| `--output`, `-o` | `output/slides.json` | 解析結果 JSON 的輸出路徑 |
| `--pretty` | `False`（flag） | 額外把 JSON 結果美化印到終端機（若沒指定 `--output` 也會自動印出） |
| `--indent` | `2` | JSON 輸出的縮排空白數 |
| `--verbose` | `False`（flag） | 印出更詳細的執行進度訊息 |
| `--strict` | `False`（flag） | 若任何一頁沒有 notes，直接中止並回報錯誤（適合用於檢查簡報是否漏寫備忘稿） |
| `--generate-audio` | `False`（flag） | 啟用語音生成，會呼叫 edge-tts 把每頁 notes 轉成 MP3 |
| `--audio-output-dir` | `output/audio` | 生成的 MP3 與 `manifest.json` 存放目錄（需搭配 `--generate-audio` 才有作用） |
| `--voice` | `Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)` | edge-tts 使用的語音。也可用簡短格式如 `zh-TW-YunJheNeural`，若完整格式在你的環境報錯可改用簡短格式 |
| `--rate` | `-10%` | 語速調整，語音會比原始語速慢 10%；正值加快、負值放慢，例如 `+10%`、`-20%`。⚠️ **負值務必用 `--rate=-20%` 等號寫法**，不要用空格分隔的 `--rate "-20%"`（見下方說明） |
| `--pitch` | `+0Hz` | 音高調整，預設不改變音高 |
| `--tts-max-retries` | `3` | edge-tts 生成失敗後（僅限判斷為暫時性的網路/服務錯誤）最多重試幾次，設為 `0` 停用重試。**必須是 0 或正整數**，帶負值會直接被 CLI 拒絕並提示錯誤 |
| `--tts-retry-delay` | `2.0`（秒） | 兩次重試之間的等待秒數 |
| `--subtitles-output` | `output/captions.srt` | 字幕輸出路徑，每次執行都會自動產生；需要 `--generate-audio`（或既有的 `manifest.json`）提供的逐字語音時間才能產出有內容的字幕，否則會寫出空白 `.srt`。**這次執行有沒有同時加 `--export-video` 會決定用哪種對齊方式**：沒有的話用「預測版」（加總每頁音檔時長猜位置，Step 8）；有的話會等匯出完成後才寫出，改用「真實起始時間版」（比對實際影片音軌量測，Step 10，較準）——見下方 Step 8／10 的說明 |
| `--insert-audio` | `False`（flag） | 把已生成的音訊插入 PPTX 對應投影片，圖示縮小移到右上角並盡量隱藏。需要 Windows + PowerPoint + pywin32，且需已用 `--generate-audio` 產生過音檔（或指定的 `--audio-output-dir` 底下已有 `manifest.json`） |
| `--pptx-output` | 覆蓋輸入檔 | 搭配 `--insert-audio` 使用，指定插入音訊後另存的 PPTX 路徑；未指定則直接覆蓋原始輸入檔 |
| `--insert-audio-timeout` | `1800`（秒） | `--insert-audio` 等待整個插入+存檔流程完成的逾時秒數。若 PowerPoint 卡住，超過這個時間會拋出錯誤，而不是無限期卡住。設為 `0` 可恢復成無限期等待 |
| `--export-video` | `False`（flag） | 用 PowerPoint「建立視訊」功能匯出 MP4。需要 Windows + PowerPoint + pywin32。若同時有 `--insert-audio`，會匯出剛插入音訊的那份；否則直接匯出 `pptx_path`（或 `--pptx-output` 指定的檔案） |
| `--video-output` | PPTX 路徑改副檔名為 `.mp4` | 搭配 `--export-video` 使用，指定匯出的 MP4 路徑 |
| `--video-resolution` | `720` | 匯出解析度（垂直像素），對應 PowerPoint 預設選項：`480`（標準）、`720`（HD）、`1080`（Full HD）、`2160`（4K）；寬度會依投影片比例自動計算 |
| `--video-fps` | `30` | 匯出影片的每秒畫面格數 |
| `--video-quality` | `85` | 編碼品質，0–100（PowerPoint 官方預設值就是 85） |
| `--video-default-duration` | `5.0` | 沒有錄製時間、也沒有自動播放音訊的頁面（例如封面頁）要停留幾秒，對應 PowerPoint 匯出視窗的「每張投影片所用秒數」 |
| `--video-use-recorded-timings` | `False`（flag） | 是否改用簡報錄製的時間/旁白，而不是 `--video-default-duration` / 音訊時長驅動的時間。預設關閉，對應 PowerPoint「不使用錄製的時間和旁白」選項 |
| `--video-timeout` | `3600`（秒） | 等待 PowerPoint 匯出完成的逾時秒數，投影片數量多或解析度高時建議調大 |
| `--global-scale-correction` | `1.0`（不修正） | 只在 `--subtitles-output` 搭配 `--export-video`（真實起始時間對齊模式）時有作用。修正一個跟已播放時間成正比、環境相依的字幕時間系統性偏差（詳見 CHANGELOG v0.6.1 第四輪修正）。**這不是通用常數**，每份 deck/每台機器可能需要不同的值（甚至不需要），必須自行校準，完整流程見 [docs/CALIBRATION.md](docs/CALIBRATION.md) |
| `--log-dir` | `logs` | 存放帶日期檔名 log 檔的資料夾（例如 `logs/2026-07-28.log`）。這個檔案**永遠記錄完整 DEBUG 細節，不受 `--verbose` 影響**，方便事後除錯 |
| `--no-file-log` | `False`（flag） | 停用寫入 log 檔案，只印到終端機 |

> ⚠️ **關於 `--rate` 負值的一個 Python argparse 陷阱**：像 `--rate "-10%"` 這種用空格分隔、值又以 `-` 開頭的寫法，會被 `argparse` 誤判成另一個選項旗標而報錯 `expected one argument`（`--pitch` 因為預設是 `+0Hz`，以 `+` 開頭，不受影響）。**負值請一律用等號寫法**，例如：`--rate=-20%`（等號連在一起、不要空格）。加速（正值）用空格或等號都可以，例如 `--rate "+10%"` 或 `--rate=+10%` 皆正常。

### 使用範例

**只解析、不生成語音，並在終端機印出美化後的 JSON：**

```powershell
python src/main.py examples/sample_test.pptx --pretty
```

**嚴格模式，檢查是否有頁面漏寫 notes：**

```powershell
python src/main.py examples/sample_test.pptx --strict
```

**生成語音，使用加快 10% 的語速：**

```powershell
python src/main.py examples/sample_test.pptx --generate-audio --rate "+10%"
```

**指定輸出到自訂資料夾，並顯示詳細訊息：**

```powershell
python src/main.py examples/sample_test.pptx --output output/my_slides.json --audio-output-dir output/my_audio --generate-audio --verbose
```

**只把已生成的音訊插入 PPTX，另存新檔，不覆蓋原始檔案：**

```powershell
python src/main.py examples/sample_test.pptx --insert-audio --audio-output-dir output/audio --pptx-output output/deck_with_audio.pptx
```

**只匯出 MP4（假設已經有插好音訊的 pptx），用 1080p 匯出：**

```powershell
python src/main.py output/deck_with_audio.pptx --export-video --video-output output/deck.mp4 --video-resolution 1080
```

**完整流程（解析 + 語音 + 字幕 + 插入音訊 + 匯出 MP4）：** 指令見上方「11. 一次到底：單一指令完成整個流程」，這裡不重複貼一次。

---

## 🧩 進階與選用功能

以下是選用功能的獨立說明文件，第一次使用/日常使用不需要看，遇到對應情境再點進去即可：

- **字幕/切點對不準、需要校準**：[docs/CALIBRATION.md](docs/CALIBRATION.md)（`--global-scale-correction` 怎麼校準、免動手自動估算 vs 手動校準）
- **匯出的 MP4 太長，想依換頁邊界切成多段**：[docs/SPLIT_VIDEO.md](docs/SPLIT_VIDEO.md)（`scripts/split_video_by_slides.py`）
- **想把字幕直接燒進畫面（硬字幕）**：[docs/SPLIT_VIDEO.md](docs/SPLIT_VIDEO.md)（`scripts/burn_subtitles.py`、或 `split_video_by_slides.py --burn-subtitles` 切分段時順便燒）

開發者/架構向的內容（專案結構總覽、例外階層、Skip vs Abort 錯誤處理策略、如何執行測試、系統架構圖）都整理在 [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md)，一般使用不需要看這份文件。

日常操作用得到的一點 Logging 資訊：終端機輸出預設簡潔（`--verbose` 顯示更多細節），但 `logs/YYYY-MM-DD.log` 永遠保留完整 DEBUG 細節，事後除錯或回報問題時可以直接附上；用 `--log-dir` 指定其他資料夾，或 `--no-file-log` 完全停用檔案記錄。

---

## ⚠️ 已知限制（摘要）

* **PowerPoint 編輯畫面 / 現場放映模式仍需點擊音符圖示才會播放**：插入音訊後，PowerPoint 編輯 UI 顯示的 Start 設定固定是「按一下時」，用「投影片放映」模式現場簡報時需要多點一下才會出聲。**已確認不影響匯出的 MP4 影片**，目前刻意不處理這個情境，優先確保匯出正確。
* **`PlayOnEntry` 旗標的必要性尚未完全理解原理，僅為實測結論**：拿掉這個舊版旗標會讓匯出的 MP4 完全沒聲音、且每頁變回固定 5 秒，即使編輯 UI 上完全看不出差異。
* **`CreateVideoStatus` 的狀態列舉值是依 Microsoft 官方文件假設，未逐一比對所有 PowerPoint 版本**：程式碼已加安全網（回報完成後仍會檢查輸出檔案是否存在、非空）降低風險。
* **`insert_audio()` 的逾時（`--insert-audio-timeout`）只能停止等待，無法強制關閉卡住的 PowerPoint 行程**。
* **真實起始時間對齊模式（`--export-video` + `--subtitles-output`）可能需要手動校準 `--global-scale-correction`**：在一份真實 2 小時 40 分鐘的 deck 上發現，字幕時間量測本身帶有一個跟已播放時間成正比、環境相依的系統性偏差，確切成因尚未定位到程式碼層級（已排除匯出檔案音畫不同步、重取樣誤差等可能性）。預設值 `1.0`（不修正）在偏差不明顯的情況下應該沒問題，但長影片建議先校準這個係數，完整流程見 [docs/CALIBRATION.md](docs/CALIBRATION.md)。

以上限制的技術背景、實測過程與底層原理，請見 [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) 的「PowerPoint COM 特性」章節。完整待辦與已知限制清單請見 [TODO.md](TODO.md)。

---

## 🧰 需求與環境

- Python 3.9 或以上
- Windows 作業系統（音訊插入與 MP4 匯出功能需要）
- 已安裝 Microsoft PowerPoint（供 `ppt_automation.py` 使用 Windows COM 自動化插入音訊、匯出 MP4）
- 若要生成語音，需可連線到 Edge-TTS 服務（`speech.platform.bing.com`）
- 若要產生字幕，需安裝 `ffmpeg` 並加入 PATH（供 `pydub` 量測每張投影片實際音檔時長使用）；純粹生成語音本身不需要 ffmpeg
- `jieba`（`requirements.txt` 已包含）：中文字幕斷句時避免從詞語中間硬切，第一次呼叫時會建立內部字典，稍微增加起始延遲，屬正常現象

系統架構圖、資料流、模組職責等開發者向內容，請見 [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md)。

---

## 🗺️ Roadmap

規劃分兩份文件維護，避免同一件事重複列兩份清單：

* **近期、可直接排進待辦的項目**（含已評估決定不做/暫緩的項目）：[TODO.md](TODO.md)，目前包含 `--insert-audio` 的進度顯示等。
* **需要架構層級思考、還沒到可直接執行程度的長期方向**（例如現場放映自動播放、批次處理與輸出目錄管理）：[PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) 的「未來擴充方向」章節。

已完成的項目與各版本詳情請見 [CHANGELOG.md](CHANGELOG.md)。
