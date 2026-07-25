# Future Enhancements

以下項目是目前已完成或下一步優先加入的項目。

## 已完成
- 解析 `.pptx` 的投影片編號、標題與 notes
- 支援多頁簡報、長段落、空白行與無 notes 頁面
- 輸出字幕流程可使用的 JSON 結構，包含 `subtitle_text`、`has_notes`、`audio_file`
- 支援使用 edge-tts 生成 MP3，並依頁碼命名為 `slide_001.mp3`、`slide_002.mp3`
- 提供 CLI 參數：`--output`、`--pretty`、`--verbose`、`--strict`、`--generate-audio`、`--audio-output-dir`、`--voice`、`--rate`、`--pitch`
- 提供範例簡報生成與測試腳本

## 下一步優先項目

### 1. 產生 SRT 字幕
- 根據 notes 與音訊長度生成字幕檔
- 支援每頁一段或分段字幕

### 2. PowerPoint 匯出 MP4
- 透過 Windows COM 控制 PowerPoint
- 將投影片、音訊與字幕整合成影片

### 3. 批次處理多個 .pptx
- 支援一次處理多個簡報檔
- 輸出多份 JSON / 音訊 / 字幕結果
