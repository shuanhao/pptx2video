# Changelog

本文件記錄 pptx2video 各版本的重要變更，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

> **關於版本歷史準確性的說明**：`v0.4.0`、`v0.4.1` 這兩版是在有完整討論記錄的情況下整理的，內容與日期可信。`v0.3.0` 以前的條目是依專案現有文件（README / TODO / PROJECT_HANDOVER）回溯重建的功能里程碑，**並非依實際 git commit 紀錄逐筆核對**，日期為不詳、版本切分點也是概略推估。如果之後要對照實際 commit 歷史修正這段，請直接編輯下方對應章節。

## [未發布]

## [0.5.0] - 2026-07-31

字幕功能從實驗性 PoC 正式畢業：原本 `subtitle_generator.py` 用「音檔總長度平均分配」估算每句字幕時間的做法，換成真正依照 edge-tts 回報的逐字/逐詞語音時間對齊，並整合進 `main.py` 的正式管線。分五個階段完成，設計討論與真實內容驗證過程詳見專案討論記錄。

### Added

- **`src/tts.py`**：新增 `synthesize_with_word_boundaries()` / `_stream_edge_tts_audio_with_word_boundaries()`，透過 edge-tts 的 streaming API（`boundary="WordBoundary"`）取得每個語音片段的文字與時間（`offset_seconds`/`duration_seconds`），而不只是純音檔。`boundary` 參數是 edge-tts 7.2.0 才加入的，若偵測到 `TypeError`（舊版函式庫）會自動退回不帶這個參數的呼叫方式。
- **`src/subtitle_segmenter.py`**（新模組）：把備忘稿文字切成適合當一行字幕的片段，純文字運算、不涉及語音或時間。依顯示寬度（預設 16 全形字／32 半形，區分全形/半形字元）斷行，用 `jieba` 做中文斷詞避免從詞語中間硬切，去除句尾多餘標點（保留？！），正規化中英文交界的空白，段落永遠是硬邊界不跨段合併，多行需要時用動態規劃讓每行寬度盡量平均（而非貪婪塞滿導致零碎孤兒行）。
- **`src/subtitle_alignment.py`**（新模組）：把 Phase 2 切好的字幕片段對齊到 Phase 1 的 WordBoundary 時間資料，算出每行的起訖秒數，並提供 `format_srt()` 轉成標準 SRT 文字。核心是逐一比對 WordBoundary 事件的文字在原文中的位置（因為 edge-tts 本身不回傳字元位置），比對失敗時採寬鬆策略（模糊比對、必要時內插猜測），不會讓單一比對失誤中斷整段字幕產生，所有比對失誤都會記錄在回傳的 `warnings` 清單。每行字幕的結束時間會延伸到下一行開始前留一小段緩衝（預設 0.15 秒），涵蓋語句間的自然停頓。
- **`src/subtitle_pipeline.py`**（新模組）：把多張投影片各自對齊好的字幕，依照它們在最終匯出影片裡的實際時間軸（每張投影片的時長 = 音訊檔案實際長度，或沒有備忘稿時的 `default_slide_duration`）平移、串接成一份完整的 SRT。這個時間軸假設有實際用 `scripts/verify_slide_timing.py`（音訊互相關比對）在真實匯出的 MP4 上驗證過，避免誤踩其他使用者回報過的 PowerPoint 匯出「死寂空白」問題。
- `tts.generate_audio_files()` 現在預設（沒有自訂 `generator` 時）會用 `synthesize_with_word_boundaries()` 當底層實作，同一次 TTS 呼叫就順便把每張投影片的 WordBoundary 時間存成旁路檔案 `slide_XXX.wordboundaries.json`，並在 `manifest.json` 記錄檔名（欄位 `word_boundaries_file`），不需要為了字幕另外重打一次 TTS。新增 `communicate_factory` 參數方便測試注入假的 edge-tts 回應。
- `main.py` 的 `--subtitles-output` 改接上述整條鏈路：有可用的 WordBoundary 資料時產生真正對齊過的字幕；沒有時（沒跑 `--generate-audio` 也找不到既有 manifest）寫出合法但空白的 `.srt`，而不是報錯或退回舊的粗略估算。
- 新增 `jieba>=0.42.1` 依賴（`requirements.txt` / `pyproject.toml`）。
- `edge-tts` 版本需求提升為 `>=7.2.0`（`boundary` 參數是這個版本才加入的）。
- 新增手動驗證腳本（因為 sandbox 開發環境連不上 edge-tts/沒有真實 Windows + PowerPoint，這些邏輯需要在真實環境驗證）：`scripts/smoke_test_word_boundaries.py`、`scripts/smoke_test_alignment.py`、`scripts/verify_slide_timing.py`，以及配套的 `scripts/sample_notes_for_smoke_test.txt`。
- 新增 `tests/test_cli_end_to_end.py`：直接呼叫 `src.main.main()`（跟真正的 CLI 入口一樣的路徑），涵蓋解析、`--generate-audio`（mock 掉 edge-tts 網路呼叫，不需要真的連網）、`--tts-max-retries` 負值拒絕、`--strict`、`--pretty`、找不到檔案等錯誤處理的完整流程，以及本次新增的字幕產生流程。補足先前測試都只測個別函式（`extract_notes`、`build_payload`、`generate_audio_files`…）、沒有任何測試真正跑過 `main()` 本身的缺口。`--insert-audio`/`--export-video` 仍需要真實 Windows + PowerPoint，不在這個模組的涵蓋範圍內。
- 新增 `tests/test_subtitle_segmenter.py`、`tests/test_subtitle_alignment.py`、`tests/test_subtitle_pipeline.py`，以及 `tests/test_tts_generator.py`/`tests/test_tts_word_boundaries.py`/`tests/test_main_payload.py` 的對應新測試。測試總數由 58 個增加到 114 個。

### Changed

- `main.py` 的 `write_subtitle_output()` 改為呼叫 `subtitle_pipeline.generate_srt_for_deck()`，回傳值也從單純的 `Path` 改成 `(Path, warnings)`，warnings 會透過 logger 印出（例如某張投影片沒有可用的 WordBoundary 資料時）。

### Removed

- **`src/subtitle_generator.py`（原本的字幕 PoC）與 `tests/test_subtitle_generator.py`**：功能已被上述新模組取代，`main.py` 也已經不再呼叫它，故從專案移除，避免兩套字幕邏輯同時存在造成混淆。舊邏輯用「音檔總長度平均分配」估算時間，不是真正對齊語音；新邏輯精確度高很多。

### Known limitations（已記錄於 TODO.md，刻意暫緩）

- 原文中「例如：」這類自成一段的極短段落，因為段落是硬邊界，會產生顯示時間很短的獨立字幕行。
- 純英文內容在目前針對中文調校的行寬設定下，換行位置有時不夠自然（可能切在片語中間，但不會切在單字中間）。

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
