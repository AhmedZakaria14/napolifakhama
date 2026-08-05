(() => {
  const search = document.querySelector("[data-blog-search]");
  const buttons = [...document.querySelectorAll("[data-blog-filter]")];
  const cards = [...document.querySelectorAll("[data-blog-grid] .blog-card")];
  const empty = document.querySelector("[data-blog-empty]");
  if (!search || !cards.length) return;

  let category = "الكل";
  const applyFilter = () => {
    const term = search.value.trim().toLocaleLowerCase("ar");
    let shown = 0;
    cards.forEach((card) => {
      const categoryMatches = category === "الكل" || card.dataset.category === category;
      const searchMatches = !term || (card.dataset.search || "").toLocaleLowerCase("ar").includes(term);
      const visible = categoryMatches && searchMatches;
      card.hidden = !visible;
      if (visible) shown += 1;
    });
    if (empty) empty.hidden = shown > 0;
  };

  search.addEventListener("input", applyFilter);
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      category = button.dataset.blogFilter || "الكل";
      applyFilter();
    });
  });
})();
