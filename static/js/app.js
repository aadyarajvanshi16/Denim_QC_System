// =====================================================
// THEME
// =====================================================
(function () {
  const saved = localStorage.getItem("theme");
  if (saved === "light") document.body.classList.add("light-mode");

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("themeToggle");
    if (btn) {
      btn.addEventListener("click", () => {
        document.body.classList.toggle("light-mode");
        localStorage.setItem(
          "theme",
          document.body.classList.contains("light-mode") ? "light" : "dark"
        );
      });
    }

    const navToggle = document.getElementById("navToggle");
    const navLinks = document.getElementById("navLinks");
    if (navToggle && navLinks) {
      navToggle.addEventListener("click", () => navLinks.classList.toggle("open"));
    }
  });
})();

// =====================================================
// CSRF-AWARE FETCH
// =====================================================
function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

/**
 * fetchWithCsrf(url, options) — same signature as fetch(), but
 * automatically attaches the CSRF token header for POST/PUT/DELETE.
 */
function fetchWithCsrf(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    options.headers = Object.assign({}, options.headers, {
      "X-CSRFToken": csrfToken(),
    });
  }
  return fetch(url, options);
}

// =====================================================
// DESTRUCTIVE ACTION CONFIRMATION
// =====================================================
/**
 * confirmAction(message) -> Promise<boolean>
 * Renders a small modal instead of the browser's native confirm()
 * so styling stays consistent, and returns a promise resolved with
 * the user's choice.
 */
function confirmAction(message) {
  return new Promise((resolve) => {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal">
        <h3>Are you sure?</h3>
        <p class="text-muted">${message}</p>
        <div class="modal-actions">
          <button class="btn btn-ghost" data-choice="cancel">Cancel</button>
          <button class="btn btn-danger" data-choice="confirm">Confirm</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);

    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        backdrop.remove();
        resolve(false);
      }
      const choice = e.target.getAttribute("data-choice");
      if (choice) {
        backdrop.remove();
        resolve(choice === "confirm");
      }
    });
  });
}

/**
 * Wire up any <form data-confirm="..."> so it shows the confirmation
 * modal before submitting (used for delete user / delete report /
 * revoke access).
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      if (form.dataset.confirmed === "true") return;
      e.preventDefault();
      const ok = await confirmAction(form.dataset.confirm);
      if (ok) {
        form.dataset.confirmed = "true";
        form.submit();
      }
    });
  });
});
