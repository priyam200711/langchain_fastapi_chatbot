document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");
  const sessionIdInput = document.getElementById("session-id-input");
  const systemPromptInput = document.getElementById("system-prompt-input");
  const streamToggle = document.getElementById("stream-toggle");
  const webSearchToggle = document.getElementById("web-search-toggle");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const modelName = document.getElementById("model-name");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const welcomeBox = document.getElementById("welcome-box");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  const sessionsList = document.getElementById("sessions-list");

  let isGenerating = false;

  // Toggle mobile sidebar
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Auto-resize textarea
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
  });

  // Handle enter key submit
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isGenerating && chatInput.value.trim().length > 0) {
        chatForm.dispatchEvent(new Event("submit"));
      }
    }
  });

  // Prompt chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        chatInput.value = prompt;
        chatInput.dispatchEvent(new Event("input"));
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  });

  // Check health and model status
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error("Healthcheck failed");
      const data = await res.json();
      
      statusDot.className = "dot online";
      if (data.provider === "ollama") {
        statusText.textContent = "Local Ollama Active";
      } else if (data.hf_token_configured) {
        statusText.textContent = "Hugging Face Connected";
      } else {
        statusText.textContent = "Token Missing (.env)";
        statusDot.className = "dot"; // Amber warning
      }
      modelName.textContent = data.model || "Unknown";
    } catch (err) {
      statusDot.className = "dot offline";
      statusText.textContent = "Server Offline";
      modelName.textContent = "Unavailable";
    }
  }

  // Load all historical sessions for the sidebar list
  async function loadSessionsList() {
    if (!sessionsList) return;
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) return;
      const data = await res.json();
      const currentId = sessionIdInput.value.trim() || "default";

      if (!data.sessions || data.sessions.length === 0) {
        sessionsList.innerHTML = '<div class="no-sessions">No previous chats yet</div>';
        return;
      }

      sessionsList.innerHTML = "";
      data.sessions.forEach((s) => {
        const item = document.createElement("div");
        item.className = `session-item ${s.session_id === currentId ? "active" : ""}`;
        item.setAttribute("data-session-id", s.session_id);

        const contentDiv = document.createElement("div");
        contentDiv.className = "session-item-content";
        contentDiv.innerHTML = `<i class="fa-regular fa-message"></i><span class="session-item-title">${s.title || s.session_id}</span>`;

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete-session-btn";
        deleteBtn.title = "Delete this conversation";
        deleteBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';

        deleteBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (confirm(`Delete conversation "${s.title || s.session_id}"?`)) {
            await fetch(`/api/history/${encodeURIComponent(s.session_id)}`, { method: "DELETE" });
            if (sessionIdInput.value.trim() === s.session_id) {
              sessionIdInput.value = "default";
              messagesContainer.innerHTML = "";
              if (welcomeBox) welcomeBox.style.display = "block";
            }
            loadSessionsList();
          }
        });

        item.appendChild(contentDiv);
        item.appendChild(deleteBtn);

        item.addEventListener("click", () => {
          sessionIdInput.value = s.session_id;
          document.querySelectorAll(".session-item").forEach((el) => el.classList.remove("active"));
          item.classList.add("active");
          messagesContainer.innerHTML = "";
          loadHistory(s.session_id);
        });

        sessionsList.appendChild(item);
      });
    } catch (err) {
      console.warn("Could not load sessions list:", err);
    }
  }

  // Load conversation history for current session
  async function loadHistory(sessionId) {
    try {
      const res = await fetch(`/api/history/${encodeURIComponent(sessionId)}`);
      if (!res.ok) return;
      const data = await res.json();
      
      messagesContainer.innerHTML = "";
      if (data.messages && data.messages.length > 0) {
        if (welcomeBox) welcomeBox.style.display = "none";
        data.messages.forEach((msg) => {
          appendMessage(msg.role, msg.content, false);
        });
        scrollToBottom();
      } else {
        if (welcomeBox) welcomeBox.style.display = "block";
      }
    } catch (err) {
      console.warn("Could not load history:", err);
    }
  }

  // Helper to append message bubble
  function appendMessage(role, text = "", animate = false) {
    if (welcomeBox && welcomeBox.style.display !== "none") {
      welcomeBox.style.display = "none";
    }

    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = `message-avatar ${role === "user" ? "user-avatar" : "bot-avatar"}`;
    avatar.innerHTML = role === "user" 
      ? '<i class="fa-solid fa-user"></i>' 
      : '<i class="fa-solid fa-robot"></i>';

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "assistant") {
      bubble.innerHTML = renderMarkdown(text);
    } else {
      bubble.textContent = text;
    }

    if (role === "user") {
      row.appendChild(bubble);
      row.appendChild(avatar);
    } else {
      row.appendChild(avatar);
      row.appendChild(bubble);
    }

    messagesContainer.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  function renderMarkdown(content) {
    if (window.marked && typeof window.marked.parse === "function") {
      return window.marked.parse(content);
    }
    // Fallback: basic escape and line breaks
    return content
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br/>");
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Clear memory
  clearChatBtn.addEventListener("click", async () => {
    const sessionId = sessionIdInput.value.trim() || "default";
    if (confirm(`Reset conversation history for session '${sessionId}'?`)) {
      try {
        await fetch(`/api/history/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
        messagesContainer.innerHTML = "";
        if (welcomeBox) welcomeBox.style.display = "block";
        loadSessionsList();
      } catch (err) {
        alert("Failed to clear history: " + err.message);
      }
    }
  });

  // New Chat session
  newChatBtn.addEventListener("click", () => {
    const newId = "session_" + Math.random().toString(36).substring(2, 9);
    sessionIdInput.value = newId;
    document.querySelectorAll(".session-item").forEach((el) => el.classList.remove("active"));
    messagesContainer.innerHTML = "";
    if (welcomeBox) welcomeBox.style.display = "block";
    chatInput.focus();
  });

  // Session input change
  sessionIdInput.addEventListener("change", () => {
    const sessionId = sessionIdInput.value.trim() || "default";
    messagesContainer.innerHTML = "";
    if (welcomeBox) welcomeBox.style.display = "block";
    loadHistory(sessionId);
    loadSessionsList();
  });

  // Chat Form Submit
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message || isGenerating) return;

    const sessionId = sessionIdInput.value.trim() || "default";
    const systemPrompt = systemPromptInput.value.trim() || null;
    const useStreaming = streamToggle.checked;

    // Add user message to UI
    appendMessage("user", message);
    chatInput.value = "";
    chatInput.style.height = "auto";
    isGenerating = true;
    sendBtn.disabled = true;

    // Create assistant bubble
    const botBubble = appendMessage("assistant", "Thinking...");

    if (useStreaming) {
      // SSE Streaming Mode
      try {
        const response = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: message,
            session_id: sessionId,
            system_prompt: systemPrompt,
            use_web_search: webSearchToggle ? webSearchToggle.checked : true,
          }),
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let accumulatedText = "";
        let buffer = "";

        botBubble.innerHTML = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const parsed = JSON.parse(jsonStr);
                if (parsed.chunk) {
                  accumulatedText += parsed.chunk;
                  botBubble.innerHTML = renderMarkdown(accumulatedText);
                  scrollToBottom();
                } else if (parsed.error) {
                  accumulatedText += `\n\n⚠️ *Error: ${parsed.error}*`;
                  botBubble.innerHTML = renderMarkdown(accumulatedText);
                }
              } catch (e) {
                console.error("JSON parse error:", e, jsonStr);
              }
            }
          }
        }
      } catch (err) {
        botBubble.innerHTML = renderMarkdown(`⚠️ **Error:** ${err.message}`);
      } finally {
        isGenerating = false;
        sendBtn.disabled = false;
        chatInput.focus();
        loadSessionsList();
      }
    } else {
      // Standard JSON Mode
      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: message,
            session_id: sessionId,
            system_prompt: systemPrompt,
            use_web_search: webSearchToggle ? webSearchToggle.checked : true,
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        botBubble.innerHTML = renderMarkdown(data.reply);
      } catch (err) {
        botBubble.innerHTML = renderMarkdown(`⚠️ **Error:** ${err.message}`);
      } finally {
        isGenerating = false;
        sendBtn.disabled = false;
        chatInput.focus();
        scrollToBottom();
        loadSessionsList();
      }
    }
  });

  // Initial loads
  checkHealth();
  loadSessionsList();
  loadHistory(sessionIdInput.value.trim() || "default");
  // Periodically refresh health status every 30s
  setInterval(checkHealth, 30000);
});
