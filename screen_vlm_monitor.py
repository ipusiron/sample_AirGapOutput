#!/usr/bin/env python3
"""screen_vlm_monitor.py - エアギャップ画面のVLM解析スクリプト

OBS Studioの仮想カメラ（または任意のUSBカメラ）から映像を取得し、
画面に変化があったときだけローカルVLM（Ollama経由）で画面内容を解析する。

使い方:
    python screen_vlm_monitor.py                    # デフォルト設定で起動
    python screen_vlm_monitor.py --list-devices      # 利用可能なデバイス番号を一覧表示
    python screen_vlm_monitor.py --device 1          # カメラデバイス番号を指定
    python screen_vlm_monitor.py --interval 10       # 10秒間隔でチェック
    python screen_vlm_monitor.py --threshold 5.0     # 差分閾値を変更
    python screen_vlm_monitor.py --model qwen3-vl    # 使用するVLMモデルを指定
    python screen_vlm_monitor.py --prompt "..."      # VLMへのプロンプトを変更
    python screen_vlm_monitor.py --outdir ./vlm_logs # 出力先ディレクトリーを指定

前提条件:
    pip install opencv-python requests
    Ollamaがインストール済みで、VLMモデルがpull済みであること
    （例: ollama pull qwen3-vl）
"""

import argparse
import base64
import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests


MAX_DEVICE_INDEX = 9

DEFAULT_PROMPT = (
    "この画面のスクリーンショットに表示されている内容を日本語で説明してください。"
    "テキスト、エラーメッセージ、GUIの状態など、重要な情報を簡潔にまとめてください。"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="画面の差分検知VLM解析スクリプト"
    )
    parser.add_argument(
        "--device", type=int, default=0,
        help="カメラデバイス番号（デフォルト: 0）"
    )
    parser.add_argument(
        "--list-devices", action="store_true",
        help="利用可能なデバイス番号を一覧表示して終了する"
    )
    parser.add_argument(
        "--interval", type=int, default=10,
        help="チェック間隔（秒、デフォルト: 10）"
    )
    parser.add_argument(
        "--threshold", type=float, default=3.0,
        help="差分閾値（%%、デフォルト: 3.0）。この値を超えたらVLM解析を実行"
    )
    parser.add_argument(
        "--model", type=str, default="qwen3-vl",
        help="Ollamaのモデル名（デフォルト: qwen3-vl）"
    )
    parser.add_argument(
        "--prompt", type=str, default=DEFAULT_PROMPT,
        help="VLMに送るプロンプト"
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
        "--outdir", type=str, default="./vlm_logs",
        help="解析結果の出力先ディレクトリー（デフォルト: ./vlm_logs）"
    )
    parser.add_argument(
        "--ollama-url", type=str, default="http://localhost:11434",
        help="Ollama APIのURL（デフォルト: http://localhost:11434）"
    )
    return parser.parse_args()


def list_devices(outdir):
    """利用可能なカメラデバイス番号を探索して一覧表示する。"""
    print(f"カメラデバイスを探索します（0〜{MAX_DEVICE_INDEX}）。")
    available = []
    for index in range(MAX_DEVICE_INDEX + 1):
        cap = cv2.VideoCapture(index)
        ok, frame = cap.read() if cap.isOpened() else (False, None)
        backend = cap.getBackendName() if ok else ""
        cap.release()
        if not ok:
            continue  # 開けない、またはフレームを取得できないデバイス
        height, width = frame.shape[:2]
        preview = outdir / f"device_{index}.png"
        cv2.imwrite(str(preview), frame)
        print(f"  [{index}] {width}x{height} ({backend}) -> {preview}")
        available.append(index)
    print()
    if not available:
        print("利用可能なカメラデバイスが見つかりません。")
        print("OBS Studioで「仮想カメラ開始」を押したか確認してください。")
        return
    numbers = ", ".join(str(i) for i in available)
    print(f"利用可能なデバイス番号: {numbers}")
    print("プレビュー画像を確認し、目的の画面が写っている番号を")
    print("--device オプションに指定してください。")


def compute_diff_percent(frame1, frame2):
    """2フレーム間のピクセル差分を百分率で返す。"""
    if frame1 is None or frame2 is None:
        return 100.0
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = np.count_nonzero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    return (changed_pixels / total_pixels) * 100


def frame_to_base64(frame):
    """OpenCVフレームをBase64エンコードされたPNG文字列に変換する。"""
    _, buffer = cv2.imencode(".png", frame)
    return base64.b64encode(buffer).decode("utf-8")


def query_vlm(ollama_url, model, prompt, frame, max_size=1024):
    """Ollama APIにフレーム画像を送り、VLMの解析結果を返す。"""
    # VRAM節約のため、長辺をmax_sizeにリサイズしてから送信する
    h, w = frame.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    image_b64 = frame_to_base64(frame)
    payload = {
        "model": model,
        "prompt": prompt + " /no_think",
        "images": [image_b64],
        "stream": False,
        "options": {
            "num_predict": 2048,
        },
    }
    url = f"{ollama_url}/api/generate"
    resp = requests.post(url, json=payload, timeout=300)
    resp.raise_for_status()
    result = resp.json()
    return result.get("response", ""), result.get("eval_duration", 0)


def save_result(outdir, timestamp, text, frame):
    """VLM解析結果をテキストファイルとスクリーンショットとして保存する。"""
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    text_path = outdir / f"{time_str}.txt"
    image_path = outdir / f"{time_str}.png"

    text_path.write_text(text, encoding="utf-8")
    cv2.imwrite(str(image_path), frame)

    return text_path, image_path


def check_ollama(ollama_url, model):
    """Ollamaの接続とモデルの存在を確認する。"""
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        # "qwen3-vl" が "qwen3-vl:latest" にマッチするよう部分一致で確認
        if not any(model in m for m in models):
            print(f"エラー: モデル '{model}' が見つかりません。", file=sys.stderr)
            print(f"利用可能なモデル: {', '.join(models)}", file=sys.stderr)
            print(f"'ollama pull {model}' でモデルをダウンロードしてください。",
                  file=sys.stderr)
            sys.exit(1)
        return True
    except requests.ConnectionError:
        print("エラー: Ollamaに接続できません。", file=sys.stderr)
        print("Ollamaが起動しているか確認してください。", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.list_devices:
        list_devices(outdir)
        return

    # Ollamaとモデルの確認
    check_ollama(args.ollama_url, args.model)

    print(f"モデル: {args.model}")
    print(f"カメラデバイス: {args.device}")
    print(f"チェック間隔: {args.interval}秒")
    print(f"差分閾値: {args.threshold}%")
    print(f"出力先: {outdir.resolve()}")
    print()

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        print(f"エラー: カメラデバイス {args.device} を開けません。", file=sys.stderr)
        print("--list-devices オプションでデバイス番号を確認してください。", file=sys.stderr)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"キャプチャー解像度: {width}x{height}")
    print("Ctrl+C で終了します。")
    print("-" * 60)

    prev_frame = None
    vlm_count = 0

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
                vlm_count += 1
                print(f"[{time_str}] 差分 {diff:.1f}% → VLM解析中...",
                      end="", flush=True)

                start = time.time()
                text, eval_ns = query_vlm(
                    args.ollama_url, args.model, args.prompt, frame
                )
                elapsed = time.time() - start

                text_path, _ = save_result(outdir, now, text, frame)

                chars = len(text)
                print(f" {chars}文字 ({elapsed:.1f}秒) → {text_path.name}")
            else:
                print(f"[{time_str}] 差分 {diff:.1f}% → スキップ")

            prev_frame = frame.copy()
            time.sleep(args.interval)

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        cap.release()
        print()
        print(f"終了しました。VLM解析回数: {vlm_count}")


if __name__ == "__main__":
    main()
