from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "bitget_referral_url": "https://www.bitget.com/referral/register?clacCode=REPLACE_ME",
    "github": {
        "publish_enabled": True,
        "repo_name": "",
        "github_username": "",
        "github_token": "",
    },
    "optional": {
        "notes_for_chatgpt": "",
        "force_rebuild": False,
    },
}


def settings_path(project_root: Path) -> Path:
    return project_root / "config" / "user_settings.json"


def local_secrets_path(project_root: Path) -> Path:
    return project_root / "config" / ".local_secrets.json"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_local_secrets(project_root: Path) -> dict[str, Any]:
    path = local_secrets_path(project_root)
    if not path.exists():
        return {"github": {"github_token": ""}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"github": {"github_token": ""}}
    token = (((raw or {}).get("github") or {}).get("github_token") or "").strip()
    return {"github": {"github_token": token}}


def save_local_secrets(project_root: Path, token: str) -> None:
    path = local_secrets_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"github": {"github_token": token.strip()}}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_settings_for_repo(data: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(data)
    out.setdefault("github", {})["github_token"] = ""
    return out


def load_settings(project_root: Path) -> dict[str, Any]:
    path = settings_path(project_root)
    if not path.exists():
        save_settings(project_root, DEFAULT_SETTINGS)
    raw = json.loads(path.read_text(encoding="utf-8"))
    merged = deep_merge(DEFAULT_SETTINGS, raw)
    return deep_merge(merged, load_local_secrets(project_root))


def save_settings(project_root: Path, data: dict[str, Any]) -> None:
    path = settings_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    token = (((data or {}).get("github") or {}).get("github_token") or "").strip()
    if token:
        save_local_secrets(project_root, token)
    safe = sanitize_settings_for_repo(data)
    path.write_text(json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def referral_ready(settings: dict[str, Any]) -> bool:
    url = settings.get("bitget_referral_url", "").strip()
    return bool(url) and "REPLACE_ME" not in url


def infer_repo_name(settings: dict[str, Any]) -> str:
    repo_name = settings.get("github", {}).get("repo_name", "").strip()
    return repo_name or "bitget-referral-site"


def infer_site_url(settings: dict[str, Any]) -> str:
    github = settings.get("github", {})
    username = (github.get("github_username") or "").strip()
    repo_name = infer_repo_name(settings)
    if username and repo_name:
        if repo_name.lower() == f"{username.lower()}.github.io":
            return f"https://{username}.github.io"
        return f"https://{username}.github.io/{repo_name}"
    return "https://example.com"


def validate_settings(settings: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    url = settings.get("bitget_referral_url", "").strip()
    if not url:
        warnings.append("Bitget招待リンクが空です。")
    elif "bitget.com" not in url:
        warnings.append("招待リンクが Bitget ドメインではありません。")
    elif "REPLACE_ME" in url:
        warnings.append("Bitget招待リンクが初期値のままです。")

    repo_name = infer_repo_name(settings)
    if not repo_name:
        warnings.append("GitHub repo_name を決められていません。")
    return warnings


def publish_ready(settings: dict[str, Any]) -> bool:
    github = settings.get('github', {})
    if not github.get('publish_enabled', True):
        return True
    return bool((github.get('github_token') or '').strip())


def startup_needs_gui(settings: dict[str, Any]) -> bool:
    return (not referral_ready(settings)) or (not publish_ready(settings))
