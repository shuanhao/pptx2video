# Project Handover Report

## 專案名稱
pptx2video (PPTX Auto Presenter)

## 文件版本
v0.1.0 (TTS milestone)

## 目標對象
接手開發者、AI 協作 Agent

## 撰寫日期
2026-07-25

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
- 已加入單元測試：[tests/test_pptx_parser.py](tests/test_pptx_parser.py)、[tests/test_tts_generator.py](tests/test_tts_generator.py)、[tests/test_main_payload.py](tests/test_main_payload.py)

目前仍未實作的部分：
- SRT 字幕生成
- PowerPoint 自動化匯出 MP4

這表示目前專案已經從「解析原型」進展到「可產生音訊的可運作流程」，但字幕與影片輸出仍然是下一階段的目標。

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
- 根據音訊與 notes 生成 `.srt` 字幕
- 透過 PowerPoint 自動化匯出 MP4

### Phase 3：PowerPoint 輸出與動畫保留
下一步要完成 COM 自動化流程：
- 開啟 PowerPoint
- 插入音檔
- 設定播放與切換時間
- 匯出 MP4

### Phase 4：穩定性與產品化
待補強項目：
- 更完整的錯誤處理
- 更清楚的日誌輸出
- 暫存檔與輸出資料夾管理
- 進一步的 CLI 擴充

---

## 5. 每個模組的責任範圍

### 5.1 pptx_parser.py
負責：
- 解析 .pptx
- 取得投影片數量
- 取得每頁備忘稿文字
- 處理空白頁或無 notes 的情況

### 5.2 tts_engine.py
負責：
- 將文本轉為語音檔
- 使用 edge-tts 逐頁生成音檔
- 取得每段語音的時長
- 將音檔存於 temp_audios/

### 5.3 ppt_automation.py
負責：
- 啟動 PowerPoint
- 開啟簡報檔
- 插入音訊
- 設定投影片自動播放與切換時間
- 匯出 MP4
- 確保 COM 物件正常釋放

### 5.4 subtitle_generator.py
負責：
- 接收文本與每頁時長
- 進行時間累加
- 輸出 .srt 檔

### 5.5 main.py
負責：
- 串接上面所有模組
- 提供 CLI 入口
- 決定輸入與輸出路徑
- 讓使用者只需執行一個命令即可完成流程

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

如果你要接手，建議先以一個最小可執行版本為目標，先讓單一簡報從 .pptx 生成音訊，再逐步擴大到字幕與 PowerPoint 匯出影片。 


## Current Development Status

Completed:
- PPTX Parser
- Notes Extraction
- Edge-TTS
- Audio Manifest
- CLI
- Subtitle Generator (Experimental / PoC)

Current focus:
- PowerPoint Automation
- MP4 export

Subtitle Generator is intentionally kept as a PoC and is not part of the production pipeline.
