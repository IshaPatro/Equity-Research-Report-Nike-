function setupNavigation() {
  const sidebar = document.querySelector(".sidebar");
  const button = document.getElementById("mobileNav");
  const links = [...document.querySelectorAll("nav a")];

  button.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    button.setAttribute("aria-expanded", String(open));
  });

  links.forEach((link) => {
    link.addEventListener("click", () => {
      sidebar.classList.remove("open");
      button.setAttribute("aria-expanded", "false");
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.filter((entry) => entry.isIntersecting).forEach((entry) => {
      links.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  }, { rootMargin: "-35% 0px -55% 0px", threshold: 0 });

  document.querySelectorAll("main > section").forEach((section) => observer.observe(section));
}

setupNavigation();
