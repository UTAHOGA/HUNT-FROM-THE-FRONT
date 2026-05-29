(() => {
  "use strict";

  function isResearchPage() {
    const path = String(window.location.pathname || "").toLowerCase();
    return path.endsWith("/research.html") || path.endsWith("research.html");
  }

  function getSelectedHuntCode() {
    const params = new URLSearchParams(window.location.search);
    return (
      params.get("hunt_code") ||
      localStorage.getItem("selected_hunt_code") ||
      ""
    ).trim().toUpperCase();
  }

  function init() {
    if (!isResearchPage()) return;

    const huntCode = getSelectedHuntCode();
    const detailContent = document.getElementById("detailContent");
    const parent =
      detailContent?.parentElement ||
      document.querySelector(".result-card .card-body") ||
      document.querySelector(".main-stack");

    if (!parent) return;

    let panel = document.getElementById("uogaApplicationOutlookDashboard");
    if (!panel) {
      panel = document.createElement("section");
      panel.id = "uogaApplicationOutlookDashboard";
      panel.style.marginTop = "16px";
      panel.style.padding = "14px";
      panel.style.border = "1px solid rgba(170,124,84,.35)";
      panel.style.borderRadius = "18px";
      panel.style.background = "rgba(255,255,255,.05)";
      panel.style.color = "var(--text)";
      parent.appendChild(panel);
    }

    panel.innerHTML = `
      <h3 style="margin:0 0 8px;font-family:var(--font-display);">
        Hunt Application Outlook
      </h3>
      <p style="margin:0;color:var(--research-muted);">
        ${huntCode
          ? `Dashboard add-on loaded for ${huntCode}.`
          : "Select a hunt from Hunt Builder to view its application outlook."}
      </p>
    `;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();