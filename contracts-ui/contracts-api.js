/**
 * contracts-api.js
 * Bridge between the UI and the local analysis backend (FastAPI) on http://127.0.0.1:4050.
 *
 * Exposes a global function:
 *    window.askLLM(question, context)
 * so existing UI code can call it without changes.
 */

(function () {
  const BACKEND_URL = "http://127.0.0.1:4050/llm/ask-basic";

  /**
   * Call the analysis backend.
   *
   * @param {string} question  User question.
   * @param {string} context   Contract text, if available.
   * @returns {Promise<{ok: boolean, answer: string}>}
   */
  async function askLLM(question, context) {
    try {
      const payload = {
        question: question ?? "",
        context: context ?? "",
      };

      const response = await fetch(BACKEND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        console.error("[contracts-api] HTTP error from backend:", response.status, text);
        return {
          ok: false,
          answer: `Analysis server HTTP error ${response.status}.` +
                  (text ? "\\n\\nRaw response:\\n" + text.slice(0, 400) : ""),
        };
      }

      let data;
      try {
        data = await response.json();
      } catch (e) {
        console.error("[contracts-api] Cannot parse JSON from backend:", e);
        return {
          ok: false,
          answer: "Invalid JSON from analysis server.",
        };
      }

      console.log("[contracts-api] Backend JSON:", data);

      if (!data || typeof data !== "object") {
        return {
          ok: false,
          answer: "Invalid response from analysis server.",
        };
      }

      // Prefer the 'answer' field; if empty, fall back to 'error'.
      let answerText = "";
      if (typeof data.answer === "string" && data.answer.trim().length > 0) {
        answerText = data.answer.trim();
      } else if (typeof data.error === "string" && data.error.trim().length > 0) {
        answerText = data.error.trim();
      } else {
        answerText = "The analysis server returned an empty response.";
      }

      // Treat ok !== false as success (so undefined is considered OK)
      const ok = data.ok !== false;

      return {
        ok,
        answer: answerText,
      };
    } catch (err) {
      console.error("[contracts-api] Error calling backend:", err);
      return {
        ok: false,
        answer: "Could not reach analysis server on http://127.0.0.1:4050/llm/ask-basic. " +
                "Check that the Python backend is running.",
      };
    }
  }

  // Expose the function globally so the React app can use it.
  window.askLLM = askLLM;
  window.askBackend = askLLM;
  window.contractAIAsk = askLLM;

  window.contractAI = window.contractAI || {};
  window.contractAI.ask = askLLM;

  console.log("[contracts-api] LLM bridge initialized.");
})();
