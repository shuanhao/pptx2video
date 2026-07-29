# 專案交接報告

## 專案名稱
pptx2video (PPTX Auto Presenter)

## 文件版本
v0.3.0 (Core Pipeline Complete: pptx to MP4)

## 目標對象
接手開發者、AI 協作 Agent

## 撰寫日期
2026-07-26（v0.3.0 更新）

---

## 1. 專案願景與目標

pptx2video 是一套針對 Windows 桌面環境設計的輕量化自動化工具，目標是將 PowerPoint 簡報檔（.pptx）轉換為具備語音配音、動畫保留與精確字幕的 MP4 影片。

### 核心價值
- 減少人工逐張錄音與排練時間
- 保留 PowerPoint 原生動畫、轉場與字型樣式
- 避免使用 ASR/Whisper 造成字幕錯字與斷句不準
- 讓非技術使用者也能快速產出可發佈的簡報影片

---

## 2. 目前設計的技術方向

本專案採用「資料流管線」與「PowerPoint 原生自動化」架構：

1. 解析 .pptx 的頁數與備忘稿
2. 使用 Edge-TTS 產生逐頁語音
3. 透過 Windows COM 控制 PowerPoint 插入音訊並匯出 MP4
4. 根據備忘稿與音檔時長產生 SRT 字幕

### 主要技術選型
- TTS：edge-tts
  - 優點：免費、免 API Key、語音自然
- PPT 自動化：pywin32 / win32com
  - 優點：可保留原生動畫與轉場
- PPT 內容解析：python-pptx
  - 優點：可讀取投影片與備忘稿
- 字幕輸出：自訂時間累加邏輯
  - 優點：可獲得零錯字字幕

---

## 3. 目前專案實際狀態

目前倉庫已完成一個可用的里程碑版本，並且已把 TTS 流程初步接上：
- 已建立 CLI 入口：[src/main.py](src/main.py)
- 已實作 PowerPoint notes 解析：[src/pptx_parser.py](src/pptx_parser.py)
- 已實作 edge-tts 音訊生成：[src/tts.py](src/tts.py)
- 已支援多頁簡報、長段落、空白行、無 notes 頁面處理，並在無 notes 頁面跳過生成音訊
- 已提供可供後續字幕流程使用的 JSON 輸出，包含 `subtitle_text`、`has_notes`、`audio_file` 等欄位
- 已提供範例簡報生成腳本：[examples/create_sample_pptx.py](examples/create_sample_pptx.py)
- 已實作字幕生成 PoC：[src/subtitle_generator.py](src/subtitle_generator.py)
- 已實作 PowerPoint 音訊插入：[src/ppt_automation.py](src/ppt_automation.py)，透過 `pywin32` COM 自動化把音訊插入對應投影片（縮小圖示、移到右上角、盡量隱藏），並已在真實 Windows + PowerPoint 環境驗證：搭配 PowerPoint「建立視訊」匯出 MP4 時，每頁會正確依音檔長度播放並自動切換
- 已實作 MP4 匯出自動化：同樣在 [src/ppt_automation.py](src/ppt_automation.py) 的 `export_video()`，透過 `Presentation.CreateVideo()` 觸發匯出並輪詢非同步狀態，**已在真實 Windows + PowerPoint 環境完整驗證：影片正確產生，聲音與每頁時長皆對齊**
- 已加入單元測試：[tests/test_pptx_parser.py](tests/test_pptx_parser.py)、[tests/test_tts_generator.py](tests/test_tts_generator.py)、[tests/test_subtitle_generator.py](tests/test_subtitle_generator.py)、[tests/test_ppt_automation.py](tests/test_ppt_automation.py)、[tests/test_main_payload.py](tests/test_main_payload.py)

目前仍未實作的部分：
- 現場簡報放映模式的真正自動播放（目前音訊在 PowerPoint 編輯 UI 仍顯示「按一下時」，只有匯出影片的情境已驗證不受影響，見下方「重要實測發現」）
- `--insert-audio` 的迴圈還沒有即時進度顯示（`--generate-audio` 和 `--export-video` 都已經有）

這表示目前專案已經完成從「pptx → 帶配音的 MP4」的完整核心流程，並在真實環境驗證通過。剩下的主要缺口是次要體驗優化（現場放映點擊問題、部分步驟的進度顯示），以及原本就定調為非必要路徑的字幕正式化。

### 重要實測發現：`PlayOnEntry` 旗標

在開發過程中發現一個不直觀但重要的行為：`shape.AnimationSettings.PlaySettings.PlayOnEntry` 這個舊版 API，雖然在 PowerPoint 編輯 UI 上完全看不出任何效果（Start 設定依然顯示「按一下時」），但**拿掉這個設定會讓 PowerPoint「建立視訊」匯出的 MP4 完全沒有聲音、且每頁變回固定 5 秒**，設定它之後匯出就正確無誤。目前程式碼固定會設定這個旗標，但底層原理尚未查證清楚，如果之後 PowerPoint 版本行為改變，需要重新測試這個結論是否仍然成立。

### 另一個待留意的假設：`CreateVideoStatus` 列舉值

`export_video()` 用來判斷匯出是否完成的 `CreateVideoStatus` 狀態值（none/in_progress/queued/done/failed），是依照 Microsoft 官方文件的 `PpMediaTaskStatus` 列舉假設，**並未逐一比對過所有 PowerPoint 版本**。目前已加上安全網：即使 API 回報「完成」，程式還是會額外檢查輸出檔案是否真的存在且非空，來降低誤判風險。如果之後在不同 PowerPoint 版本上遇到匯出邏輯誤判（例如卡住不進行、或誤報完成），這裡是優先排查的地方。

---

## 4. 建議的實作順序

### Phase 1：已完成的基礎解析原型
已完成下列功能：
- 讀取一個 .pptx 檔
- 擷取每頁的標題與 notes
- 支援多頁、長段落、空白行與無 notes 頁面
- 輸出 JSON 並提供 CLI 介面

這個階段已經讓流程可跑通，並建立可作為後續擴充的基礎。

### Phase 2：語音與資料流程
目前已完成：
- 讀取整份簡報的 notes
- 逐頁生成語音檔
- 輸出可供後續字幕流程使用的 JSON 結構

下一步要實作：
- 根據音訊與 notes 生成 `.srt` 字幕（PoC 已完成，正式整合進管線待辦，見 Phase 4）

### Phase 3：PowerPoint 輸出與動畫保留
已完成：
- 開啟 PowerPoint（COM）
- 插入音檔（縮小圖示、移到右上角、盡量隱藏）
- 驗證搭配「建立視訊」匯出 MP4 時播放與時長正確
- 透過 COM 自動觸發「建立視訊」匯出 MP4（`export_video()`，含非同步狀態輪詢與逾時保護），**已在真實 Windows + PowerPoint 環境完整驗證**

下一步（優先度較低）：
- 若有現場放映需求，解決音訊仍需點擊才播放的限制（不影響匯出影片）

> 備註：原本規劃的「設定投影片自動播放與切換時間」已確認不需要額外處理——PowerPoint 的「建立視訊」匯出功能在沒有手動錄製時間的情況下，本來就會自動依嵌入媒體的時長決定該頁停留多久。

### Phase 4：穩定性與產品化
已完成（v0.3.0 之後，於 `robustness-improvements` 分支進行，尚未合併回 `main`）：
- 自訂例外階層（`src/exceptions.py`），取代泛用的 `RuntimeError`
- 正式 Logging（`src/logging_config.py`），終端機維持簡潔輸出，log 檔案永遠記錄完整 DEBUG 細節
- `--generate-audio` 補上原本缺失的錯誤處理
- COM 開關邏輯重構去重複（與例外分類一起做）

待補強項目：
- Recoverable Error Policy 文件化（把隱含規則整理成明確表格）
- Retry 機制（僅限 TTS 網路請求，COM 操作暫不做，風險考量見 TODO.md）
- `--insert-audio` 的進度顯示
- 暫存檔與輸出資料夾管理（已評估，決定維持現狀不自動清除，見 TODO.md）

---

## 5. 每個模組的責任範圍

### 5.1 pptx_parser.py
負責：
- 解析 .pptx
- 取得投影片數量
- 取得每頁備忘稿文字
- 處理空白頁或無 notes 的情況
- 解析失敗時拋出 `PptParseError`

### 5.2 tts_engine.py
負責：
- 將文本轉為語音檔
- 使用 edge-tts 逐頁生成音檔
- 取得每段語音的時長
- 將音檔存於 temp_audios/
- 生成失敗時拋出 `TTSGenerationError`，訊息會標明是第幾頁失敗，並保留原始例外鏈

### 5.3 ppt_automation.py
負責：
- **`insert_audio()`**：啟動 PowerPoint（COM，`pywin32`）、開啟簡報檔、插入音訊（縮小圖示、移到投影片右上角、盡量在非播放狀態隱藏 `HideWhileNotPlaying`）、設定 `PlayOnEntry = True`（實測發現匯出 MP4 是否正確依賴這個舊版旗標，即使編輯 UI 看不出效果）
- **`export_video()`**：呼叫 `Presentation.CreateVideo()` 觸發匯出（非同步 API），輪詢 `CreateVideoStatus` 直到完成/失敗/逾時，並在回報「完成」後額外檢查輸出檔案是否存在且非空（安全網，避免狀態列舉值與實際版本行為不一致時誤判成功）
- 兩個函式共用 `_powerpoint_session()` / `_open_presentation()` 這兩個 context manager 處理開啟/關閉 PowerPoint 的邏輯，避免重複程式碼；PowerPoint 無法啟動或開啟簡報時拋出 `PowerPointLaunchError`，插入完成後存檔失敗拋出 `AudioInsertionError`，匯出失敗/逾時拋出 `VideoExportError` / `VideoExportTimeoutError`
- 確保 COM 物件正常釋放（`Presentation.Close()` / `Application.Quit()`，皆包在 `finally` 區塊）

尚未負責（規劃中，優先度較低）：
- 投影片自動播放（現場放映模式）：目前刻意不處理，因為已確認不影響 MP4 匯出結果

### 5.4 subtitle_generator.py
負責：
- 接收文本與每頁時長
- 進行時間累加
- 輸出 .srt 檔

### 5.5 exceptions.py
負責：
- 定義專案自訂例外階層，共同基底 `Pptx2VideoError`
- `PptParseError`、`TTSGenerationError`、`PowerPointLaunchError`、`AudioInsertionError`、`VideoExportError`、`VideoExportTimeoutError`（同時也是內建 `TimeoutError` 的子類別，向下相容只認得 `TimeoutError` 的呼叫端）
- `FileNotFoundError`、`ValueError` 等語意已經明確的 Python 內建例外故意不重新包裝

### 5.6 logging_config.py
負責：
- 提供 `setup_logging()` 統一設定 Logging：終端機維持原本簡潔風格（無時間戳記），log 檔案（`logs/YYYY-MM-DD.log`）永遠記錄完整 DEBUG 細節、不受 `--verbose` 影響
- 重複呼叫時具備冪等性：`log_dir` 沒變就不重建 handler（避免重複輸出），`log_dir` 改變則正確關閉舊 handler 並重建
- log 資料夾無法寫入時優雅降級成只輸出到終端機，不會讓程式崩潰
- 提供 `shutdown_logging()` 供測試或需要主動釋放 log 檔案控制權的情境使用

### 5.7 main.py
負責：
- 串接上面所有模組
- 提供 CLI 入口
- 決定輸入與輸出路徑
- 讓使用者只需執行一個命令即可完成流程
- 統一在 `_fail()` 這個 helper 裡處理錯誤：先寫進 log（`logger.error()`），再透過 `parser.error()` 印給使用者看並結束程式

---

## 6. 開發注意事項

### 6.1 Windows-only 限制
這個專案的核心依賴是 PowerPoint 的 COM 自動化，因此目前設計上必須以 Windows 環境為主。

### 6.2 PowerPoint 動畫處理
若簡報中包含動畫，PowerPoint 匯出影片時可能會改變某些互動觸發方式。

建議規範：
- 盡量使用「After Previous」與 delay 設定
- 避免過度依賴 click-triggered 動畫

### 6.3 COM 物件釋放
使用 win32com 時，務必在 try/finally 中關閉 PowerPoint，避免背景殘留執行緒或記憶體洩漏。

### 6.4 字幕與語音同步
字幕與音檔時長必須一致，避免出現時間漂移。建議：
- 以每頁音訊時長為基準
- 用累加時間軸建立字幕

---

## 7. 目前文件的優點

這份設計文件的優點在於：
- 願景清楚且具體
- 技術選型合理
- 模組拆分清楚
- 下一步任務順序明確
- 已經把關鍵風險點（動畫、COM、字幕同步）列出

這種文件非常適合交給接手的開發者或 AI Agent 直接延續開發。

---

## 8. 目前文件的不足與建議補強

為了讓開發更順利，建議後續再補上以下內容：

### 建議補強 1：CLI 規格
應明確定義：
- 輸入檔案路徑
- 輸出資料夾
- 語音聲音選項
- 字幕啟用/停用

### 建議補強 2：錯誤處理規格
例如：
- 找不到 .pptx
- 沒有備忘稿
- PowerPoint 未安裝
- Edge-TTS 下載失敗

### 建議補強 3：測試計畫
建議至少加入：
- 單元測試：解析 notes
- 單元測試：字幕時間計算
- 整合測試：完整流程

### 建議補強 4：輸出資料夾規格
明確定義：
- temp_audios/
- output/
- log/
- cache/

### 建議補強 5：版本相容性
建議說明：
- Python 版本要求
- PowerPoint 版本要求
- edge-tts 版本相容性

---

## 9. 建議的下一步任務

### 優先順序
1. 建立 main.py 與 CLI 入口
2. 實作 pptx_parser.py
3. 實作 tts_engine.py
4. 實作 subtitle_generator.py
5. 實作 ppt_automation.py
6. 加入基本測試與錯誤處理
7. 更新 README 為可執行的使用手冊

---

## 10. 給接手人的一句話

這是一個「有明確願景、架構清楚、技術路線可行」的專案；目前最重要的工作不是重新設計，而是把設計逐步落成可執行的程式與流程。

如果你要接手，建議先以一個最小可執行版本為目標，先讓單一簡報從 .pptx 生成音訊，再逐步擴大到字幕與 PowerPoint 匯出影片。（*此建議寫於專案初期，目前這個最小可執行版本已經達成並擴展完成，詳見下方最新狀態。*）

## 目前開發狀態（最新）

**核心流程（pptx → 帶配音的 MP4）已完整打通，並在真實 Windows + PowerPoint 環境驗證通過。** 詳細清單與技術細節請見上方「3. 目前專案實際狀態」章節，這裡不重複列出，避免兩處內容日後不同步。

目前優先度較低、還沒做的項目：
- `--insert-audio` 的進度顯示（`--generate-audio` 和 `--export-video` 已有）
- 現場放映自動播放（目前僅影響「投影片放映」模式，不影響 MP4 匯出）
- 字幕生成器正式整合進主流程（目前為獨立 PoC）
