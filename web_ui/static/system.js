/** Start Beast — one-click system launcher UI */

async function fetchJson(url, opts) {
  const res = await fetch(url, opts);
  return res.json();
}

async function refreshBeastStatus() {
  const el = document.getElementById("beastStatus");
  if (!el) return;
  try {
    const st = await fetchJson("/api/system/status");
    const bot = st.bot ? "🤖 Bot ON" : "🤖 Bot OFF";
    const review = st.review_built ? "🃏 Review OK" : "🃏 Review build missing";
    el.textContent = `${bot} · ${review}`;
  } catch {
    el.textContent = "Server offline";
  }
}

async function startBeast() {
  const btn = document.getElementById("startBeastBtn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Starting…";
  }
  try {
    const result = await fetchJson("/api/system/start-beast", { method: "POST" });
    if (!result.ok) {
      alert(result.error || "Could not start system.");
      return;
    }
    let msg = result.message || "Beast started!";
    if (result.warning) msg += "\n\n" + result.warning;
    if (result.links) {
      msg += "\n\nOpen:\n• Calendar: " + result.links.home;
      msg += "\n• Feed: " + result.links.feed;
      msg += "\n• Swipe Review: " + result.links.review;
    }
    alert(msg);
    if (result.links && result.links.review && !window.location.pathname.startsWith("/review")) {
      const go = confirm("Open Swipe Review now?");
      if (go) window.location.href = result.links.review;
    }
  } catch (e) {
    alert("Start Beast failed. Is the server running?\n\nRun: PORT=56823 python3 web_ui/app.py");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Start Beast";
    }
    refreshBeastStatus();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("startBeastBtn");
  if (btn) btn.addEventListener("click", startBeast);
  refreshBeastStatus();
  setInterval(refreshBeastStatus, 15000);
});
