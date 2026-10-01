# 音訊準備：固定檔名、每次全部重轉

本文件取代原整合評估與 Stage 1～6 紀錄中的「版本目錄、快取重用、失敗保留整批舊版」設計。Stage 文件保留當時測試歷史，不表示新行為已通過真機驗收。

## 使用方式

`--audio-tail-silence` 維持唯一開關：0 不轉換，1～10 秒（可小數）啟用。M4A 預設 AAC-LC、64k、24000 Hz、單聲道；WAV 使用 PCM 16-bit。原始 audio 不修改。

```powershell
python src/main.py examples/MPU_WK01.pptx --audio-output-dir output/audio --audio-tail-silence 4 --prepared-audio-dir output/audio_prepared --output output/slides.json --subtitles-output output/preview.srt
```

上述命令使用已有原始音訊，另產生 JSON 與預測字幕。原有完整流程可照常加上 generate-audio、insert-audio、export-video。`--force-prepare-audio` 已移除，傳入會由 CLI 拒絕。

## 產物與重跑

```text
audio_prepared/
  manifest.json
  slide_001.m4a
  slide_001.wordboundaries.json
  slide_002.m4a
  slide_002.wordboundaries.json
```

每次啟用補秒，都從原始 MP3 處理完整 manifest，無快取、無續跑，不累加上次靜音。`--slides` 仍只限定 TTS 重生頁面，準備階段仍全頁重轉。分開執行插入或匯出的 CLI，只要再次啟用非零補秒，同樣全頁重轉。

WordBoundary 直接複製，不增加靜音事件。manifest 保存來源／產物雜湊、轉換設定與量測資料，以支援 anchor 分析及來源追溯；這些資料不再用於重用判斷。

## 提交與失敗

1. 檢查來源、參數及工具；此時尚未修改正式音訊。
2. 原子發布 schema_version=2、status=incomplete 的 manifest，再開始逐頁覆寫。
3. 每頁音訊先轉暫存檔，解碼驗證成功後才替換固定檔名。WordBoundary 複製期間若失敗，整批仍不可用。
4. 全部完成且來源雜湊再驗證通過後，原子發布 status=ready 的 manifest。

中途失敗或程序中斷，目錄可能混有新舊資料；不承諾整批回復。插入、字幕與定位入口拒絕 incomplete，必須重新執行準備，從第一頁全部重轉。若連開始標記都無法寫入，程式在覆寫音訊之前停止；若最後提交失敗，保留 incomplete。

同一 prepared 目錄應依序使用，不支援準備與消費同時執行。已匯出影片對應的音訊不得在字幕定位期間重轉。

## 舊資料

舊 schema 1 的完成 manifest 仍可讀取。重新準備時改寫為平面檔名與 schema 2；舊 UUID 目錄不自動刪除，以免破壞舊產物。切換 M4A／WAV 或刪除頁面後，未被新 manifest 引用的檔案也不自動清理；消費端以 manifest 為準。

字幕三候選與兩階段工作方式不變：第一階段結束後人工選定 SRT，再獨立燒錄。第二階段不重轉音訊。

## 本次驗證

完整 unittest：242 tests 通過（48.375 秒）。涵蓋真實 ffmpeg 的 M4A／WAV、1／1.5／4／8／10 秒、原始檔不變、重跑全數轉換且不累加靜音、第二頁失敗後拒絕消費與全批重跑、開始／結尾 manifest 提交失敗，以及舊 UUID 目錄遷移後保留。CLI 未呼叫 TTS 的重轉路徑亦有驗證。

本次未重新進行真實 PowerPoint 匯出與人工播放，Stage 6 仍未完成；未直接執行 Pylance。既有 pydub 測試的 ResourceWarning 仍存在。
