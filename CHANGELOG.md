# Changelog

本文件記錄 pptx2video 各版本的重要變更，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

> **關於版本歷史準確性的說明**：本文件在 2026-08 依實際 `git log` 逐筆核對過 v0.3.0～v0.5.1 這段區間，修正了一處版本歸屬錯誤（見 v0.4.1 條目）與一處遺漏（`insert_audio()` 即時進度回報，同樣補在 v0.4.1）；`v0.5.0` 起的內容/日期已對照實際 commit 與 tag 位置確認無誤。`v0.3.0` 以前的條目仍是依專案現有文件（README / TODO / PROJECT_HANDOVER）回溯重建的功能里程碑，並未逐筆對照 commit，日期為不詳、版本切分點也是概略推估——如果之後要對照實際 commit 歷史修正這段，請直接編輯下方對應章節。

## [未發布]

## [0.9.0] - 2026-08-06

### Changed

- **字幕每行最大長度從「全形 16 個字」調整為「全形 18 個字」**：`src/subtitle_segmenter.py` 的 `DEFAULT_MAX_DISPLAY_WIDTH` 從 `32` 改為 `36`（顯示寬度單位，全形字算 2，故 18 × 2 = 36）。`tests/test_subtitle_segmenter.py` 同步更新對應的邊界測試（18 個全形字仍在同一行、19 個字必須被斷成多行）。這是純設定值調整，`src/main.py` 沒有把這個寬度開放成 CLI 參數、`scripts/` 底下也沒有腳本寫死這個數字，因此只需要改這兩個檔案。
  對已經產出的檔案的影響：只需要用 `scripts/regenerate_srt_from_export.py` 重新產生 `.srt`（不需要重跑 TTS/插入音訊/匯出影片）；如果之前用 `split_video_by_slides.py` 切過分段影片，記得連 `--subtitles` 也重新切一次，讓分段字幕套用新的斷行長度。

### Added

- **新增燒字幕（硬字幕）功能：`src/subtitle_burner.py` + `scripts/burn_subtitles.py` + `split_video_by_slides.py --burn-subtitles`**：把字幕直接燒進影片畫面，燒成一條固定寬高、固定位置的黑色長條、白色無外框文字疊在上面——不是 libass 內建 `BorderStyle=3` 那種隨每行文字長短自動縮放寬度的貼字黑底框，也不是預設的白字黑外框樣式。背景：專案負責人想要字幕黑底的大小固定不變（不論這行字幕多長），並且要能避開投影片模板本身的頁尾元素（logo、頁碼），這兩點都是 libass 自動貼字框做不到的；黑條的寬高、位置、字型（`Noto Sans CJK TC`）、字級（`15`）等預設值，是對照一份真實 1280x720 匯出投影片、實際目測反覆調整校正出來的（**不是通用常數**，換解析度/字型/字幕斷行長度都可能要重新校正，見 `docs/SPLIT_VIDEO.md`）。
  `src/subtitle_burner.py` 提供 `build_burn_filter()`（純字串組裝，含 Windows 絕對路徑冒號在 ffmpeg filtergraph 語法裡的跳脫處理——不跳脫的話磁碟機代號的 `:` 會被誤判成新的 filter 參數而整串解析失敗，不是「檔案找不到」這種好懂的錯誤）跟 `burn_subtitles_into_video()`（實際呼叫 ffmpeg，一律重新編碼視訊 `libx264`、直接複製音訊 `-c:a copy`）。`scripts/burn_subtitles.py` 是獨立 CLI，可以燒任一組 `.mp4`/`.srt`（完整版或已切好的某一段都可以）；`split_video_by_slides.py` 新增的 `--burn-subtitles`（需搭配 `--subtitles`）則是在切每一段的同時，立刻用同一套邏輯多產生一個 `segment_N_burned.mp4`，原本未燒字幕的 `segment_N.mp4` 跟軟字幕 `segment_N.srt` 依然保留，方便之後只想調整字幕樣式時不用重新切影片。黑條寬高/位置/字型/字級/`crf` 都可以用 CLI 參數覆寫，不用改程式碼。
  新增測試：`tests/test_subtitle_burner.py`（濾鏡字串組裝、Windows 路徑跳脫的純邏輯測試 + 用合成影片驗證實際燒出來的檔案可播放、時長不變的端對端測試）、`tests/test_split_video_by_slides.py` 新增 `--burn-subtitles` 缺少 `--subtitles` 時報錯、以及完整 CLI 端對端（合成雙投影片 deck，確認 `segment_N.mp4`/`.srt`/`_burned.mp4` 都正確產生）的測試。

- **新增選用的 `requirements-dev.txt`（`pytest`）**：測試套件原本就能用 stdlib 的 `unittest`（`python -m unittest discover -s tests -v`）完整執行，不需要安裝任何額外套件；這次追查 Windows 編碼問題時另外驗證用 `pytest tests/ -q` 跑同一套測試，輸出比較精簡、之後也可能需要 `-k` 篩選單一測試，因此把它列為選用開發相依套件，避免以後需要用的時候又要重新想「這個要裝什麼」。`pyproject.toml` 同步新增 `[project.optional-dependencies] dev = ["pytest>=7.0"]`，可用 `pip install -e ".[dev]"` 或 `pip install -r requirements-dev.txt` 安裝；不裝也完全不影響專案本身或既有 `unittest` 測試方式。

### Fixed

- **修正相鄰字幕時間戳會重疊、燒字幕時整句消失的問題**：測試燒字幕功能、對照真實課程影片時，使用者發現某一句字幕沒有出現在畫面上。追查後發現這兩句字幕的原始時間戳本身就有重疊（後一句比前一句還沒結束就開始了），用相同時間戳重現燒字幕過程後確認：字幕沒有真的被丟掉，而是 libass 遇到重疊字幕時的內建碰撞迴避機制，把後面那句自動往上推到 `scripts/burn_subtitles.py` 畫的固定黑條範圍**之外**，疊在沒有黑底的原始畫面上——真實影片裡那個位置通常是投影片的淺色背景，白字疊上去幾乎看不見，因此看起來像是「消失」了。
  根本原因追到 `src/subtitle_alignment.py` 的 `align_segments_with_word_boundaries()`：當 `subtitle_segmenter.py` 把一整句話從中間斷成兩行字幕的地方，剛好落在 edge-tts 某個 WordBoundary 事件的文字範圍中間（例如一整句沒有標點可斷、被迫因為行寬限制而硬斷），這一個事件會同時被算進前後兩句的時間範圍——把前一句的結束時間拉晚、同時把後一句的開始時間拉早，兩句的時間戳因此重疊。這個 bug 存在於字幕產生的核心邏輯裡，不是燒字幕或切分段造成的；燒字幕只是把原本軟字幕上不容易被注意到的問題，變成肉眼可見的「整句消失」。
  修正方式：在原有「把結束時間往後延伸、填補句子間自然停頓」的收尾邏輯裡，新增一個相反方向的收斂——如果某句字幕的結束時間已經超過下一句的開始時間（重疊），就把它收斂到下一句開始的時間點，並以自身開始時間為下限，避免收斂後產生負時長。完整重現過程、診斷細節見 `docs/SUBTITLE_OVERLAP_INCIDENT.md`。
  新增測試：`tests/test_subtitle_alignment.py` 新增 `test_straddling_word_boundary_event_does_not_overlap_adjacent_segments`（完整重現跨斷句點的 WordBoundary 事件情境）、`test_clamping_never_inverts_a_segment_into_negative_duration`（驗證嚴重重疊時不會產生負時長的畸形資料）。
  **影響範圍**：這個修正改的是 `.srt` 產生邏輯本身，軟字幕跟燒字幕都會受惠，不只是燒字幕情境；已經產出的 `deck.mp4` 需要重新執行 `scripts/regenerate_srt_from_export.py` 才能套用，如果之前切過分段，`split_video_by_slides.py --subtitles`（要的話再加 `--burn-subtitles`）也要重新跑一次。
  **真實 deck 驗證**：使用者重新產生真實課程 deck 的 `captions.srt` 後，提供新舊完整版本（各 3,360 條字幕）比對，逐條掃描時間戳重疊：舊版有 6 處重疊（0.42～0.54 秒），新版全數修正、且沒有引入新的重疊。另外從語料庫的逐字時間軸資料直接查證到 edge-tts 確實會把多字詞（如「系統的」「廣泛」）合併成單一 WordBoundary 事件，時長與觀察到的重疊量級吻合，佐證根本原因推論無誤。過程中另外發現一個成因相關但獨立的問題——`subtitle_segmenter.py` 的 jieba 斷詞在極少數情況下會斷錯詞界，導致「廣泛」被拆到兩行字幕（跟本次修正的時間戳重疊無關），已記錄於 `docs/SUBTITLE_OVERLAP_INCIDENT.md` 第 10 節，尚未修正。

- **修正在 Windows 上、當 stdout/stderr 被導向管線（pipe）或檔案時，印出中文字會讓程式直接崩潰的問題**：使用者在自己的 Windows 機器上執行 `pytest`（會用 `subprocess.run(..., capture_output=True, text=True)` 呼叫 `scripts/check_narration_gaps.py`）時，`test_detects_real_shaped_drop_and_exits_1` 測試失敗——起初懷疑跟同一時間調整 `DEFAULT_MAX_DISPLAY_WIDTH` 有關，追查後確認兩者無關；真正原因是 `check_narration_gaps.py` 印出「疑似漏講內容」預覽（含中文）時，`print()` 底層用的是 `sys.stdout` 當下解析出的編碼。互動式終端機通常會拿到 UTF-8（或作業系統目前使用中的主控台字碼頁），但**被導向管線或重新導向到檔案的 stdout/stderr**，Python 會改用 `locale.getpreferredencoding()`，在使用者這台非 Unicode 預設的 Windows 安裝上解析出來的是 `cp1252`——一個完全無法表示任何中文字元的舊式單位元組字碼頁。實際重現後拿到的錯誤是 `UnicodeEncodeError: 'charmap' codec can't encode characters ...: character maps to <undefined>`，程式在印出任何東西之前就直接崩潰，測試因為 stdout 是空字串而斷言失敗；同一份指令直接在互動式終端機執行卻完全正常，一開始因此容易誤判成跟其他變更有關。
  修正方式：`src/logging_config.py` 新增 `ensure_utf8_console()`，在 `sys.stdout`／`sys.stderr` 尚未是 UTF-8 時呼叫 `.reconfigure(encoding="utf-8", errors="replace")`；已經是 UTF-8、或該串流不支援 `.reconfigure()`（較舊版 Python 或非標準串流物件）時安全地略過，`ValueError`／`OSError` 也會被吞掉，確保這個防禦性工具本身永遠不會變成讓整支程式崩潰的原因。`setup_logging()`（`src/main.py` 主流程會呼叫）在建立 console handler 之前會先呼叫這個函式；另外 10 支獨立腳本（`scripts/calibrate_scale.py`、`check_narration_gaps.py`、`dump_slide_bounds.py`、`regenerate_srt_from_export.py`、`smoke_test_alignment.py`、`smoke_test_word_boundaries.py`、`split_video_by_slides.py`、`verify_slide_timing.py`、`verify_srt_accuracy.py`、`verify_tts_alignment.py`）的 `main()` 一開始也都各自呼叫，因為這些腳本不一定會經過 `setup_logging()`。
  新增測試：`tests/test_logging_config.py::EnsureUtf8ConsoleTests`（非 UTF-8 串流會被重新設定、已是 UTF-8 的串流會略過、不支援 `.reconfigure()` 的串流不會崩潰、`.reconfigure()` 拋出 `ValueError`/`OSError` 會被安全吞掉且不影響另一個串流、`sys.stdout`/`sys.stderr` 為 `None` 不會崩潰、對真實的 `io.StringIO()` 物件也不會崩潰）。這個問題是使用者在自己機器上實際重現、並提供完整 traceback 後才確認根因。
  **後續追加修正（同一輪、使用者套用上述修正後在自己機器上重新驗證時發現）**：把 `check_narration_gaps.py` 的 stdout 改成 UTF-8 之後，透過 `subprocess.run(capture_output=True, text=True)` 呼叫它的測試（`tests/test_check_narration_gaps.py`、`tests/test_calibrate_scale.py`）改成崩潰在**父行程**這一端——`subprocess.run()` 在 `text=True` 但沒有明確指定 `encoding=` 時，是用父行程自己的預設編碼（一樣是 `locale.getpreferredencoding()`）去解碼子行程捕捉到的 bytes；子行程現在寫出的是合法 UTF-8 多位元組序列，父行程卻還是拿 `cp1252` 去解，變成 `UnicodeDecodeError: 'charmap' codec can't decode byte ...`，跟原本的 `UnicodeEncodeError` 是同一個根因（雙方對「這個管線該用什麼編碼」沒有共識）的另一種呈現方式。修正方式：兩份測試檔的 `subprocess.run(...)` 呼叫都明確加上 `encoding="utf-8", errors="replace"`，讓父子兩端的編碼假設一致，不再各自依賴系統 locale 猜測。

## [0.8.0] - 2026-08-04

### Added

- **`scripts/split_video_by_slides.py`（新工具）**：把已匯出的 MP4 依「換頁面的地方」切成多段檔案，而不是依任意的時間長度硬切。背景：使用者的 deck 約 20 頁，匯出的 MP4 長達 2.5～3 小時，希望分成 3 段，但要求切點必須剛好落在換頁邊界上，不能切在講稿講到一半的地方。PowerPoint 的 `Presentation.CreateVideo()`（`ppt_automation.export_video()` 底層呼叫的 API）沒有任何「只匯出某個投影片範圍」的參數——每次呼叫一定是匯出整份簡報，如果為了分段而重新匯出 3 次，2.5～3 小時的匯出時間會直接乘上 3 倍。這個新工具改成「對已經匯出好的單一 MP4 事後切割」：重用 `audio_position_locator.locate_slide_start_and_end_times()`（跟 `regenerate_srt_from_export.py` 用來校正字幕的同一個真實起始時間量測函式）取得每一頁narration 真正開始播放的時間點，保證切點精準落在頁面交界，而不是任意時間戳記。
  - 支援兩種切點決定方式：`--num-segments N`（自動選出 N-1 個切點，讓每一段的長度盡量平均，用「逐一比對每個尚未使用過的頁面邊界與該段目標時間點的距離」的貪婪法選擇，而非只看與理論上等分點最近的單一邊界，避免因為某幾頁特別長而讓某一段明顯比其他段長很多）；`--split-after-slides 7 14`（明確指定要在哪幾頁之後切，例如切成 1-7、8-14、15-end 三段）。
  - 實際切割用 ffmpeg 的 `-c copy`（stream copy，不重新編碼）以求速度，代價是切點會吸附到該時間點之前最近的關鍵影格，而不是絕對影格精準；加上 `--reencode` 可以改成重新編碼以取得影格精準的切點（速度慢很多）。
  - 跟 `regenerate_srt_from_export.py` 一樣支援 `--global-scale-correction`（見 v0.6.1 第四輪修正、`scripts/calibrate_scale.py`、`scripts/verify_srt_accuracy.py`），而且這裡校正是否準確更重要：字幕時間軸差個零點幾秒觀眾未必有感，但切點沒校正好，可能會把下一頁narration的前一小段直接切掉或留在上一段結尾。
  - **`--subtitles`（同一個 commit 追加）**：只切影片、不處理字幕的話，整份 deck 的 `captions.srt` 時間軸沒有跟著每一段影片各自歸零，第 2、3 段之後字幕就完全對不上畫面。加上 `--subtitles output/captions.srt`（必須是 Step 10 真實起始時間對齊版本，不能是 Step 8 單獨執行時的「預測版」）之後，會在切每一段影片的同時也把字幕切成對應的 `segment_N.srt`，各自從 `00:00:00` 重新算起——而且刻意**重用跟切影片時完全相同的切點時間戳**，不是另外重新量一次，確保同一段的 `.mp4`/`.srt` 對「時間 0 秒」的認定一致。落在切點範圍外的字幕行整行捨棄；橫跨切點的字幕行（理論上不該發生，因為切點本來就選在某頁narration 的真正起點）會被裁切到所在那一段的範圍內，不會整行丟掉或重複出現在兩段裡。新增了手刻的 `_parse_srt()`（沒有另外引入外部套件，因為要讀的只有這個專案自己 `format_srt()` 寫出來的簡單格式）跟 `_slice_srt_for_segment()`。
  - 已有 `tests/test_split_video_by_slides.py`：純邏輯的切點選擇測試（等分/不等長投影片/邊界只能用一次/排除第 1 頁自己的起始時間等情境）、SRT 解析與切片測試（標準格式解析、跳過格式異常區塊、只保留有重疊的字幕行並歸零、裁切橫跨邊界的字幕行、邊界剛好相接時的零長度重疊會被捨棄），以及 `_probe_duration_seconds()`/`_run_ffmpeg_segment()` 的 ffmpeg 端對端測試（用合成測試影片驗證量測整支影片長度、切出指定時間區間、確認輸出檔案存在且長度正確），最後這組跟 `test_calibrate_scale.py` 一樣用 `@unittest.skipUnless(shutil.which("ffmpeg") ...)` 包起來，沒有 ffmpeg 的環境會自動跳過而不是失敗。全部 16 個測試都通過，整個套件目前 167 個測試全過。

## [0.7.0] - 2026-08-04

### Added

- **`scripts/calibrate_scale.py`（新工具）**：把手動推導 `global_scale_correction`（見 v0.6.1 第四輪修正）的流程從「手動列出量測值、貼進試算表、手算回歸」變成可重複執行的腳本。背景：v0.6.1 第四輪修正得到的 k=1.00121，只在使用者自己這一台機器、這一份 deck、這一套 PowerPoint 安裝上驗證過（見 `DEFAULT_GLOBAL_SCALE_CORRECTION` docstring 的明確警告：這不是通用常數）。不論這個約 0.12% 的偏差最終被證實是 PowerPoint 匯出管線的普遍特性、還是單純這台機器的本地因素，任何人要在自己的環境上得到專屬的校正值，都不應該重複一遍當初手動做的流程。
  用法：先用預設（不加 `--global-scale-correction`，等同 1.0）跑一次完整流程產生未校正的 `output/deck.mp4`；用媒體播放器的「跳至指定時間」功能（不是用眼睛看進度條）精確記錄幾個（建議 5～8 個，涵蓋整份 deck 頭尾）投影片實際開始講話的真實秒數，存成一個 `{"投影片編號": 真實秒數, ...}` 的 JSON 檔；執行 `python scripts/calibrate_scale.py --video ... --manifest ... --slides-json ... --observations 你的觀測.json`，會重新量測（`global_scale_correction=1.0`）那幾頁未校正的時間，用跟原始 k=1.00121 相同的回歸方式（強制過原點的最小平方法）算出建議值，並印出 RMS／最大殘差供判斷擬合品質；可用 `--report` 額外輸出一份含逐頁量測值/觀測值/殘差的 JSON 記錄。
  若殘差明顯比原始校準（RMS 0.27 秒／2 小時 40 分 deck）差很多，腳本會提示可能不是單純的全域比例偏差，建議檢查逐頁殘差是否集中在特定一兩頁（可能是那幾頁本身量測不穩，而非需要 per-slide 校正——見下方「已評估、決定不做」的討論）。
  新增測試：`tests/test_calibrate_scale.py`（`_fit_scale()` 的單元測試 + 一個端到端測試，用合成音檔驗證腳本能從已知套用的縮放係數精確反推回同一個值）。
- **`--generate-audio` 新增「疑似漏講內容」自動偵測**：在一份真實 18 頁 deck 上，發現第 9 頁的講稿裡有一大段（約 300 字、正常語速要念 50 幾秒的內容，涵蓋「Flash 的第四點」與「第五點」兩個完整重點）edge-tts 在合成語音時完全沒有念出來——不是拋例外、不是網路錯誤，音檔本身就是短的，`wordboundaries.json` 也只是安靜地跳過那段文字。使用者實際抽聽 mp3 確認：從「因此。」講完後，下一句直接接到好幾句之後的「今天大家先建立概念即可」，中間整段內容確實消失了。這代表最終影片實際播出的內容有缺漏，比字幕時間對不準嚴重得多，而且**先前完全沒有任何機制會提示這件事**——`align_segments_with_word_boundaries()` 原有的「No WordBoundary events matched segment」警告雖然間接反映了這個現象，但是逐句印出、跟一般標點符號沒對上的正常情況混在一起，不會特別標示「這一段特別大、看起來不對勁」，也不會顯示到底漏了哪些字，很容易被忽略過去。
  新增 `src/subtitle_alignment.py` 的 `find_suspected_dropped_narration()`：重新使用 `align_segments_with_word_boundaries()` 內部同一套「WordBoundary 事件 → 原始文字位置」比對邏輯，找出所有已比對上的事件之間的間隔，同時看「間隔了多少字」跟「間隔了多少秒」——用這一頁**自己**其餘部分量到的語速當基準，如果某個間隔的字數換算成預期時長，實際音檔時長卻遠遠不夠（預設：不到預期時長的 30%，且間隔字數至少 15 字，避免對一般被跳過的標點符號、換行誤判），就判定為疑似漏講，回傳漏掉的確切文字內容、發生的音檔時間點、預期時長與實際時長。這個判斷方式已經在真實的第 9 頁資料上驗證過：能精準抓出那唯一一段被跳過的內容，前後其他正常的間隔都不會誤判。
  `src/tts.py` 的 `generate_audio_files()` 新增：每頁用預設 generator 產生完 audio 後，自動呼叫這個檢查，結果存進該頁 manifest 條目的 `"narration_gap_warnings"`（沒有問題時是空陣列），並可透過新的 `on_narration_gap` callback 即時收到通知——刻意設計成生成音訊時就會執行，不需要等到後面字幕產生階段才會發現，這樣即使只用 `--generate-audio` + `--insert-audio` + `--export-video`（完全沒有跑字幕功能）也一樣會被檢查到。`src/main.py` 接上這個 callback，用單獨一行、明顯區別於其他訊息的 `POSSIBLE DROPPED NARRATION` 警告印出，內容包含建議去聽的音檔時間點跟漏掉的文字內容預覽，不會被淹沒在其他逐句警告裡。
  新增回歸測試：`tests/test_subtitle_alignment.py::FindSuspectedDroppedNarrationTests`（含用合成資料重現漏講情境、確認正常語速與零星標點符號跳過不會被誤判）、`tests/test_tts_generator.py::test_default_generator_flags_suspected_dropped_narration`、`test_custom_generator_skips_narration_gap_check`。
  這是一個啟發式判斷、不是保證——分辨依據是「跟這一頁自己其餘部分的語速相比是否合理」，理論上一段講稿裡刻意寫的長時間停頓也可能被誤判，但目前只在真實資料上驗證過會準確抓到真正的漏講內容；如果之後發現誤判，可以透過 `find_suspected_dropped_narration()` 的 `min_gap_chars`／`pace_ratio_threshold` 參數調整敏感度。
- **`src/main.py` 的 `--generate-audio` 新增 `--slides` 篩選參數**：只重新生成指定頁碼（例如 `--slides 6,9` 或 `--slides 6,8-10`），不用整份 deck 重跑一次 edge-tts。動機：上面「疑似漏講內容」偵測上線後，實際會遇到「某一頁被標記出疑似漏講，想單獨重新生成/重新檢查那一頁」的情境，但原本 `generate_audio_files()` 每次執行都會用當次的 slides 清單整份覆寫 `manifest.json`——如果只想處理一頁，整份 deck（例如已知的 2 小時 40 分那份）要重新呼叫一次 edge-tts，成本很高。加了 `--slides` 之後，`src/main.py` 只會把篩選出的頁面交給 `generate_audio_files()`，並在寫回 `manifest.json` 前，把這次沒有重新生成的其他頁面的舊條目原封不動合併回去，不會因為只跑一頁就把其他頁的紀錄弄丟；篩選到 deck 裡不存在的頁碼會直接報錯中止，不會靜默略過。`generate_audio_files()` 本身不知道有這個篩選機制，維持「呼叫端給哪些頁面就完整生成/描述那些頁面」的單純語意，篩選與合併都在 `src/main.py` 這一層處理。
- **`scripts/check_narration_gaps.py`（新工具）**：讓「疑似漏講內容」偵測（上面 `find_suspected_dropped_narration()`）可以獨立套用在**已經生成過**的音檔上，完全不需要重新呼叫 edge-tts。動機：這個檢查目前只會在 `--generate-audio` 執行過程中自動觸發——對於在這個功能上線之前就已經生成好的 `manifest.json` + `slide_XXX.wordboundaries.json`（例如使用者手上原本就有、用來發現第 9 頁問題的那批資料），沒有辦法在不整份重新生成音訊的情況下事後套用這個檢查。這個腳本直接讀取既有的 `manifest.json`、對應的 `wordboundaries.json` 檔案、以及 `output/slides.json`（或用 `--pptx` 直接從簡報重新抽取備忘稿文字），逐頁呼叫同一個 `find_suspected_dropped_narration()` 並印出跟 `--generate-audio` 執行時一樣格式的 `POSSIBLE DROPPED NARRATION` 警告；支援 `--slides 6,9` 只檢查特定頁面。找到疑似漏講內容時結束代碼為 1（沒有問題或該頁沒有可檢查的資料則為 0），方便串進腳本判斷。
  新增測試：`tests/test_cli_end_to_end.py::test_slides_flag_regenerates_only_selected_slide_and_merges_manifest`、`test_slides_flag_rejects_slide_number_not_in_deck`、`tests/test_check_narration_gaps.py`（`parse_slide_selector()` 單元測試 + 端到端子行程測試，涵蓋真實形狀的漏講重現、正常語速不誤判、`--slides` 篩選）。
- **`scripts/verify_srt_accuracy.py` 新增自動回歸出 `--global-scale-correction` 建議值的功能，不需要 Audacity/人耳確認**：使用者在照著 README「🎯 校準」流程校準真實 deck 時，反映不希望每次匯出影片後都要重新開 Audacity、一頁一頁手動核對真實時間點才能校準或驗證。追查發現：`verify_srt_accuracy.py` 這支工具原本就是為了驗證字幕準確度而寫的，本來就會自動對整份 deck抽樣多個字、逐一跟實際匯出的 mp4 音軌做交叉比對，量出每個字**真正**的位置（`measured_word_position`）——這跟 `scripts/calibrate_scale.py` 手動校準流程裡「人工用 Audacity 核對出的真實時間」在數學上是同一種東西，只是一個是機器自動測、一個要人耳確認，兩者都可以拿去跟「套用目前係數後的預測位置」做同一種回歸（`真實時間 = k × 預測時間`，強制過原點的最小平方法）反推出 `k`。也就是說，這支工具在完成原本「驗證準不準」的任務時，其實已經蒐集到推導校正係數所需要的全部資料，只是原本沒有把這一步做出來、印出來。
  修正方式：新增 `_fit_scale()`（跟 `scripts/calibrate_scale.py` 裡同名函式的回歸公式完全相同，刻意重複實作而非互相 import，讓兩支腳本各自能獨立使用），在完成逐字抽樣後，用蒐集到的 `(套用目前係數後的預測位置, 交叉比對量到的真實位置)` 這些點對，直接回歸出建議的 `--global-scale-correction` 值，並印出套用後的 RMS／最大殘差供判斷擬合品質——整個過程不需要開 Audacity、不需要人耳確認任何一個時間點。取捨已在腳本 docstring 與 README 中說明清楚：這個估算值的樣本是機器自動挑選、自動比對出來的，沒有獨立的人耳驗證當對照組，deck 越長、抽樣的字越多會越可靠；準確度真的很重要的場合，建議跟 `calibrate_scale.py` 手動校準的結果交叉核對，不要只依賴這個自動估算值。
  已用真實回歸公式的單元測試驗證 `_fit_scale()`（合成已知比例的資料，確認能精確反推回同一個值，並驗證分母為零時正確拋出錯誤）。

### Fixed

- **`src/subtitle_alignment.py` 的 `_match_word_boundaries()` 在漏講段落附近夾著重複短詞時，會把疑似漏講的位置跟範圍判斷錯**：在同一份 18 頁 deck 上又發現一次真實漏講（第 10 頁），edge-tts 把「SRAM 斷電後資料立即消失。Flash 則可以永久保存。第四。SRAM 的讀寫速度非常快。」整段跳過，直接接到後面的「Flash 的讀取速度雖然也很快」。問題出在：「Flash」這個字剛好在被跳過的段落裡也出現過一次（「Flash 則可以永久保存」），而比對邏輯原本是「從目前游標位置起，抓文字裡下一個出現的相同字」——不管後面還有沒有更晚、更符合時序的同一個字。結果audio 裡真正屬於第二個「Flash」的那段語音時間，被誤配到了文字裡第一個「Flash」的位置；再加上緊接著的「的」同樣重複出現，錯位被連鎖放大，讓一段長達 65 字、只用不到 3 秒念完（明顯異常）的真實漏講，被拆成好幾小段各自獨立比對，其中兩段小到低於偵測門檻、完全沒被抓到，另外兩段雖然被抓到，回報的漏講內容跟位置卻是錯的（使用者實際抽聽確認後才發現回報的範圍不完整）。
  修正方式：`_find_boundary_span()` 新增消歧邏輯——當同一個 WordBoundary 文字在搜尋窗口內出現不只一次時，不再無條件選最前面那個，而是分別嘗試「以這個候選位置接續下去，能不能讓接下來幾個（預設 3 個）WordBoundary 事件的文字，也在附近找到」，挑選讓後續比對最連貫、跳過字數最少的那個候選位置；只有單一候選、或沒有足夠後續事件可供比對時，才維持原本「取第一個」的行為，避免對絕大多數（本來就不重複、不受影響）的比對邏輯增加不必要的計算或風險。修正後重新比對第 10 頁的真實資料，`find_suspected_dropped_narration()` 正確回報成一整段、範圍完全對應使用者抽聽確認的漏講內容，不再被拆成碎片。
  新增回歸測試：`tests/test_subtitle_alignment.py::RepeatedWordDisambiguationTests`（用合成資料重現「重複詞夾在漏講段落邊界」的真實情境，並確認一般重複詞——沒有漏講時——仍然照時間順序正確比對，不會被消歧邏輯弄巧成拙）。
  已用第 6、9、10 頁三份真實 wordboundaries 資料重新驗證：第 6、9 頁（已確認修好、重新生成過）維持零誤判，第 10 頁的真實漏講正確合併回報成一整段。
- **（後續修正）上面第 10 頁的消歧修正本身引入了一個新的迴歸**：使用者只重新生成第 10 頁（`--generate-audio --slides 10`）後，`--generate-audio` 附帶觸發的字幕重新生成階段（每次都會重新處理**整份** deck 既有的 manifest/wordboundaries 資料，不只是這次重新生成的頁面）意外讓完全沒被動到的第 13 頁冒出一大串新的「Could not locate WordBoundary text」警告（超過 700 個，佔該頁全部事件的 8 成以上）。使用者提出疑問：這是 edge-tts 端新出的問題，還是本地處理端的問題？用第 13 頁真實 wordboundaries 資料 + 完整原稿逐步排查後確認：**是本地處理端的迴歸，不是 edge-tts 的問題**——第 13 頁的原稿裡有兩段字面上幾乎重複的句子（先是摘要「...分成四個階段：Input，也就是輸入。」，稍後接著是細節「...第一個階段，Input，也就是輸入。」），而上面消歧修正的評分方式（把「游標到候選位置的距離」跟「候選位置後續能不能順利接上」直接相加取最小值）在這種情況下，會因為「，Input」比「：\nInput」少跳過一個字，讓**距離較遠、但續接稍微乾淨一點點**的候選位置「個」贏過緊接在游標後面、明顯正確的那個，一次跳過約 135 字的真實內容，並像骨牌一樣在後面的「資訊」「是」等常見重複字上重演，最終讓游標提早跑到接近全文結尾，後面所有事件都因為在游標之後找不到對應文字而報錯。（過程中還嘗試過「限制候選位置的續接搜尋範圍，不能跨過下一個相同字的出現位置」這個修法，結果在「是」「資訊」這類極高頻字上又太過嚴格、誤傷了另一批原本正確的比對，最終捨棄。）
  修正方式：`_pick_best_candidate()` 改用字典序評分，而非直接加總——**優先**依「續接品質」（候選位置後續能不能順利接上，即原本的評分方式）排序；只有當多個候選位置的續接品質差距在 `_CONTINUATION_TIE_THRESHOLD`（10 字）以內、視為「大致打平」時，才用「離游標的距離」當作決定性的次要依據，選比較近的那個。這個門檻刻意設在「一兩個字的標點符號差異」與「一整段被跳過的真實內容（實際案例動輒 20～30 字以上）」之間：兩個相似句子造成的續接品質差距通常只有 1～2 字，遠低於門檻，會用距離正確判斷；而真正的漏講（如上面第 10 頁的 Flash 案例）造成的續接品質差距高達數十字，遠超門檻，續接品質本身就足以正確判斷，不需要靠距離。
  新增回歸測試：`tests/test_subtitle_alignment.py::RepeatedWordDisambiguationTests::test_near_duplicate_phrase_prefers_nearby_candidate_over_slightly_cleaner_far_one`（用合成資料重現「兩段字面近似的句子連續出現」情境）。
  已用第 6、9、10、13 頁四份真實 wordboundaries 資料重新驗證：全部維持零誤判、零警告；第 6 頁與第 10 頁各自的原始（真實漏講）資料仍正確合併回報成單一一段疑似漏講。
- **單獨執行 `--subtitles-output`（不加 `--generate-audio`）時，就算 `output/audio/manifest.json` 已經存在，也不會讀取它，而是直接寫出空白的 `.srt`**：使用者實際照著步驟 7、8 分開下指令的流程操作時發現，步驟 8 的字幕產生指令範例裡也帶了 `--generate-audio`，因而提出疑問——如果步驟 7 已經生成過音檔，步驟 8 是否還需要再加一次 `--generate-audio`？這樣不就等於把語音重新生成一遍？追查後確認：**是的，在修正前的程式碼裡確實需要**，而且不是文件寫錯——`--insert-audio` 與「`--export-video` 後的真實起始時間字幕」兩條路徑都已經有 `_resolve_audio_manifest()`，找不到這次執行產生的 manifest 時會自動改讀磁碟上既有的 `manifest.json`；但「不匯出影片、單純只要字幕」這條路徑（`--subtitles-output` 且沒有 `--export-video`）從一開始就沒有套用這個 fallback，只會用這次執行實際跑過 `--generate-audio` 才會有的資料，manifest.json 就算就在旁邊也完全不會去讀。實際寫一個「先跑一次 `--generate-audio` 產生 manifest，再單獨跑一次不帶 `--generate-audio` 的 `--subtitles-output`」的重現腳本，確認第二次執行真的寫出一個空白（零字幕）的 `.srt`。
  修正方式：把 `_resolve_audio_manifest()` 的定義提前到組出 `payload` 之前，讓「不匯出影片」這條字幕產生路徑也比照 `--insert-audio`／真實起始時間路徑，改用 `_resolve_audio_manifest()` 解析要用的 manifest（這次執行產生的優先，沒有的話退回讀取既有 `manifest.json`），並在 manifest 來源不是這次執行產生時，用它重新組一份 `payload` 給字幕產生函式用，而不是直接沿用只反映「這次執行」狀態的舊 `payload`。修正後上面的重現腳本第二次執行能正確產生出跟第一次一樣的字幕內容，不需要重新呼叫 edge-tts。
  新增回歸測試：`tests/test_cli_end_to_end.py::test_subtitles_output_alone_reuses_existing_manifest_without_generate_audio`。
  README 步驟 8 已同步更新，補上單獨執行 `--subtitles-output`（不重新生成音檔）的指令範例，並修正原本「沒有 `--generate-audio` 一定會寫出空白 `.srt`」這段已經過時、不準確的說明。

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
