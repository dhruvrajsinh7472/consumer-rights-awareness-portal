/**
 * Main Client-Side JavaScript
 * - Accessible mobile menu
 * - Live search autocomplete via /api/search
 * - FAQ accordion toggling
 * - Problem and FAQ category filtering
 */

document.addEventListener("DOMContentLoaded", () => {
  initMobileNav();
  initLiveSearch();
  initFaqAccordion();
  initCategoryFilters();
});

/* Mobile Navigation */
function initMobileNav() {
  const toggleBtn = document.querySelector(".mobile-toggle");
  const navMenu = document.querySelector(".nav-menu");

  if (!toggleBtn || !navMenu) return;

  toggleBtn.addEventListener("click", () => {
    const isExpanded = toggleBtn.getAttribute("aria-expanded") === "true";
    toggleBtn.setAttribute("aria-expanded", !isExpanded);
    navMenu.classList.toggle("open");
  });

  // Close menu on escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && navMenu.classList.contains("open")) {
      navMenu.classList.remove("open");
      toggleBtn.setAttribute("aria-expanded", "false");
      toggleBtn.focus();
    }
  });
}

/* Live Search Autocomplete */
function initLiveSearch() {
  const searchInput = document.getElementById("global-search-input");
  const searchDropdown = document.getElementById("search-dropdown");

  if (!searchInput || !searchDropdown) return;

  let debounceTimer = null;

  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.trim();

    clearTimeout(debounceTimer);
    if (query.length < 2) {
      searchDropdown.innerHTML = "";
      searchDropdown.classList.remove("active");
      return;
    }

    debounceTimer = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then((res) => res.json())
        .then((data) => {
          renderSearchResults(data.results, query, searchDropdown);
        })
        .catch((err) => {
          console.error("Search error:", err);
        });
    }, 250);
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
      searchDropdown.classList.remove("active");
    }
  });
}

function renderSearchResults(results, query, dropdown) {
  dropdown.innerHTML = "";

  if (!results || results.length === 0) {
    dropdown.innerHTML = `
      <div style="padding: 1rem; color: var(--slate-500); font-size: 0.875rem; text-align: center;">
        No consumer rights or issue guides found matching "<strong>${escapeHtml(query)}</strong>".
        <div style="margin-top: 8px;">
          <a href="/search?q=${encodeURIComponent(query)}" style="color: var(--teal-700); font-weight: 600;">Go to Search Page &rarr;</a>
        </div>
      </div>
    `;
    dropdown.classList.add("active");
    return;
  }

  const list = document.createElement("div");
  results.slice(0, 6).forEach((item) => {
    const a = document.createElement("a");
    a.href = item.url || item.url_for_slug || `/search?q=${encodeURIComponent(query)}`;
    a.className = "search-result-item";

    let typeClass = "type-guide";
    let typeLabel = item.type_label || "Resolution Guide";
    if (item.type === "right") {
      typeClass = "type-right";
    } else if (item.type === "faq") {
      typeClass = "type-faq";
    } else if (item.type === "resource") {
      typeClass = "type-resource";
    }

    a.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
          <span class="search-result-type ${typeClass}">${escapeHtml(typeLabel)}</span>
          ${item.verification_status ? `<span style="font-size: 0.6875rem; color: var(--emerald-700); font-weight: 600;">✓ Verified</span>` : ''}
        </div>
        <div class="search-result-title">${escapeHtml(item.title)}</div>
        <div class="search-result-snippet">${escapeHtml(item.summary || "")}</div>
      </div>
    `;
    list.appendChild(a);
  });

  // Footer: View all results on /search
  const footerLink = document.createElement("a");
  footerLink.href = `/search?q=${encodeURIComponent(query)}`;
  footerLink.className = "search-dropdown-footer";
  footerLink.style.display = "block";
  footerLink.style.padding = "0.75rem 1rem";
  footerLink.style.borderTop = "1px solid var(--border-subtle)";
  footerLink.style.backgroundColor = "var(--slate-50)";
  footerLink.style.fontSize = "0.8125rem";
  footerLink.style.fontWeight = "600";
  footerLink.style.color = "var(--teal-700)";
  footerLink.style.textAlign = "center";
  footerLink.innerHTML = `View all ${results.length} results on Search Page &rarr;`;
  list.appendChild(footerLink);

  dropdown.appendChild(list);
  dropdown.classList.add("active");
}

/* FAQ Accordion */
function initFaqAccordion() {
  const faqButtons = document.querySelectorAll(".faq-question");

  faqButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".faq-item");
      const isOpen = item.classList.contains("open");

      // Optional: close other open items
      document.querySelectorAll(".faq-item.open").forEach((el) => {
        if (el !== item) el.classList.remove("open");
      });

      if (isOpen) {
        item.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      } else {
        item.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  });
}

/* Client Category Filtering */
function initCategoryFilters() {
  const filterButtons = document.querySelectorAll(".filter-btn[data-category]");
  const filterItems = document.querySelectorAll("[data-item-category]");
  const faqSearchInput = document.getElementById("faq-search-input");
  const faqEmptyState = document.getElementById("faq-empty-state");
  const faqResetBtn = document.getElementById("faq-reset-filter-btn");

  if (!filterButtons.length && !filterItems.length && !faqSearchInput) return;

  let activeCategory = "all";
  let activeKeyword = "";

  function applyFilters() {
    let visibleCount = 0;
    filterItems.forEach((item) => {
      const itemCat = item.getAttribute("data-item-category") || "";
      const text = item.textContent.toLowerCase();

      const matchesCat = (activeCategory === "all" || itemCat === activeCategory);
      const matchesText = (!activeKeyword || text.includes(activeKeyword));

      if (matchesCat && matchesText) {
        item.style.display = "";
        visibleCount++;
      } else {
        item.style.display = "none";
      }
    });

    if (faqEmptyState) {
      faqEmptyState.style.display = (visibleCount === 0) ? "block" : "none";
    }
  }

  filterButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      activeCategory = btn.getAttribute("data-category") || "all";
      filterButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      applyFilters();
    });
  });

  if (faqSearchInput) {
    faqSearchInput.addEventListener("input", (e) => {
      activeKeyword = e.target.value.trim().toLowerCase();
      applyFilters();
    });
  }

  if (faqResetBtn) {
    faqResetBtn.addEventListener("click", () => {
      activeCategory = "all";
      activeKeyword = "";
      if (faqSearchInput) faqSearchInput.value = "";
      filterButtons.forEach((b) => {
        if (b.getAttribute("data-category") === "all") b.classList.add("active");
        else b.classList.remove("active");
      });
      applyFilters();
    });
  }
}

/* Helper escape HTML */
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
