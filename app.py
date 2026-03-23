import os
import json
import base64
import io
import uuid
import struct
import random
import threading
import time
import logging

from flask import Flask, jsonify, request, render_template
import requests as http_requests
import qrcode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CREDENTIALS_PATH = os.path.expanduser("~/.weixin_cow_credentials.json")

# ---------------------------------------------------------------------------
# Provider Models – bot_type + default_base added
# ---------------------------------------------------------------------------
PROVIDER_MODELS = {
    "openai": {
        "label": "OpenAI",
        "key_field": "open_ai_api_key",
        "base": "open_ai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://api.openai.com/v1",
        "models": ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview", "o1-mini"],
    },
    "claude": {
        "label": "Claude (Anthropic)",
        "key_field": "claude_api_key",
        "base": "claude_api_base",
        "bot_type": "claudeAI",
        "default_base": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-sonnet-4-5", "claude-sonnet-4-0", "claude-opus-4-0", "claude-3-5-sonnet-latest"],
    },
    "gemini": {
        "label": "Google Gemini",
        "key_field": "gemini_api_key",
        "base": "gemini_api_base",
        "bot_type": "gemini",
        "default_base": "https://generativelanguage.googleapis.com",
        "models": ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro-preview-05-06", "gemini-2.5-flash-preview-05-20", "gemini-2.0-flash"],
    },
    "deepseek": {
        "label": "DeepSeek",
        "key_field": "open_ai_api_key",
        "base": "open_ai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "minimax": {
        "label": "MiniMax",
        "key_field": "minimax_api_key",
        "base": "minimax_api_base",
        "bot_type": "minimax",
        "default_base": "https://api.minimaxi.com/v1",
        "models": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2.1-lightning", "MiniMax-M2"],
    },
    "zhipu": {
        "label": "智谱 AI (GLM)",
        "key_field": "zhipu_ai_api_key",
        "base": "zhipu_ai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-5-turbo", "glm-5", "glm-4.7", "glm-4-plus", "glm-4-flash", "glm-4-air", "glm-4-airx", "glm-4-long"],
    },
    "qwen": {
        "label": "通义千问 (Qwen)",
        "key_field": "dashscope_api_key",
        "base": "qwen_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.5-plus", "qwen3-max", "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwq-plus"],
    },
    "moonshot": {
        "label": "Kimi (Moonshot)",
        "key_field": "moonshot_api_key",
        "base": "moonshot_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.5", "kimi-k2", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
    },
    "doubao": {
        "label": "豆包 (Doubao)",
        "key_field": "open_ai_api_key",
        "base": "open_ai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-seed-2-0-code-preview-260215", "doubao-seed-2-0-pro-260215", "doubao-seed-2-0-lite-260215", "doubao-seed-2-0-mini-260215"],
    },
    "xunfei": {
        "label": "讯飞星火",
        "key_field": "open_ai_api_key",
        "base": "open_ai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://spark-api-open.xf-yun.com/v1",
        "models": ["4.0Ultra", "generalv3.5", "max-32k", "generalv3", "pro-128k", "lite"],
    },
    "linkai": {
        "label": "LinkAI",
        "key_field": "linkai_api_key",
        "base": "linkai_api_base",
        "bot_type": "chatGPT",
        "default_base": "https://api.link-ai.tech/v1",
        "models": ["linkai-4o", "linkai-4o-mini", "linkai-3.5"],
    },
}

DEFAULT_CONFIG = {
    "model": "gpt-4o",
    "provider": "openai",
    "open_ai_api_key": "",
    "open_ai_api_base": "https://api.openai.com/v1",
    "temperature": 0.7,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "conversation_max_tokens": 2500,
    "character_desc": "你是一个有用的助手。",
    "single_chat_prefix": "",
    "single_chat_reply_prefix": "",
    "single_chat_reply_suffix": "",
    "clear_memory_commands": '["#清除记忆"]',
    "enable_web_search": False,
    "bocha_api_key": "",
}

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_CONFIG)


def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_credentials():
    if os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# ilink API helpers (extracted from weixin_api.py)
# ---------------------------------------------------------------------------

def _random_wechat_uin():
    return base64.b64encode(struct.pack(">I", random.getrandbits(32))).decode()


def _ilink_headers(token=""):
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_wechat_uin(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def ilink_post(base_url, path, token, payload, timeout=40):
    url = f"{base_url.rstrip('/')}/{path}"
    resp = http_requests.post(url, json=payload, headers=_ilink_headers(token), timeout=timeout)
    return resp.json()


def ilink_getupdates(base_url, token, buf=""):
    return ilink_post(base_url, "ilink/bot/getupdates", token, {"get_updates_buf": buf}, timeout=40)


def ilink_sendtext(base_url, token, to_user, text, context_token):
    return ilink_post(base_url, "ilink/bot/sendmessage", token, {
        "msg": {
            "from_user_id": "",
            "to_user_id": to_user,
            "client_id": uuid.uuid4().hex[:16],
            "message_type": 2,
            "message_state": 2,
            "item_list": [{"type": 1, "text_item": {"text": text}}],
            "context_token": context_token,
        }
    })


# ---------------------------------------------------------------------------
# CDN media download (AES-128-ECB decrypt)
# ---------------------------------------------------------------------------

CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"

# item type constants
ITEM_TEXT = 1
ITEM_IMAGE = 2
ITEM_VOICE = 3
ITEM_FILE = 4
ITEM_VIDEO = 5


def _aes_ecb_decrypt(data, key):
    from Crypto.Cipher import AES
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(data)
    pad_len = decrypted[-1]
    if pad_len > 16:
        return decrypted
    return decrypted[:-pad_len]


def _parse_aes_key(aes_key_str):
    """Parse AES key from hex string or base64-encoded value → 16 bytes."""
    try:
        key_bytes = bytes.fromhex(aes_key_str)
        if len(key_bytes) == 16:
            return key_bytes
    except (ValueError, TypeError):
        pass
    decoded = base64.b64decode(aes_key_str)
    if len(decoded) == 32:
        return bytes.fromhex(decoded.decode("ascii"))
    if len(decoded) == 16:
        return decoded
    raise ValueError(f"Invalid AES key length: {len(decoded)}")


def _download_image_as_base64(image_item):
    """Download image from CDN, decrypt, return (mime_type, base64_str) or None."""
    from urllib.parse import quote
    media = image_item.get("media", {})
    encrypt_param = media.get("encrypt_query_param", "")
    aes_key_str = image_item.get("aeskey", "") or media.get("aes_key", "")
    if not encrypt_param or not aes_key_str:
        logger.warning("Image missing CDN params")
        return None
    try:
        url = f"{CDN_BASE_URL}/download?encrypted_query_param={quote(encrypt_param)}"
        resp = http_requests.get(url, timeout=30)
        resp.raise_for_status()
        key = _parse_aes_key(aes_key_str)
        decrypted = _aes_ecb_decrypt(resp.content, key)
        b64 = base64.b64encode(decrypted).decode()
        # detect mime from magic bytes
        if decrypted[:3] == b'\xff\xd8\xff':
            mime = "image/jpeg"
        elif decrypted[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        elif decrypted[:4] == b'GIF8':
            mime = "image/gif"
        elif decrypted[:4] == b'RIFF' and decrypted[8:12] == b'WEBP':
            mime = "image/webp"
        else:
            mime = "image/jpeg"  # fallback
        return mime, b64
    except Exception as e:
        logger.error("Image download/decrypt failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Web search (Bocha API, same as original project)
# ---------------------------------------------------------------------------

def web_search(query, api_key, count=5):
    """Search the web via Bocha API, return formatted context string."""
    try:
        resp = http_requests.post("https://api.bocha.cn/v1/web-search", json={
            "query": query,
            "count": count,
            "freshness": "noLimit",
            "summary": True,
        }, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, timeout=15)
        if resp.status_code != 200:
            logger.warning("Bocha search HTTP %s", resp.status_code)
            return ""
        data = resp.json()
        pages = data.get("data", {}).get("webPages", {}).get("value", [])
        if not pages:
            return ""
        parts = []
        for i, p in enumerate(pages[:count], 1):
            title = p.get("name", "")
            snippet = p.get("summary") or p.get("snippet", "")
            url = p.get("url", "")
            parts.append(f"[{i}] {title}\n{snippet}\n{url}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return ""


# ---------------------------------------------------------------------------
# AI call helpers
# ---------------------------------------------------------------------------

MAX_HISTORY = 20  # max conversation turns per user

# per-user conversation history: { user_id: [ {role, content}, ... ] }
conversation_store = {}
conversation_lock = threading.Lock()


def _get_history(user_id):
    with conversation_lock:
        return list(conversation_store.get(user_id, []))


def _append_history(user_id, role, content):
    with conversation_lock:
        if user_id not in conversation_store:
            conversation_store[user_id] = []
        conversation_store[user_id].append({"role": role, "content": content})
        # trim to last N turns
        if len(conversation_store[user_id]) > MAX_HISTORY * 2:
            conversation_store[user_id] = conversation_store[user_id][-(MAX_HISTORY * 2):]


def _clear_history(user_id):
    with conversation_lock:
        conversation_store.pop(user_id, None)


def _resolve_provider(cfg):
    """Determine which provider entry to use based on config."""
    provider_key = cfg.get("provider", "openai")
    p = PROVIDER_MODELS.get(provider_key)
    if not p:
        p = PROVIDER_MODELS["openai"]
        provider_key = "openai"
    return provider_key, p


def call_ai(user_text, user_id, cfg, image_b64=None):
    """Call AI provider and return reply text. image_b64=(mime, b64str) for vision."""
    provider_key, p = _resolve_provider(cfg)
    api_key = cfg.get(p["key_field"], "")
    base_url = cfg.get(p["base"], "") or p.get("default_base", "")
    model = cfg.get("model", "gpt-4o")
    system_prompt = cfg.get("character_desc", "你是一个有用的助手。")
    temperature = cfg.get("temperature", 0.7)

    if not api_key:
        return "[错误] 未配置 API Key，请在配置面板中设置"

    # check clear memory commands
    clear_cmds = cfg.get("clear_memory_commands", "[]")
    try:
        cmds = json.loads(clear_cmds) if isinstance(clear_cmds, str) else clear_cmds
    except Exception:
        cmds = []
    if user_text.strip() in cmds:
        _clear_history(user_id)
        return "记忆已清除"

    # build messages
    history = _get_history(user_id)

    # web search augmentation
    search_context = ""
    if cfg.get("enable_web_search") and cfg.get("bocha_api_key") and user_text and not image_b64:
        search_context = web_search(user_text, cfg["bocha_api_key"])
    if search_context:
        system_prompt += (
            "\n\n以下是与用户问题相关的网络搜索结果，请参考这些信息回答，"
            "如果搜索结果与问题无关可忽略：\n\n" + search_context
        )

    # build user content (text-only or vision)
    if image_b64:
        mime, b64str = image_b64
        if provider_key == "claude":
            user_content = []
            if user_text:
                user_content.append({"type": "text", "text": user_text})
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64str},
            })
        else:
            # OpenAI-compatible vision format
            user_content = []
            if user_text:
                user_content.append({"type": "text", "text": user_text})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64str}"},
            })
    else:
        user_content = user_text

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_content}]

    try:
        if provider_key == "claude":
            reply = _call_claude(api_key, base_url, model, messages, temperature)
        elif provider_key == "gemini" and "googleapis.com" in base_url:
            reply = _call_gemini_native(api_key, base_url, model, messages, temperature, image_b64)
        else:
            reply = _call_openai_compatible(api_key, base_url, model, messages, temperature)
    except Exception as e:
        logger.error("AI call failed: %s", e)
        return f"[AI 调用失败] {e}"

    # store conversation (text-only summary for history)
    history_user = user_text if user_text else "[图片]"
    _append_history(user_id, "user", history_user)
    _append_history(user_id, "assistant", reply)
    return reply


def _call_openai_compatible(api_key, base_url, model, messages, temperature):
    url = f"{base_url.rstrip('/')}/chat/completions"
    resp = http_requests.post(url, json={
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_claude(api_key, base_url, model, messages, temperature):
    url = f"{base_url.rstrip('/')}/v1/messages"
    # Claude expects system separate, and no "system" role in messages
    system_text = ""
    claude_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            claude_messages.append({"role": m["role"], "content": m["content"]})

    body = {
        "model": model,
        "max_tokens": 4096,
        "messages": claude_messages,
        "temperature": temperature,
    }
    if system_text:
        body["system"] = system_text

    resp = http_requests.post(url, json=body, headers={
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Claude returns content as a list of blocks
    parts = data.get("content", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


def _call_gemini_native(api_key, base_url, model, messages, temperature, image_b64=None):
    """Call Gemini via its native generateContent API."""
    url = f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent?key={api_key}"

    # build parts for Gemini
    system_text = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"] if isinstance(m["content"], str) else ""
            continue
        role = "user" if m["role"] == "user" else "model"
        content = m["content"]
        if isinstance(content, str):
            contents.append({"role": role, "parts": [{"text": content}]})
        elif isinstance(content, list):
            # vision content from call_ai — rebuild for Gemini format
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append({"text": block["text"]})
            # image handled separately below
            if parts:
                contents.append({"role": role, "parts": parts})

    # if there's an image, add it to the last user message
    if image_b64:
        mime, b64str = image_b64
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"].append({
                "inline_data": {"mime_type": mime, "data": b64str}
            })

    body = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}

    resp = http_requests.post(url, json=body, headers={
        "Content-Type": "application/json",
    }, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # extract text from first candidate
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return "[Gemini 未返回内容]"


# ---------------------------------------------------------------------------
# Bot message loop (background thread)
# ---------------------------------------------------------------------------

class BotEngine:
    def __init__(self):
        self._thread = None
        self._running = False
        self._stop_event = threading.Event()
        self.stats = {"received": 0, "replied": 0, "errors": 0, "started_at": None}

    @property
    def running(self):
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return False
        self._stop_event.clear()
        self._running = True
        self.stats = {"received": 0, "replied": 0, "errors": 0, "started_at": time.time()}
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if not self._running:
            return False
        self._running = False
        self._stop_event.set()
        return True

    def _loop(self):
        logger.info("Bot engine started")
        creds = load_credentials()
        if not creds or creds.get("status") != "confirmed":
            logger.error("No valid credentials, stopping bot")
            self._running = False
            return

        base_url = creds.get("baseurl", "")
        token = creds.get("bot_token", "")
        buf = ""

        while self._running and not self._stop_event.is_set():
            try:
                data = ilink_getupdates(base_url, token, buf)

                # check for errors / session expiry
                ret = data.get("ret", 0)
                errcode = data.get("errcode", 0)
                if errcode == -14 or ret == -14:
                    logger.error("Session expired (errcode=%s), stopping bot", errcode)
                    self.stats["errors"] += 1
                    break
                if ret != 0:
                    logger.warning("getupdates ret=%s errmsg=%s", ret, data.get("errmsg", ""))
                    self.stats["errors"] += 1
                    if not self._stop_event.wait(3):
                        continue

                buf = data.get("get_updates_buf", buf)
                msgs = data.get("msgs", [])

                for msg in msgs:
                    self._handle_message(msg, base_url, token)

            except Exception as e:
                logger.error("getupdates error: %s", e)
                self.stats["errors"] += 1
                # avoid tight error loop
                if not self._stop_event.wait(3):
                    continue

        logger.info("Bot engine stopped")
        self._running = False

    def _handle_message(self, msg, base_url, token):
        # only handle user messages (message_type=1)
        if msg.get("message_type") != 1:
            return

        self.stats["received"] += 1
        user_id = msg.get("from_user_id", "")
        context_token = msg.get("context_token", "")

        # parse item_list: extract text, image, voice, file/video
        text = ""
        image_item = None
        has_file = False
        has_video = False

        for item in msg.get("item_list", []):
            itype = item.get("type", 0)
            if itype == ITEM_TEXT:
                text = item.get("text_item", {}).get("text", "")
            elif itype == ITEM_IMAGE:
                image_item = item.get("image_item", {})
            elif itype == ITEM_VOICE:
                # use voice transcription text if available
                voice_text = item.get("voice_item", {}).get("text", "")
                if voice_text:
                    text = voice_text
            elif itype == ITEM_FILE:
                has_file = True
            elif itype == ITEM_VIDEO:
                has_video = True

        cfg = load_config()
        prefix = cfg.get("single_chat_reply_prefix", "")
        suffix = cfg.get("single_chat_reply_suffix", "")

        try:
            # case 1: image (with optional text caption)
            if image_item:
                logger.info("Received image from %s (text=%s)", user_id, text[:30] if text else "")
                img_data = _download_image_as_base64(image_item)
                if img_data:
                    prompt = text or "请描述这张图片"
                    reply = call_ai(prompt, user_id, cfg, image_b64=img_data)
                else:
                    reply = call_ai(text or "[用户发送了一张图片，但下载失败]", user_id, cfg)
                full_reply = f"{prefix}{reply}{suffix}"
                ilink_sendtext(base_url, token, user_id, full_reply, context_token)
                self.stats["replied"] += 1
                return

            # case 2: text or voice transcription
            if text:
                logger.info("Received from %s: %s", user_id, text[:50])
                reply = call_ai(text, user_id, cfg)
                full_reply = f"{prefix}{reply}{suffix}"
                ilink_sendtext(base_url, token, user_id, full_reply, context_token)
                self.stats["replied"] += 1
                return

            # case 3: file or video without text → unsupported hint
            if has_file or has_video:
                hint = "暂不支持文件/视频消息，请发送文字或图片 🙂"
                ilink_sendtext(base_url, token, user_id, hint, context_token)
                self.stats["replied"] += 1
                return

            # no recognizable content, ignore

        except Exception as e:
            logger.error("Reply failed for %s: %s", user_id, e)
            self.stats["errors"] += 1


bot_engine = BotEngine()

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/providers")
def providers():
    return jsonify(PROVIDER_MODELS)


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def post_config():
    current = load_config()
    incoming = request.get_json(force=True)
    current.update(incoming)
    save_config(current)
    return jsonify({"ok": True})


# --- WeChat QR login ---

@app.route("/api/weixin/qr", methods=["GET"])
def weixin_qr():
    try:
        resp = http_requests.get(
            "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3",
            timeout=15,
        )
        data = resp.json()
        qr_token = data.get("qrcode", "")
        qr_img_url = data.get("qrcode_img_content", "")
        if not qr_token or not qr_img_url:
            return jsonify({"ok": False, "error": "未获取到 qrcode", "raw": data}), 500

        img = qrcode.make(qr_img_url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({"ok": True, "qrcode": qr_token, "image": f"data:image/png;base64,{b64}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/weixin/qr/poll", methods=["POST"])
def weixin_qr_poll():
    try:
        body = request.get_json(force=True)
        qrcode_val = body.get("qrcode", "")
        if not qrcode_val:
            return jsonify({"ok": False, "error": "missing qrcode"}), 400

        resp = http_requests.get(
            f"https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status?qrcode={http_requests.utils.quote(qrcode_val)}",
            headers={"iLink-App-ClientVersion": "1"},
            timeout=35,
        )
        data = resp.json()
        status = data.get("status", "")

        if status == "confirmed":
            creds = {
                "status": "confirmed",
                "bot_token": data.get("bot_token", ""),
                "ilink_bot_id": data.get("ilink_bot_id", ""),
                "baseurl": data.get("baseurl", ""),
                "ilink_user_id": data.get("ilink_user_id", ""),
            }
            with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
                json.dump(creds, f, ensure_ascii=False, indent=2)

        return jsonify({"ok": True, "status": status, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --- WeChat credential status ---

@app.route("/api/weixin/status", methods=["GET"])
def weixin_status():
    creds = load_credentials()
    if creds and creds.get("status") == "confirmed" and creds.get("bot_token"):
        return jsonify({"ok": True, "logged_in": True})
    return jsonify({"ok": True, "logged_in": False})


# --- Bot lifecycle ---

@app.route("/api/bot/start", methods=["POST"])
def bot_start():
    # check credentials first
    creds = load_credentials()
    if not creds or creds.get("status") != "confirmed":
        return jsonify({"ok": False, "error": "未登录微信，请先扫码"}), 400
    # check API key
    cfg = load_config()
    provider_key, p = _resolve_provider(cfg)
    api_key = cfg.get(p["key_field"], "")
    if not api_key:
        return jsonify({"ok": False, "error": "未配置 API Key，请先在模型配置中设置"}), 400

    if bot_engine.running:
        return jsonify({"ok": True, "message": "Bot 已在运行中"})
    ok = bot_engine.start()
    return jsonify({"ok": ok, "message": "Bot 已启动" if ok else "启动失败"})


@app.route("/api/bot/stop", methods=["POST"])
def bot_stop():
    ok = bot_engine.stop()
    return jsonify({"ok": ok, "message": "Bot 已停止" if ok else "Bot 未在运行"})


@app.route("/api/bot/status", methods=["GET"])
def bot_status():
    running = bot_engine.running
    stats = dict(bot_engine.stats)
    if stats.get("started_at"):
        stats["uptime_seconds"] = int(time.time() - stats["started_at"])
    return jsonify({"ok": True, "running": running, "stats": stats})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
