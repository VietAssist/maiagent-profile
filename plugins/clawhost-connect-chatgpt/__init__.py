import asyncio
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import yaml


_DASHBOARD_URL = "http://127.0.0.1:9119"
_PROFILE = "maiagent"
_POLL_TASKS = set()
_ACTIVE_LOGIN = None
_CONNECT_LOCK = None
_SUCCESS_MESSAGE = (
    "✅ ChatGPT / Codex connected successfully. "
    "Default model: gpt-5.6-luna (max reasoning)."
)


def _json_request(opener, url, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with opener.open(request, timeout=20) as response:
        raw = response.read(16384).decode("utf-8", errors="replace")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise RuntimeError("Hermes dashboard returned an invalid response.")
    return result


def _start():
    username = os.environ.get("HERMES_DASHBOARD_BASIC_AUTH_USERNAME", "admin")
    password = os.environ.get("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("Hermes dashboard credentials are unavailable.")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    _json_request(
        opener,
        _DASHBOARD_URL + "/auth/password-login",
        method="POST",
        payload={
            "provider": "basic",
            "username": username,
            "password": password,
            "next": "/",
        },
    )
    profile = urllib.parse.urlencode({"profile": _PROFILE})
    data = _json_request(
        opener,
        _DASHBOARD_URL + "/api/providers/oauth/openai-codex/start?" + profile,
        method="POST",
    )
    session_id = data.get("session_id")
    url = data.get("verification_url")
    code = data.get("user_code")
    interval = data.get("poll_interval", 5)
    if not all(isinstance(value, str) and value for value in (session_id, url, code)):
        raise RuntimeError("Hermes dashboard returned an invalid OAuth session.")
    if not isinstance(interval, (int, float)) or interval < 1:
        interval = 5
    return opener, session_id, url, code, float(interval)


def _poll_once(opener, session_id):
    quoted = urllib.parse.quote(session_id, safe="")
    return _json_request(
        opener,
        _DASHBOARD_URL + "/api/providers/oauth/openai-codex/poll/" + quoted,
    )


def _notification_targets():
    home = os.environ.get("TELEGRAM_HOME_CHANNEL", "").strip()
    return ["telegram"] if home else []


def _send_success_notification():
    for target in _notification_targets():
        try:
            subprocess.run(
                [
                    "/opt/hermes/bin/hermes",
                    "-p",
                    _PROFILE,
                    "send",
                    "--to",
                    target,
                    _SUCCESS_MESSAGE,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue


def _activate_codex_default():
    profile_home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    config_path = profile_home / "config.yaml"
    config = (yaml.safe_load(config_path.read_text()) or {}) if config_path.exists() else {}
    if not isinstance(config, dict):
        raise RuntimeError("Hermes profile config is invalid.")
    config["model"] = {
        "default": "gpt-5.6-luna",
        "provider": "openai-codex",
        "base_url": "https://chatgpt.com/backend-api/codex",
    }
    agent = config.get("agent")
    if not isinstance(agent, dict):
        agent = {}
        config["agent"] = agent
    agent["reasoning_effort"] = "max"
    config_temp = config_path.with_suffix(".yaml.next")
    config_temp.write_text(yaml.safe_dump(config, sort_keys=False))
    os.chmod(config_temp, 0o600)
    config_temp.replace(config_path)


async def _poll(opener, session_id, interval):
    for _attempt in range(180):
        await asyncio.sleep(interval)
        try:
            data = await asyncio.to_thread(_poll_once, opener, session_id)
        except (OSError, ValueError, RuntimeError, urllib.error.HTTPError):
            continue
        status = data.get("status")
        if status == "approved":
            await asyncio.to_thread(_activate_codex_default)
            await asyncio.to_thread(_send_success_notification)
            return
        if status in {"denied", "expired", "error"}:
            return


def _release(task):
    global _ACTIVE_LOGIN
    _POLL_TASKS.discard(task)
    if _ACTIVE_LOGIN is not None and _ACTIVE_LOGIN[2] is task:
        _ACTIVE_LOGIN = None


def _retain(task):
    _POLL_TASKS.add(task)
    task.add_done_callback(_release)


async def _connect(_raw_args):
    global _ACTIVE_LOGIN, _CONNECT_LOCK
    if _CONNECT_LOCK is None:
        _CONNECT_LOCK = asyncio.Lock()
    async with _CONNECT_LOCK:
        if _ACTIVE_LOGIN is not None:
            return "{}\n{}".format(_ACTIVE_LOGIN[0], _ACTIVE_LOGIN[1])
        try:
            opener, session_id, url, code, interval = await asyncio.to_thread(_start)
            task = asyncio.create_task(_poll(opener, session_id, interval))
            _ACTIVE_LOGIN = (url, code, task)
            _retain(task)
            return "{}\n{}".format(url, code)
        except (OSError, ValueError, RuntimeError, urllib.error.HTTPError):
            return "Unable to start ChatGPT connection. Please try again."


def register(ctx):
    ctx.register_command(
        name="connect-chatgpt",
        handler=_connect,
        description="Connect your ChatGPT account",
    )
