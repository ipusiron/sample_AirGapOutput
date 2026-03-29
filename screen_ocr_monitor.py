#!/usr/bin/env python3
"""screen_ocr_monitor.py - エアギャップ画面の差分検知OCRスクリプト

OBS Studioの仮想カメラ（または任意のUSBカメラ）から映像を取得し、
画面に変化があったときだけOCRを実行してテキストを保存する。

使い方:
    python screen_ocr_monitor.py                    # デフォルト設定で起動
    python screen_ocr_monitor.py --device 1          # カメラデバイス番号を指定
    python screen_ocr_monitor.py --interval 10       # 10秒間隔でチェック
    python screen_ocr_monitor.py --threshold 5.0     # 差分閾値を変更
    python screen_ocr_monitor.py --lang jpn+eng      # 日本語+英語でOCR
    python screen_ocr_monitor.py --outdir ./ocr_logs # 出力先ディレクトリーを指定

前提条件:
    pip install opencv-python pytesseract
    Tesseract OCRがインストール済みであること
    日本語OCRを使う場合はjpn.traineddataが必要
"""

import argparse
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract


def parse_args():
    parser = argparse.ArgumentParser(
        description="画面の差分検知OCRスクリプト"
    )
    parser.add_argument(
        "--device", type=int, default=0,
        help="カメラデバイス番号（デフォルト: 0）"
    )
    parser.add_argument(
        "--interval", type=int, default=5,
        help="チェック間隔（秒、デフォルト: 5）"
    )
    parser.add_argument(
        "--threshold", type=float, default=3.0,
        help="差分閾値（%%、デフォルト: 3.0）。この値を超えたらOCRを実行"
    )
    parser.add_argument(
        "--lang", type=str, default="eng",
        help="Tesseract言語（デフォルト: eng）。例: jpn+eng"
    )
    parser.add_argument(
        "--width", type=int, default=1920,
        help="キャプチャー幅（デフォルト: 1920）"
    )
    parser.add_argument(
        "--height", type=int, default=1080,
        help="キャプチャー高さ（デフォルト: 1080）"
    )
    parser.add_argument(
        "--outdir", type=str, default="./ocr_logs",
        help="OCR結果の出力先ディレクトリー（デフォルト: ./ocr_logs）"
    )
    return parser.parse_args()


def compute_diff_percent(frame1, frame2):
    """2フレーム間のピクセル差分を百分率で返す。"""
    if frame1 is None or frame2 is None:
        return 100.0
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray1, gray2)
    # 閾値30以上の変化があるピクセルをカウント
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = np.count_nonzero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    return (changed_pixels / total_pixels) * 100


def run_ocr(frame, lang):
    """フレームに対してOCRを実行し、テキストを返す。"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray, lang=lang)
    return text.strip()


def save_result(outdir, timestamp, text, frame):
    """OCR結果をテキストファイルとスクリーンショットとして保存する。"""
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    text_path = outdir / f"{time_str}.txt"
    image_path = outdir / f"{time_str}.png"

    text_path.write_text(text, encoding="utf-8")
    cv2.imwrite(str(image_path), frame)

    return text_path, image_path


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"カメラデバイス: {args.device}")
    print(f"チェック間隔: {args.interval}秒")
    print(f"差分閾値: {args.threshold}%")
    print(f"OCR言語: {args.lang}")
    print(f"出力先: {outdir.resolve()}")
    print()

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        print(f"エラー: カメラデバイス {args.device} を開けません。", file=sys.stderr)
        print("--device オプションでデバイス番号を変更してください。", file=sys.stderr)
        sys.exit(1)

    # 解像度を1920x1080に設定（仮想カメラのデフォルトが640x480のため）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    # 実際に設定された解像度を表示
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"キャプチャー解像度: {width}x{height}")
    print("Ctrl+C で終了します。")
    print("-" * 60)

    prev_frame = None
    ocr_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("フレーム取得に失敗しました。リトライします...", file=sys.stderr)
                time.sleep(1)
                continue

            diff = compute_diff_percent(prev_frame, frame)
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")

            if diff >= args.threshold:
                ocr_count += 1
                print(f"[{time_str}] 差分 {diff:.1f}% → OCR実行中...", end="", flush=True)

                text = run_ocr(frame, args.lang)
                text_path, image_path = save_result(outdir, now, text, frame)

                lines = len(text.splitlines())
                chars = len(text)
                print(f" {chars}文字/{lines}行 → {text_path.name}")
            else:
                print(f"[{time_str}] 差分 {diff:.1f}% → スキップ")

            prev_frame = frame.copy()
            time.sleep(args.interval)

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        cap.release()
        print()
        print(f"終了しました。OCR実行回数: {ocr_count}")


if __name__ == "__main__":
    main()
