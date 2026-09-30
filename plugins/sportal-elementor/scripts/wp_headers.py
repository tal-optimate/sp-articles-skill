#!/usr/bin/env python3
"""headersHelper for the Elementor connection: print the WordPress Basic-auth header as JSON.

Reads the login that save_keys.py stored from the plugin's settings form. Prints {} until that has happened
(first start after entering the keys): the connection then fails once and works after a restart or /mcp reconnect.
"""
import base64
import glob
import json
import os

base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
headers = {}
for path in glob.glob(os.path.join(base, "plugins", "data", "*sportal-elementor*", "keys.json")):
    try:
        with open(path, encoding="utf-8") as f:
            k = json.load(f)
        token = base64.b64encode(("%s:%s" % (k["wp_user"], k["wp_app_password"])).encode()).decode()
        headers = {"Authorization": "Basic " + token}
        break
    except (OSError, ValueError, KeyError):
        pass
print(json.dumps(headers))
