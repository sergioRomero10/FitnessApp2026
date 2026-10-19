// FitnessApp 2.0 — JavaScript mínimo, sin jQuery.
// Mejora progresiva: si el JS falla, los formularios siguen funcionando con recarga normal.

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

function showToast(message, variant = "dark") {
  const container = document.getElementById("toasts");
  if (!container || !window.bootstrap) return;
  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${variant} border-0`;
  el.setAttribute("role", "status");
  el.innerHTML = `<div class="d-flex"><div class="toast-body"></div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
  el.querySelector(".toast-body").textContent = message; // textContent: nunca se interpreta como HTML
  container.appendChild(el);
  el.addEventListener("hidden.bs.toast", () => el.remove());
  new bootstrap.Toast(el, { delay: 2500 }).show();
}

// Estrella de favoritos sin recargar la página
document.addEventListener("submit", async (event) => {
  const form = event.target.closest(".js-fav-form");
  if (!form) return;
  event.preventDefault();

  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken },
    });
    if (response.status === 401) {
      const data = await response.json();
      window.location.href = `${data.login_url}?next=${encodeURIComponent(location.pathname + location.search)}`;
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const { favorite } = await response.json();
    button.classList.toggle("is-fav", favorite);
    button.setAttribute("aria-pressed", String(favorite));
    button.title = favorite ? "Remove from favourites" : "Add to favourites";
    button.querySelector("i").className = `bi ${favorite ? "bi-star-fill" : "bi-star"}`;
    showToast(favorite ? "Added to favourites" : "Removed from favourites");
  } catch (error) {
    console.error(error);
    showToast("Could not update favourites. Try again.", "danger");
  } finally {
    button.disabled = false;
  }
});

// Confirmación antes de acciones destructivas (borrar dieta...)
document.addEventListener("submit", (event) => {
  const message = event.target.dataset?.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
