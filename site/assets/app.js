// Small enhancements; every page works without this file.
(() => {
  const base = document.body.dataset.base || "/";
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };

  // Home: the role switch picks where city links go.
  const home = !!document.querySelector(".hero");
  if (home) {
    const params = new URLSearchParams(location.search);
    let role = params.get("role") || store.get("role") || "";
    const seg = document.querySelectorAll(".seg a");
    const dataRole = { student: "student", phd: "phd", work: "worker" };
    const apply = () => {
      seg.forEach((a) => a.classList.toggle("on", a.dataset.role === role));
      document.querySelectorAll("a[data-slug]").forEach((a) => {
        a.href = base + a.dataset.slug + "/" + (role ? role + "/" : "");
      });
      // Hide national cards that do not fit the chosen role, and empty groups.
      document.querySelectorAll(".card").forEach((c) => {
        c.classList.toggle("hide", !!role && !c.dataset.roles.split(" ").includes(dataRole[role]));
      });
      document.querySelectorAll(".group").forEach((g) => {
        const shown = g.querySelectorAll(".card:not(.hide)").length;
        g.hidden = shown === 0;
        const n = g.querySelector(".count");
        if (n) n.textContent = shown;
      });
    };
    seg.forEach((a) => a.addEventListener("click", (ev) => {
      ev.preventDefault();
      role = a.dataset.role === role ? "" : a.dataset.role;
      store.set("role", role);
      apply();
    }));
    apply();
  } else {
    const on = document.querySelector(".seg a.on");
    if (on && on.dataset.role) store.set("role", on.dataset.role);
  }

  // City search: filter chips, Enter opens the first match.
  const q = document.getElementById("q");
  if (q) {
    const chips = [...document.querySelectorAll(".cchip")];
    q.addEventListener("input", () => {
      const v = q.value.trim().toLowerCase();
      chips.forEach((c) => c.classList.toggle("hide", !!v && !c.dataset.q.includes(v)));
    });
    q.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      const first = chips.find((c) => !c.classList.contains("hide"));
      if (first) location.href = first.href;
    });
  }
})();
