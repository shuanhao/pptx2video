# 可選 TTS 後端

兩種產出的完整命令與相依圖見 [完整流程手冊](FULL_WORKFLOW.md)。使用者已回報以實際教材
執行全流程；MPU_WK04 的 27 頁音訊與含音訊 PPTX／VTT 有 log 支持，詳細驗證範圍見該手冊。

## 使用方式

既有指令維持預設 `edge-tts`。第二套傳輸需明確指定，沒有自動 fallback：

```powershell
$Examples = "examples"
$Output = "output\MPU_WK04"

python -m pptx2video "$Examples\MPU_WK04.pptx" `
  --generate-audio --tts-backend edge-websocket `
  --audio-output-dir "$Output\audio" `
  --output "$Output\slides_source.json" `
  --subtitles-output= --rate=+0% --verbose
```

`--tts-backend edge-tts` 明確選擇原套件。`--tts-max-retries`（預設 10 次額外重試）及
`--tts-retry-delay`（預設 5 秒）由兩套後端共用。僅重用音訊、生成 VTT 或匯出影片時，
不會建立 TTS 連線；後端參數只影響 `--generate-audio`。

`--slides 7` 可只重生第 7 頁。其餘 manifest entries 保留，包括各頁原有的 `tts`
來源資訊。重生後須重新準備 M4A／插入 PPTX／匯出影片與字幕，既有衍生成品不會自動更新。

## 設定相容性

| 設定 | edge-tts | edge-websocket |
| --- | --- | --- |
| voice | 完整名稱或短名稱 | 完整名稱轉為短名稱；亦接受短名稱 |
| rate | signed integer %，例如 `+0%`、`-10%` | 相同 |
| pitch | signed integer Hz，例如 `+0Hz` | 百分比，或零值 Hz；`+0Hz` 轉為 `0%` |

第二後端拒絕非零 Hz，不猜測 Hz 與百分比的換算；不會忽略使用者設定。
原套件的預設聲音與設定保持不變。這兩套傳輸皆使用 Microsoft 消費者語音服務，
並非兩個獨立供應商。

## 模組與合約

```text
main.py（CLI 選頁及載入舊 manifest）
  -> tts.generate_audio_files（共同重試、驗證、漏講檢查、發布）
       -> tts_backend.TTSBackend.synthesize(request, temporary_mp3)
            -> tts_edge.EdgeTTSBackend
            -> tts_websocket.EdgeWebSocketBackend
       -> slide_NNN.mp3 + slide_NNN.wordboundaries.json + manifest.json
            -> 原有 VTT / SRT / audio_preparation / PowerPoint 流程
```

- `SynthesisRequest`：原文、voice、rate、pitch。後端不認識頁碼、字幕、補秒或 PowerPoint。
- `SynthesisResult`：WordBoundary 及後端 metadata。時間統一為整頁 MP3 起點相對秒數，
  每筆包含 `text`、`offset_seconds`、`duration_seconds`。
- `TTSBackendError`：可顯示的摘要及 `retryable`。新傳輸不把帶 token 的網址放進摘要；
  verbose 的原始例外鏈仍可能包含服務網址。
- 原套件 adapter 保留原始例外與工廠注入，以相容既有呼叫及例外鏈；共同層仍辨識
  `NoAudioReceived` 與握手錯誤。新傳輸用中立錯誤合約。
- `synthesize_with_word_boundaries()` 及原有常數仍可從 `src.tts` 匯入，供舊腳本使用。
- 舊 `generator=` 路徑仍是 audio-only；回傳 timing 不會自動成為正式後端。
  原套件零 boundary 事件仍可產生空 sidecar；新傳輸要求音訊、boundary、`turn.end` 俱全。

每頁 entry 的新增可選 `tts` 欄位記錄 backend、版本及該頁設定。頂層 voice/rate/pitch
保留為最近一次生成設定，不能代表混合 manifest 所有頁面的來源。舊 manifest 不需遷移；
缺少每頁 metadata 代表來源未知，不會推定為某個後端。prepared manifest 保留這些欄位。

### WordBoundary XML 文字相容性

實作版本 2 新增 `boundary_text_normalization: source-checked-xml-v1`。回傳的完整 XML
實體只解碼一層，且必須能對應原文；保留原文刻意寫出的 `&amp;` 等字串。修改過的事件
以可選 `raw_text` 保存原始值，`offset_seconds`／`duration_seconds` 原樣保留。

MPU_WK04 第 26 頁另發現服務將 `System` 回傳為 `mp; Sy`。只有在前一事件為 `&`、
原文下一個 ASCII 字詞與回傳字串等長、回傳字串可由跳脫後原文的相同索引切片精確
重現，且下一事件可錨定字尾時才恢復原文。其餘未知不匹配不修補、不忽略，VTT 仍會阻擋。
這是 metadata 相容處理，不代表已聽檢並證明該字詞實際唸出。

既有 `edge-websocket` entry 缺少 normalization 標記時，字幕共用管線在記憶體中進行
同樣轉換，使用 Notes 而非可編輯的 subtitle_text；MP3、sidecar 與 manifest 均不重寫。
舊 `edge-tts` 及沒有後端來源的資料維持原有讀取行為。VTT 檔案本身為符合規格而輸出的
`&amp;` 是合法文字跳脫，與原始 WordBoundary 未解碼造成無法對齊是不同層次。

## 發布與恢復

整批合成先在 audio 目錄內的臨時目錄完成，重試會清除該次暫存音訊。
任何一頁合成失敗時，既有正式音訊、時間資料及 manifest 保持原樣；本次已完成的其他頁
也不會發布。進度 callback 表示合成完成，正式檔案在整批成功後才發布。

發布固定檔名不是多檔案原子交易：先以原子替換方式寫入
`generation: {schema_version: 1, status: incomplete}` manifest，再替換音訊與 sidecars，
最後以 `ready` manifest 收尾。中途中斷時，共用驗證會阻擋載入／音訊準備／字幕與插入。
不要同時執行生成及消費同一個音訊目錄，也不支援並行寫入。

若 manifest 是 incomplete，請先**不帶 `--slides`、不帶音訊準備參數，重新完整生成音訊**，
再執行衍生流程。部分重生不能修復一個狀態未知的整批發布。

低階 API 不傳 `manifest_path` 時仍回傳 manifest。若目錄原有 `manifest.json`，
替換檔案前會將其標記 incomplete；呼叫者需自行發布回傳 manifest。CLI 一律傳入路徑。

共同驗證檢查音訊非空及 boundary 的數值／順序合法性；沒有新增基本 TTS 的 FFmpeg 依賴。
這不等於完整解碼、音訊長度邊界驗證或每字確實唸出的證明。漏講檢查仍是非阻斷 heuristic。

## 實驗性後端限制及驗證

`edge-websocket` 直接連到 `api.msedgeservices.com`，依先前觀察的網頁 frame 格式實作，
不呼叫第三方網站代理，也不修改 edge-tts 模組全域設定。版本／格式集中在該模組常數中。
GEC 與 trusted token 仍依賴 edge-tts 套件內部 helper，協定改變時可能需要維護。

目前整頁送一個 SSML request，connect 15 秒、讀取 30 秒、總計 90 秒 timeout。
不實作逐行切段、MP3 拼接或自動切換傳輸；非常長的 Notes 仍可能遭服務限制。
時間限制是合成請求時間，並非成品音訊播放長度上限。

2026-11-19 先前診斷原型曾完成 MPU_WK04 第 7 頁及另外三組文字（4/4），
那是歷史線上紀錄，不能當成此重構版本的線上驗證或長期可用性保證。
本次自動測試使用假 transport，驗證協定解析、完成訊號、錯誤、重試、發布、CLI、
混合 manifest，以及新輸出直接接到既有 VTT／SRT 的相容性。

本次重構驗證紀錄（2026-11-19）：HEAD 原有 TTS 測試 31 項通過；最終完整測試
274 項通過。另以重構後正式 CLI 的 `edge-websocket` 後端，單次、不重試生成第 7 頁
成功，MP3 完整解碼長度 373.656 秒、24 kHz 單聲道，992 筆 WordBoundary，最後一筆
結束 372.8 秒。既有管線產生逐頁 VTT 及單頁相對時間 SRT，無字幕警告。
隔離結果在 `output/MPU_WK04/diagnostics/tts-backend-refactor-20261119/verification.json`；
不代表整份簡報、長時間穩定性、逐字聽檢或 PowerPoint 匯出已驗證。

後續 XML metadata 修正後，完整回歸曾達 281 項通過；使用者重新執行 2A，確認 27 份 VTT、
27 頁音訊插入且 0 跳過。後續回報已執行影片至字幕燒錄流程，未另提供對齊精度等詳細數據。
上述 274／281 項為各階段歷史測試紀錄，不表示本次文件編輯重新執行測試。

批次真實 log 同時顯示 Python 3.9 transport 清理的 `Event loop is closed`，以及第 16、26 頁
各兩次 429 後成功；這些問題尚未修復。PowerPoint 儲存成功但未自動關閉亦另列 TODO。
