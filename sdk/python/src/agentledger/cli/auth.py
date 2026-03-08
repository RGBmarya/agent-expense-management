"""CLI authentication — API key storage via OS keyring (preferred) or file fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".agentledger"
CONFIG_FILE = CONFIG_DIR / "config.json"

_KEYRING_SERVICE = "agentledger-cli"
_KEYRING_USERNAME = "api_key"


def _keyring_available() -> bool:
    try:
        import keyring
        # Verify backend is usable (not the fail backend)
        keyring.get_keyring()
        return True
    except Exception:
        return False


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    # Restrict permissions
    CONFIG_FILE.chmod(0o600)


def save_api_key(api_key: str, endpoint: str = "") -> None:
    if _keyring_available():
        import keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, api_key)
    else:
        config = _load_config()
        config["api_key"] = api_key
        _save_config(config)
    if endpoint:
        config = _load_config()
        config["endpoint"] = endpoint
        _save_config(config)


def get_api_key() -> str:
    # Environment variable takes precedence
    env_key = os.getenv("AGENTLEDGER_API_KEY", "")
    if env_key:
        return env_key
    # Try keyring first
    if _keyring_available():
        import keyring
        key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if key:
            return key
    # Fall back to file
    config = _load_config()
    return config.get("api_key", "")


def get_endpoint() -> str:
    env_ep = os.getenv("AGENTLEDGER_ENDPOINT", "")
    if env_ep:
        return env_ep
    config = _load_config()
    return config.get("endpoint", "https://api.agentledger.dev")


def clear_config() -> None:
    if _keyring_available():
        import keyring
        try:
            keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        except Exception:
            pass
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
