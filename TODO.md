# 待辦事項

已完成的項目請見 [CHANGELOG.md](CHANGELOG.md)，這裡只保留還沒完成的工作、刻意不做的項目，以及已知限制。

## 待進行

- `--insert-audio` 的進度顯示（`--generate-audio` 和 `--export-video` 都已經有即時進度回報，插入音訊的迴圈還沒有）
- Output Validation 強化（目前只驗證檔案存在且非空，更進階的檢查如「能否開啟」「影片長度是否合理」先不做，等有實際需求再考慮）

## 已評估、決定不做

- **Temporary File Cleanup**（自動清除 `output/audio`、`manifest.json` 等）——會打斷分階段執行的工作流程（例如今天先 `--generate-audio`，明天才 `--insert-audio`），刻意保留現狀。
- **COM 操作（`insert_audio()` / `export_video()`）自動重試**——重試前若沒有先確保舊的 PowerPoint 物件已關閉，反而可能製造殭屍程序，風險大於效益。注意這跟 TTS 網路請求的重試機制是分開的決定：TTS 重試已經實作（見 CHANGELOG v0.4.0 的 `--tts-max-retries`），因為兩者失敗情境的風險屬性不同（網路重試安全，COM 重試不安全）。

## 已知限制（目前不打算修）

- 插入的音訊在 PowerPoint 編輯 UI 仍顯示「按一下時」，用「投影片放映」現場播放時需要點擊才會出聲。已確認**不影響**匯出的 MP4 影片。只有在未來真的需要現場放映自動播放時才需要回頭處理。
- `CreateVideoStatus` 的狀態列舉值是依 Microsoft 官方文件假設，未逐一比對所有 PowerPoint 版本。程式碼已加上安全網（回報「完成」後仍會檢查輸出檔案是否存在、非空）來降低這個風險。
- `insert_audio()` 的逾時保護（`--insert-audio-timeout`）只能停止「等待」，無法強制關閉卡住的 PowerPoint 行程；逾時後背景可能仍有殘留的行程。

## 低優先

- 字幕生成器（實驗性 PoC，不在本次文件整理範圍內）
  - 智慧斷句
  - 閱讀節奏優化
  - Tokenizer
  - 整合進正式管線（目前是獨立的 PoC，未串接主流程）
