"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI. Lĩnh viết, theo docs/connect-model.md.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str, json_mode: bool = False) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, GỒM CẢ token suy luận / suy nghĩ nếu API tính riêng
    json_mode=True: xin model trả đúng một object JSON (dùng cho model lần 1, design §4.2).
    Lỗi gọi model (hết lượt, sai key, mất mạng): để exception bay ra — khung ghi lỗi vào cột error.
    Lỗi tạm (429, 5xx, mất kết nối) post_json thử lại tối đa 3 lần trước khi báo lỗi.

Chọn nhà cung cấp trong .env:
    MODEL_PROVIDER = fake | gemini | openai | openrouter | anthropic | ollama
    MODEL_NAME     = mã gọi API của model (vd gemini-3.8-flash)
    API_KEY        = key của nhóm (không dán vào code)
    MODEL_THINKING = (tuỳ chọn, chỉ Gemini) mức suy nghĩ, vd low — để trống thì dùng mặc định của model
Để trống MODEL_PROVIDER = chế độ giả (câu giả, token 0): luồng vẫn chạy hết để thử khung.
"""
import json
import os
import random
import time
import urllib.error
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOW_RAW = False   # đổi thành True để in nguyên phản hồi của API khi cần tìm tên trường
TIMEOUT = 90


def load_env(path=os.path.join(ROOT, ".env")):
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có. Khung — không cần sửa."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("API_KEY") or "").strip()
MODEL_THINKING = (os.environ.get("MODEL_THINKING") or "").strip()


# Lỗi tạm của API (quá tải, hết lượt theo phút, mất kết nối): thử lại tối đa ATTEMPTS lần, chờ 1 s rồi 2 s (+ ngẫu
# nhiên) để nhiều BS nhắn cùng lúc không cùng gọi lại một lúc. Lỗi khác (sai key, 400…) và hết giờ chờ báo ngay:
# thử lại hết giờ chờ làm BS đợi tới 3 × TIMEOUT.
RETRY_STATUS = {429, 500, 502, 503, 504}
ATTEMPTS = 3


def post_json(url, headers, body, timeout=TIMEOUT):
    """Gửi POST JSON, trả về JSON phản hồi. Chỉ dùng thư viện chuẩn (urllib)."""
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers=dict({"Content-Type": "application/json"}, **headers))
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUS or attempt == ATTEMPTS:
                raise RuntimeError("HTTP %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError) or attempt == ATTEMPTS:
                raise RuntimeError("URLError: %s" % e.reason)
        time.sleep(attempt + random.random() / 2)
    if SHOW_RAW:
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    return data


# ------------------------------------------------------------------ từng nhà cung cấp

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
URL_OPENAI = "https://api.openai.com/v1/chat/completions"
URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
URL_CLAUDE = "https://api.anthropic.com/v1/messages"
URL_OLLAMA = "http://localhost:11434/api/chat"


def call_gemini(system, user, json_mode):
    config = {"temperature": 0}
    if json_mode:
        config["responseMimeType"] = "application/json"
    if MODEL_THINKING:
        config["thinkingConfig"] = {"thinkingLevel": MODEL_THINKING}
    body = {"contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    data = post_json(URL_GEMINI % MODEL_NAME, {"x-goog-api-key": API_KEY}, body)
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini không trả câu trả lời: %s" % json.dumps(data.get("promptFeedback", {}))[:200])
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    u = data.get("usageMetadata") or {}
    return {"text": text, "tokens_in": u.get("promptTokenCount", 0),
            "tokens_out": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)}


def call_openai_format(url, system, user, json_mode):
    """OpenAI và các API cùng định dạng (OpenRouter…). completion_tokens đã gồm token suy luận."""
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"model": MODEL_NAME, "messages": messages}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = post_json(url, {"Authorization": "Bearer " + API_KEY}, body)
    u = data["usage"]
    return {"text": data["choices"][0]["message"]["content"] or "",
            "tokens_in": u["prompt_tokens"], "tokens_out": u["completion_tokens"]}


def call_claude(system, user, json_mode):
    data = post_json(URL_CLAUDE,
                     {"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
                     {"model": MODEL_NAME, "max_tokens": 2048, "system": system or "",
                      "messages": [{"role": "user", "content": user}]})
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    u = data["usage"]
    return {"text": text, "tokens_in": u["input_tokens"], "tokens_out": u["output_tokens"]}


def call_ollama(system, user, json_mode):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"model": MODEL_NAME, "messages": messages, "stream": False}
    if json_mode:
        body["format"] = "json"
    data = post_json(URL_OLLAMA, {}, body, timeout=300)
    return {"text": data["message"]["content"],
            "tokens_in": data.get("prompt_eval_count", 0), "tokens_out": data.get("eval_count", 0)}


@model_call
def call_model(system: str, user: str, json_mode: bool = False) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}
    if MODEL_PROVIDER == "gemini":
        r = call_gemini(system, user, json_mode)
    elif MODEL_PROVIDER == "openai":
        r = call_openai_format(URL_OPENAI, system, user, json_mode)
    elif MODEL_PROVIDER == "openrouter":
        r = call_openai_format(URL_OPENROUTER, system, user, json_mode)
    elif MODEL_PROVIDER == "anthropic":
        r = call_claude(system, user, json_mode)
    elif MODEL_PROVIDER == "ollama":
        r = call_ollama(system, user, json_mode)
    else:
        raise NotImplementedError(
            "MODEL_PROVIDER=%s chưa hỗ trợ trong codebase/ai.py (dùng: gemini, openai, openrouter, anthropic, ollama)"
            % MODEL_PROVIDER)
    # OpenRouter đặt tên model kèm hãng ("google/gemini-3.8-flash"); trả tên không kèm hãng để
    # `run.py simulate` khớp được với bảng giá trong cost/personas.yaml.
    return {"text": r["text"], "model": MODEL_NAME.split("/")[-1],
            "tokens_in": int(r["tokens_in"] or 0), "tokens_out": int(r["tokens_out"] or 0)}
