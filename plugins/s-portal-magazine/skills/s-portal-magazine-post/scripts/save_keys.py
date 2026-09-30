#!/usr/bin/env python3
"""SessionStart hook: hand the keys from the plugin's settings form to magazine_post.py.

Claude Code gives plugin settings only to hooks (as CLAUDE_PLUGIN_OPTION_<KEY>), not to commands Claude runs,
so this writes them to keys.json in the plugin's private data folder (owner-readable only). Prints nothing.
"""
import json
import os

KEYS = ("openai_api_key",)  # the WordPress login comes from the sportal-elementor plugin
data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "plugins", "data", "s-portal-magazine-sportal")
values = {k: os.environ.get("CLAUDE_PLUGIN_OPTION_" + k.upper(), "").strip() for k in KEYS}
if any(values.values()):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "keys.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(values, f)
