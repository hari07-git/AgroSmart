(function () {
  async function autofillWeather() {
    const btn = document.querySelector("[data-weather='autofill']");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "Loading...";
      try {
        const res = await fetch("/api/weather/current", { credentials: "same-origin" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to fetch weather");

        const t = document.querySelector("input[name='temperature']");
        const h = document.querySelector("input[name='humidity']");
        const r = document.querySelector("input[name='rainfall']");
        if (t && data.temperature_c != null) t.value = data.temperature_c;
        if (h && data.humidity_pct != null) h.value = data.humidity_pct;
        if (r) r.value = data.rain_3h_mm || data.rain_1h_mm || 0;

        const note = document.querySelector("[data-weather='note']");
        if (note) note.textContent = `Filled from OpenWeather for ${data.location}`;
      } catch (err) {
        const note = document.querySelector("[data-weather='note']");
        if (note) note.textContent = String(err.message || err);
      } finally {
        btn.disabled = false;
        btn.textContent = "Auto-fill weather";
      }
    });
  }
  document.addEventListener("DOMContentLoaded", autofillWeather);
})();
