# TTS 語速診斷（2026-11-12）

## 環境與方法

- 整合分支 `integration/audio-video-vtt`，Python 3.13.2，edge-tts 7.3.1。
- 直接呼叫已安裝的 `edge_tts.Communicate`，繞過主 CLI、重試、音訊準備與 PowerPoint，使用 `examples/sample_test.pptx` 第 2 頁 454 字備忘稿。
- 固定音高 `+0Hz`，主對照使用 WordBoundary。每次呼叫獨立輸出，不覆寫正式驗收媒體。全程保留有限等待，不把部分音訊視為成功。
- 原始診斷檔位於本機忽略目錄 `output/acceptance/tts_diagnostics/`，不納入 Git。

## 結果

| 案例 | 結果 |
|---|---|
| YunJhe，全文，交錯 -10%／+0%，各 3 次 | -10% 三次均 NoAudioReceived、0 bytes、0 筆逐字時間；+0% 三次均成功、395280 bytes、196 筆逐字時間 |
| YunJhe，前 30 字，-10% | NoAudioReceived、0 bytes |
| YunJhe，全文，-5% | NoAudioReceived、0 bytes |
| YunJhe，全文，+10% | 25 秒總時限內未完成；僅 50400 bytes、28 筆逐字時間，記為超時失敗，不是有效產物 |
| HsiaoChen，全文，-10%，WordBoundary | 成功、513936 bytes、196 筆逐字時間 |
| YunJhe，全文，-10%，SentenceBoundary | NoAudioReceived、0 bytes |

六次交錯測試全文 SHA-256：`4a732c4de21b7fd25e0af529378d4dbe83b1e1a092fd133181db2542ce99b863`。原始逐次耗時、例外、檔案與逐字資料均保留於本機 `20261112T084519Z/report.json` 所在目錄；補充範圍測試見 `scope/report.json`。

## 結論與限制

這次失敗不需要主 CLI 或重試迴圈即可重現；不是墊秒、影片匯出或字幕燒錄造成。相同文字在 +0% 可穩定完成，另一個語音在 -10% 亦成功，支持「YunJhe 與語速組合相關的上游合成問題」方向，但不足以確定服務端或套件協定的根因，也不宣稱所有非零語速／其他語音均失敗。

增加重試次數不是已證實有效的解法，既有有限次重試政策保持不變。沒有自動替換語音或語速，沒有升級或修改套件。使用者本輪以明確 `--rate=+0%` 產生範例原始音訊並完成媒體驗收；使用者同意將 CLI 與所有 TTS 模組入口的預設由 -10% 改為 +0%（原速）。仍可明確指定 -10% 等其他語速，失敗後保持原參數有限重試，耗盡則中止，不會靜默降級。既有音訊與 manifest 不自動重生。

上游文件仍列語速調整與負百分比語法，因此不將 -10% 判定為非法參數：[edge-tts 說明](https://github.com/rany2/edge-tts#changing-rate-volume-and-pitch)。本輪 Python API 直接傳入 rate，已排除 PowerShell 負值參數解析因素。

## 預設調整後的實際驗證

完整 unittest 回歸 254 項全部通過、無跳過，含預設語速與明確語速傳至 service／manifest 的驗證、CLI 預設傳遞及既有重試／媒體測試。

省略 `--rate`，使用主 CLI、YunJhe、同一份範例簡報重新生成原始音訊，3 頁全部成功、未觸發重試。manifest 確認 `rate=+0%`，逐頁 WordBoundary 筆數為 196／221／188，MP3 大小為 395280／464544／395568 bytes。本機產物為 `output/acceptance/sample/audio_default_rate0`，未覆寫前次驗收資料。這證明新預設可用，不代表非零語速根因已修復。
