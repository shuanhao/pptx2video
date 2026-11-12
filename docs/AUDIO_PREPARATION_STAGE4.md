# Stage 4：三份候選字幕與診斷報告

> 本文件是該階段完成時的紀錄；「後續／尚未」僅指當時。Stage 1～5 功能目前已實作，現行規格見 [音訊準備手冊](AUDIO_PREPARATION.md)，剩餘驗收見 [Stage 6](AUDIO_PREPARATION_STAGE6.md)。

> 設計更新：音訊準備已改為同層固定檔名、每次全部重轉，移除 `--force-prepare-audio` 與快取重用。以下關於版本化、整批回復與重用的敘述保留為歷史紀錄；現行規則見 [音訊準備手冊](AUDIO_PREPARATION.md)。舊驗收結果不等同新版已通過驗收。


本階段完成第一部分的產物保留：主 CLI 匯出 MP4 後產生候選字幕並結束，由使用者人工核對後才另外燒字幕。720／1080 黑條自動缩放仍屬 Stage 5；本階段不執行燒錄，也不自動選擇最準的 SRT。

## 產物與相依性

指定 `--export-video --subtitles-output output/captions.srt` 時：

| 產物 | 內容 |
|---|---|
| `captions_preview.srt` | 在匯出前產生，累計實際使用的完整音訊長度（含補秒）與無旁白頁預設時長 |
| `captions_initial.srt` | 匯出後定位，額外全域係數固定 1.0 |
| `captions.srt` | 使用同一份未校正定位結果，套用指定全域係數一次 |
| `captions_alignment_report.json` | 本次批次識別、來源、各產物狀態、逐頁定位與退回資訊 |

自訂 `lesson.srt` 時自動衍生 `lesson_preview.srt`、`lesson_initial.srt`、`lesson_alignment_report.json`。全域係數為 1.0 時 initial 與 captions 內容一致，仍保留兩份供明確追溯。不重複定位，不重新執行 WordBoundary 文字對齊；三份字幕共用同一批相對時間字幕資料。

0 秒原始音訊流程也保留三份字幕。舊定位方法仍沿用，報告以 `legacy_measured` 明確區分，不能聲稱已通過 prepared 音訊的匹配品質門檻。沒有 `--export-video` 時保留原有單份預測字幕行為，不產生假的實測版本。

## 失敗與提交政策

- preview 在插入／匯出之前提交。匯出或插入失敗時保留已生成 preview，報告其餘產物尚未產生。
- 無法抽取／定位影片音訊時保留 preview 與已匯出的影片，回報失敗；不再以預測版覆蓋 initial／captions。
- initial 與 captions 分別驗證非有限時間、零／負時長、時間重疊及超出影片時長。任一版本失敗，不影響另一份合法版本提交；整體以 `partial_failure` 回報，CLI 非零結束。
- 每個檔案先寫暫存再原子替換；失败保留前次同名字幕，不把舊檔列為本次成功。這是逐檔提交，不是跨所有檔案的單一交易；若程序突然中斷或報告本身無法寫入，須依報告狀態與檔案雜湊核對，不只看檔案是否存在。
- 第一部分正常完成後顯示人工核對提示並結束；不等待互動輸入，也不呼叫燒字幕工具。

## 如何讀取報告

頂層 `run_id` 與 UTC `created_at` 識別本次執行。來源資訊包含音訊／WordBoundary SHA-256、manifest 與字幕來源文字資料 SHA-256，以及影片路徑、大小與修改時間。影片識別採檔案資訊，未對大型影片另做完整內容雜湊。

`artifacts` 逐份記錄：

- `ready`：本次成功，附 run_id、SHA-256、字幕數及使用係數。
- `failed`：本次該版本失敗，附錯誤原因；同名舊檔可能仍在。
- `not_generated`：因上游失敗未生成。
- `pending`：尚未完成；若程序已結束或中斷，不可視為成功。
- `existing_before_run`：執行前是否已有該檔，協助辨識舊產物。

`summary` 與 `counts` 列出 matched、head_only、predicted、silent、legacy_measured 的頁碼及數量。`slides` 保存 raw anchor 座標、品質、拒絕原因、採用起點與局部比例，以及人工檢查時間區間；這些以未加額外全域校正的影片座標記錄。caption 版本的係數在各 artifact 下記錄，時間映射為「raw 起點＋頁內字幕時間×raw 比例」再乘該係數。

`missing_caption_slides` 列出有旁白卻沒有可生成字幕的頁面；`warnings` 保留文字對齊、資料缺失與定位警告。ready 表示成功生成候選檔，不代表所有頁面的語音同步已由人工確認。

開始預測與匯出後定位前均核對音訊／WordBoundary 來源，若匯出期間改動，停止產生混用資料的字幕。這增加來源雜湊的讀取成本，但不重新執行 TTS 或 PowerPoint。

## 獨立重建

`scripts/regenerate_srt_from_export.py` 現在共用相同候選管理模組，會保留三份 SRT 與診斷報告；既有搜尋窗口、anchor 長度及校正係數參數仍可使用。例如：

```powershell
python scripts/regenerate_srt_from_export.py `
  --video output/deck.mp4 `
  --manifest output/audio_prepared/manifest.json `
  --slides-json output/slides.json `
  --output output/captions.srt `
  --global-scale-correction 1.0
```

重建仍須以該影片實際使用的音訊 manifest 為準。原音訊流程請指定原始 manifest；此命令不轉碼音訊、不重匯出影片、不燒字幕。

## 驗證

測試涵蓋命名、預測包含補秒及空白頁 offset、單次定位／文字對齊、1.0 版本一致、非 1.0 不重複校正、單一版本失敗、原子提交失敗、舊檔辨識、來源變更、匯出失敗，以及第一部分結束不燒錄。另以真實 ffmpeg／ffprobe、音訊與 WordBoundary 執行重建 CLI，檢查三份 SRT、報告與實測起點。

真實 PowerPoint 大型簡報驗收、人工選字幕及 Stage 5 燒錄驗收仍待後續完成。
