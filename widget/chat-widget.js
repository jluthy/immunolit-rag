// widget/chat-widget.js
(function () {
  function renderMessage(container, role, content, citations) {
    const el = document.createElement("div");
    el.className = `immunolit-chat__message immunolit-chat__message--${role}`;
    el.textContent = content;
    if (citations && citations.length) {
      const cite = document.createElement("div");
      cite.className = "immunolit-chat__citations";
      cite.textContent = "Sources: " + citations.map((p) => `PMID ${p}`).join(", ");
      el.appendChild(cite);
    }
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  window.initImmunolitChat = function (containerId, apiBaseUrl) {
    const root = document.getElementById(containerId);
    root.className = "immunolit-chat";

    const messages = document.createElement("div");
    messages.className = "immunolit-chat__messages";
    root.appendChild(messages);

    const row = document.createElement("div");
    row.className = "immunolit-chat__input-row";
    const input = document.createElement("input");
    input.placeholder = "Ask about the immunology literature in this corpus...";
    const button = document.createElement("button");
    button.textContent = "Ask";
    row.appendChild(input);
    row.appendChild(button);
    root.appendChild(row);

    async function send() {
      const query = input.value.trim();
      if (!query) return;
      renderMessage(messages, "user", query);
      input.value = "";
      button.disabled = true;
      try {
        const resp = await fetch(`${apiBaseUrl}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });
        if (!resp.ok) throw new Error("backend unavailable");
        const data = await resp.json();
        renderMessage(messages, "bot", data.answer, data.citations);
        if (window.__immunolitHighlightPmids) {
          window.__immunolitHighlightPmids(data.citations);
        }
      } catch (err) {
        renderMessage(messages, "bot", "Sorry, the backend is warming up or unavailable. Please try again in a moment.");
      } finally {
        button.disabled = false;
      }
    }

    button.addEventListener("click", send);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  };
})();
