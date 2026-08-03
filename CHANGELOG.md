# Changelog

本文件記錄 pptx2video 各版本的重要變更，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

> **關於版本歷史準確性的說明**：本文件在 2026-08 依實際 `git log` 逐筆核對過 v0.3.0～v0.5.1 這段區間，修正了一處版本歸屬錯誤（見 v0.4.1 條目）與一處遺漏（`insert_audio()` 即時進度回報，同樣補在 v0.4.1）；`v0.5.0` 起的內容/日期已對照實際 commit 與 tag 位置確認無誤。`v0.3.0` 以前的條目仍是依專案現有文件（README / TODO / PROJECT_HANDOVER）回溯重建的功能里程碑，並未逐筆對照 commit，日期為不詳、版本切分點也是概略推估——如果之後要對照實際 commit 歷史修正這段，請直接編輯下方對應章節。

## [未發布]

## [0.6.1] - 2026-07-31

在真實的 2 小時 40 分鐘測試 deck 上實際套用 v0.6.0 的「真實起始時間」字幕對齊後，發現結果反而比 v0.5.0 的預測式做法更差：新舊兩版 `.srt` 到影片尾端的落差接近 10 秒，且字幕明顯偏快（比實際語音提早出現）。套用第一輪修正（anchor）後重新測試，落差縮小到約 2 秒，但仍未完全消除，找到第二個根因後一併修正，兩輪修正都記錄在這個版本。

### Fixed

- **`src/audio_position_locator.py`**：修正 `locate_slide_start_times()` 用「整段」投影片音檔（可能長達數百秒）做互相關比對模板時的系統性偏差。用白噪音（比正弦波更接近語音的寬頻、非週期訊號）做受控實驗證實：PowerPoint 匯出時似乎會對嵌入音訊做極輕微的時間伸縮（約 0.1%），這個比例在幾秒內感覺不出來，但整段拿來當比對模板時，伸縮誤差會隨模板長度累積——實測 120 秒音檔伸縮 0.1% 後，整段比對誤差約 -0.198 秒，只取前 8 秒當模板則誤差僅約 -0.005 秒。誤差方向與大小都能解釋使用者回報的「講稿越長、字幕偏移越多、且偏快」症狀。修正方式：新增 `DEFAULT_ANCHOR_SECONDS`（預設 8 秒），比對時只用每頁音檔開頭的這段時間當模板，不再用整段；投影片音檔本身短於這個秒數時，退回使用整段。
  同時修正一個相關的次要問題：先前當某頁的音檔遺失或無法解碼時，用來推算下一頁搜尋範圍中心點的 `predicted_start` 沒有跟著往前推進，等同於假設那一頁時長是 0 秒，會讓後續每一頁的預測搜尋中心點都跟著偏掉；現在會用 `default_slide_duration` 作為退回估計值往前推進。
- `scripts/verify_slide_timing.py`、`scripts/regenerate_srt_from_export.py`：新增 `--anchor-seconds` 參數（預設同 `DEFAULT_ANCHOR_SECONDS`），可視需要覆寫這個 anchor 長度。
- 新增回歸測試 `tests/test_audio_position_locator.py::test_anchor_avoids_bias_from_slightly_time_stretched_embedded_audio`，用模擬 0.1% 時間伸縮的音檔重現並驗證此修正。
- **（第二輪修正）`src/subtitle_pipeline.py`**：anchor 修正只解決了每頁「起始位置」的偏差，但沒解決同一頁**內部**的字幕時間漂移——`generate_srt_from_true_starts()` 先前只把量到的真實起始時間當作整頁的位移量，頁面內部每句字幕的相對時間仍然是用原始（未伸縮）mp3 的 WordBoundary 資料直接套用，對於 5～8 分鐘的長頁面，同一個約 0.1% 的匯出伸縮效應會在頁面內部逐句累積，越接近該頁結尾就越偏——這正是套用 anchor 修正後，使用者仍回報「到最後還是快了約 2 秒」的根本原因。修正方式：新增頁面級縮放係數計算，用相鄰兩個「已量測到真實起始時間」的投影片之間的真實間距，除以兩者間的預測（加總時長）間距，得到該頁自己的實際伸縮比例，套用在該頁所有字幕的相對時間上，而不是原封不動使用。deck 中最後一個有量到起始時間、但後面沒有下一頁可以量測間距的投影片（通常是最後一頁），改用整份 deck 其他頁面量到的伸縮比例的平均值，而非假設沒有伸縮，並在 warnings 中註記。
- 新增回歸測試 `tests/test_subtitle_pipeline.py::GenerateSrtFromTrueStartsTests::test_scales_intra_slide_captions_by_measured_stretch_ratio`、`test_last_measured_slide_uses_deck_wide_average_scale_with_warning`。
- **（第三輪修正，依實測資料排查後找到的真正根因）**：第二輪修正套用後，使用者在真實 deck 上重測仍回報「到最後還是差了約 2 秒」，因此暫停繼續猜測，改用新增的兩支診斷工具（`scripts/verify_tts_alignment.py` 驗證 edge-tts 產出的 mp3/wordboundaries 本身、`scripts/verify_srt_accuracy.py` 直接對真實影片音軌逐字比對）在使用者的真實 20 頁 deck 上實測。結果顯示：
  1. `verify_tts_alignment.py`：每一頁的 mp3 都比對應的 wordboundaries 最後一個事件多出約 1 秒（edge-tts 結尾的固定靜音尾巴），數值在所有頁面間高度一致，判定為正常現象、不是問題來源。
  2. `verify_srt_accuracy.py`：對整份 deck 20 頁、57 個取樣字直接量測，`implied_local_scale`（每個字反推出的伸縮比例）在全部樣本間高度集中（0.9983～1.00000，多數落在 0.9988～0.9989），且 `naive_delta` 隨著字在頁面內的 offset 大致成比例增長——**直接證實「頁內等比例伸縮」這個模型本身是對的**。
  3. 但第二輪修正估計伸縮比例的方式（用「下一頁的量測起點」反推這一頁的真實時長）把「這一頁自己的伸縮」跟「PowerPoint 在頁與頁之間額外插入的間隙」混在一起計算，這個混淆才是殘餘 2 秒誤差的真正來源。
  修正方式：**`src/audio_position_locator.py`** 新增 `locate_slide_start_and_end_times()`，除了原本的「起點」leading anchor 量測外，再用同一頁音檔**結尾**的 anchor 獨立量出這一頁自己的「終點」，兩者都只依賴這一頁自己的音檔，完全不受下一頁影響。**`src/subtitle_pipeline.py`** 的 `generate_srt_from_true_starts()` 新增可選參數 `true_ends_by_slide`；當某頁同時有量到起點與終點時，優先直接用「終點－起點」除以預測時長算出這一頁自己的真實伸縮比例，不再依賴下一頁；沒有直接量到終點的頁面（例如只用了 `locate_slide_start_times()`）才退回原本「靠下一頁推算」的舊方法。`src/main.py`、`scripts/regenerate_srt_from_export.py` 都已改用新的 `locate_slide_start_and_end_times()`。
  新增回歸測試：`tests/test_audio_position_locator.py::test_start_and_end_measured_independently_reflect_real_stretch`、`tests/test_subtitle_pipeline.py::test_direct_end_measurement_is_unaffected_by_inter_slide_gap`、`test_omitting_true_ends_falls_back_to_inferred_scale_biased_by_the_gap`。
- **（第四輪修正，推翻第一輪「PowerPoint 加速音訊」的假設，找到真正的全域根因）**：第三輪修正套用後，`verify_srt_accuracy.py` 的密集逐字取樣（對第2、8、20頁近3000個字取樣）顯示 `corrected_delta` 全部落在 ±0.03 秒內，理論上已經非常準；但使用者實際在 VLC 精確跳轉到模型預測的絕對秒數時，畫面卻仍停留在前一頁，且落差隨影片播放時間拉長而持續擴大（第8頁約4秒、第20頁末尾約12秒）。進一步排查：
  1. 使用者確認匯出的 mp4「畫面換頁」與「語音」彼此對得上（沒有播放器端的音畫不同步），`ffprobe` 也顯示視訊軌與音訊軌宣告的長度僅差 0.02 秒（9577.10s vs 9577.12s）——排除「匯出檔案本身音畫不同步」。
  2. 用受控實驗（1000 秒已知精確時長的測試訊號）分別跑過 `_extract_audio_track()`（ffmpeg `-ar 8000`）與 `_load_mono_array()`（pydub `set_frame_rate(8000)`）兩條路徑，換算回秒數都精準到 1000.000 秒——排除「重取樣造成浮點誤差」。
  3. 把使用者實際逐頁核對（21 頁全部，涵蓋整份 2 小時 40 分深）的真實時間，拿去跟 `locate_slide_start_and_end_times()` 量到的時間做回歸，發現只要套用一個**單一全域乘數 k≈1.00121**（不分頁面、不看內容，只跟該時間點在影片中的絕對位置成正比），殘差就整份 deck 收斂到 RMS 0.27 秒、最大 0.53 秒——遠優於「每頁各自累加一個固定秒數」的替代模型（RMS 0.44 秒）。三個额外的精確跳轉驗證點（第8、14、20/21頁）套用 k 之後誤差都在 0.2 秒內。
  4. 決定性的交叉驗證：把這個全域係數 k=1.00121 乘上第三輪修正量到的「頁內伸縮比例」0.99887（第8頁），結果是 1.0000788——幾乎精準等於 1.0000。這代表**第一輪修正一開始假設的「PowerPoint 匯出時把嵌入音訊加速播放約0.1%」其實從未存在**：那個約 0.12% 的「頁內伸縮」，從頭到尾都只是這同一個全域量測偏差的另一種呈現方式，不是影片本身的性質。真正、且唯一需要修正的，是 `locate_slide_start_and_end_times()` / `locate_slide_start_times()` 這兩個函式回傳的**絕對時間**本身，帶有一個跟已播放時間成正比、環境相依的系統性偏差——確切是互相關比對（`find_best_offset_seconds`）內部哪一個環節造成的，目前**尚未定位到程式碼層級**，但已经有一個經整份 deck 驗證過、精準到次秒等級的修正方法可以先行套用。
  修正方式：**`src/audio_position_locator.py`** 新增 `DEFAULT_GLOBAL_SCALE_CORRECTION`（預設 1.0，不修正）與新參數 `global_scale_correction`（`locate_slide_start_times()`、`locate_slide_start_and_end_times()` 均新增），套用時直接乘上每一個回傳的時間值。**這不是通用常數**——不同機器/PowerPoint版本/deck 可能有不同（甚至沒有）這個偏差，必須各自校準：拿這個工具量到的幾個分散在整份deck的時間點，跟用媒體播放器「跳至指定時間」功能精確驗證過的真實時間比對，回歸出 `真實時間/量測時間` 的比例。`src/main.py`（`--global-scale-correction`）、`scripts/regenerate_srt_from_export.py`、`scripts/dump_slide_bounds.py` 都已新增對應的 CLI 參數，預設維持 1.0 不影響既有行為。
  新增回歸測試：`tests/test_audio_position_locator.py::test_global_scale_correction_multiplies_every_returned_time`。

### Added

- `scripts/verify_tts_alignment.py`（新診斷工具）：檢查每頁 `.mp3` 與 `.wordboundaries.json` 兩者是否內部一致，完全不需要匯出的影片，用來排除「問題出在 edge-tts 這一步」的可能性。
- `scripts/verify_srt_accuracy.py`（新診斷工具）：從每頁的 wordboundaries 挑幾個字（頭/中/尾），直接把該字在原始 mp3 的音訊片段拿去跟匯出影片的真實音軌互相關比對，量出這個字真正出現的位置，印出跟「起點+原始 offset（未縮放）」預測值的差距與反推出的伸縮比例——這是第三輪修正實際依據的實測資料來源。第四輪修正時新增 `--slides`（限定特定頁面）與 `--csv-output`（把每個取樣字連同它在頁面內的位置比例一起存成 CSV），用來對懷疑有局部異常的頁面做密集（幾乎每字）取樣分析。

**已在使用者實際回報問題的那份 2 小時 40 分鐘 deck 上驗證**：套用第三輪修正後，用 `scripts/verify_srt_accuracy.py` 加上的 `corrected_delta` 欄位（套用這一頁自己直接量到的伸縮比例後，跟真實影片逐字比對的殘餘誤差）重新抽樣 20 頁、57 個字，殘餘誤差從修正前的最大 -0.837 秒收斂到 -0.082～+0.022 秒，絕大多數落在 ±0.02 秒內。第四輪修正（全域比例校正）套用後，用使用者親自逐頁核對的 21 個真實時間點驗證，殘差進一步收斂到 RMS 0.27 秒、全deck最大 0.53 秒。

### Known limitations

- deck 中最後一個有量測起始時間、但音檔長度不足以放下兩個獨立 anchor（起點+終點）的投影片，仍會退回用其他頁面的平均伸縮比例推估，理論上仍可能留下小幅殘餘誤差。
- 少數取樣點的 `corrected_delta` 落在 -0.08～-0.04 秒等級（例如真實 deck 測試中的第 5、7、11、3 頁），推測是真實語音內容（相對於白噪音測試訊號）互相關比對本身的精度極限，非系統性偏差；如果之後要進一步壓低，可以考慮加大 `--anchor-seconds` 或改用更長的 anchor 視窗。
- **`global_scale_correction` 的確切成因尚未定位到程式碼層級**：已排除匯出檔案本身音畫不同步、以及本專案重取樣路徑(ffmpeg/pydub)的浮點誤差，但 `find_best_offset_seconds()` 互相關比對內部究竟是哪個環節造成這個跟已播放時間成正比的系統性偏差，還沒有確認。目前的修正是經驗校準值，不是根因修復——不同 deck/環境的 k 值可能不同，甚至可能不需要這個修正，每次都需要重新校準，不能直接套用別人量到的數字。

## [0.6.0] - 2026-07-31

在一份真實的長講稿測試（20 頁、每頁 5～8 分鐘、總長約 2 小時 40 分）中發現：v0.5.0 的字幕合併邏輯（把每頁 mp3 時長加總、預測每頁在整支影片裡的位置）跟 PowerPoint 實際匯出的影片時間軸會逐頁累積漂移，到影片尾端偏移量達到數秒（用 `scripts/verify_slide_timing.py` 實測，最大偏移 9.09 秒），而且不是單純的等比例壓縮/延展，無法用一個全域縮放係數校正。字幕合併從「預測」改成「匯出影片後實測」。

### Added

- **`src/audio_position_locator.py`**（新模組）：把 `scripts/verify_slide_timing.py` 原本內建、只用來印診斷報表的音訊互相關比對邏輯（`find_best_offset_seconds`、FFT-based cross-correlation）抽出來成為正式模組，新增 `locate_slide_start_times()`，對已匯出的 MP4 抽出音軌，逐頁比對每張投影片自己的 mp3，量出每頁語音在最終影片裡「真正」開始播放的時間點，取代原本「預測」的做法。
- **`src/subtitle_pipeline.py`**：新增 `generate_srt_from_true_starts()`，使用 `locate_slide_start_times()` 量到的真實起始時間排字幕時間軸，取代原本單純把每頁時長加總的預測方式。原本的 `generate_srt_for_deck()`（預測路徑）保留不變，內部改為共用新拆出的 `_build_slide_captions()`（每頁的相對時間對齊邏輯，跟時間軸怎麼擺放無關）。一張投影片如果沒有量到真實起始時間（例如音檔遺失/影片音軌抽取失敗），該頁會退回使用預測位置並記錄警告，不會讓整份字幕開天窗。
- `main.py`：當 `--subtitles-output` 與 `--export-video` 同時使用時，字幕產生順序改成**先匯出影片、再用真實起始時間重建字幕**，取代原本「先產生字幕、再匯出影片」的順序——舊順序在字幕產生當下影片還不存在，沒有東西可以拿來比對。只有 `--subtitles-output`、沒有 `--export-video` 時（例如只想先確認字幕內容、還不急著匯出），維持原本「預測」路徑，因為這種情況下沒有已匯出的影片可以測量。真實起始時間比對失敗時（例如缺少 ffmpeg），會記錄警告並自動退回預測路徑，不會讓已經成功匯出的影片因為字幕比對失敗而整個中止。
- `scripts/verify_slide_timing.py` 改為呼叫 `audio_position_locator` 共用同一份比對邏輯（原本是獨立一份、跟正式管線各自維護），繼續保留原本的診斷報表輸出（每頁 predicted/measured/delta 表格），作為獨立驗證工具使用。
- 新增 `tests/test_audio_position_locator.py`（含一個用 `ffmpeg` 產生真實音訊、實際跑過互相關比對的端到端測試，不是全靠 mock）、擴充 `tests/test_subtitle_pipeline.py` 涵蓋 `generate_srt_from_true_starts()`。

### Changed

- **新增 `numpy`、`scipy` 為正式相依套件**（`requirements.txt` / `pyproject.toml`）：原本這兩個套件只有 `scripts/verify_slide_timing.py` 這支診斷腳本需要，屬於非必要依賴；現在 `--subtitles-output` 搭配 `--export-video` 使用時，正式管線本身也需要它們做音訊互相關比對，因此提升為必要依賴。

### Known limitations（已記錄於 TODO.md）

- 只有 `--export-video` 同時執行時，字幕才會用「真實起始時間」對齊；如果只產生字幕、不匯出影片，仍然只能用預測時間軸，長講稿情境下可能不準。
- 真實起始時間比對需要額外抽取整支影片音軌、逐頁跑互相關比對，長影片（例如本次測試的 2 小時 40 分鐘）會讓 `--subtitles-output` 搭配 `--export-video` 的執行時間變長；確切耗時未正式量測記錄。

## [0.5.1] - 2026-07-31

### Fixed

- 修正 `--insert-audio` 與 `--export-video` 在同一行指令裡接續執行時，`export_video()` 會以 `CoInitialize 尚未被呼叫`（`CO_E_NOTINITIALIZED`）失敗的問題。根本原因：v0.4.1 為 `insert_audio()` 加上的逾時保護，讓它的 COM 呼叫改在背景執行緒執行、並在該執行緒呼叫 `pythoncom.CoInitialize()`；但呼叫端（主）執行緒本身從未被初始化過 COM，而 `export_video()` 一直都是直接在呼叫端執行緒跑 COM 呼叫，因此第一次在主執行緒做 COM 呼叫時就失敗。`ppt_automation.py` 的 `export_video()` 現在改成透過既有的 `_run_in_com_thread()` 執行（沿用同一條執行緒，不是額外開新執行緒），確保呼叫前一定執行過 `CoInitialize()`。同時修正 `insert_audio(timeout_seconds=None)`（即 `--insert-audio-timeout 0`）這個目前還沒被實際踩到、但成因相同的潛在問題，讓它也統一走 `_run_in_com_thread()`。

## [0.5.0] - 2026-07-31

字幕功能從實驗性 PoC 正式畢業：原本 `subtitle_generator.py` 用「音檔總長度平均分配」估算每句字幕時間的做法，換成真正依照 edge-tts 回報的逐字/逐詞語音時間對齊，並整合進 `main.py` 的正式管線。分五個階段完成，設計討論與真實內容驗證過程詳見專案討論記錄。

### Added

- **`src/tts.py`**：新增 `synthesize_with_word_boundaries()` / `_stream_edge_tts_audio_with_word_boundaries()`，透過 edge-tts 的 streaming API（`boundary="WordBoundary"`）取得每個語音片段的文字與時間（`offset_seconds`/`duration_seconds`），而不只是純音檔。`boundary` 參數是 edge-tts 7.2.0 才加入的，若偵測到 `TypeError`（舊版函式庫）會自動退回不帶這個參數的呼叫方式。
- **`src/subtitle_segmenter.py`**（新模組）：把備忘稿文字切成適合當一行字幕的片段，純文字運算、不涉及語音或時間。依顯示寬度（預設 16 全形字／32 半形，區分全形/半形字元）斷行，用 `jieba` 做中文斷詞避免從詞語中間硬切，去除句尾多餘標點（保留？！），正規化中英文交界的空白，段落永遠是硬邊界不跨段合併，多行需要時用動態規劃讓每行寬度盡量平均（而非貪婪塞滿導致零碎孤兒行）。
- **`src/subtitle_alignment.py`**（新模組）：把 Phase 2 切好的字幕片段對齊到 Phase 1 的 WordBoundary 時間資料，算出每行的起訖秒數，並提供 `format_srt()` 轉成標準 SRT 文字。核心是逐一比對 WordBoundary 事件的文字在原文中的位置（因為 edge-tts 本身不回傳字元位置），比對失敗時採寬鬆策略（模糊比對、必要時內插猜測），不會讓單一比對失誤中斷整段字幕產生，所有比對失誤都會記錄在回傳的 `warnings` 清單。每行字幕的結束時間會延伸到下一行開始前留一小段緩衝（預設 0.15 秒），涵蓋語句間的自然停頓。
- **`src/subtitle_pipeline.py`**（新模組）：把多張投影片各自對齊好的字幕，依照它們在最終匯出影片裡的實際時間軸（每張投影片的時長 = 音訊檔案實際長度，或沒有備忘稿時的 `default_slide_duration`）平移、串接成一份完整的 SRT。這個時間軸假設有實際用 `scripts/verify_slide_timing.py`（音訊互相關比對）在真實匯出的 MP4 上驗證過，避免誤踩其他使用者回報過的 PowerPoint 匯出「死寂空白」問題。
- `tts.generate_audio_files()` 現在預設（沒有自訂 `generator` 時）會用 `synthesize_with_word_boundaries()` 當底層實作，同一次 TTS 呼叫就順便把每張投影片的 WordBoundary 時間存成旁路檔案 `slide_XXX.wordboundaries.json`，並在 `manifest.json` 記錄檔名（欄位 `word_boundaries_file`），不需要為了字幕另外重打一次 TTS。新增 `communicate_factory` 參數方便測試注入假的 edge-tts 回應。
- `main.py` 的 `--subtitles-output` 改接上述整條鏈路：有可用的 WordBoundary 資料時產生真正對齊過的字幕；沒有時（沒跑 `--generate-audio` 也找不到既有 manifest）寫出合法但空白的 `.srt`，而不是報錯或退回舊的粗略估算。
- 新增 `jieba>=0.42.1` 依賴（`requirements.txt` / `pyproject.toml`）。
- `edge-tts` 版本需求提升為 `>=7.2.0`（`boundary` 參數是這個版本才加入的）。
- 新增手動驗證腳本（因為 sandbox 開發環境連不上 edge-tts/沒有真實 Windows + PowerPoint，這些邏輯需要在真實環境驗證）：`scripts/smoke_test_word_boundaries.py`、`scripts/smoke_test_alignment.py`、`scripts/verify_slide_timing.py`，以及配套的 `scripts/sample_notes_for_smoke_test.txt`。
- 新增 `tests/test_cli_end_to_end.py`：直接呼叫 `src.main.main()`（跟真正的 CLI 入口一樣的路徑），涵蓋解析、`--generate-audio`（mock 掉 edge-tts 網路呼叫，不需要真的連網）、`--tts-max-retries` 負值拒絕、`--strict`、`--pretty`、找不到檔案等錯誤處理的完整流程，以及本次新增的字幕產生流程。補足先前測試都只測個別函式（`extract_notes`、`build_payload`、`generate_audio_files`…）、沒有任何測試真正跑過 `main()` 本身的缺口。`--insert-audio`/`--export-video` 仍需要真實 Windows + PowerPoint，不在這個模組的涵蓋範圍內。
- 新增 `tests/test_subtitle_segmenter.py`、`tests/test_subtitle_alignment.py`、`tests/test_subtitle_pipeline.py`，以及 `tests/test_tts_generator.py`/`tests/test_tts_word_boundaries.py`/`tests/test_main_payload.py` 的對應新測試。測試總數由 58 個增加到 114 個。

### Changed

- `main.py` 的 `write_subtitle_output()` 改為呼叫 `subtitle_pipeline.generate_srt_for_deck()`，回傳值也從單純的 `Path` 改成 `(Path, warnings)`，warnings 會透過 logger 印出（例如某張投影片沒有可用的 WordBoundary 資料時）。

### Removed

- **`src/subtitle_generator.py`（原本的字幕 PoC）與 `tests/test_subtitle_generator.py`**：功能已被上述新模組取代，`main.py` 也已經不再呼叫它，故從專案移除，避免兩套字幕邏輯同時存在造成混淆。舊邏輯用「音檔總長度平均分配」估算時間，不是真正對齊語音；新邏輯精確度高很多。

### Known limitations（已記錄於 TODO.md，刻意暫緩）

- 原文中「例如：」這類自成一段的極短段落，因為段落是硬邊界，會產生顯示時間很短的獨立字幕行。
- 純英文內容在目前針對中文調校的行寬設定下，換行位置有時不夠自然（可能切在片語中間，但不會切在單字中間）。

## [0.4.1] - 2026-07-30

### Fixed

- 修正 `--tts-max-retries` 傳負值時的靜默錯誤：重試迴圈原本寫成 `range(1, max_retries + 2)`，當 `max_retries` 為負值時這個 range 會是空的，導致 TTS 生成函式從未被實際呼叫過，卻仍把該頁記錄成生成成功寫進 `manifest.json`。現在 `tts.generate_audio_files()` 會把負值 clamp 成 `0`，CLI 層（`main.py` 的 `_non_negative_int`）也會直接拒絕負值並回報明確錯誤。
- 修正 `insert_audio()` 沒有逾時保護的問題：原本插入音訊時的所有 COM 呼叫（開啟簡報、插入音訊、存檔）都是同步阻塞，PowerPoint 卡住（例如被信任設定/修復對話框擋住）會讓整個流程無限期掛住。新增可選的 `timeout_seconds` 參數，透過背景執行緒 + `concurrent.futures` 的 `future.result(timeout=...)` 包住整段流程。

### Added

- 新增例外類別 `AudioInsertionTimeoutError`（繼承 `AudioInsertionError` 與內建 `TimeoutError`），逾時時拋出，用法比照既有的 `VideoExportTimeoutError`。
- CLI 新增 `--insert-audio-timeout` 參數（預設 1800 秒，設為 `0` 可恢復無限期等待的舊行為）。
- **TTS 生成的重試機制**（依實際 git log 核對後從 v0.4.0 移到這裡，見本文件頂端的版本歷史準確性說明）：僅套用在 edge-tts 網路請求上（區分可重試/不可重試的錯誤類型，例如缺 ffmpeg、憑證錯誤不重試），新增 CLI 參數 `--tts-max-retries`（預設 3）、`--tts-retry-delay`（預設 2 秒）。COM 操作（PowerPoint 自動化）刻意不做自動重試，見 README「錯誤處理策略」與 TODO.md「已評估、決定不做」。
- **`insert_audio()` 即時進度回報**（依實際 git log 核對後補上，先前完全沒有記錄）：迴圈逐頁插入音訊時，透過 `progress_callback(current, total, slide_num, status)` 即時回報處理進度，跟 `--generate-audio`/`--export-video` 既有的進度回報一致。
- 補上對應的回歸測試（`tests/test_tts_generator.py`、`tests/test_pptx_parser.py`、`tests/test_ppt_automation.py`），測試總數由 47 個增加到 52 個。

### Changed

- `pyproject.toml` 的 `description` 從「Parse PowerPoint notes and export slide metadata as JSON」更新為「Convert PowerPoint presentations into narrated MP4 videos using Edge-TTS and PowerPoint automation」，反映目前實際功能範圍。
- `main.py` 的 `extract_notes()` try/except 改用 `else` 區塊，讓「所有例外分支都會經由 `_fail()` 結束程式，因此 `slides` 保證會被賦值」這件事更明確。

## [0.4.0] - 2026-07-28

延續 v0.3.0 之後規劃的穩定性（Robustness）改善，從 `robustness-improvements` 分支合併回 `main`。

### Added

- 自訂例外階層（`src/exceptions.py`）：`Pptx2VideoError` 為共同基底，底下有 `PptParseError`、`TTSGenerationError`、`PowerPointLaunchError`、`AudioInsertionError`、`VideoExportError`、`VideoExportTimeoutError`（同時也是內建 `TimeoutError` 子類別），取代原本泛用的 `RuntimeError`。
- 正式 Logging（`src/logging_config.py`）：終端機維持原本簡潔輸出風格（無時間戳記），同時永遠把完整 DEBUG 細節記錄到 `logs/YYYY-MM-DD.log`，不受 `--verbose` 影響。新增 CLI 參數 `--log-dir`、`--no-file-log`。
- README 新增「錯誤處理策略（Skip vs Abort）」表格，把原本隱含在程式邏輯裡的規則文件化。

### Changed

- `--generate-audio` 補上錯誤處理（原本完全沒有，`--insert-audio`/`--export-video` 有但這個沒有）。
- `insert_audio()` 與 `export_video()` 共用的 COM 開關邏輯重構去重複，抽成 `_powerpoint_session()` / `_open_presentation()` 兩個 context manager。

## [0.3.0 及更早版本] - 日期不詳（回溯整理）

> 以下內容依現有文件重建的功能里程碑，非逐筆 commit 紀錄，版本切分點為概略推估。

### Added

- 建立 CLI 入口（`src/main.py`），可解析 `.pptx` 並輸出結構化 JSON。
- PowerPoint notes 解析（`src/pptx_parser.py`）：讀取投影片編號、標題、備忘稿，支援多頁簡報、長段落、空白行、無 notes 頁面（自動跳過生成音訊）。
- Edge-TTS 音訊生成（`src/tts.py`）：把備忘稿轉成 MP3，依頁碼命名，並產生 `manifest.json`。
- PowerPoint 音訊插入自動化（`src/ppt_automation.py: insert_audio`）：透過 `pywin32` COM 自動化，把生成的 MP3 插入對應投影片，圖示縮小並移到右上角、盡量在非播放狀態隱藏。
- MP4 匯出自動化（`src/ppt_automation.py: export_video`）：透過 `Presentation.CreateVideo()` 觸發 PowerPoint「建立視訊」，輪詢非同步匯出狀態直到完成，並在回報完成後額外檢查輸出檔案確實存在（安全網）。
- 字幕生成 PoC（`src/subtitle_generator.py`）：依備忘稿與（若可用）實際音檔時長輸出 `.srt`，作為架構驗證，尚未整合進正式管線（此功能不在本次文件整理範圍內）。
- 範例簡報生成腳本（`examples/create_sample_pptx.py`）與初版單元測試。
