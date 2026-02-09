"use strict";

(function () {
  // ⚠️ Aquí está el backend Python que ya probaste con Invoke-RestMethod
  const BACKEND_URL = "http://127.0.0.1:4050/llm/ask-basic";

  let currentContractName = null;
  let currentContractText = "";

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function buildLayout() {
    const root = document.getElementById("app");
    if (!root) return;

    root.innerHTML = "";

    const wrapper = el(
      "div",
      "flex h-full bg-gradient-to-br from-slate-50 to-slate-100"
    );

    // ===== LEFT SIDEBAR =====
    const sidebar = el(
      "div",
      "w-80 bg-white border-r border-slate-200 flex flex-col"
    );

    const header = el("div", "p-6 border-b border-slate-200");
    const headerRow = el("div", "flex items-center gap-3 mb-4");
    const iconWrap = el("div", "p-2 bg-blue-600 rounded-lg");
    const icon = el("span", "text-white text-lg font-bold");
    icon.textContent = "📄";
    iconWrap.appendChild(icon);
    const titleBox = el("div");
    const title = el(
      "h1",
      "text-xl font-bold text-slate-800",
      "ContractAI Pro"
    );
    const subtitle = el(
      "p",
      "text-xs text-slate-500",
      "Legal Analysis System"
    );
    titleBox.appendChild(title);
    titleBox.appendChild(subtitle);
    headerRow.appendChild(iconWrap);
    headerRow.appendChild(titleBox);
    header.appendChild(headerRow);

    const uploadTitle = el(
      "h3",
      "text-sm font-semibold text-slate-700 mb-3",
      "Upload Contract (.txt recommended)"
    );
    header.appendChild(uploadTitle);

    const uploadBtn = el(
      "label",
      "w-full p-4 border-2 border-dashed border-slate-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all flex flex-col items-center gap-2 cursor-pointer"
    );
    const uploadIcon = el("span", "text-3xl", "⬆️");
    const uploadText = el(
      "span",
      "text-sm text-slate-600 font-medium",
      "Click to choose a contract"
    );
    const uploadHint = el(
      "span",
      "text-xs text-slate-400",
      "TXT works best. PDF/DOC may give noisy text."
    );
    uploadBtn.appendChild(uploadIcon);
    uploadBtn.appendChild(uploadText);
    uploadBtn.appendChild(uploadHint);

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".txt,.pdf,.doc,.docx";
    fileInput.className = "hidden";
    fileInput.id = "contract-file-input";

    header.appendChild(uploadBtn);
    header.appendChild(fileInput);

    sidebar.appendChild(header);

    const sidebarBody = el("div", "p-6 space-y-4 flex-1 overflow-y-auto");

    const activeCard = el(
      "div",
      "bg-green-50 border border-green-200 rounded-lg p-4 hidden"
    );
    activeCard.id = "active-contract-card";
    const activeTitleRow = el("div", "flex items-start justify-between mb-2");
    const activeInfo = el("div", "flex items-center gap-2");
    const activeDot = el(
      "div",
      "w-2 h-2 rounded-full bg-green-500 mt-1 flex-shrink-0"
    );
    const activeTextBox = el("div", "flex-1 min-w-0");
    const activeName = el(
      "p",
      "text-sm font-semibold text-green-800 truncate"
    );
    activeName.id = "active-contract-name";
    const activeStatus = el(
      "p",
      "text-xs text-green-600",
      "Active contract loaded"
    );
    activeTextBox.appendChild(activeName);
    activeTextBox.appendChild(activeStatus);
    activeInfo.appendChild(activeDot);
    activeInfo.appendChild(activeTextBox);
    activeTitleRow.appendChild(activeInfo);
    activeCard.appendChild(activeTitleRow);
    sidebarBody.appendChild(activeCard);

    const capabilities = el(
      "div",
      "bg-blue-50 border border-blue-200 rounded-lg p-4"
    );
    const capTitleRow = el(
      "h3",
      "text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2"
    );
    const capIcon = el("span", "", "⚙️");
    capTitleRow.appendChild(capIcon);
    capTitleRow.appendChild(document.createTextNode("AI Capabilities"));
    capabilities.appendChild(capTitleRow);
    const capList = el("ul", "text-xs text-blue-700 space-y-1");
    [
      "Risk analysis",
      "Clause review",
      "Negotiation strategy",
      "Plain-language explanations",
    ].forEach((txt) => {
      const li = el("li");
      li.textContent = "✓ " + txt;
      capList.appendChild(li);
    });
    capabilities.appendChild(capList);
    sidebarBody.appendChild(capabilities);

    sidebar.appendChild(sidebarBody);

    // ===== MAIN PANEL =====
    const main = el("div", "flex-1 flex flex-col");
    const mainHeader = el(
      "div",
      "bg-white border-b border-slate-200 p-6 flex flex-col"
    );
    const mainTitle = el(
      "h2",
      "text-2xl font-bold text-slate-800",
      "Legal AI Consultant"
    );
    const mainSub = el(
      "p",
      "text-sm text-slate-500 mt-1",
      "Upload a contract and ask questions in natural language."
    );
    mainHeader.appendChild(mainTitle);
    mainHeader.appendChild(mainSub);
    main.appendChild(mainHeader);

    const chatContainer = el(
      "div",
      "flex-1 overflow-y-auto p-6 bg-slate-50"
    );
    const chatInner = el(
      "div",
      "space-y-6 max-w-4xl mx-auto"
    );
    chatInner.id = "chat-messages";

    const welcome = el(
      "div",
      "bg-white border border-slate-200 rounded-2xl p-6 text-slate-700"
    );
    welcome.innerHTML =
      "<p class='font-semibold mb-2'>Welcome to ContractAI Pro.</p>" +
      "<p class='text-sm mb-2'>1. Upload a contract file on the left.</p>" +
      "<p class='text-sm mb-2'>2. Ask questions like:<br>" +
      "<span class='ml-3'>• What is this document about?<br>" +
      "• What are the key risks for me?<br>" +
      "• Summarize the termination clause.</span></p>" +
      "<p class='text-xs text-slate-500 mt-2'>The local model will analyze only what you load. All processing stays on this machine.</p>";
    chatInner.appendChild(welcome);

    chatContainer.appendChild(chatInner);
    main.appendChild(chatContainer);

    const inputBar = el(
      "div",
      "border-t border-slate-200 bg-white p-6"
    );
    const inputWrap = el("div", "max-w-4xl mx-auto flex gap-3");
    const input = el(
      "input",
      "flex-1 px-6 py-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
    );
    input.type = "text";
    input.placeholder = "Ask about the contract...";
    input.id = "chat-input";
    const sendBtn = el(
      "button",
      "px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 flex items-center gap-2 font-semibold",
      "Send"
    );
    sendBtn.id = "chat-send";

    inputWrap.appendChild(input);
    inputWrap.appendChild(sendBtn);
    inputBar.appendChild(inputWrap);
    main.appendChild(inputBar);

    wrapper.appendChild(sidebar);
    wrapper.appendChild(main);
    root.appendChild(wrapper);

    // ===== HANDLERS =====
    uploadBtn.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        currentContractName = file.name;
        currentContractText = text;

        activeName.textContent = file.name;
        activeCard.classList.remove("hidden");

        addAssistantMessage(
          `Contract "${file.name}" loaded. Ask me about clauses, risks, obligations, or a high-level summary.`
        );
      } catch (err) {
        console.error("Error reading file", err);
        addAssistantMessage(
          "I couldn't read that file. TXT works best; PDF/DOC may need conversion to text."
        );
      }
    });

    async function handleSend() {
      const q = input.value.trim();
      if (!q) return;
      input.value = "";
      addUserMessage(q);

      const payload = { question: q };
      if (currentContractText && currentContractText.trim().length > 0) {
        payload.context = currentContractText;
      } else {
        payload.context =
          "No contract file was loaded. Answer in general legal terms for contracts.";
      }

      const typingId = addAssistantMessage("Analyzing...", true);

      try {
        const resp = await fetch(BACKEND_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json; charset=utf-8",
          },
          body: JSON.stringify(payload),
        });

        let data;
        try {
          data = await resp.json();
        } catch {
          const raw = await resp.text();
          console.error("Non-JSON response from backend:", raw);
          replaceAssistantMessage(
            typingId,
            "Backend returned non-JSON response. Check the Python server console."
          );
          return;
        }

        if (!resp.ok || !data || data.ok === false) {
          console.error("Backend error", resp.status, data);
          replaceAssistantMessage(
            typingId,
            "The analysis server reported an error: " +
              (data && (data.error || data.detail) ? data.error || data.detail : "Unknown error.")
          );
          return;
        }

        replaceAssistantMessage(
          typingId,
          typeof data.answer === "string" && data.answer.trim().length > 0
            ? data.answer
            : "The model returned an empty answer."
        );
      } catch (err) {
        console.error("Error calling backend", err);
        replaceAssistantMessage(
          typingId,
          "Could not reach the analysis server at " + BACKEND_URL + ". Is the Python backend running?"
        );
      }
    }

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });

    function appendMessage(role, text) {
      const row = el("div", "flex gap-4" + (role === "user" ? " justify-end" : ""));
      if (role === "assistant") {
        const avatar = el(
          "div",
          "w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0"
        );
        const icon = el("span", "text-white text-sm", "AI");
        avatar.appendChild(icon);
        row.appendChild(avatar);
      }
      const bubbleWrap = el("div", role === "user" ? "max-w-2xl" : "flex-1");
      const bubble = el(
        "div",
        "rounded-2xl p-4 text-sm " +
          (role === "user"
            ? "bg-blue-600 text-white ml-auto"
            : "bg-white border border-slate-200 text-slate-800")
      );
      bubble.textContent = text;
      bubbleWrap.appendChild(bubble);
      row.appendChild(bubbleWrap);
      chatInner.appendChild(row);
      chatInner.scrollTop = chatInner.scrollHeight;
      chatContainer.scrollTop = chatContainer.scrollHeight;
      return row;
    }

    function addUserMessage(text) {
      appendMessage("user", text);
    }

    function addAssistantMessage(text, isTyping) {
      const row = appendMessage("assistant", text);
      const id = Date.now().toString() + Math.random().toString(16).slice(2);
      row.dataset.messageId = id;
      if (isTyping) {
        const bubble = row.querySelector("div div");
        if (bubble) bubble.classList.add("opacity-70");
      }
      return id;
    }

    function replaceAssistantMessage(id, newText) {
      const node = chatInner.querySelector(`[data-message-id="${id}"]`);
      if (!node) {
        addAssistantMessage(newText);
        return;
      }
      const bubble = node.querySelector("div div");
      if (bubble) {
        bubble.textContent = newText;
        bubble.classList.remove("opacity-70");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", buildLayout);
})();
