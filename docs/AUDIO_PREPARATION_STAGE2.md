# Stage 2：CLI 與 effective 音訊資料流

此階段已接入音訊準備 CLI。anchor 保護、三份候選字幕及黑條自動縮放仍屬後續階段，尚未完成；不要把現在的匯出字幕當成已通過完整 1～10 秒定位驗收。

## 新參數

| 參數 | 預設／用途 |
|---|---|
| `--audio-tail-silence` | 0：原音訊流程；1～10：啟用補秒，可使用小數 |
| `--prepared-audio-dir` | 啟用時預設 `output/audio_prepared` |
| `--prepared-audio-format` | 啟用時預設 `m4a`，另支援 `wav` |
| `--prepared-audio-bitrate` | M4A 預設 `64k`；WAV 不接受明確指定 |
| `--prepared-audio-sample-rate` | 啟用時預設 24000 |
| `--prepared-audio-channels` | 啟用時預設 1 |
| `--force-prepare-audio` | 從原始音訊強制重建，不累加補秒 |

未提供 `--prepare-audio`。補秒為 0 卻明確提供任一 prepared 設定，即使等於預設值，也會在解析 PPTX、建立日誌或執行 TTS 之前報錯。非有限補秒、非法範圍、格式設定衝突與來源／輸出目錄重疊也會提前拒絕。

## 執行順序

1. 驗證參數；啟用時拒絕將已標記 prepared 的 manifest 當成原始來源，且在 TTS 寫入前檢查。
2. 選擇性執行 TTS；`--slides` 仍只限定重生頁面，沿用原有完整 manifest 合併。
3. 讀取完整原始 manifest。啟用補秒時呼叫準備模組，重用或重建衍生資料。
4. JSON payload、預測字幕、插入音訊與匯出後字幕統一使用 effective manifest／音訊目錄。

補秒為 0 不呼叫準備模組，不自動選取殘留 prepared 目錄。原有 manifest 現在也會反映到 JSON，而非只提供給插入或字幕步驟。準備失敗會停止後續 JSON、字幕與插入流程，既有來源資料保留。

## 已有原始 TTS 的準備範例

```powershell
python src/main.py examples/MPU_WK01.pptx `
  --audio-output-dir output/audio `
  --audio-tail-silence 4 `
  --prepared-audio-dir output/audio_prepared `
  --output output/slides.json `
  --subtitles-output output/captions_preview.srt
```

此命令不重新呼叫 TTS，也不匯出影片；會寫 JSON 及預測字幕。重跑相同設定重用衍生音訊。需要 WAV 時增加 `--prepared-audio-format wav`。

完整流程可另外搭配既有 `--generate-audio`、`--insert-audio` 與 `--export-video`，但字幕定位仍是尚未完成 Stage 3 保護的既有實作。單獨對已插入音訊的 PPTX 匯出時，補秒不會修改其嵌入媒體；CLI 會提醒核對實際嵌入音訊與本次 prepared 設定是否一致。更改音訊設定須從乾淨原始 PPTX 重新插入。

## 驗證範圍

CLI 測試涵蓋提早拒絕非法參數、0 秒、既有來源不呼叫 TTS、完整 manifest 合併後才準備、準備失敗阻止後續步驟、JSON／插入／匯出字幕資料一致，以及真實 ffmpeg 下 CLI 重跑不再次轉碼。PowerPoint 呼叫的串接使用 mock 驗證，未宣稱真機匯出驗收完成。
