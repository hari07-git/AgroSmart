(function () {
  function langToSpeech(lang) {
    if (lang === "hi") return "hi-IN";
    if (lang === "te") return "te-IN";
    return "en-IN";
  }

  function getLang() {
    const select = document.querySelector('select[name="lang"]');
    return select ? select.value : "en";
  }

  function stopSpeaking() {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
  }

  function speakText(text) {
    if (!("speechSynthesis" in window)) return;
    stopSpeaking();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langToSpeech(getLang());
    window.speechSynthesis.speak(utter);
  }

  document.addEventListener("click", (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.matches("[data-voice='speak']")) {
      const selector = target.getAttribute("data-voice-target");
      if (!selector) return;
      const el = document.querySelector(selector);
      if (!el) return;
      speakText(el.textContent || "");
    }
    if (target.matches("[data-voice='stop']")) stopSpeaking();
  });
})();
