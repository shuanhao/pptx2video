# Stage 1：音訊準備模組

> 本文件是該階段完成時的紀錄；「後續／尚未」僅指當時。Stage 1～5 功能目前已實作，現行規格見 [音訊準備手冊](AUDIO_PREPARATION.md)，剩餘驗收見 [Stage 6](AUDIO_PREPARATION_STAGE6.md)。

> 設計更新：音訊準備已改為同層固定檔名、每次全部重轉，移除 `--force-prepare-audio` 與快取重用。以下關於版本化、整批回復與重用的敘述保留為歷史紀錄；現行規則見 [音訊準備手冊](AUDIO_PREPARATION.md)。舊驗收結果不等同新版已通過驗收。


本階段新增 `src/audio_preparation.py`、`AudioPreparationError` 與模組測試，尚未接入主 CLI、PowerPoint 或字幕定位流程。評估報告中的新 CLI 參數目前仍不可使用。

## 模組介面

- `AudioPreparationOptions`：補秒預設 0；啟用範圍 1～10 秒，可用小數。預設 M4A、AAC-LC 64k、24 kHz、單聲道；WAV 使用 PCM 16-bit。
- `validate_preparation_options()`：檢查設定與來源／輸出目錄分離。未啟用時不檢查轉碼工具、不建立輸出。Stage 2 CLI 須以 `explicit_options` 傳入明確指定的轉換參數，以辨識明確指定預設值的衝突。
- `probe_audio()`：取得格式並解碼量測樣本時長，不把完整 PCM 載入記憶體。
- `prepare_audio_file()`：處理單份原始 MP3，驗證輸出後才提交。
- `prepare_audio_manifest()`：讀取呼叫端提供的合併後原始 manifest，回傳 `manifest`、`audio_dir`、`converted`、`reused`。
- `is_prepared_entry_current()`：比對來源、WordBoundary、設定、工具版本及輸出雜湊，判定可否重用。

## 資料與失敗處理

原始 MP3、WordBoundary 與 manifest 留在原處。衍生檔案放入獨立輸出目錄內的唯一生成子目錄，manifest 使用相對路徑。WordBoundary 原樣複製；來源沒有 WordBoundary 時保留 `null`。

每頁記錄來源雜湊、設定、工具資訊、原始與衍生解碼時長、輸出雜湊及生成識別碼。保留既有 manifest 和頁面的其他欄位。強制重建也從原始音訊開始，不累加靜音；已標記 prepared 的 manifest 不可當來源。

整批完成且再次核對來源後，才原子替換 `manifest.json`。轉換或提交失敗不覆寫前批 manifest 引用的音訊；可能留下未引用的生成目錄，本階段不自動清除。請勿同時向同一 prepared 目錄執行多個寫入程序；本階段沒有跨程序鎖。

未標記的歷史手動補秒 MP3 無法自動辨識，呼叫端須提供乾淨原始來源。AAC 時長容許兩個 1024-sample frame 的封裝／尾端 padding 差異；WAV 容許兩個樣本的重取樣捨入差異。這些檢查不等於已驗證 PowerPoint 或字幕同步。

## 驗證

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_audio_preparation.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

真實 ffmpeg 測試涵蓋 M4A／WAV 的 1、1.5、4、8、10 秒、格式與解碼時長、原始資料不變、WAV 旁白逐樣本不變及新增靜音、來源／設定／產物變更失效、強制重建、缺少 WordBoundary、路徑防護、工具缺失，以及批次與提交失敗。缺少 ffmpeg／ffprobe 時整合測試明確跳過。

PowerPoint 真機播放、anchor、三份字幕與燒錄驗收留待後續階段。
