# PPTX Auto Presenter (`pptx2video`)

一個基於 Python 的自動化工具，能自動解析 PowerPoint 簡報檔（`.pptx`）的頁數與備忘稿內容，透過 **Edge-TTS** 生成高質感神經網路語音，並自動回填至 PowerPoint 匯出帶配音的 MP4 影片與精確的 SRT 字幕檔。

---

## 🚀 快速開始（Windows）

以下步驟適合在 Windows PowerShell 中從 GitHub 下載這個專案後直接開始使用。

### 1. 下載專案

```powershell
git clone https://github.com/<your-username>/pptx2video.git
cd pptx2video
```

### 2. 建立虛擬環境

```powershell
py -3 -m venv .venv
```

### 3. 啟動虛擬環境

```powershell
.\.venv\Scripts\Activate.ps1
```

若 PowerShell 擋下執行腳本，可先執行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. 安裝依賴套件

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 生成範例簡報（可選）

```powershell
python examples/create_sample_pptx.py
```

### 6. 執行解析流程

```powershell
python src/main.py examples/sample_test.pptx --output output/slides.json
```

或使用更像套件的方式：

```powershell
python -m pptx2video examples/sample_test.pptx --output output/slides.json
```

這會讀取簡報檔，解析每頁的標題與 notes，並輸出 JSON 到 [output/slides.json](output/slides.json)。

### 7. CLI 進階選項

```powershell
python src/main.py examples/sample_test.pptx --verbose --pretty
python src/main.py examples/sample_test.pptx --strict
```

- `--verbose`：輸出更詳細的執行訊息
- `--strict`：若某頁沒有 notes，直接中止執行

---

## 📁 專案結構

```text
pptx2video/
├── src/                # 主要程式碼
│   ├── main.py         # CLI 入口
│   ├── pptx_parser.py  # 解析 .pptx 與 notes
│   └── __init__.py
├── tests/              # 測試檔案
├── examples/           # 範例腳本與範例簡報
├── output/             # 輸出檔案
├── temp/               # 暫存資料夾
├── requirements.txt    # Python 相依套件
├── pyproject.toml      # 專案設定
└── README.md           # 專案說明
```

---

## 🧪 執行測試

```powershell
python -m unittest discover -s tests -v
```

---

## ✅ 目前已完成的功能

* **解析 `.pptx` 投影片內容**：可讀取投影片編號、標題與 notes。
* **支援長篇備忘稿**：可處理多段落、換行與空白行。
* **支援沒有 notes 的頁面**：封面頁與結束頁也能正常處理。
* **輸出 JSON**：可將解析結果輸出為結構化 JSON 檔。
* **提供 CLI 介面**：支援 `--output`、`--pretty`、`--verbose`、`--strict` 等選項。
* **提供範例與測試**：內建範例簡報生成腳本與單元測試。

## 🚧 後續發展方向

* **語音生成**：整合 `edge-tts`，將 notes 轉成音訊檔。
* **PowerPoint 匯出**：透過 Windows COM 控制 PowerPoint 匯出 MP4。
* **字幕生成**：根據語音時長輸出 `.srt` 字幕。

---

## 🧰 需求與環境

- Python 3.9 或以上
- Windows 作業系統
- 已安裝 Microsoft PowerPoint（因為本專案使用 Windows COM 自動化控制 PowerPoint）
- 可連線到 Edge-TTS 服務

## 🏗️ 系統架構與資料流

```mermaid
graph TD
    A[輸入 .pptx 簡報檔] --> B[pptx_parser.py<br>提取頁數與備忘稿]
    B --> C[tts_engine.py<br>呼叫 Edge-TTS 生成音檔]
    C --> D[(暫存檔 temp_audios/)]
    
    D --> E[ppt_automation.py<br>win32com 控制 PowerPoint]
    D --> F[subtitle_generator.py<br>計算時間戳]
    
    E --> G[輸出 output.mp4]
    F --> H[輸出 output.srt]