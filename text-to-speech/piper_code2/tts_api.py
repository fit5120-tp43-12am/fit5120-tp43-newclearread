"""
业务层 TTS API：把前端/其他服务的 JSON 转发给 Piper HTTP 服务，原样返回 WAV。

先在本机启动 Piper（默认 5000 端口），例如：
  python -m piper.http_server -m .\\models\\en_US-lessac-medium.onnx

再启动本服务（默认 8080，避免与 Piper 端口冲突）：
  set PIPER_SYNTH_URL=http://127.0.0.1:5000/
  python tts_api.py

浏览器打开 http://127.0.0.1:8080/ 可粘贴文字并播放（与 API 同源，无跨域问题）。

合成慢主要是 Piper 在算语音（尤其 CPU）；加快：Piper 加 --cuda、换更小模型、缩短文本。见 static/index.html 页内说明。

环境变量：
  PIPER_SYNTH_URL  Piper 合成地址，须以 / 结尾或指向根路径 POST /
  TTS_API_HOST     本服务监听地址，默认 0.0.0.0
  TTS_API_PORT     本服务端口，默认 8080
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, request, send_from_directory

app = Flask(__name__)
SCRIPT_DIR = Path(__file__).resolve().parent
# 复用连接，略减每次转发到 Piper 的 TCP/HTTP 握手开销（合成本身仍是大头）
_HTTP_SESSION = requests.Session()


def _piper_base_url() -> str:
    u = os.environ.get("PIPER_SYNTH_URL", "http://127.0.0.1:5000").rstrip("/") + "/"
    return u


def _cors(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = os.environ.get("CORS_ORIGIN", "*")
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.after_request
def _after(resp: Response) -> Response:
    return _cors(resp)


def _decode_body_bytes(raw_bytes: bytes) -> str:
    if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
        return raw_bytes.decode("utf-16", errors="replace")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return raw_bytes.decode("utf-8-sig", errors="replace")
    charset = getattr(request, "charset", None)
    for enc in (charset, "utf-8-sig", "utf-8", "latin-1"):
        if not enc:
            continue
        try:
            return raw_bytes.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _json_payload() -> tuple[dict[str, Any], bytes]:
    """返回 (解析出的 dict, 原始 body 字节)，供错误时诊断。"""
    raw_bytes = request.get_data(cache=True)
    if not raw_bytes:
        if request.form:
            return {k: request.form.get(k) for k in request.form}, raw_bytes
        return {}, raw_bytes

    text = _decode_body_bytes(raw_bytes).strip().lstrip("\ufeff")
    # 整段被多包了一层引号时（复制粘贴 / 某些 shell），去掉后再解析
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1].strip()
    try:
        body = json.loads(text)
        if isinstance(body, dict):
            return body, raw_bytes
    except json.JSONDecodeError:
        pass
    if request.form:
        return {k: request.form.get(k) for k in request.form}, raw_bytes
    return {}, raw_bytes


def _as_text_field(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _build_piper_body(
    body: dict[str, Any], raw_bytes: bytes
) -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
    text = _as_text_field(body.get("text"))
    if not text:
        hint = (
            "未解析到 text：请发 JSON 且包含非空字段 text；"
            "PowerShell 推荐："
            '$body = ''{"text":"Hello","voice":"en_US-lessac-medium"}''; '
            "Invoke-WebRequest ... -Body $body"
        )
        err_obj: dict[str, Any] = {
            "error": "text 为必填字段且不能为空",
            "hint": hint,
            "received_bytes": len(raw_bytes),
        }
        if raw_bytes:
            prev = raw_bytes[:160]
            try:
                err_obj["body_preview"] = prev.decode("utf-8", errors="replace")
            except Exception:
                err_obj["body_preview_repr"] = repr(prev)
        return None, (
            Response(
                json.dumps(err_obj, ensure_ascii=False),
                status=400,
                mimetype="application/json; charset=utf-8",
            ),
            400,
        )

    piper_body: dict[str, Any] = {"text": text}

    voice = body.get("voice")
    if voice:
        piper_body["voice"] = voice

    if "length_scale" in body and body["length_scale"] is not None:
        piper_body["length_scale"] = body["length_scale"]
    if "noise_scale" in body and body["noise_scale"] is not None:
        piper_body["noise_scale"] = body["noise_scale"]
    if "noise_w_scale" in body and body["noise_w_scale"] is not None:
        piper_body["noise_w_scale"] = body["noise_w_scale"]

    if "speaker" in body and body["speaker"] is not None:
        piper_body["speaker"] = body["speaker"]
    if "speaker_id" in body and body["speaker_id"] is not None:
        piper_body["speaker_id"] = body["speaker_id"]

    return piper_body, None


def _forward_to_piper(piper_body: dict[str, Any]) -> Response:
    url = _piper_base_url()
    try:
        r = _HTTP_SESSION.post(
            url, json=piper_body, timeout=int(os.environ.get("PIPER_TIMEOUT_SEC", "300"))
        )
    except requests.RequestException as e:
        err_json = json.dumps({"error": "无法连接 Piper", "detail": str(e)}, ensure_ascii=False)
        return Response(err_json, status=502, mimetype="application/json; charset=utf-8")

    if r.status_code != 200:
        ct = r.headers.get("Content-Type", "text/plain")
        return Response(r.content, status=r.status_code, mimetype=ct)

    return Response(
        r.content,
        status=200,
        mimetype="audio/wav",
        headers={"Content-Disposition": 'inline; filename="tts.wav"'},
    )


def _handle_tts_route() -> Response:
    body, raw_bytes = _json_payload()
    piper_body, err = _build_piper_body(body, raw_bytes)
    if err is not None:
        return err[0]
    assert piper_body is not None
    return _forward_to_piper(piper_body)


@app.route("/tts/full-text", methods=["POST", "OPTIONS"])
def tts_full_text():
    if request.method == "OPTIONS":
        return Response(status=204)
    return _handle_tts_route()


@app.route("/tts/summary", methods=["POST", "OPTIONS"])
def tts_summary():
    if request.method == "OPTIONS":
        return Response(status=204)
    return _handle_tts_route()


@app.route("/tts/section", methods=["POST", "OPTIONS"])
def tts_section():
    if request.method == "OPTIONS":
        return Response(status=204)
    return _handle_tts_route()


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "piper_url": _piper_base_url()}


@app.route("/", methods=["GET"])
def tts_page():
    """简单网页：粘贴文字、调用同源 TTS 接口并播放 WAV。"""
    return send_from_directory(SCRIPT_DIR / "static", "index.html")


if __name__ == "__main__":
    host = os.environ.get("TTS_API_HOST", "0.0.0.0")
    port = int(os.environ.get("TTS_API_PORT", "8080"))
    print(f"TTS API 监听 http://{host}:{port}  ->  Piper {_piper_base_url()}")
    print(f"网页界面：http://127.0.0.1:{port}/  （本机请用 127.0.0.1 或 localhost）")
    app.run(host=host, port=port, debug=False)
