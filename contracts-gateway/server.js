const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();

// Targets
const UI_TARGET  = process.env.UI_TARGET  || "http://127.0.0.1:3020";
const API_TARGET = process.env.API_TARGET || "http://127.0.0.1:4050";

// Basic hardening headers
app.disable("x-powered-by");

// Health endpoint for you/boss to test quickly
app.get("/health", (req, res) => {
  res.json({ ok: true, ui: UI_TARGET, api: API_TARGET });
});

// Proxy API first (so /llm/... and /upload... don't get eaten by UI)
const apiProxy = createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
  ws: true,
  xfwd: true,
  logLevel: "warn",
  // IMPORTANT: do not parse body; allow streaming for file uploads
  selfHandleResponse: false
});

// Add here any backend routes your UI calls:
app.use("/llm", apiProxy);
app.use("/upload", apiProxy);
app.use("/api", apiProxy);        // if your backend uses /api/*
app.use("/contracts", apiProxy);  // if your backend uses /contracts/*
app.use("/files", apiProxy);      // if your backend uses /files/*

// Proxy everything else to the UI dev server
app.use("/", createProxyMiddleware({
  target: UI_TARGET,
  changeOrigin: true,
  ws: true,
  xfwd: true,
  logLevel: "warn"
}));

const PORT = process.env.PORT || 8080;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Gateway running on http://127.0.0.1:${PORT}`);
  console.log(`UI -> ${UI_TARGET}`);
  console.log(`API -> ${API_TARGET}`);
});
