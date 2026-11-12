# 每頁 VTT（PPTX 用途）

沿用原始 MP3 與 word-boundary sidecar，每頁輸出 `slide_NNN.vtt`，時間相對於該頁音訊起點。無旁白頁不產生 VTT。自行在 PowerPoint 音訊物件加入字幕，並調整播放屬性。

```powershell
.\.venv\Scripts\python.exe -m pptx2video input.pptx --audio-output-dir output/audio --vtt-output-dir output/vtt --subtitles-output=
```

先依 [README 初始化步驟](../README.md) 建立本 working copy 的 `.venv`、安裝套件並確認 FFmpeg／ffprobe。可加 `--generate-audio` 產生原始 MP3；已有 `manifest.json` 時直接重用，不需要重做 TTS。`--subtitles-output=` 關閉 CLI 原有的預設全片 SRT 輸出，避免 PowerShell 空字串傳參差異。

VTT 不改動 MP3、不補尾端靜音、不插入字幕或設定 PowerPoint 播放屬性。準備過的音訊 manifest 不接受作為 VTT 來源。輸出資料夾請專用於本次簡報；不會清理舊檔。

寫檔前檢查每頁時間：有限且非負、結束晚於開始、毫秒精度仍有長度、無重疊且不超出音訊長度（容許 1ms 誤差）。缺少 timing、音訊無法量測或對齊警告會中止輸出，應人工檢查來源；不自動修正 cues。

同次執行可搭配 `--audio-tail-silence`：VTT 固定讀取 `--audio-output-dir` 的原始 MP3 manifest；JSON、SRT、插入及影片定位則使用 prepared 音訊。VTT 時間與驗證仍以原始 MP3 為準，PowerPoint 手動掛載時請使用對應的原始 MP3；prepared 媒體的字幕掛載尚未驗收。

## 完整操作流程

以下指令從專案根目錄執行。先產生音訊與 VTT：

```powershell
.\.venv\Scripts\python.exe -m pptx2video "examples\sample_test.pptx" `
  --generate-audio `
  --audio-output-dir "output\audio" `
  --vtt-output-dir "output\vtt" `
  --output "output\slides.json" `
  --subtitles-output= `
  --rate=+0% `
  --pitch=+0Hz `
  --tts-max-retries 3 `
  --tts-retry-delay 5 `
  --log-dir "output\logs" `
  --verbose
```

再重用音訊產生新的 PPTX（需要 Windows 桌面版 PowerPoint）：

```powershell
.\.venv\Scripts\python.exe -m pptx2video "examples\sample_test.pptx" `
  --insert-audio `
  --audio-output-dir "output\audio" `
  --pptx-output "output\sample_test_with_audio.pptx" `
  --output "output\slides.json" `
  --subtitles-output= `
  --log-dir "output\logs" `
  --verbose
```

開啟新 PPTX，在第 2、3、4 頁的音訊物件手動掛載同頁碼的 VTT；第 1、5 頁無旁白。依需求手動改成進入頁面自動播放，再儲存簡報。`--insert-audio` 不會掛載 VTT 或替你完成這些播放設定。

## TTS 無音訊回應與限制

`No audio was received` 表示 TTS 未回傳音訊，不等於 CLI 參數錯誤。此例外已納入重試：`--tts-max-retries 3 --tts-retry-delay 5` 表示每頁最多嘗試 4 次，間隔 5 秒；CLI 預設間隔仍為 2 秒。實測重試可恢復，但根因未確認，不能保證不再發生。

重試耗盡會中止整批，可能留下空白或不完整 MP3；manifest 僅在整批成功後寫出，失敗後既有 manifest 也可能與已覆寫音檔不一致。因此不能只看檔案存在就判定成功，也不能假設失敗批次可直接續跑。首次整批失敗時，建議完整重跑。成功後保留 MP3、word-boundary JSON 與 manifest，後續產生 VTT／嵌入音訊不要加 `--generate-audio`，可避免再次呼叫線上服務。

## 手動驗收紀錄

本輪整合回歸確認字幕同步、前進換頁停止前頁音訊、儲存關閉重開正常；返回上一頁仍不自動播放，維持既有限制。原始音訊使用 +0% 語速生成，現行預設亦改為 +0%。YunJhe 的 -10% 無音訊限制與診斷範圍見 [語速診斷](TTS_RATE_DIAGNOSTIC.md)；有限次重試不保證解除這個問題。

2026-11-12 使用者回報：範例簡報 3 頁旁白成功產生並嵌入 PPTX；手動掛載 VTT 後字幕隨音訊同步播放，手動設為自動播放後進頁即播放正常，未發現漏句。第 4 頁曾無音訊回應，重試後成功。

測試版本：適用於 Microsoft 365 的 Microsoft PowerPoint，64 位元，MSO 組建 2610，版本 `16.0.20527.20150`（依使用者提供資訊記錄）。使用者另確認儲存關閉再開啟、首次進入旁白頁自動播放及字幕同步、播放中前往下一頁停止前頁音訊均通過。

返回上一頁自動重播尚未通過：各頁音訊皆設定「自動」。第 3 頁播放中第一次按 Page Up，音訊停止但仍在第 3 頁；第二次按 Page Up 返回第 2 頁但未自動播放；第三次按 Page Up 仍停在第 2 頁且未播放。後續對照確認：用數字加 Enter 跳到指定頁也不自動播放，此時點擊滑鼠會前往下一頁並播放該頁內容，而非重播目標頁。移除 VTT、保留音訊設定後結果相同，因此此現象並非僅在掛載 VTT 時出現；返回重播的播放設定／PowerPoint 行為仍待另行確認，不修改 VTT 作為解法。這些結果不延伸為其他簡報、Video、Stage 6 或 2026HRT 重疊問題的驗收。

使用者另回報既有影片流程可產生 MP4、套用校正係數重產全片 SRT 並燒錄字幕。這是本分支的 main 既有流程回歸操作，不包含未移入的音訊準備功能或 Stage 6。

首次提交前完整測試曾有 202 項通過、1 項既有尾端定位測試失敗。該問題已由獨立修復 PR #3 合併 main（`e78c396`），再整合至 VTT 分支；修復未放寬測試容差。整合後完整測試為 **204 項通過，另有 7 個 subtests 通過**。修復根因、測試及真實影片修正前後 SRT 相同且實播同步的紀錄，見 [尾端定位修正](AUDIO_END_ANCHOR_FIX.md)。測試環境套件快照可依 README 的 `pip freeze` 指令保存。

實際操作驗收補充：滑鼠點擊下一頁、簡報筆下一頁皆確認新頁音訊自動播放、字幕同步且前頁音訊停止。簡報筆上一頁與鍵盤 Page Up 相同，需要按兩次才能返回，返回後不自動播放音訊。故 VTT 產生、掛載、同步及正常前進播放通過；返回自動重播列為獨立的播放限制，尚未解決。移除 VTT 後仍有相同返回行為。

## 共用邏輯

VTT 共用 `subtitle_pipeline._build_slide_captions()` 提供的每頁相對 cues，沿用既有斷句與對齊邏輯。

VTT 僅新增格式、驗證與 CLI 寫檔入口，不依賴音訊準備或影片校正流程，字幕行寬維持既有預設 36。

影片用途仍使用原有 PowerPoint 匯出、全片 SRT 校正與 ffmpeg 燒錄流程；每頁 VTT 不改動這些流程。
