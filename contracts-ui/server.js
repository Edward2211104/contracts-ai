/**
 * CLEAN CONTRACTS-AI SERVER v2
 * - Contract storage in data/contracts.json
 * - Endpoints:
 *   GET    /api/contracts
 *   POST   /api/contracts
 *   DELETE /api/contracts/:id
 *   POST   /api/llm/ask-v2
 *   POST   /ask-doc-ui
 */

import express from "express";
import path from "path";
import fs from "fs/promises";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

// --- Basic config ---
const app  = express();
const PORT = process.env.PORT || 3020;
const LLM_API_URL = process.env.LLM_API_URL || "http://127.0.0.1:4050";

// --- Middlewares ---
app.use(express.json({ limit: "20mb" }));
app.use(express.urlencoded({ extended: true }));

app.use((req, _res, next) => {
  console.log(`[REQ] ${req.method} ${req.url}`);
  next();
});

// Serve static UI
app.use(express.static(path.join(__dirname, "public")));

// --- Contracts helpers ---
const CONTRACTS_FILE = path.join(__dirname, "data", "contracts.json");

async function loadContracts() {
  try {
    const json = await fs.readFile(CONTRACTS_FILE, "utf8");
    return JSON.parse(json);
  } catch (err) {
    if (err.code === "ENOENT") return [];
    console.error("Error reading contracts file", err);
    return [];
  }
}

async function saveContracts(contracts) {
  try {
    await fs.mkdir(path.dirname(CONTRACTS_FILE), { recursive: true });
    await fs.writeFile(CONTRACTS_FILE, JSON.stringify(contracts, null, 2), "utf8");
  } catch (err) {
    console.error("Error writing contracts file", err);
  }
}

// --- API: GET /api/contracts ---
app.get("/api/contracts", async (_req, res) => {
  const contracts = await loadContracts();
  res.json({ ok: true, contracts });
});

// --- API: POST /api/contracts ---
app.post("/api/contracts", async (req, res) => {
  try {
    const b = req.body || {};

    const name = b.name || b.contractName || "";
    if (!name.trim()) {
      return res.status(400).json({
        ok: false,
        error: "Please provide at least a contract name."
      });
    }

    const now = new Date().toISOString();
    const id  = b.id || Date.now().toString();

    const contract = {
      id,
      source:     b.source       || "manual",
      name,
      contractor: b.contractor   || b.contractorName || "",
      type:       b.type         || b.contractType   || "",
      phone:      b.phone        || "",
      start:      b.start        || b.startDate      || "",
      end:        b.end          || b.endDate        || "",
      total:      Number(b.total ?? b.totalCost ?? 0) || 0,
      due:        b.due          || "< 7 days",
      pdfFile:    b.pdfFile      || b.pdfFileName    || "",
      contractText: (b.contractText || "").toString(),
      createdAt:  now,
      updatedAt:  now
    };

    const contracts = await loadContracts();
    const filtered  = contracts.filter(c => String(c.id) !== String(id));
    filtered.push(contract);
    await saveContracts(filtered);

    res.json({ ok: true, contract });
  } catch (err) {
    console.error("Error in POST /api/contracts", err);
    res.status(500).json({
      ok: false,
      error: "Failed to save contract",
      detail: String(err)
    });
  }
});

// --- API: DELETE /api/contracts/:id ---
app.delete("/api/contracts/:id", async (req, res) => {
  const { id } = req.params;
  try {
    const contracts = await loadContracts();
    const filtered  = contracts.filter(c => String(c.id) !== String(id));
    await saveContracts(filtered);
    res.json({ ok: true });
  } catch (err) {
    console.error("Error in DELETE /api/contracts/:id", err);
    res.status(500).json({
      ok: false,
      error: "Failed to delete contract",
      detail: String(err)
    });
  }
});

// --- LLM call helper ---
async function callLlm(question, contractText, extraContext = "") {
  const payload = {
    question: (question || "").toString(),
    contractText: (contractText || "").toString(),
    extraContext: (extraContext || "").toString()
  };

  const resp = await fetch(`${LLM_API_URL}/llm/ask-basic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`LLM HTTP ${resp.status}: ${text}`);
  }

  const data = await resp.json();
  return data.answer ?? data;
}

// --- API: POST /api/llm/ask-v2 (raw access for tests) ---
app.post("/api/llm/ask-v2", async (req, res) => {
  try {
    const body = req.body || {};
    const answer = await callLlm(
      body.question || "",
      body.contractText || "",
      body.extraContext || ""
    );
    res.json({ ok: true, answer });
  } catch (err) {
    console.error("Error in /api/llm/ask-v2", err);
    res.status(500).json({
      ok: false,
      error: "Unexpected error contacting the LLM.",
      detail: String(err)
    });
  }
});

// --- Build text for LLM from a stored contract ---
function buildContractText(contract) {
  if (contract && contract.contractText && contract.contractText.trim().length > 0) {
    return contract.contractText;
  }

  // Fallback: structured summary (cuando no hay texto)
  const parts = [];
  parts.push("Structured contract metadata:");

  if (contract.source)     parts.push(`Source: ${contract.source}`);
  if (contract.name)       parts.push(`Name: ${contract.name}`);
  if (contract.contractor) parts.push(`Contractor: ${contract.contractor}`);
  if (contract.type)       parts.push(`Type: ${contract.type}`);
  if (contract.phone)      parts.push(`Phone: ${contract.phone}`);
  if (contract.start)      parts.push(`Start date: ${contract.start}`);
  if (contract.end)        parts.push(`End date: ${contract.end}`);
  if (contract.total)      parts.push(`Total amount (USD): ${contract.total}`);
  if (contract.due)        parts.push(`Due status: ${contract.due}`);
  if (contract.pdfFile)    parts.push(`PDF file: ${contract.pdfFile}`);

  parts.push("Note: No full clause text was provided, only structured metadata.");
  return parts.join(" - ");
}

// --- API: POST /ask-doc-ui (UI main endpoint) ---
app.post("/ask-doc-ui", async (req, res) => {
  try {
    const body = req.body || {};
    const question   = (body.question || "").toString();
    const contractId = body.contractId ? body.contractId.toString() : "";

    if (!question.trim()) {
      return res.status(400).json({ ok: false, error: "Missing question." });
    }

    const contracts = await loadContracts();
    const contract  = contracts.find(c => String(c.id) === contractId);

    const contractText = contract ? buildContractText(contract) : "";
    const extraContext = contract
      ? `This question is about the contract "${contract.name}" with id ${contract.id}.`
      : "No contract was found for this question.";

    const answer = await callLlm(question, contractText, extraContext);

    res.json({
      ok: true,
      answer,
      usedContractId: contract ? contract.id : null,
      hasFullText: !!(contract && contract.contractText && contract.contractText.trim())
    });
  } catch (err) {
    console.error("Error in /ask-doc-ui", err);
    res.status(500).json({
      ok: false,
      error: "Unexpected error contacting the LLM.",
      detail: String(err)
    });
  }
});

// --- SPA fallback ---
app.get("*", (_req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// --- Start server ---
app.listen(PORT, () => {
  console.log(`Contracts-AI server v2 listening on http://localhost:${PORT}`);
  console.log("LLM API URL:", LLM_API_URL);
});

