#!/usr/bin/env bun
// Keys for the s-portal magazine plugin, kept only in the OS keychain (macOS Keychain, Windows Credential Manager,
// Linux libsecret) via Bun.secrets. Same pattern as Optimate's clockify-daily-review plugin.
//
//   bun sportal-auth.js login [wordpress|openai|cloudways]   ask (hidden), verify, save; no argument = all three
//   bun sportal-auth.js status                               check each stored key against its service
//   bun sportal-auth.js logout                               remove all stored keys
// Internal (used by the plugin, never prints to a person):
//   headers cloudways|elementor   JSON auth headers for the MCP servers (headersHelper)
//   export                        JSON keys for the skill's Python script
import { secrets } from "bun";

const SERVICE = "co.optimate.sportal-magazine";
const SITE = "https://s-portal.co.il";
const DEFAULT_WP_USER = "sportal.digital@gmail.com";
const KEYS = {
  wp_user: { name: "wp-user", env: "SPORTAL_WP_USER" },
  wp_app_password: { name: "wp-app-password", env: "SPORTAL_WP_APP_PASSWORD" },
  openai_api_key: { name: "openai-api-key", env: "OPENAI_API_KEY" },
  cloudways_token: { name: "cloudways-token", env: "CLOUDWAYS_ACCESS_TOKEN" },
};

// Windows Credential Manager silently truncates long values (~2.5 KB per entry, and Cloudways tokens are long), so
// values are stored in chunks: "<name>" holds "chunks:N" and "<name>.1" … "<name>.N" hold the pieces.
const CHUNK = 600;
const item = (name) => ({ service: SERVICE, name });

async function readRaw(name) {
  const head = await secrets.get(item(name));
  if (!head || !head.startsWith("chunks:")) return head;
  const n = Number(head.slice(7));
  let out = "";
  for (let i = 1; i <= n; i++) {
    const part = await secrets.get(item(`${name}.${i}`));
    if (part == null) return null;
    out += part;
  }
  return out;
}

async function load(key) {
  try {
    const v = await readRaw(KEYS[key].name);
    if (v) return v;
  } catch {
    // no keychain backend (e.g. headless Linux): fall back to the environment
  }
  return (process.env[KEYS[key].env] || "").trim() || null;
}

async function remove(key) {
  const name = KEYS[key].name;
  let removed = false;
  try {
    const head = await secrets.get(item(name));
    if (head && head.startsWith("chunks:")) {
      for (let i = 1; i <= Number(head.slice(7)); i++) await secrets.delete(item(`${name}.${i}`)).catch(() => {});
    }
    removed = await secrets.delete(item(name));
  } catch {}
  return removed;
}

async function save(key, value) {
  const name = KEYS[key].name;
  await remove(key);
  const parts = [];
  for (let i = 0; i < value.length; i += CHUNK) parts.push(value.slice(i, i + CHUNK));
  for (let i = 0; i < parts.length; i++) await secrets.set({ ...item(`${name}.${i + 1}`), value: parts[i] });
  await secrets.set({ ...item(name), value: `chunks:${parts.length}` });
  if ((await readRaw(name)) !== value) {
    throw new Error(`the keychain didn't store the ${key.replace(/_/g, " ")} correctly`);
  }
}

/** Reads a line from the terminal; hidden unless `visible`. Falls back to plain stdin when piped. */
async function ask(prompt, { visible = false } = {}) {
  const stdin = process.stdin;
  process.stderr.write(prompt);
  if (!stdin.isTTY) {
    const text = await new Response(Bun.stdin.stream()).text();
    return text.trim();
  }
  stdin.setRawMode(true);
  stdin.resume();
  stdin.setEncoding("utf8");
  return new Promise((resolve, reject) => {
    let value = "";
    const onData = (chunk) => {
      for (const char of chunk) {
        if (char === "\r" || char === "\n") {
          cleanup();
          process.stderr.write("\n");
          return resolve(value.trim());
        }
        if (char === "\u0003") {
          cleanup();
          process.stderr.write("\n");
          return reject(new Error("Cancelled."));
        }
        if (char === "\u007f" || char === "\b") {
          if (value && visible) process.stderr.write("\b \b");
          value = value.slice(0, -1);
        } else {
          value += char;
          if (visible) process.stderr.write(char);
        }
      }
    };
    const cleanup = () => {
      stdin.off("data", onData);
      stdin.setRawMode(false);
      stdin.pause();
    };
    stdin.on("data", onData);
  });
}

const basic = (user, pass) => "Basic " + Buffer.from(`${user}:${pass}`).toString("base64");

async function verifyWordPress(user, pass) {
  const r = await fetch(`${SITE}/wp-json/wp/v2/users/me?context=edit`, { headers: { Authorization: basic(user, pass) } });
  if (r.status === 401 || r.status === 403) throw new Error("wrong user or application password");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const me = await r.json();
  const caps = me.capabilities || {};
  if (!caps.publish_posts || !caps.upload_files) throw new Error(`${me.name} can't publish or upload (needs the Editor role)`);
  return `${me.name} (WordPress user ${me.id})`;
}

async function verifyOpenAI(key) {
  const r = await fetch("https://api.openai.com/v1/models", { headers: { Authorization: `Bearer ${key}` } });
  if (r.status === 401) throw new Error("invalid key");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return "key works";
}

async function verifyCloudways(token) {
  const r = await fetch("https://mcp.cloudways.com/mcp/", {
    method: "POST",
    headers: {
      "X-Access-Token": token,
      "X-Mcp-Host": "claude-code",
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "sportal-auth", version: "1" } },
    }),
  });
  if (r.status === 401 || r.status === 403) throw new Error("token rejected");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return "token works";
}

async function loginWordPress() {
  console.error("\nWordPress (s-portal.co.il): the application password from wp-admin → Users → Profile → Application Passwords.");
  const current = (await load("wp_user")) || DEFAULT_WP_USER;
  const user = (await ask(`WordPress user [${current}]: `, { visible: true })) || current;
  const pass = await ask("Application password (hidden, spaces are fine): ");
  if (!pass) return console.error("Skipped WordPress (nothing entered)."), false;
  const who = await verifyWordPress(user, pass).catch((e) => (console.error(`✗ Rejected by WordPress: ${e.message}. Nothing saved.`), null));
  if (!who) return false;
  await save("wp_user", user);
  await save("wp_app_password", pass);
  console.error(`✓ WordPress saved to the keychain. Authenticated as ${who}.`);
  return true;
}

async function loginOpenAI() {
  console.error("\nOpenAI (cover images): the API key, starts with sk-.");
  const key = await ask("OpenAI API key (hidden): ");
  if (!key) return console.error("Skipped OpenAI (nothing entered)."), false;
  const ok = await verifyOpenAI(key).catch((e) => (console.error(`✗ Rejected by OpenAI: ${e.message}. Nothing saved.`), null));
  if (!ok) return false;
  await save("openai_api_key", key);
  console.error("✓ OpenAI key saved to the keychain.");
  return true;
}

async function loginCloudways() {
  console.error("\nCloudways (clears the site cache): the access token from platform.cloudways.com → API.");
  const token = await ask("Cloudways access token (hidden): ");
  if (!token) return console.error("Skipped Cloudways (nothing entered)."), false;
  const ok = await verifyCloudways(token).catch((e) => (console.error(`✗ Rejected by Cloudways: ${e.message}. Nothing saved.`), null));
  if (!ok) return false;
  await save("cloudways_token", token);
  console.error("✓ Cloudways token saved to the keychain.");
  return true;
}

async function status() {
  const checks = [
    ["WordPress", async () => {
      const [u, p] = [await load("wp_user"), await load("wp_app_password")];
      if (!u || !p) throw new Error("not set");
      return verifyWordPress(u, p);
    }],
    ["OpenAI", async () => {
      const k = await load("openai_api_key");
      if (!k) throw new Error("not set");
      return verifyOpenAI(k);
    }],
    ["Cloudways", async () => {
      const t = await load("cloudways_token");
      if (!t) throw new Error("not set");
      return verifyCloudways(t);
    }],
  ];
  let bad = 0;
  for (const [label, check] of checks) {
    const msg = await check().then((m) => `✓ ${label}: ${m}`, (e) => (bad++, `✗ ${label}: ${e.message}`));
    console.error(msg);
  }
  if (bad) console.error(`\nFix with: bun "${import.meta.path}" login`);
  return bad ? 1 : 0;
}

async function main(cmd, arg) {
  switch (cmd) {
    case "setup":
    case "login": {
      const steps = { wordpress: loginWordPress, openai: loginOpenAI, cloudways: loginCloudways };
      const run = arg ? [steps[arg]] : Object.values(steps);
      if (run.includes(undefined)) return console.error(`Unknown key "${arg}". Use: wordpress | openai | cloudways`), 1;
      console.error("s-portal magazine: connect your keys. Input is hidden; each key is checked before it's saved.");
      let failed = 0;
      for (const step of run) if (!(await step())) failed++;
      console.error(failed ? `\n${failed} key(s) not saved. Run login again for those.` :
        "\nAll set. Restart Claude Code (or reconnect from /mcp) to pick up the keys.");
      return failed ? 1 : 0;
    }
    case "status":
      return status();
    case "logout": {
      let n = 0;
      for (const k of Object.keys(KEYS)) if (await remove(k)) n++;
      console.error(n ? `Removed ${n} key(s) from the keychain.` : "No stored keys to remove.");
      return 0;
    }
    case "headers": {
      // headersHelper: must print a JSON object; {} when a key is missing (the server then reports it).
      if (arg === "cloudways") {
        const t = await load("cloudways_token");
        console.log(JSON.stringify(t ? { "X-Access-Token": t, "X-Mcp-Host": "claude-code" } : {}));
      } else if (arg === "elementor") {
        const [u, p] = [await load("wp_user"), await load("wp_app_password")];
        console.log(JSON.stringify(u && p ? { Authorization: basic(u, p) } : {}));
      } else {
        console.log("{}");
      }
      return 0;
    }
    case "export": {
      const out = {};
      for (const k of ["wp_user", "wp_app_password", "openai_api_key"]) {
        const v = await load(k);
        if (v) out[k] = v;
      }
      console.log(JSON.stringify(out));
      return 0;
    }
    default:
      console.error("Use: login [wordpress|openai|cloudways] | status | logout");
      return 1;
  }
}

main(process.argv[2], process.argv[3]).then(
  (code) => process.exit(code),
  (e) => {
    console.error(e.message || String(e));
    process.exit(1);
  },
);
