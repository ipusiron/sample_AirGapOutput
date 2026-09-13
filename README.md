# エアギャップ・ブリッジ ― サンプルコード

技術同人誌『エアギャップ・ブリッジ 隔離環境のデータ出力技法』で使用するサンプルコードです。

## 収録スクリプト

### screen_ocr_monitor.py（第8章）

OBS Studioの仮想カメラから映像を取得し、画面に変化があったときだけOCRを実行してテキストを保存する差分検知OCRスクリプトです。

#### 前提条件

- Python 3.8以上
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)（Windows向けインストーラー）
- 日本語OCRを使う場合はTesseractの日本語言語パック（`jpn.traineddata`）

#### インストール

```bash
pip install opencv-python pytesseract
```

#### 使い方

```bash
# OBS Studioで「仮想カメラ開始」を押してから実行する
python screen_ocr_monitor.py --device 2 --interval 5 --lang jpn+eng
```

#### オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--device` | カメラデバイス番号 | 0 |
| `--interval` | チェック間隔（秒） | 5 |
| `--threshold` | 差分閾値（%） | 3.0 |
| `--lang` | Tesseract言語 | eng |
| `--width` | キャプチャー幅 | 1920 |
| `--height` | キャプチャー高さ | 1080 |
| `--outdir` | 出力先ディレクトリー | ./ocr_logs |

#### Tesseract日本語言語パックの追加

```powershell
# jpn.traineddataをダウンロード後、管理者権限のPowerShellで実行
Copy-Item jpn.traineddata "C:\Program Files\Tesseract-OCR\tessdata\"
```

インストール済みの言語を確認するには：

```bash
tesseract --list-langs
```

### com.user.caffeinate.plist（第8章）

macOSのcaffeinateコマンドをログイン時に自動起動するためのlaunchd設定ファイルです。
HDMIキャプチャーによる常時監視環境で、Mac Miniのスリープを恒久的に抑制します。

#### 使い方

```bash
# ~/Library/LaunchAgents/ にコピーして登録
cp com.user.caffeinate.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.caffeinate.plist

# 解除する場合
launchctl unload ~/Library/LaunchAgents/com.user.caffeinate.plist
```

### screen_vlm_monitor.py（第9章）

OBS Studioの仮想カメラから映像を取得し、画面に変化があったときだけローカルVLM（Ollama経由）で画面内容を解析してテキストを保存するスクリプトです。

#### 前提条件

- Python 3.8以上
- [Ollama](https://ollama.com/)（ローカルLLM/VLM実行エンジン）
- Qwen3-VLモデル（`ollama pull qwen3-vl` でダウンロード）
- NVIDIA GPU（VRAM 8GB以上推奨）

#### インストール

```bash
pip install opencv-python requests
```

#### 使い方

```bash
# Ollamaが起動していることを確認し、OBS Studioで「仮想カメラ開始」を押してから実行する
python screen_vlm_monitor.py --device 2 --interval 15 --outdir ./vlm_logs
```

#### オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--device` | カメラデバイス番号 | 0 |
| `--interval` | チェック間隔（秒） | 10 |
| `--threshold` | 差分閾値（%） | 3.0 |
| `--model` | Ollamaのモデル名 | qwen3-vl |
| `--prompt` | VLMに送るプロンプト | （日本語での画面説明を指示） |
| `--width` | キャプチャー幅 | 1920 |
| `--height` | キャプチャー高さ | 1080 |
| `--outdir` | 出力先ディレクトリー | ./vlm_logs |
| `--ollama-url` | Ollama APIのURL | http://localhost:11434 |

## 書籍情報

- 書名: エアギャップ・ブリッジ 隔離環境のデータ出力技法
- 著者: IPUSIRON
- FAQ・正誤表: [Security Akademeia](https://akademeia.info/)

## ライセンス

MIT License
