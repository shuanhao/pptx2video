# Changelog

本文件記錄 pptx2video 各版本的重要變更，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

> **關於版本歷史準確性的說明**：`v0.4.0`、`v0.4.1` 這兩版是在有完整討論記錄的情況下整理的，內容與日期可信。`v0.3.0` 以前的條目是依專案現有文件（README / TODO / PROJECT_HANDOVER）回溯重建的功能里程碑，**並非依實際 git commit 紀錄逐筆核對**，日期為不詳、版本切分點也是概略推估。如果之後要對照實際 commit 歷史修正這段，請直接編輯下方對應章節。

## [未發布]

### Added

- 新增 `tests/test_cli_end_to_end.py`：直接呼叫 `src.main.main()`（跟真正的 CLI 入口一樣的路徑），涵蓋解析、`--generate-audio`（mock 掉 edge-tts 網路呼叫，不需要真的連網）、`--tts-max-retries` 負值拒絕、`--strict`、`--pretty`、找不到檔案等錯誤處理的完整流程。補足先前測試都只測個別函式（`extract_notes`、`build_payload`、`generate_audio_files`…）、沒有任何測試真正跑過 `main()` 本身的缺口。`--insert-audio`/`--export-video` 仍需要真實 Windows + PowerPoint，不在這個模組的涵蓋範圍內。測試總數由 52 個增加到 58 個。

## [0.4.1] - 2026-07-30

### Fixed

- 修正 `--tts-max-retries` 傳負值時的靜默錯誤：重試迴圈原本寫成 `range(1, max_retries + 2)`，當 `max_retries` 為負值時這個 range 會是空的，導致 TTS 生成函式從未被實際呼叫過，卻仍把該頁記錄成生成成功寫進 `manifest.json`。現在 `tts.generate_audio_files()` 會把負值 clamp 成 `0`，CLI 層（`main.py` 的 `_non_negative_int`）也會直接拒絕負值並回報明確錯誤。
- 修正 `insert_audio()` 沒有逾時保護的問題：原本插入音訊時的所有 COM 呼叫（開啟簡報、插入音訊、存檔）都是同步阻塞，PowerPoint 卡住（例如被信任設定/修復對話框擋住）會讓整個流程無限期掛住。新增可選的 `timeout_seconds` 參數，透過背景執行緒 + `concurrent.futures` 的 `future.result(timeout=...)` 包住整段流程。

### Added

- 新增例外類別 `AudioInsertionTimeoutError`（繼承 `AudioInsertionError` 與內建 `TimeoutError`），逾時時拋出，用法比照既有的 `VideoExportTimeoutError`。
- CLI 新增 `--insert-audio-timeout` 參數（預設 1800 秒，設為 `0` 可恢復無限期等待的舊行為）。
- 補上對應的回歸測試（`tests/test_tts_generator.py`、`tests/test_pptx_parser.py`、`tests/test_ppt_automation.py`），測試總數由 47 個增加到 52 個。

### Changed

- `pyproject.toml` 的 `description` 從「Parse PowerPoint notes and export slide metadata as JSON」更新為「Convert PowerPoint presentations into narrated MP4 videos using Edge-TTS and PowerPoint automation」，反映目前實際功能範圍。
- `main.py` 的 `extract_notes()` try/except 改用 `else` 區塊，讓「所有例外分支都會經由 `_fail()` 結束程式，因此 `slides` 保證會被賦值」這件事更明確。

## [0.4.0] - 2026-07-28

延續 v0.3.0 之後規劃的穩定性（Robustness）改善，從 `robustness-improvements` 分支合併回 `main`。

### Added

- 自訂例外階層（`src/exceptions.py`）：`Pptx2VideoError` 為共同基底，底下有 `PptParseError`、`TTSGenerationError`、`PowerPointLaunchError`、`AudioInsertionError`、`VideoExportError`、`VideoExportTimeoutError`（同時也是內建 `TimeoutError` 子類別），取代原本泛用的 `RuntimeError`。
- 正式 Logging（`src/logging_config.py`）：終端機維持原本簡潔輸出風格（無時間戳記），同時永遠把完整 DEBUG 細節記錄到 `logs/YYYY-MM-DD.log`，不受 `--verbose` 影響。新增 CLI 參數 `--log-dir`、`--no-file-log`。
- TTS 生成的重試機制：僅套用在 edge-tts 網路請求上（區分可重試/不可重試的錯誤類型，例如缺 ffmpeg、憑證錯誤不重試），新增 CLI 參數 `--tts-max-retries`（預設 3）、`--tts-retry-delay`（預設 2 秒）。COM 操作（PowerPoint 自動化）刻意不做自動重試，見 README「錯誤處理策略」與下方「已評估、決定不做」。
- README 新增「錯誤處理策略（Skip vs Abort）」表格，把原本隱含在程式邏輯裡的規則文件化。

### Changed

- `--generate-audio` 補上錯誤處理（原本完全沒有，`--insert-audio`/`--export-video` 有但這個沒有）。
- `insert_audio()` 與 `export_video()` 共用的 COM 開關邏輯重構去重複，抽成 `_powerpoint_session()` / `_open_presentation()` 兩個 context manager。

## [0.3.0 及更早版本] - 日期不詳（回溯整理）

> 以下內容依現有文件重建的功能里程碑，非逐筆 commit 紀錄，版本切分點為概略推估。

### Added

- 建立 CLI 入口（`src/main.py`），可解析 `.pptx` 並輸出結構化 JSON。
- PowerPoint notes 解析（`src/pptx_parser.py`）：讀取投影片編號、標題、備忘稿，支援多頁簡報、長段落、空白行、無 notes 頁面（自動跳過生成音訊）。
- Edge-TTS 音訊生成（`src/tts.py`）：把備忘稿轉成 MP3，依頁碼命名，並產生 `manifest.json`。
- PowerPoint 音訊插入自動化（`src/ppt_automation.py: insert_audio`）：透過 `pywin32` COM 自動化，把生成的 MP3 插入對應投影片，圖示縮小並移到右上角、盡量在非播放狀態隱藏。
- MP4 匯出自動化（`src/ppt_automation.py: export_video`）：透過 `Presentation.CreateVideo()` 觸發 PowerPoint「建立視訊」，輪詢非同步匯出狀態直到完成，並在回報完成後額外檢查輸出檔案確實存在（安全網）。
- 字幕生成 PoC（`src/subtitle_generator.py`）：依備忘稿與（若可用）實際音檔時長輸出 `.srt`，作為架構驗證，尚未整合進正式管線（此功能不在本次文件整理範圍內）。
- 範例簡報生成腳本（`examples/create_sample_pptx.py`）與初版單元測試。
