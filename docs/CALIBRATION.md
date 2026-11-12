# 校準 `--global-scale-correction`

> 這份文件是給「用 `--subtitles-output` + `--export-video`（真實起始時間對齊模式）產字幕，或用 `scripts/split_video_by_slides.py` 切分段影片時，發現字幕/切點跟畫面對不準」的情境看的進階疑難排解文件。第一次使用這個工具、或字幕/切點目前看起來就是準的，不需要看這份文件。回到 [README.md](../README.md)。

歷史長影片曾出現與播放時間成比例的偏差，但並非每份影片都有。預設維持 1.0，先人工核對 initial；已同步時不需校準。M4A 補秒案例曾出現套用 1.001221 反而延後，不能沿用舊值。

## 自動估算：只作待核對的候選值

`scripts/verify_srt_accuracy.py` 可由抽樣音訊比對估算校正係數。這些樣本不是獨立人工真值，估算不取代聽音驗收：

```powershell
python scripts/verify_srt_accuracy.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json
```

跑完會在最後印出建議值跟套用後的 RMS／最大殘差，例如：

```
Suggested --global-scale-correction (fitted from the 42 sample(s) above, no manual measurement needed): 1.00118
Residual after applying it: RMS 0.041s, max 0.187s across the sampled words.
```

取得建議值後可另輸出候選並比對，不直接視為正確答案：

```powershell
python scripts/regenerate_srt_from_export.py --video output/deck.mp4 --manifest output/audio/manifest.json --slides-json output/slides.json --output output/captions.srt --global-scale-correction 1.00118
```

自動樣本可能共享定位偏差；增加樣本不保證消除誤配。可用 `--samples-per-slide` 增加密度，但應以獨立時間點核對。

## 手動校準流程（想要最高準確度、或想交叉驗證自動估算結果時使用）

`scripts/calibrate_scale.py` 是手動校準的工具——需要你自己實際核對過幾個真實時間點，換來的是有獨立人耳驗證過的校準值，適合用在準確度真的很重要的場合。

### 使用流程

1. 先用預設值（不加 `--global-scale-correction`，等同 1.0）跑一次完整流程，產出未校正的 `output/deck.mp4` 與 `output/audio/manifest.json`。
2. 挑 5～8 個（越分散越好，deck 的頭、中、尾都要有）投影片，用能顯示精確時間戳的方式（見下方「怎麼量真實時間」），量出這幾頁旁白**真正開始出聲**的真實秒數。
3. 把量到的時間存成一個 JSON 檔（見下方「`my_observations.json` 的格式」），檔名建議固定用 `my_observations.json`（已加進 `.gitignore`，不會被誤 commit）。
4. 執行：

```powershell
python scripts/calibrate_scale.py `
  --video output/deck.mp4 `
  --manifest output/audio/manifest.json `
  --slides-json output/slides.json `
  --observations my_observations.json `
  --report calibration_report.json
```

腳本會印出建議的 `--global-scale-correction` 值，以及套用後的 RMS／最大殘差供你判斷擬合品質。`--report` 是選用的，會多寫一份 `calibration_report.json`（同樣已加進 `.gitignore`），內含逐頁的量測值/觀測值/殘差，方便之後回頭檢查是否有特定頁面殘差異常大。

### `my_observations.json` 的格式

一個 JSON 物件，key 是投影片編號（字串或數字都可以），value 是你量到的真實秒數：

```json
{
  "2": 5.12,
  "6": 2173.22,
  "11": 4891.03,
  "17": 7950.03,
  "20": 9105.27
}
```

注意事項：

- 每個 key-value 後面（除了最後一個）都要有逗號，這是最容易手誤的地方（JSON 語法錯誤會直接讓腳本在讀檔那一步就報錯）。
- value 量的是「這一頁旁白**開始出聲**的瞬間」，不是「畫面切換」的瞬間——這兩者通常幾乎同一時刻，但如果某頁有轉場動畫、或想要最準的結果，請以聲音為準（見下一節）。

### 怎麼量真實時間

**不建議**只用眼睛看畫面配合耳朵聽音量來抓，很難抓到小於一秒的精確度。推薦做法是只處理音訊、不用管畫面：

1. 用 ffmpeg 把 `output/deck.mp4` 的音軌單獨抽出來：`ffmpeg -i output/deck.mp4 -vn -acodec pcm_s16le output_audio.wav`
2. 用免費的 **Audacity** 打開這個 wav 檔（如果不知道大概要找哪個位置，可以先用預設值跑一次 `scripts/dump_slide_bounds.py`，拿它算出來的粗略、未校正時間當作放大搜尋的起點——這個值本身有偏差，但拿來定位大概位置綽綽有餘）。
3. 放大時間軸，找到波形從一片平坦（靜音）第一次明顯跳出波峰的轉折點，把游標點在那裡。
4. Audacity 下方選取工具列會直接顯示精確到毫秒的時間戳，換算成秒填進 `my_observations.json`。

這個方法不需要處理畫面、不需要 frame-by-frame 的影片剪輯軟體，精確度（約 ±0.05～0.1 秒）也遠遠超過校準這個偏差所需要的水準——回歸用的是最小平方法，觀測點時間跨度越大，同樣的量測誤差對算出來的係數影響就越小。

### 產出的兩個檔案不需要進版控

`my_observations.json`（你自己量的時間，因人/因deck而異）跟 `calibration_report.json`（腳本產出的擬合記錄）都已經加進 `.gitignore`，不會被 `git add -A` 之類的指令意外收進去。如果你想留存某次校準的記錄，用檔名另存（例如 `calibration_report_2h40m_deck.json`）並手動決定要不要加進版控，不要用預設檔名去 commit。

## 校準完的值要用在哪些地方

`--global-scale-correction` 沒有任何地方會幫你記住——設定檔、環境變數都不會保存它，**每一次**呼叫下列指令都要自己明確帶入同一個值：

- Step 10 / 一次到底指令的 `--export-video` + `--subtitles-output`（見 [README.md](../README.md) 的「快速開始」）
- `scripts/regenerate_srt_from_export.py`
- `scripts/split_video_by_slides.py`（見 [SPLIT_VIDEO.md](SPLIT_VIDEO.md)）

主 CLI 與重建入口以 k=1.0 定位一次，再共用 records 產生 initial（1.0）與校正版（指定 k）；分段入口另行定位，其 k 只影響切點，不再乘到輸入 SRT。燒字幕不做時間校正。
