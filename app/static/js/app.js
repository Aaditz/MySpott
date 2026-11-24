/* MySpott: small enhancements. The site works without JavaScript; this only adds the
   phone menu button. */
(function () {
  "use strict";

  // Lets the stylesheet know JavaScript is available (it then folds the menu on phones).
  document.documentElement.classList.add("js");

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.querySelector("[data-nav-toggle]");
    var menu = document.querySelector("[data-nav-menu]");
    if (!toggle || !menu) {
      return;
    }

    function isOpen() {
      return toggle.getAttribute("aria-expanded") === "true";
    }

    function setOpen(open) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      menu.setAttribute("data-open", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      setOpen(!isOpen());
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && isOpen()) {
        setOpen(false);
        toggle.focus();
      }
    });

    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        setOpen(false);
      }
    });

    var wide = window.matchMedia("(min-width: 48rem)");
    wide.addEventListener("change", function (event) {
      if (event.matches) {
        setOpen(false);
      }
    });
  });
})();