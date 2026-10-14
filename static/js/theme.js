const themeSelect = document.getElementById("theme-select");

// Read the saved theme, or use dark mode by default.
const savedTheme = localStorage.getItem("storyverse-theme") || "dark";

// Apply a theme to the page.
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("storyverse-theme", theme);
}

// Apply the saved theme when the page opens.
applyTheme(savedTheme);

// Update the dropdown if it exists on this page.
if (themeSelect) {
  themeSelect.value = savedTheme;

  themeSelect.addEventListener("change", function () {
    applyTheme(themeSelect.value);
  });
}
