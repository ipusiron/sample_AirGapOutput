# エアギャップ・ブリッジ ― サンプルコード

技術同人誌『エアギャップ・ブリッジ 隔離環境のデータ出力技法』で使用するサンプルコードです。

## 収録スクリプト

### screen_ocr_monitor.py（第7章）

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

## 書籍情報

- 書名: エアギャップ・ブリッジ 隔離環境のデータ出力技法
- 著者: IPUSIRON
- FAQ・正誤表: [Security Akademeia](https://akademeia.info/)

## ライセンス

MIT License
