# 事件報告：Windows 上因 cp1252 編碼導致的 UnicodeEncodeError / UnicodeDecodeError 崩潰

- **發生/發現日期**：2026-08（`DEFAULT_MAX_DISPLAY_WIDTH` 相關改動之後的測試中意外撞見）
- **影響範圍**：`scripts/check_narration_gaps.py`、`src/main.py` 的疑似漏講警告路徑、以及其他所有會印出中文文字的獨立腳本，**僅限**「輸出被導向管線或檔案（非互動式終端機）」且「系統 locale 解析出的預設編碼不是 UTF-8」這兩個條件同時成立時才會觸發（本案例是使用者這台 Windows 機器，Python 3.13，英文/`cp1252` locale）。
- **嚴重程度**：中——不會造成資料損毀或影片/字幕錯誤，但會讓「疑似漏講內容偵測」這個安全網功能本身在被測試/自動化呼叫時直接崩潰，等於安全網失效卻沒有明確提示；也讓 `pytest`/`unittest` 的相關測試出現看似無關、難以定位的失敗。
- **狀態**：已修復並經使用者在自己的 Windows 機器上實機驗證通過。

---

## 1. 事情是怎麼發生的（根本原因）

問題其實分成兩層，本質上是同一件事的兩種呈現方式：**Python 的文字編碼解析方式，取決於這段位元組流「最後要去哪裡」，而不是單純看作業系統或系統語言設定。**

### 第一層：子行程「寫」的時候崩潰（UnicodeEncodeError）

`scripts/check_narration_gaps.py` 在偵測到疑似漏講內容時，會用 `print(f"...{preview!r}")` 印出一段中文預覽文字。這行程式碼本身完全沒問題——問題出在 `print()` 底層用什麼編碼把這段文字轉成位元組：

- 在**互動式終端機**（人直接打開 PowerShell 執行）裡，Windows 通常會透過 Console API 走 UTF-8（或作業系統目前作用中的主控台字碼頁）。
- 但如果 stdout **被導向管線或重新導向到檔案**（例如 `subprocess.run(capture_output=True)`、`command > out.txt`），Python 會改用 `locale.getpreferredencoding()` 決定編碼。在使用者這台「非 Unicode 預設」的 Windows 安裝上，這個值解析出來是 `cp1252`——一個源自西歐語系的舊式單位元組字碼頁，**完全無法表示任何中文字元**。

於是只要這段程式碼被以「管線」的方式呼叫，印出中文的瞬間就會拋出：

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 183-222: character maps to <undefined>
```

程式在印出任何東西之前就直接崩潰（Python 未捕捉例外的預設結束代碼是 1）。

### 第二層：呼叫端「讀」的時候崩潰（UnicodeDecodeError）

修好第一層、讓子行程改寫 UTF-8 之後，緊接著在使用者驗證時發現：呼叫這支腳本的 `subprocess.run(capture_output=True, text=True)`（`tests/test_check_narration_gaps.py` 內部、以及使用者自己寫的重現腳本 `repro_gap2.py`）如果沒有明確指定 `encoding=`，一樣會退回用**呼叫端自己**的 `locale.getpreferredencoding()`（同一台機器，一樣是 `cp1252`）去解碼子行程回傳的原始 bytes。

子行程現在寫出的是合法的 UTF-8 多位元組序列，呼叫端卻拿 `cp1252` 去解讀，於是變成：

```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 254: character maps to <undefined>
```

也就是說：修好了「寫」的那一端，但「讀」的那一端沒有跟著改，雙方對這條管線該用什麼編碼失去了共識，問題只是換了個位置重新出現。

> ℹ️ 這兩層的共通點：**只要牽涉到管線／檔案重新導向，Windows 上就不能假設編碼一定是 UTF-8**，寫入端跟讀取端都必須明確講好用什麼編碼，不能各自依賴系統 locale 默默猜測。

---

## 2. 這個問題是怎麼被發現的（時間軸）

1. **起點是一個不相關的提問**：使用者詢問如果把 `DEFAULT_MAX_DISPLAY_WIDTH` 從 32 改成 36 或 40，基於已產出的檔案，哪些步驟需要重做。這個問題本身已回答完畢，跟本次事件無關。
2. **使用者貼出一個測試失敗**：`tests/test_check_narration_gaps.py::test_detects_real_shaped_drop_and_exits_1` 失敗，並問「這是不是我改 `DEFAULT_MAX_DISPLAY_WIDTH` 造成的？」
3. **先排除了最直覺的懷疑**：檢查 `check_narration_gaps.py` 的 import 關係，確認它從未 import `subtitle_segmenter.py`（`DEFAULT_MAX_DISPLAY_WIDTH` 所在的模組），兩者邏輯上互不相干；同時在沙盒環境重跑同一個測試，7/7 全過。這說明失敗跟該項改動無關，但還沒找到真正原因。
4. **重新讀失敗訊息本身**：`AssertionError: 'POSSIBLE DROPPED NARRATION' not found in ''`——stdout 是**空字串**，代表子行程根本沒有正常印出任何東西就結束了，而不是印出了「錯誤」的內容。這是關鍵線索：不是邏輯算錯，而是程式提前中止。
5. **讀原始碼、提出假設**：回頭讀 `check_narration_gaps.py` 裡實際印出中文預覽的那行 `print(f"...{preview!r}")`，聯想到 Windows 上「互動式終端機」與「被管線捕捉」的 stdout 編碼解析路徑不同，提出「這是一個 Windows 專屬、只有在被 subprocess 捕捉時才會出現的編碼崩潰」的假設。
6. **多輪由使用者在真機上重現，逐步逼近真正觸發條件**：
   - 使用者直接執行 `check_narration_gaps.py` 對他自己的真實資料 → **沒有崩潰**。但這不代表假設錯誤，因為他的真實資料剛好沒有偵測到任何疑似漏講，崩潰路徑的 `print()` 根本沒被執行到。
   - 提供 `repro_gap.py`，用跟失敗測試完全相同的合成資料，強迫產生一筆「疑似漏講」的偵測結果，直接呼叫 `main()` → **依然沒有崩潰**。因為是直接在終端機裡執行，走的是互動式主控台的編碼路徑（通常是 UTF-8），不是管線路徑。
   - 提供 `repro_gap2.py`，改用跟失敗測試完全相同的 `subprocess.run(capture_output=True, text=True)` 呼叫方式 → **成功重現崩潰**，拿到完整 traceback，確認就是 `check_narration_gaps.py` 第 158 行 `print(...)` 的 `UnicodeEncodeError`。
7. **修好第一層後，使用者驗證時又撞見第二層**：套用 `ensure_utf8_console()` 修法後，使用者重新執行 `repro_gap2.py`，改成拋出 `UnicodeDecodeError`（發生在 `subprocess.py` 內部 `_readerthread` 讀取子行程輸出的地方）。經分析確認是前述「讀」的那一端沒有指定 `encoding=` 所致，修正 `subprocess.run()` 呼叫加上 `encoding="utf-8", errors="replace"` 後，最終確認完全解決。

---

## 3. 分析過程中用到的關鍵判斷依據

- **「stdout 是空字串」比「stdout 內容錯誤」更嚴重**：空字串代表程式**提前中止**，而不是邏輯輸出結果不對，這把懷疑方向從「演算法/斷句邏輯」轉向「程式執行過程本身出了狀況」。
- **同一支程式，直接執行正常、被 subprocess 捕捉才會崩潰**：這個「行為隨呼叫方式而不同」的現象，是判斷這是 Windows stdout 編碼解析路徑問題（而不是單純的資料或邏輯 bug）的最強訊號。
- **沙盒環境本身測不出這個問題**：沙盒（Linux）的系統 locale 就是 UTF-8，`locale.getpreferredencoding()` 恆為 `utf-8`，不會觸發 `cp1252` 分支；因此這個 bug 只能靠使用者在真實 Windows 機器上重現與驗證，沙盒這邊「全部測試通過」並不能代表這個問題不存在——這也是為什麼整個診斷過程需要使用者多輪配合在自己機器上執行重現腳本。
- **逐步縮小重現條件**（直接執行 → 直接呼叫合成資料 → 用 subprocess 捕捉合成資料）是能夠精準定位問題的關鍵方法，而不是一開始就假設是某個特定改動造成的。

---

## 4. 如何解決

### 4.1 核心修法：`ensure_utf8_console()`

在 `src/logging_config.py` 新增一個共用函式：

```python
def ensure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower().replace("-", "") == "utf8":
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass
```

設計重點：

- 已經是 UTF-8 的串流直接略過，不重複設定。
- 不支援 `.reconfigure()`（較舊版 Python，或非標準串流物件）時安全跳過，不強求。
- `.reconfigure()` 本身失敗（`ValueError`/`OSError`，例如串流已關閉/detached）時吞掉例外，不讓這個防禦性小工具反而變成新的崩潰點。
- `errors="replace"`：即使真的遇到無法編碼的字元，也是印出替代字元，不是整個程式崩潰。

**佈線位置**：

- `setup_logging()`（`src/main.py` 主流程會呼叫）在建立 console handler **之前**呼叫，確保正式 CLI 主流程一定會套用到。
- 另外 10 支不一定會經過 `setup_logging()` 的獨立腳本，各自在 `main()` 一開始呼叫：`check_narration_gaps.py`、`calibrate_scale.py`、`dump_slide_bounds.py`、`regenerate_srt_from_export.py`、`smoke_test_alignment.py`、`smoke_test_word_boundaries.py`、`split_video_by_slides.py`、`verify_slide_timing.py`、`verify_srt_accuracy.py`、`verify_tts_alignment.py`。

### 4.2 第二層修法：讓 subprocess 呼叫端的解碼跟子行程的編碼一致

在會用 `subprocess.run(capture_output=True, text=True)` 捕捉這些腳本輸出的地方，明確加上 `encoding="utf-8", errors="replace"`：

- `tests/test_check_narration_gaps.py` 的 `_run()` helper
- `tests/test_calibrate_scale.py` 呼叫 `calibrate_scale.py` 的那次 `subprocess.run()`（防禦性加上，目前該腳本輸出雖是純 ASCII，但保持一致、避免未來加入中文輸出時重蹈覆轍）
- 使用者本機的 `repro_gap2.py` 重現腳本

### 4.3 測試覆蓋

新增 `tests/test_logging_config.py::EnsureUtf8ConsoleTests`，用假的串流物件（`FakeStream`，可指定任意 `encoding` 與是否支援 `.reconfigure()`）模擬各種情境，因為沙盒環境本身沒有 `cp1252` 系統可以真實觸發：

- 非 UTF-8 串流會被正確呼叫 `.reconfigure(encoding="utf-8", errors="replace")`
- 已是 UTF-8（含大小寫、有無連字號的寫法差異，如 `UTF-8`）的串流會被略過，不重複設定
- 不支援 `.reconfigure()` 的串流不會拋出 `AttributeError`
- `.reconfigure()` 拋出 `ValueError`/`OSError` 時會被安全吞掉，且不影響另一個串流繼續被處理
- `sys.stdout`/`sys.stderr` 為 `None` 時不會崩潰
- 對真實的 `io.StringIO()` 物件（沒有 `.reconfigure()`）呼叫，確認不會崩潰

全部 174 個測試（原有 167 個 + 新增 7 個）通過。

---

## 5. 之前為什麼都沒有發現

三個條件平常很少同時成立，是這個 bug 能潛伏這麼久的主因：

1. **這條程式碼路徑本身很少被真正執行到。** 疑似漏講偵測是 v0.7.0 才加的新功能，設計成「大部分時候應該印不出東西」——只有真的偵測到疑似漏講才會走到那行 `print()`。使用者對真實資料執行時（0 個 suspected drops），完全不會觸發這行程式碼；只有測試套件裡刻意構造「一定要偵測到漏講」的合成資料才會踩到。
2. **互動式終端機會掩蓋問題。** 同一支程式，直接在 PowerShell 裡執行完全正常——因為互動式主控台跟被程式捕捉的管線，Windows 底層走的是兩條不同的編碼解析路徑。只有當輸出真的被 `subprocess.run(capture_output=True)` 這種方式捕捉時（測試套件內部就是這樣呼叫的），問題才會現形。
3. **沙盒環境本身測不出來。** 這邊的 Linux 沙盒系統 locale 就是 UTF-8，`locale.getpreferredencoding()` 永遠回傳 `utf-8`，同一段程式碼在這裡執行、跑測試完全不會觸發 `cp1252` 分支，因此光靠「沙盒這邊測試全過」無法發現這類問題，只能在使用者實際的 Windows 機器上才驗證得出來。

換句話說：這是一個需要「特定作業系統 + 特定輸出目的地（管線而非互動終端機）+ 特定資料（真的偵測到問題）」三個條件同時成立才會顯現的 bug，直到這次因為另一個不相關的改動而重新完整跑了一次測試套件，才意外撞見。

---

## 6. 後續已一併處理的事項

- 新增選用的開發相依套件 `requirements-dev.txt`（`pytest`）與 `pyproject.toml` 的 `[project.optional-dependencies] dev`，方便之後如果需要更精簡的測試輸出或 `-k` 篩選功能時直接安裝，不裝完全不影響現有 `python -m unittest discover -s tests -v` 的執行方式。
- `CHANGELOG.md` 的 `[未發布]` 區段已記錄本次的 `### Fixed`（含根因說明）與 `### Added`（pytest 選用相依套件）。

## 7. 給未來的提醒

> ⚠️ 任何會印出中文（或其他非 ASCII）文字、且輸出可能被管線／檔案捕捉的程式碼，都應該假設執行環境的 stdout/stderr 編碼**不保證是 UTF-8**，尤其是在 Windows 上。新增會印文字的程式碼路徑時，優先透過已經呼叫過 `ensure_utf8_console()` 的進入點（`setup_logging()` 或各腳本 `main()` 開頭），不要另外開新的、沒有做這件事的輸出路徑。

> ⚠️ 任何新增的 `subprocess.run(capture_output=True, text=True)` 呼叫，只要目標程式可能輸出非 ASCII 文字，都應該明確指定 `encoding="utf-8", errors="replace"`，不要依賴 `text=True` 的預設行為（該預設一樣會退回呼叫端系統的 `locale.getpreferredencoding()`）。
