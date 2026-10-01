# Stage 5：字幕黑條自動縮放

> 設計更新：音訊準備已改為同層固定檔名、每次全部重轉，移除 `--force-prepare-audio` 與快取重用。以下關於版本化、整批回復與重用的敘述保留為歷史紀錄；現行規則見 [音訊準備手冊](AUDIO_PREPARATION.md)。舊驗收結果不等同新版已通過驗收。


人工確認 SRT 後獨立執行：
```powershell
python scripts/burn_subtitles.py --video output/deck.mp4 --srt output/captions_initial.srt --output output/deck_burned.mp4
```

預設 `--bar-scale-mode auto` 使用 ffprobe 的實際影片尺寸：1280×720 採 650／38／40；1920×1080 採 975／57／60（黑條寬／高／底部至頂邊距離）。FontSize=15、MarginV=1 不縮放，兩者為 ASS 樣式座標值，不是直接輸出像素。

三個幾何參數可逐項覆寫為最終像素；1080p 加 `--bar-width 900` 得到 900／57／60。`--bar-scale-mode fixed` 使用舊有 650／38／40 預設，也允許覆寫。1080p 未指定尺寸的預設效果因此有意改變。

auto 僅支援無旋轉、方形像素的上述尺寸；其他影片需 fixed 或完整三個手動值。黑條須位於畫面內，高度不可大於底部 offset。所有模式均需 ffprobe 驗證，失敗停止、不猜測尺寸。輸出不得與輸入影片或字幕同一路徑。

分段入口 `scripts/split_video_by_slides.py --burn-subtitles` 支援相同選項，共用 `src/subtitle_burner.py` 的 probe／resolve 邏輯。第一階段不自動選字幕或燒錄，不需重跑 TTS 或 PowerPoint。

## 驗證與待辦

測試涵蓋 auto／fixed、部分及完整覆寫、非法值、不支援幾何及 probe 失敗停止。合成 720p／1080p 影片實際燒錄後解碼影格，量測黑條寬高及位置，容許色度取樣與編碼邊界 1～2 px。1080p 包含獨立 CLI 與分段 CLI 驗證。

Stage 6 仍須真實 PowerPoint、大型簡報、人工字幕同步與長句版面驗收，再合併 main。

本機完整 unittest：240 tests 通過（49.5 秒）；5 個修改的 Python 檔案語法檢查及 git diff --check 通過。未直接執行 Pylance。1080p 分段合成測試採 2 fps，避免測試環境的 x264 記憶體配置限制；正式影片編碼參數未變。既有 pydub 測試仍有 ResourceWarning，但不影響此次測試結果。
