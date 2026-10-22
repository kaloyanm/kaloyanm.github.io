(function () {
  var root = document.documentElement;

  /* ---------- theme ---------- */
  var toggle = document.getElementById("theme-toggle");

  function syncThemeLabel() {
    if (!toggle) return;
    var dark = root.getAttribute("data-theme") === "dark";
    toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  if (toggle) {
    syncThemeLabel();
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      syncThemeLabel();
    });
  }

  /* ---------- index dialog ---------- */
  var dialog = document.getElementById("index-dialog");
  var openBtns = document.querySelectorAll("[data-index-open]");
  var closeBtn = document.querySelector("[data-index-close]");

  if (dialog && openBtns.length && typeof dialog.showModal === "function") {
    var shortcut = openBtns[0].querySelector("kbd");
    if (shortcut && navigator.platform && navigator.platform.indexOf("Mac") === -1) {
      shortcut.textContent = "Ctrl K";
    }

    openBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        dialog.showModal();
      });
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        dialog.close();
      });
    }

    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });

    dialog.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        dialog.close();
      });
    });

    document.addEventListener("keydown", function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (dialog.open) dialog.close();
        else dialog.showModal();
      }
    });
  }

  /* ---------- reading progress ---------- */
  var progress = document.querySelector("[data-progress]");
  if (progress) {
    var updateProgress = function () {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = max > 0 ? window.scrollY / max : 0;
      progress.style.width = (Math.min(Math.max(ratio, 0), 1) * 100) + "%";
    };
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
    updateProgress();
  }

  /* ---------- copy link ---------- */
  var copyBtn = document.querySelector("[data-copy-link]");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var done = function () {
        var previous = copyBtn.textContent;
        copyBtn.textContent = "Copied";
        window.setTimeout(function () {
          copyBtn.textContent = previous;
        }, 1800);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(window.location.href).then(done).catch(function () {
          copyBtn.textContent = "Copy failed";
        });
      } else {
        copyBtn.textContent = "Copy failed";
      }
    });
  }
})();
