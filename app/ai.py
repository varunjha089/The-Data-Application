"""AI writing: which provider and model write the report (Settings, AI writing), the API keys, and the list of models of a provider.
Standard library only. The key is never written into a project, app_config.json, a log or a command line:
  - macOS: the login Keychain (service "The Data Application AI", account = provider), written through `security -i` on its standard input;
  - other systems, and runs with THE_DATA_APP_HOME set (tests, trials): the file ai_keys.json in the settings folder, readable by the user only;
  - an environment variable (ANTHROPIC_API_KEY, GEMINI_API_KEY or GOOGLE_API_KEY) is used when no key was saved.
The provider, the model and the choices are kept in app_config.json under "ai" (no key there)."""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

from . import config
from .paths import APP_DATA

PROVIDERS = {"anthropic": {"label": "Anthropic (Claude)", "env": ["ANTHROPIC_API_KEY"], "keys_page": "https://console.anthropic.com/settings/keys",
                           "suggested": "claude-opus-5-5"},
             "gemini": {"label": "Google (Gemini)", "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"], "keys_page": "https://aistudio.google.com/apikey",
                        "suggested": ""}}
SERVICE = "The Data Application AI"
KEY_FILE = APP_DATA / "ai_keys.json"
KEYCHAIN = os.environ.get("THE_DATA_APP_KEYCHAIN", "")       # a keychain file instead of the login keychain (tests)
KEY_RE = re.compile(r"^[A-Za-z0-9_\-.]{20,200}$")


def _keychain():
    return sys.platform == "darwin" and (bool(KEYCHAIN) or not os.environ.get("THE_DATA_APP_HOME"))


def _kc():
    """the keychain file argument of `security` (none: the login keychain)"""
    return [KEYCHAIN] if KEYCHAIN else []


def settings():
    """the saved choices: provider, model per provider, send the plot pictures"""
    s = config.app_load().get("ai") or {}
    prov = s.get("provider") if s.get("provider") in PROVIDERS else "anthropic"
    return {"provider": prov, "models": s.get("models") or {}, "images": bool(s.get("images", False))}


def save_settings(values):
    cfg = config.app_load()
    s = settings()
    if values.get("provider") in PROVIDERS:
        s["provider"] = values["provider"]
    if isinstance(values.get("model"), str):
        s["models"][s["provider"]] = values["model"][:120]
    if "images" in values:
        s["images"] = bool(values["images"])
    cfg["ai"] = s
    config.app_save(cfg)
    return s


def model(provider=None):
    s = settings()
    return s["models"].get(provider or s["provider"], "")


# ---------------------------------------------------------------- keys
def _file_keys():
    return config.read_json(KEY_FILE)


def set_key(provider, key):
    """save the key (Keychain on macOS); returns (ok, message)"""
    key = (key or "").strip()
    if provider not in PROVIDERS:
        return False, "Unknown provider."
    if not KEY_RE.match(key):
        return False, "This does not look like an API key (letters, digits, - and _ only, at least 20 characters)."
    if _keychain():
        cmd = f'add-generic-password -U -s "{SERVICE}" -a "{provider}" -w "{key}"' + (f' "{KEYCHAIN}"' if KEYCHAIN else "") + "\n"   # on stdin, never on the command line
        r = subprocess.run(["security", "-i"], input=cmd, capture_output=True, text=True)
        if r.returncode != 0 or "error" in (r.stderr or "").lower():
            return False, "The key could not be saved in the Keychain."
        return True, "Saved in the macOS Keychain."
    keys = _file_keys()
    keys[provider] = key
    config.write_json(KEY_FILE, keys)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    return True, f"Saved in {KEY_FILE.name} in the settings folder (readable by you only)."


def delete_key(provider):
    if _keychain():
        subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", provider] + _kc(), capture_output=True)
    keys = _file_keys()
    if provider in keys:
        keys.pop(provider)
        config.write_json(KEY_FILE, keys)


def _saved_key(provider):
    if _keychain():
        r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", provider, "-w"] + _kc(), capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    return _file_keys().get(provider, "")


def key(provider):
    """(key, where it comes from) or ("", "none")"""
    k = _saved_key(provider)
    if k:
        return k, "keychain" if _keychain() else "file"
    for name in PROVIDERS[provider]["env"]:
        if os.environ.get(name):
            return os.environ[name], "environment variable " + name
    return "", "none"


def status():
    """what the Settings card shows: per provider whether a key is there (only its last 4 characters), the chosen model"""
    s = settings()
    out = {"provider": s["provider"], "images": s["images"], "providers": {}}
    for p, info in PROVIDERS.items():
        k, where = key(p)
        out["providers"][p] = {"label": info["label"], "has_key": bool(k), "where": where, "ending": k[-4:] if k else "", "model": s["models"].get(p, ""),
                               "keys_page": info["keys_page"], "suggested": info["suggested"]}
    return out


# ---------------------------------------------------------------- models
def _url(provider):
    """the provider's address (THE_DATA_APP_ANTHROPIC_URL / THE_DATA_APP_GEMINI_URL point the tests at a local stand-in)"""
    if provider == "anthropic":
        return os.environ.get("THE_DATA_APP_ANTHROPIC_URL", "https://api.anthropic.com").rstrip("/")
    return os.environ.get("THE_DATA_APP_GEMINI_URL", "https://generativelanguage.googleapis.com").rstrip("/")


def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def list_models(provider):
    """(ok, [{"id", "label"}] or message): the models the key may use, newest first as the provider lists them"""
    k, _ = key(provider)
    if not k:
        return False, "No API key for this provider yet."
    try:
        if provider == "anthropic":
            out, after = [], None
            for _ in range(10):
                url = _url("anthropic") + "/v1/models?limit=100" + (f"&after_id={after}" if after else "")
                d = _get(url, {"x-api-key": k, "anthropic-version": "2026-10-21"})
                out += [{"id": m["id"], "label": m.get("display_name") or m["id"]} for m in d.get("data", [])]
                if not d.get("has_more"):
                    break
                after = d.get("last_id")
            return True, out
        out, token = [], None
        for _ in range(10):
            url = _url("gemini") + "/v1beta/models?pageSize=200" + (f"&pageToken={token}" if token else "")
            d = _get(url, {"x-goog-api-key": k})
            out += [{"id": m["name"].split("/", 1)[-1], "label": m.get("displayName") or m["name"]} for m in d.get("models", [])
                    if "generateContent" in (m.get("supportedGenerationMethods") or [])]
            token = d.get("nextPageToken")
            if not token:
                break
        return True, out
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            return False, f"The key was refused (HTTP {e.code}): check that you copied the whole key."
        return False, f"The provider answered HTTP {e.code}; try again later."
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, f"The provider cannot be reached ({e}). Is there an internet connection?"
