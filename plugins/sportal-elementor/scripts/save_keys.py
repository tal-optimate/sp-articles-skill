#!/usr/bin/env python3
"""SessionStart hook: save the WordPress login from the plugin's settings form.

Claude Code hands plugin settings only to hooks (as CLAUDE_PLUGIN_OPTION_<KEY>). This writes them to keys.json in
the plugin's private data folder (owner-readable only), where wp_headers.py (the Elementor connection) and the
magazine skill's script read them. Prints nothing.
"""
import json
import os

KEYS = ("wp_user", "wp_app_password")
data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "plugins", "data", "sportal-elementor-sportal")
values = {k: os.environ.get("CLAUDE_PLUGIN_OPTION_" + k.upper(), "").strip() for k in KEYS}
if all(values.values()):
    os.makedirs(data_dir, exist_ok=True)
    fd = os.open(os.path.join(data_dir, "keys.json"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(values, f)
