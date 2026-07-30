# 待辦事項

## 高優先

- PowerPoint 自動化
  - [x] 插入音訊（`ppt_automation.py: insert_audio`，已搭配 MP4 匯出驗證正確）
  - [x] ~~自動播放~~ — 匯出 MP4 不需要這個：PowerPoint「建立視訊」會忽略編輯畫面上「按一下時／自動」的設定，直接依內嵌音訊本身的時長播放。如果之後有現場放映（非匯出影片）的需求，這仍是待處理項目，詳見下方「已知限制」。
  - [x] ~~轉場時間設定~~ — 不需要：PowerPoint 匯出「建立視訊」在沒有手動錄製時間的情況下，本來就會自動依嵌入音訊的時長決定每頁停留多久，不需要額外邏輯。
- MP4 匯出
  - [x] 透過 COM 自動觸發 PowerPoint「建立視訊」（`ppt_automation.py: export_video`）。已在真實 Windows + PowerPoint 環境完整驗證：影片正確產生，每頁時長對齊音訊長度。

## 穩定性改善計劃（Robustness）

依 v0.3.0 之後的穩定性提升規劃，已從 `robustness-improvements` 分支合併回 `main`（v0.4.0）：

- [x] Exception 分類（`src/exceptions.py`）：`PptParseError`、`TTSGenerationError`、`PowerPointLaunchError`、`AudioInsertionError`、`VideoExportError`、`VideoExportTimeoutError`，取代原本泛用的 `RuntimeError`
- [x] 正式 Logging（`src/logging_config.py`）：終端機維持原本簡潔輸出，同時永遠把完整 DEBUG 細節記錄到 `logs/YYYY-MM-DD.log`，不受 `--verbose` 影響；新增 `--log-dir`、`--no-file-log` 兩個 CLI 參數
- [x] `--generate-audio` 補上錯誤處理（原本完全沒有，`--insert-audio`/`--export-video` 有但這個沒有）
- [x] COM 開關邏輯重構去重複（`insert_audio()` 與 `export_video()` 共用 `_powerpoint_session()` / `_open_presentation()`，與 Exception 分類一起做，因為兩者都要動到同一段程式碼）
- [x] Recoverable Error Policy 文件化：整理成 README.md 的「錯誤處理策略（Skip vs Abort）」表格。過程中討論過是否把 TTS 生成失敗改成「單頁失敗記錄、繼續處理其他頁」，**決定維持現狀（fail fast）**——TTS 失敗常是系統性問題（服務掛掉、網路斷線），fail fast 能立刻讓使用者知道，不用等所有頁面都跑過一輪才發現全部失敗
- [ ] Retry 機制：**僅限 TTS 網路請求**（失敗重試最多 3 次、間隔 2 秒）。COM 操作暫不做重試，因為失敗重試前若沒有先確保舊的 PowerPoint 物件已關閉，反而可能製造殭屍程序，風險大於效益
- [ ] `--insert-audio` 的進度顯示（`--generate-audio` 和 `--export-video` 都已經有即時進度回報，插入音訊的迴圈還沒有）
- [ ] Output Validation 強化（目前只驗證檔案存在且非空，更進階的檢查如「能否開啟」「影片長度是否合理」先不做，等有實際需求再考慮）
- [x] `insert_audio()` 補上逾時保護：新增 `--insert-audio-timeout`（預設 1800 秒），透過背景執行緒 + `concurrent.futures` 的 `future.result(timeout=...)` 包住整個插入+存檔流程，逾時會拋出新的 `AudioInsertionTimeoutError`（同時也是 `TimeoutError` 子類別，用法與 `VideoExportTimeoutError` 一致）。**注意此逾時只是停止等待，無法強制關閉卡住的 PowerPoint 行程**，這點與專案既有「COM 操作不做自動重試」的風險考量一致
- [x] 修正 `--tts-max-retries` 負值的靜默錯誤：`range(1, max_retries + 2)` 在 `max_retries` 為負值時會是空迴圈，導致 TTS 生成函式從未被實際呼叫，卻仍把該頁記錄成生成成功寫進 `manifest.json`。已在 `tts.generate_audio_files()` 內部把負值 clamp 成 0 作為防呆，並在 CLI 層用 `type=_non_negative_int` 直接拒絕負值、給出明確錯誤訊息

已評估、決定不做：
- Temporary File Cleanup（自動清除 `output/audio`、`manifest.json` 等）——會打斷分階段執行的工作流程（例如今天先 `--generate-audio`，明天才 `--insert-audio`），刻意保留現狀

## 已知限制（目前不打算修）

- 插入的音訊在 PowerPoint 編輯 UI 仍顯示「按一下時」，用「投影片放映」現場播放時需要點擊才會出聲。已確認**不影響**匯出的 MP4 影片。只有在未來真的需要現場放映自動播放時才需要回頭處理。
- `CreateVideoStatus` 的狀態列舉值是依 Microsoft 官方文件假設，未逐一比對所有 PowerPoint 版本。程式碼已加上安全網（回報「完成」後仍會檢查輸出檔案是否存在、非空）來降低這個風險。

## 低優先

- 字幕生成器（實驗性 PoC）
  - 智慧斷句
  - 閱讀節奏優化
  - Tokenizer
  - 整合進正式管線（目前是獨立的 PoC，未串接主流程）
