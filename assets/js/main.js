(() => {
  const root = document.documentElement;
  let savedTheme = null;
  try {
    savedTheme = localStorage.getItem("fakhama-theme");
  } catch (_) {
    // The site still works when browser storage is blocked.
  }
  if (savedTheme) root.dataset.theme = savedTheme;

  const themeButton = document.querySelector("[data-theme-toggle]");
  const updateThemeLabel = () => {
    if (!themeButton) return;
    const dark = root.dataset.theme === "dark";
    themeButton.textContent = dark ? "☀" : "☾";
    themeButton.setAttribute(
      "aria-label",
      dark ? "تفعيل الوضع النهاري" : "تفعيل الوضع الليلي",
    );
  };
  updateThemeLabel();
  themeButton?.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try {
      localStorage.setItem("fakhama-theme", root.dataset.theme);
    } catch (_) {
      // Keep the selected theme for the current page only.
    }
    updateThemeLabel();
  });

  const menuButton = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-nav-links]");
  const closeMenu = () => {
    menu?.classList.remove("open");
    menuButton?.setAttribute("aria-expanded", "false");
    if (menuButton) {
      menuButton.textContent = "☰";
      menuButton.setAttribute("aria-label", "فتح القائمة");
    }
  };
  menuButton?.addEventListener("click", () => {
    const open = menu?.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(Boolean(open)));
    menuButton.textContent = open ? "×" : "☰";
    menuButton.setAttribute(
      "aria-label",
      open ? "إغلاق القائمة" : "فتح القائمة",
    );
  });
  menu
    ?.querySelectorAll("a")
    .forEach((link) => link.addEventListener("click", closeMenu));
  window.addEventListener("resize", () => {
    if (window.innerWidth > 980) closeMenu();
  });
  document.addEventListener("click", (event) => {
    if (menu?.classList.contains("open") && !event.target.closest(".nav"))
      closeMenu();
  });

  document.querySelectorAll(".faq-question").forEach((button) => {
    button.addEventListener("click", () => {
      const item = button.closest(".faq-item");
      const willOpen = !item.classList.contains("open");
      item.classList.toggle("open", willOpen);
      button.setAttribute("aria-expanded", String(willOpen));
      button.querySelector("span:last-child").textContent = willOpen
        ? "−"
        : "+";
    });
  });

  const lightbox = document.querySelector("[data-lightbox]");
  const lightboxImage = lightbox?.querySelector("img");
  const lightboxCloseButton = lightbox?.querySelector("[data-lightbox-close]");
  let lightboxTrigger = null;
  const closeLightbox = () => {
    lightbox?.classList.remove("open");
    lightbox?.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    lightboxTrigger?.focus();
  };
  document.querySelectorAll("[data-gallery-image]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!lightbox || !lightboxImage) return;
      const image = button.querySelector("img");
      if (!image) return;
      lightboxTrigger = button;
      lightboxImage.src = image.src;
      lightboxImage.alt = image.alt;
      lightbox.classList.add("open");
      lightbox.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
      lightboxCloseButton?.focus();
    });
  });
  lightboxCloseButton?.addEventListener("click", closeLightbox);
  lightbox?.addEventListener("click", (event) => {
    if (event.target === lightbox) closeLightbox();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeLightbox();
      closeMenu();
    }
  });

  document.querySelectorAll("[data-whatsapp-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const message = `السلام عليكم، أريد عرض سعر من أفران ومشبات الفخامة.\n\nالاسم: ${data.get("name")}\nرقم الجوال: ${data.get("phone")}\nالمنتج المطلوب: ${data.get("service")}\nتفاصيل الطلب: ${data.get("message")}`;
      const whatsappUrl = `https://wa.me/966556182491?text=${encodeURIComponent(message)}`;
      const newWindow = window.open(whatsappUrl, "_blank", "noopener");
      if (!newWindow) window.location.href = whatsappUrl;
    });
  });

  const observer =
    "IntersectionObserver" in window
      ? new IntersectionObserver(
          (entries) =>
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                observer.unobserve(entry.target);
              }
            }),
          { threshold: 0.12 },
        )
      : null;
  document
    .querySelectorAll(".reveal")
    .forEach((element) =>
      observer ? observer.observe(element) : element.classList.add("visible"),
    );
})();
