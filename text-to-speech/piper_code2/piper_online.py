import argparse
import sys

import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# HTTP 服务地址（piper.http_server 的合成接口是 POST /，不是 /speak）
url = "http://127.0.0.1:5000/"


def main() -> None:
    p = argparse.ArgumentParser(description="向本机 Piper HTTP 发请求并保存 output.wav")
    p.add_argument(
        "text",
        nargs="?",
        help="要朗读的文字；省略则从标准输入读取（适合管道或重定向）",
    )
    args = p.parse_args()
    if args.text is not None:
        text = args.text.strip()
    else:
        text = sys.stdin.read().strip()
    if not text:
        print(
            "错误：未提供文字。示例：python piper_online.py \"Hello world\"",
            file=sys.stderr,
        )
        raise SystemExit(1)

    data = {
        "text": text,
        "voice": "en_US-lessac-medium",
    }

    response = requests.post(url, json=data)

    if response.status_code != 200:
        print("出错了:", response.status_code)
        print(response.text)
        raise SystemExit(1)

    out_wav = SCRIPT_DIR / "output.wav"
    with open(out_wav, "wb") as f:
        f.write(response.content)

    print(f"生成完成：{out_wav}")


if __name__ == "__main__":
    main()
