# Stage 6：真機與大型簡報驗收

> 設計更新：音訊準備已改為同層固定檔名、每次全部重轉，移除 `--force-prepare-audio` 與快取重用。以下關於版本化、整批回復與重用的敘述保留為歷史紀錄；現行規則見 [音訊準備手冊](AUDIO_PREPARATION.md)。舊驗收結果不等同新版已通過驗收。


狀態：進行中，尚未完成驗收，尚未合併 main。

合併前現況：Stage 1～5 與固定檔名／全批重轉的程式工作已完成；目前剩餘驗證、人工測試與文件核對。下方「重用 24 頁」等結果為舊版本的歷史實驗，不是現行執行方式。固定檔名版 commit `822f32b` 已通過 242 個自動化測試；真機端到端需再驗證，不能以舊版結果代替。

## 已確認基準

- Stage 5 commit：`65949a4`，已同步遠端。
- Stage 5 完整自動化測試 240 tests 通過；不等同真實 PowerPoint 驗收。
- Python 環境具 pywin32 312、edge-tts 7.2.8、ffmpeg、ffprobe。
- 獨立 PowerPoint COM 實例在提升權限的執行環境可啟動並關閉，版本 16.0。受限環境曾回報登入工作階段不存在。
- `examples/sample_test.pptx` 為 5 頁；`examples/MPU_WK01.pptx` 為 24 頁。
- 大型簡報目前備忘稿與 `output.mpu-w1-new/slides.json` 的 24 頁備忘稿一致，可用該次原始 audio 作本機準備測試。此比對不等同重新驗證每段音訊發音內容。
- 所有新增媒體寫入 `output/stage6/`，不覆寫既有實驗資料。

## 驗收矩陣

| 案例 | 自動檢查 | 人工檢查 | 狀態 |
|---|---|---|---|
| sample、原始 MP3、0 秒 | 原流程、三份字幕 | 語音完整及字幕同步 | 待執行 |
| sample、M4A、4 秒、1080p | 轉換及插入完成；使用者手動匯出後重建字幕 | 全片聲音完整、補秒正常，p2/3/4 首尾及中間抽測同步 | 人工聲音／停留／字幕驗收通過；CLI 自動匯出仍未通過 |
| sample、M4A、1／8／10 秒 | 邊界秒數、anchor 與退回報告 | 尾端語音及換頁 | 待執行 |
| sample、WAV、4 秒 | 格式替代、定位 | 語音對照 | 待執行 |
| MPU_WK01、M4A、4 秒 | 完整 24 頁、重跑重用、來源保護、三份字幕 | 前中後、長頁首尾、最後一句 | 準備及真機插入完成，尚未匯出 |
| 人工選定字幕後燒錄 | 720／1080、fixed／手動覆寫 | 長句不溢出、黑條位置及字型 | 範例已選 initial，1440×1080 手動覆寫燒錄版聲音與字幕通過；其他版面及 auto 真片驗收待完成 |

## 需要人工介入

使用者已明確授權將 sample_test.pptx 備忘稿傳送至 Microsoft Edge-TTS，3 頁旁白生成及插入完成。首次指令遭審查拒絕後，取得授權再執行，現已無此待辦。

## 範例人工驗收結果

使用者手動以 1080p 匯出 `output/stage6/sample/m4a4/deck_with_audio.mp4`，於 VLC 掛載 `captions_manual_export_initial.srt`，確認全片聲音完整、停留正常，第 2／3／4 頁第一句、最後一句與中間抽測皆同步。此結論限於本次 M4A 補 4 秒的範例。

先前自動匯出期間發生 Windows 分頁檔不足（1455），PowerPoint 匯出中斷。手動成功不能取代 CLI 自動匯出驗收；Stage 6 仍保留此項待辦。下一步以已選定 initial 產生燒錄版，人工確認黑條、字型及長句版面。燒錄使用既有函式的 extra_ffmpeg_args 限制 x264 為 2 執行緒，降低本機記憶體需求，不改正式預設。

ffprobe 實測手動匯出尺寸為 1440×1080、SAR=1:1、DAR=4:3。auto 模式依設計拒絕此尺寸，並未生成燒錄版。後續版面預覽改明確指定 975／57／60 像素，不修改自動縮放支援範圍；此預覽不等同 1920×1080 的 auto 真片驗收。

明確幾何覆寫後燒錄成功，產物為 `output/stage6/sample/m4a4/deck_manual_export_burned.mp4`，使用 `captions_manual_export_initial.srt`，待人工檢查黑條位置、長句邊界及字型。

使用者後續確認 `deck_manual_export_burned.mp4` 的聲音、字幕正確，記錄為本次 1440×1080、明確黑條幾何覆寫之燒錄版人工驗收通過（聲音與字幕）。黑條位置、長句邊界與字型未另獲明確回覆，不擴大解讀為所有版面項目已通過。此結果也不取代 16:9 auto、其他補秒秒數、WAV、大型簡報或 CLI 自動匯出的待驗收項目。

取得影片後需實際聆聽與選定 SRT；anchor 的 ready／matched 不代表已通過人工同步驗收。若有 head_only／predicted，依 alignment_report 的頁码與時間區間優先檢查。

每頁停留應區分原有尾端靜音與新增靜音；空白頁仍使用既有預設頁面時長。不可只憑最後一句吻合就通過所有頁。

## 合併條件

記錄各案例產物、命令、成功／退回／失敗結果及人工確認後，再完成 Stage 6 提交、合併 main。未完成真機或人工驗收前不標示全功能通過。

## 本機大型簡報準備命令

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python src/main.py examples/MPU_WK01.pptx --audio-output-dir output.mpu-w1-new/audio --audio-tail-silence 4 --prepared-audio-dir output/stage6/mpu_wk01/m4a4/audio_prepared --output output/stage6/mpu_wk01/m4a4/slides.json --subtitles-output output/stage6/mpu_wk01/m4a4/preparation_preview.srt --log-dir output/stage6/logs
```

首次未限制執行緒的呼叫出現 OpenBLAS 記憶體配置失敗，因此重試時僅針對此程序環境限制執行緒，不更改全域環境或正式程式。此命令只準備音訊及預測字幕，尚未插入／匯出，不能視為大型簡報影片驗收。

本機準備結果：24 頁全部完成；再次呼叫準備模組 converted=[]、reused=24。於首次準備執行期間建立的 49 個來源檔案雜湊基準，在重跑後全部一致；這不等同首次執行前後的完整雜湊對照。機器可讀結果位於 `output/stage6/preparation_check.json`。

真實 PowerPoint 插入完成：24 頁 inserted、0 skipped，產物為 `output/stage6/mpu_wk01/m4a4/deck_with_audio.pptx`。另讀取 PPTX ZIP 內嵌媒體，確認全部 24 份 prepared 音訊 SHA-256 都存在於內嵌媒體中。這證明插入來源一致，不代表 MP4 匯出無斷音。先完成短範例匯出與播放驗收，再進行耗時的大型簡報匯出。

預測字幕警告：第 16 頁 segment 147、第 20 頁 segment 9、第 23 頁 segment 47 的「」」未匹配而插值；第 22、23 頁 `mp; Connecti` 無法在來源文字游標之後找到而略過。必須後續人工核對，不能將預測成功視為無對齊問題。
