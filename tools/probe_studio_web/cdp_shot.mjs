// Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
// 探針(probe)の撮影係: headless Chrome を DevTools protocol で動かし、ページが「出来た」と言うまで待って撮る。
//   node cdp_shot.mjs <chrome.exe> <url> <out.png> <ready JS 式> [timeout ms] [脚本 JS(撮る前に評価)] [幅] [高さ]
// --screenshot は WebAssembly の読み込みを待たないので(2 秒で撮れてしまう)、window.__ready 相当の式を自分で待つ。
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, out, readyExpr, timeoutArg, script, wArg, hArg] = process.argv.slice(2);
const timeout = Number(timeoutArg || 120000);
const W = Number(wArg || 1400), H = Number(hArg || 800);
const port = 9333 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "cdp-shot-"));
const proc = spawn(chrome, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
  `--user-data-dir=${profile}`, `--remote-debugging-port=${port}`, `--window-size=${W},${H}`, "about:blank"],
  { stdio: "ignore" });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let rc = 1;
try {
  let targets = null;
  for (let i = 0; i < 100 && !targets; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch { await sleep(200); }
  }
  if (!targets) throw new Error("chrome の DevTools に繋がらない");
  const page = targets.find(t => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = new Map();
  const events = [];
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    else if (m.method === "Runtime.exceptionThrown") events.push("EXC " + JSON.stringify(m.params.exceptionDetails).slice(0, 1500));
    else if (m.method === "Runtime.consoleAPICalled") events.push(m.params.type + " " + m.params.args.map(a => a.value ?? a.description ?? "").join(" ").slice(0, 600)); };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const evalJs = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send("Page.enable"); await send("Runtime.enable");
  const t0 = Date.now();
  await send("Page.navigate", { url });
  let ready = false;
  while (Date.now() - t0 < timeout) {
    try { ready = !!(await evalJs(readyExpr)); } catch { ready = false; }
    if (ready) break;
    await sleep(250);
  }
  const waited = Date.now() - t0;
  if (!ready) {
    const body = await evalJs("document.body ? document.body.innerText.slice(0, 3000) : ''");
    const shot0 = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(out.replace(/\.png$/, "_timeout.png"), Buffer.from(shot0.result.data, "base64"));
    throw new Error(`ready 式が ${timeout} ms 以内に真にならない: ${readyExpr}\n--- page text ---\n${body}\n--- console / exceptions ---\n${events.slice(-30).join("\n")}`);
  }
  let scriptResult = null;
  if (script) { scriptResult = await evalJs(script); await sleep(300); }
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(out, Buffer.from(shot.result.data, "base64"));
  const info = await evalJs("JSON.stringify(window.__probe || (window.__state && {ready: window.__state.ready, timings: window.__state.timings, nops: window.__state.nops, image: window.__state.image, last_run: window.__state.last_run, error: window.__state.error}) || null)");
  console.log(JSON.stringify({ out, waited_ms: waited, script_result: scriptResult, page_state: info ? JSON.parse(info) : null }));
  ws.close();
  rc = 0;
} catch (e) {
  console.error("cdp_shot:", e.message || e);
} finally {
  proc.kill();
  await sleep(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
process.exit(rc);
