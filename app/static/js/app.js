/* MySpott: small enhancements. The site works without JavaScript; this adds the phone menu
   button, the show/hide password button, "please wait" on forms while they are sent,
   closable messages and the "are you sure?" dialog. */
(function () {
  "use strict";

  // Lets the stylesheet know JavaScript is available.
  document.documentElement.classList.add("js");

  // ---------------------------------------------------------------- phone menu
  function setupMenu() {
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
  }

  // ---------------------------------------------------------- show/hide password
  function hidePassword(button) {
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) {
      return;
    }
    input.setAttribute("type", "password");
    button.textContent = "Show";
    button.setAttribute("aria-label", "Show password");
    button.setAttribute("aria-pressed", "false");
  }

  function setupPasswordToggles() {
    var buttons = document.querySelectorAll("[data-password-toggle]");
    Array.prototype.forEach.call(buttons, function (button) {
      var input = document.getElementById(button.getAttribute("aria-controls"));
      if (!input) {
        return;
      }
      button.addEventListener("click", function () {
        var show = input.getAttribute("type") === "password";
        input.setAttribute("type", show ? "text" : "password");
        button.textContent = show ? "Hide" : "Show";
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        button.setAttribute("aria-pressed", show ? "true" : "false");
      });
    });
  }

  // ------------------------------------------------- "please wait" while sending
  function submitButtons(form) {
    return form.querySelectorAll('button[type="submit"]');
  }

  function setupSubmitOnce() {
    var forms = document.querySelectorAll("form[data-submit-once]");
    Array.prototype.forEach.call(forms, function (form) {
      form.addEventListener("submit", function (event) {
        if (form.getAttribute("aria-busy") === "true") {
          event.preventDefault(); // already being sent: ignore a second click
          return;
        }
        form.setAttribute("aria-busy", "true");
        // Wait one tick, so the browser has collected the form data before the button is disabled.
        setTimeout(function () {
          Array.prototype.forEach.call(submitButtons(form), function (button) {
            button.setAttribute("data-original-text", button.textContent);
            button.textContent = form.getAttribute("data-loading-text") || "Please wait…";
            button.setAttribute("disabled", "");
          });
        }, 0);
      });
    });
  }

  // ---------------------------------------------------------- closable messages
  function setupDismiss() {
    document.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest("[data-dismiss]") : null;
      if (!button) {
        return;
      }
      var box = button.closest("[data-dismissible]");
      if (box && box.parentNode) {
        box.parentNode.removeChild(box);
      }
    });
  }

  // --------------------------------------------------------- "are you sure?" dialog
  // Any form with a data-confirm attribute asks first. The server must never rely on this
  // question for safety: without JavaScript the form is simply sent.
  function setupConfirm() {
    var dialog = document.getElementById("confirm-dialog");
    if (!dialog) {
      return;
    }
    var title = document.getElementById("confirm-title");
    var message = document.getElementById("confirm-message");
    var accept = dialog.querySelector("[data-confirm-accept]");
    var pendingForm = null;

    function send(form) {
      form.setAttribute("data-confirmed", "true");
      if (form.requestSubmit) {
        form.requestSubmit();
      } else {
        form.submit();
      }
    }

    // Capture phase: this runs before the form's own handlers, so a cancelled question
    // never triggers "please wait".
    document.addEventListener(
      "submit",
      function (event) {
        var form = event.target;
        if (!form || !form.getAttribute || form.getAttribute("data-confirm") === null) {
          return;
        }
        if (form.getAttribute("data-confirmed") === "true") {
          form.removeAttribute("data-confirmed");
          return; // the person already said yes: let it through
        }
        event.preventDefault();
        event.stopPropagation();

        var text = form.getAttribute("data-confirm");
        if (typeof dialog.showModal !== "function") {
          if (window.confirm(text)) {
            send(form);
          }
          return;
        }

        pendingForm = form;
        title.textContent = form.getAttribute("data-confirm-title") || "Are you sure?";
        message.textContent = text;
        accept.textContent = form.getAttribute("data-confirm-label") || "Confirm";
        accept.className = form.getAttribute("data-confirm-tone") === "primary" ? "btn btn-primary" : "btn btn-danger";
        dialog.showModal();
      },
      true
    );

    dialog.addEventListener("close", function () {
      var form = pendingForm;
      var confirmed = dialog.returnValue === "confirm";
      pendingForm = null;
      dialog.returnValue = "";
      if (form && confirmed) {
        send(form);
      }
    });

    // A click on the dark area around the dialog counts as "cancel".
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        dialog.close("cancel");
      }
    });
  }

  // Coming back with the browser's Back button can show the page as it was left. Undo any
  // "please wait" state, and never leave a typed password showing.
  function resetPage() {
    var forms = document.querySelectorAll("form[data-submit-once]");
    Array.prototype.forEach.call(forms, function (form) {
      form.removeAttribute("aria-busy");
      Array.prototype.forEach.call(submitButtons(form), function (button) {
        var original = button.getAttribute("data-original-text");
        if (original !== null && original !== undefined) {
          button.textContent = original;
          button.removeAttribute("data-original-text");
        }
        button.removeAttribute("disabled");
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-password-toggle]"), hidePassword);
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupMenu();
    setupPasswordToggles();
    setupDismiss();
    setupConfirm();
    setupSubmitOnce();
  });

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) {
      resetPage();
    }
  });
})();