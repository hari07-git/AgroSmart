(() => {
  const btn = document.querySelector("[data-chatbot-toggle]");
  const panel = document.querySelector("[data-chatbot-panel]");
  const form = document.querySelector("[data-chatbot-form]");
  const input = document.querySelector("[data-chatbot-input]");
  const msgs = document.querySelector("[data-chatbot-messages]");
  const quick = document.querySelectorAll("[data-chatbot-quick]");

  if (!btn || !panel || !form || !input || !msgs) return;

  const addMsg = (role, text) => {
    const el = document.createElement("div");
    el.className = "chatbot-msg chatbot-" + role;
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  };

  const setOpen = (open) => {
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      setTimeout(() => input.focus(), 0);
      if (!msgs.dataset.welcomed) {
        msgs.dataset.welcomed = "1";
        addMsg(
          "bot",
          "Hi. Ask me about Crop Recommendation, Fertilizer Guidance, Disease Detection, OTP, exports, language. For deep help: agrosmartz7@gmail.com."
        );
      }
    }
  };

  btn.addEventListener("click", () => setOpen(panel.hidden));

  for (const q of quick) {
    q.addEventListener("click", () => {
      const text = q.getAttribute("data-chatbot-quick") || "";
      if (!text) return;
      setOpen(true);
      input.value = text;
      form.requestSubmit();
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = (input.value || "").trim();
    if (!text) return;
    input.value = "";
    addMsg("user", text);

    try {
      const res = await fetch("/api/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json().catch(() => ({}));
      addMsg("bot", (data && data.reply) || "Sorry, I could not answer that. Contact agrosmartz7@gmail.com.");
    } catch (_err) {
      addMsg("bot", "Network error. Please try again. For help: agrosmartz7@gmail.com.");
    }
  });

  // Start closed by default.
  setOpen(false);
})();

