# 專案交接報告

## 專案名稱
pptx2video (PPTX Auto Presenter)

## 文件版本
對應程式版本 v0.4.1；本文件於 Round 2 文件重新分工時大幅改寫，移除與 README.md / CHANGELOG.md / TODO.md 重複的內容，只保留架構設計、設計原因、PowerPoint COM 特性、開發注意事項、維護建議與未來擴充方向。

## 目標對象
接手開發者、AI 協作 Agent

## 撰寫日期
2026-07-30

---

## 快速導覽

這份文件不重複記錄「現在有哪些功能、CLI 怎麼用」這類內容，那些請見：

- 功能特色、CLI 使用方式、快速開始：[README.md](README.md)
- 版本歷史：[CHANGELOG.md](CHANGELOG.md)
- 待辦事項與已知限制：[TODO.md](TODO.md)

這份文件專注在「為什麼這樣設計、開發時要注意什麼、之後接手要往哪裡擴充」。

---

## 1. 專案願景與目標

pptx2video 是一套針對 Windows 桌面環境設計的輕量化自動化工具，目標是將 PowerPoint 簡報檔（.pptx）轉換為具備語音配音、動畫保留與精確字幕的 MP4 影片。

### 核心價值
- 減少人工逐張錄音與排練時間
- 保留 PowerPoint 原生動畫、轉場與字型樣式
- 避免使用 ASR/Whisper 造成字幕錯字與斷句不準
- 讓非技術使用者也能快速產出可發佈的簡報影片

---

## 2. 設計方向與技術選型

本專案採用「資料流管線」與「PowerPoint 原生自動化」架構：

1. 解析 .pptx 的頁數與備忘稿
2. 使用 Edge-TTS 產生逐頁語音
3. 透過 Windows COM 控制 PowerPoint 插入音訊並匯出 MP4
4. 根據備忘稿與音檔時長產生 SRT 字幕（PoC，尚未整合進主流程）

### 主要技術選型與原因

| 選型 | 原因 |
|---|---|
| TTS：`edge-tts` | 免費、免 API Key、語音自然 |
| PPT 自動化：`pywin32` / `win32com` | 可保留原生動畫與轉場，這是選擇 PowerPoint COM 而非其他影片合成方案（例如純粹用 ffmpeg 疊圖）的核心原因 |
| PPT 內容解析：`python-pptx` | 可直接讀取投影片與備忘稿，不需要另外解析 XML |
| 字幕輸出：自訂時間累加邏輯，而非 ASR/Whisper | 備忘稿文字本身就是逐字稿，用時間累加對齊可以得到零錯字字幕，不需要承擔語音辨識的辨識錯誤風險 |

---

## 3. PowerPoint COM 特性（重要，之後維護務必先讀）

這節記錄的是「花了實測才確認、但不查文件完全猜不到」的 PowerPoint COM 行為，是這個專案最容易踩坑的地方。

### `PlayOnEntry` 旗標

`shape.AnimationSettings.PlaySettings.PlayOnEntry` 這個舊版 API，雖然在 PowerPoint 編輯 UI 上完全看不出任何效果（Start 設定依然顯示「按一下時」），但**拿掉這個設定會讓 PowerPoint「建立視訊」匯出的 MP4 完全沒有聲音、且每頁變回固定 5 秒**，設定它之後匯出就正確無誤。目前程式碼（`ppt_automation.py: insert_audio`）固定會設定這個旗標，但底層原理尚未查證清楚——如果之後 PowerPoint 版本更新導致行為改變，這裡需要重新測試這個結論是否仍然成立。

### `CreateVideoStatus` 列舉值

`export_video()` 用來判斷匯出是否完成的 `CreateVideoStatus` 狀態值（none/in_progress/queued/done/failed），是依照 Microsoft 官方文件的 `PpMediaTaskStatus` 列舉假設，**並未逐一比對過所有 PowerPoint 版本**。目前已加上安全網：即使 API 回報「完成」，程式還是會額外檢查輸出檔案是否真的存在且非空，來降低誤判風險。如果之後在不同 PowerPoint 版本上遇到匯出邏輯誤判（例如卡住不進行、或誤報完成），這裡是優先排查的地方。

### 轉場時間不需要額外處理

原本規劃過「設定投影片自動播放與切換時間」，後來確認不需要——PowerPoint 的「建立視訊」匯出功能在沒有手動錄製時間的情況下，本來就會自動依嵌入媒體（也就是插入的音訊）的時長決定該頁停留多久，不需要額外邏輯去計算或設定。

### 現場放映模式仍需點擊音符圖示

透過 COM 的 `AddMediaObject2` 插入媒體時，音訊的 Start 設定固定顯示「按一下時」，跟手動用 UI 插入不同；曾嘗試透過 `slide.TimeLine.MainSequence` 修改動畫觸發方式，但在實測環境中不穩定（找不到對應效果）。**已確認這件事不影響 MP4 匯出**，只影響「投影片放映」現場播放模式，因此目前刻意不處理，優先確保匯出正確無誤。若之後有現場放映（非匯出影片）的需求，需要再回來解決。

### v0.4.1 修的兩個問題背後的原因

v0.4.1 修正的 `insert_audio()` 逾時保護與 `--tts-max-retries` 負值防呆，技術細節與程式碼變更請見 [CHANGELOG.md](CHANGELOG.md) 的對應條目。這裡只補充一個設計取捨：`insert_audio()` 的逾時是用背景執行緒 + `future.result(timeout=...)` 包住整段流程，而不是對個別 COM 呼叫個別加 timeout——因為 COM 呼叫本身沒有原生的逾時參數，唯一能做的是「限制等待這整段同步流程的總時間」，逾時後也**無法強制關閉卡住的 PowerPoint**，只能讓呼叫端不再繼續等待。這跟下面 5.5 節「COM 操作為何不做自動重試」是同一個風險考量的兩種展現方式。

---

## 4. 每個模組的責任範圍

### 4.1 pptx_parser.py
負責：
- 解析 .pptx
- 取得投影片數量
- 取得每頁備忘稿文字
- 處理空白頁或無 notes 的情況
- 解析失敗時拋出 `PptParseError`

### 4.2 tts.py
負責：
- 將文本轉為語音檔
- 使用 edge-tts 逐頁生成音檔
- 生成失敗時拋出 `TTSGenerationError`，訊息會標明是第幾頁失敗，並保留原始例外鏈
- 僅對判斷為暫時性的網路/服務錯誤重試（見 `_is_retryable`），`max_retries` 若傳負值會被 clamp 成 0，確保重試迴圈至少執行一次，不會出現「從未呼叫生成、卻仍記錄成功」的情況（v0.4.1 修正）

### 4.3 ppt_automation.py
負責：
- **`insert_audio()`**：啟動 PowerPoint（COM，`pywin32`）、開啟簡報檔、插入音訊（縮小圖示、移到投影片右上角、盡量在非播放狀態隱藏 `HideWhileNotPlaying`）、設定 `PlayOnEntry = True`（見第 3 節）。支援可選的 `timeout_seconds` 參數，逾時拋出 `AudioInsertionTimeoutError`（v0.4.1 新增）
- **`export_video()`**：呼叫 `Presentation.CreateVideo()` 觸發匯出（非同步 API），輪詢 `CreateVideoStatus` 直到完成/失敗/逾時，並在回報「完成」後額外檢查輸出檔案是否存在且非空（安全網，見第 3 節）
- 兩個函式共用 `_powerpoint_session()` / `_open_presentation()` 這兩個 context manager 處理開啟/關閉 PowerPoint 的邏輯，避免重複程式碼；PowerPoint 無法啟動或開啟簡報時拋出 `PowerPointLaunchError`，插入完成後存檔失敗拋出 `AudioInsertionError`，匯出失敗/逾時拋出 `VideoExportError` / `VideoExportTimeoutError`
- 確保 COM 物件正常釋放（`Presentation.Close()` / `Application.Quit()`，皆包在 `finally` 區塊）

尚未負責（規劃中，優先度較低）：
- 投影片自動播放（現場放映模式）：目前刻意不處理，因為已確認不影響 MP4 匯出結果

### 4.4 subtitle_generator.py
負責：
- 接收文本與每頁時長
- 進行時間累加
- 輸出 .srt 檔

### 4.5 exceptions.py
負責：
- 定義專案自訂例外階層，共同基底 `Pptx2VideoError`
- `PptParseError`、`TTSGenerationError`、`PowerPointLaunchError`、`AudioInsertionError`、`AudioInsertionTimeoutError`、`VideoExportError`、`VideoExportTimeoutError`——兩個 `*TimeoutError` 同時也是內建 `TimeoutError` 的子類別，向下相容只認得 `TimeoutError` 的呼叫端
- `FileNotFoundError`、`ValueError` 等語意已經明確的 Python 內建例外故意不重新包裝

### 4.6 logging_config.py
負責：
- 提供 `setup_logging()` 統一設定 Logging：終端機維持原本簡潔風格（無時間戳記），log 檔案（`logs/YYYY-MM-DD.log`）永遠記錄完整 DEBUG 細節、不受 `--verbose` 影響
- 重複呼叫時具備冪等性：`log_dir` 沒變就不重建 handler（避免重複輸出），`log_dir` 改變則正確關閉舊 handler 並重建
- log 資料夾無法寫入時優雅降級成只輸出到終端機，不會讓程式崩潰
- 提供 `shutdown_logging()` 供測試或需要主動釋放 log 檔案控制權的情境使用

### 4.7 main.py
負責：
- 串接上面所有模組
- 提供 CLI 入口
- 決定輸入與輸出路徑
- 讓使用者只需執行一個命令即可完成流程
- 統一在 `_fail()` 這個 helper 裡處理錯誤：先寫進 log（`logger.error()`），再透過 `parser.error()` 印給使用者看並結束程式

---

## 5. 開發注意事項

### 5.1 Windows-only 限制
這個專案的核心依賴是 PowerPoint 的 COM 自動化，因此目前設計上必須以 Windows 環境為主。測試套件透過假的 COM 物件（見 `tests/test_ppt_automation.py`）讓大部分邏輯可以在任何作業系統跑，但這不能取代在真實 Windows + PowerPoint 環境的實測——第 3 節列的所有 COM 行為都是這樣實測出來的。

### 5.2 PowerPoint 動畫處理
若簡報中包含動畫，PowerPoint 匯出影片時可能會改變某些互動觸發方式。

建議規範：
- 盡量使用「After Previous」與 delay 設定
- 避免過度依賴 click-triggered 動畫

### 5.3 COM 物件釋放
使用 win32com 時，務必在 try/finally 中關閉 PowerPoint，避免背景殘留執行緒或記憶體洩漏。`_powerpoint_session()` / `_open_presentation()` 已經封裝了這個邏輯，新增功能時應該重用這兩個 context manager，不要自己再開一套。

### 5.4 字幕與語音同步
字幕與音檔時長必須一致，避免出現時間漂移。建議：
- 以每頁音訊時長為基準
- 用累加時間軸建立字幕

### 5.5 COM 操作為何不做自動重試

TTS 網路請求有自動重試機制（見 4.2），但 `insert_audio()` / `export_video()` 這類 COM 操作刻意不做自動重試：重試前如果沒有先確保舊的 PowerPoint 物件已經完全關閉，重試反而可能製造殭屍程序，風險大於效益。這是跟「插入逾時只停止等待、不強制關閉」（見第 3 節最後一段）同一個風險考量下的一致決策，之後如果要改變這個決策，需要先解決「如何確認舊 PowerPoint 行程已清乾淨」這個前提問題。

---

## 6. 維護建議

- **修改 `insert_audio()` / `export_video()` 前，先讀完第 3 節**：這兩個函式的行為高度依賴實測發現的 COM 特性（`PlayOnEntry`、`CreateVideoStatus`），單看程式碼容易誤以為某些設定是多餘的而砍掉。
- **版本相容性尚未正式驗證**：目前沒有明確記錄專案在哪些 Python 版本（`pyproject.toml` 只寫 `>=3.9`）、哪些 PowerPoint 版本上實測過。如果之後要支援更多環境，建議先補上這份相容性矩陣，尤其是 `CreateVideoStatus` 列舉值這種「文件說的跟實測不一定一致」的地方。
- **輸出資料夾規劃還很粗略**：目前只有 `output/`、`logs/`、`temp/` 幾個目錄，沒有正式規範哪些檔案該放哪裡、要保留多久。專案目前刻意不自動清理暫存檔（見 [TODO.md](TODO.md)），但如果之後要做批次處理，這塊需要重新設計。
- **新增功能前，先確認 CHANGELOG.md / TODO.md 是否需要同步更新**：Round 1 文件整理時發現過「TODO 裡某項目其實已經實作完成，但checkbox 沒打勾」這種文件落後於程式碼的情況，之後每次合併新功能都建議順手檢查這兩份文件有沒有跟上。

---

## 7. 未來擴充方向

近期、具體可執行的待辦事項維護在 [TODO.md](TODO.md)，這裡只記錄需要架構層級思考、還沒到可以直接排進待辦的方向：

- **現場放映自動播放**：解決第 3 節提到的「插入音訊後現場放映仍需點擊」問題。目前判斷優先度低，因為已確認不影響 MP4 匯出這條主要路徑；如果之後有真的需要現場簡報（非僅匯出影片）的使用情境，才需要回來重新研究 `slide.TimeLine.MainSequence` 或其他 COM API。
- **字幕生成正式化**：目前 `subtitle_generator.py` 是獨立的 PoC，尚未整合進 `main.py` 的主流程，也還沒對齊 README 描述的「零錯字字幕」精確度目標（智慧斷句、閱讀節奏優化、Tokenizer 等）。
- **批次處理與輸出目錄管理**：支援多檔輸入、更完整的輸出目錄規劃，跟第 6 節「輸出資料夾規劃還很粗略」是同一件事的兩個角度。
- **同一個 PowerPoint session 共用**：目前 `--insert-audio` 跟 `--export-video` 在同一行指令裡執行時，PowerPoint 會被開關兩次（各自獨立完成後就關閉）。這不影響結果，只是多花一點時間；如果之後有大量批次處理、在意這個開銷，可以優化成同一個 session 共用，但需要重新設計 `_powerpoint_session()` 的生命週期管理。

暫不處理、優先度更低的方向（超出目前專案定位，需要更大規模重新設計才能做）：
- GUI 支援
- Plugin 架構
- 更細粒度的 Output Validation（目前只驗證檔案存在且非空，「能否開啟」「影片長度是否合理」等更進階檢查暫緩，等有實際需求再做）

---

## 給接手人的一句話

這是一個「有明確願景、架構清楚、技術路線可行」的專案，核心流程（pptx → 帶配音的 MP4）已經完整打通並在真實 Windows + PowerPoint 環境驗證過。接手時最重要的資源是第 3 節「PowerPoint COM 特性」——那些都是花時間實測出來的坑，不要在不了解原因的情況下移除或簡化那些看似多餘的設定。
