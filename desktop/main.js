const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

let procs = [];

function run(cmd, args, cwd) {
  const p = spawn(cmd, args, { cwd, stdio: "inherit" });
  procs.push(p);
  return p;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
  });
  win.loadURL("http://127.0.0.1:8080");
}

app.whenReady().then(() => {
  const root = path.resolve(__dirname, "..");
  const llm = path.join(root, "contracts-llm");
  const ui  = path.join(root, "contracts-ui");
  const gw  = path.join(root, "contracts-gateway");

  // NOTE: In the DMG build we will run a packaged backend start script for mac
  // For now, we just open the window; the build workflow will ensure mac backend start exists.
  createWindow();
});

app.on("window-all-closed", () => {
  procs.forEach(p => { try { p.kill(); } catch(e){} });
  if (process.platform !== "darwin") app.quit();
});
