# PPTX Auto Presenter (`pptx2video`)

一個基於 Python 的自動化工具，目標是自動解析 PowerPoint 簡報檔（`.pptx`）的頁數與備忘稿內容，並透過 **Edge-TTS** 生成語音，後續再朝向 PowerPoint 匯出帶配音的 MP4 影片與 SRT 字幕的流程前進。

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
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
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

### 7. 生成語音（TTS）

```powershell
python -m pptx2video examples/sample_test.pptx --generate-audio --audio-output-dir output/audio --voice "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)" --rate "-10%%" --pitch "+0Hz"
```

這會把有 notes 的投影片轉成 MP3，並建立對應的音訊 manifest。

### 8. CLI 進階選項

```powershell
python src/main.py examples/sample_test.pptx --verbose --pretty
python src/main.py examples/sample_test.pptx --strict
```

- `--verbose`：輸出更詳細的執行訊息
- `--strict`：若某頁沒有 notes，直接中止執行
- `--generate-audio`：將 notes 轉成 MP3
- `--audio-output-dir`：指定 MP3 輸出目錄
- `--voice`：指定 edge-tts 的聲音
- `--rate`：指定語速
- `--pitch`：指定音高

---

## 📁 專案結構

```text
pptx2video/
├── src/                # 主要程式碼
│   ├── main.py         # CLI 入口與 JSON 輸出
│   ├── pptx_parser.py  # 解析 .pptx 與 notes
│   ├── tts.py          # edge-tts 音訊生成
│   └── __init__.py
├── tests/              # 測試檔案
│   ├── test_pptx_parser.py
│   ├── test_tts_generator.py
│   └── test_main_payload.py
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
* **支援沒有 notes 的頁面**：封面頁與結束頁也能正常處理，並自動跳過生成音訊。
* **輸出 JSON**：可將解析結果輸出為結構化 JSON，並提供 `subtitle_text`、`has_notes`、`audio_file` 等字幕流程所需欄位。
* **語音生成**：已接入 `edge-tts`，可將 notes 轉成 MP3，並依頁碼命名。
* **提供 CLI 介面**：支援 `--output`、`--pretty`、`--verbose`、`--strict`、`--generate-audio`、`--audio-output-dir`、`--voice`、`--rate`、`--pitch` 等選項。
* **提供範例與測試**：內建範例簡報生成腳本與單元測試。

## 🚧 後續發展方向

* **字幕生成**：根據音訊與 notes 內容輸出 `.srt` 字幕。
* **PowerPoint 匯出**：透過 Windows COM 控制 PowerPoint 匯出 MP4。
* **批次處理與輸出整理**：支援多檔輸入與更完整的輸出目錄管理。

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

## Current Status

### Completed
- PPTX Parser
- Notes Extraction
- Edge-TTS Audio Generation
- Audio Manifest
- CLI
- Subtitle Generator (Experimental / PoC)

### In Progress
- PowerPoint Automation (Insert Audio / Auto Play / Transition Timing)

### Planned
- Export MP4 using Microsoft PowerPoint

### Experimental Features
The current Subtitle Generator is a Proof of Concept (PoC). It is retained for architecture validation and is not yet part of the official video generation pipeline.
