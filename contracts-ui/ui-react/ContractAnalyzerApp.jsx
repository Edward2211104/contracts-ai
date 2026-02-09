import React, { useState } from "react";

const LLM_API_URL = "http://127.0.0.1:4050/llm/ask-basic";

export default function ContractAnalyzerApp() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "ai",
      text:
        "Hi, I am your contract analysis assistant. Upload a contract on the left and ask me anything you want to understand, summarize, or negotiate.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function sendMessage() {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage = {
      id: Date.now(),
      sender: "user",
      text: trimmed,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(LLM_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          // Si en el futuro pasamos contexto del contrato, va aquí.
          context: "",
        }),
      });

      let answerText;
      if (!response.ok) {
        answerText = `I couldn't reach the analysis server (status ${response.status}). Please check that the backend is running on port 4050.`;
      } else {
        // Nuestro backend devuelve TEXTO PLANO (no JSON)
        answerText = await response.text();
        if (!answerText || !answerText.trim()) {
          answerText =
            "I couldn't generate a useful answer for that question. Try asking it in a different way.";
        }
      }

      const aiMessage = {
        id: Date.now() + 1,
        sender: "ai",
        text: answerText,
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      console.error("Error calling LLM backend:", err);
      const aiMessage = {
        id: Date.now() + 1,
        sender: "ai",
        text:
          "There was a connection error talking to the analysis server. Make sure the backend (llm_proxy.py) is running on port 4050.",
      };
      setMessages((prev) => [...prev, aiMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={
              "chat-message " +
              (msg.sender === "ai" ? "chat-message-ai" : "chat-message-user")
            }
          >
            {msg.text}
          </div>
        ))}
        {isLoading && (
          <div className="chat-message chat-message-ai">
            Analyzing the contract...
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Ask about the contract..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
        />
        <button
          className="chat-send-button"
          onClick={sendMessage}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? "Analyzing..." : "Send"}
        </button>
      </div>
    </div>
  );
}
