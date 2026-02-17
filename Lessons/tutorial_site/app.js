(function () {
  function wireCopyButtons() {
    var copyButtons = document.querySelectorAll(".copy-btn");
    copyButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetId = btn.getAttribute("data-copy-target");
        var node = document.getElementById(targetId);
        if (!node) {
          return;
        }
        navigator.clipboard.writeText(node.textContent || "");
        var oldText = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () {
          btn.textContent = oldText;
        }, 900);
      });
    });
  }

  function wireAnswerButtons() {
    var revealButtons = document.querySelectorAll(".reveal-btn");
    revealButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetId = btn.getAttribute("data-answer-target");
        var answer = document.getElementById(targetId);
        if (!answer) {
          return;
        }
        var nowVisible = answer.classList.toggle("visible");
        btn.textContent = nowVisible ? "Hide answer" : "Reveal answer";
      });
    });
  }

  function wireVideoShowcase() {
    var showcases = document.querySelectorAll("[data-showcase]");
    showcases.forEach(function (showcase) {
      var tabs = Array.prototype.slice.call(showcase.querySelectorAll(".showcase-tab"));
      var slides = Array.prototype.slice.call(showcase.querySelectorAll(".showcase-slide"));
      if (!tabs.length || !slides.length) {
        return;
      }

      var currentIndex = 0;

      function stopInactiveVideos(activeId) {
        slides.forEach(function (slide) {
          var video = slide.querySelector("video");
          if (!video) {
            return;
          }
          if (slide.getAttribute("data-showcase-id") !== activeId) {
            video.pause();
          }
        });
      }

      function activate(index) {
        if (index < 0) {
          index = slides.length - 1;
        } else if (index >= slides.length) {
          index = 0;
        }
        currentIndex = index;

        var activeSlide = slides[index];
        var activeId = activeSlide.getAttribute("data-showcase-id");

        tabs.forEach(function (tab) {
          var isActive = tab.getAttribute("data-showcase-target") === activeId;
          tab.classList.toggle("is-active", isActive);
          tab.setAttribute("aria-selected", isActive ? "true" : "false");
          tab.tabIndex = isActive ? 0 : -1;
        });

        slides.forEach(function (slide) {
          var isActive = slide.getAttribute("data-showcase-id") === activeId;
          slide.classList.toggle("is-active", isActive);
        });

        stopInactiveVideos(activeId);
      }

      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          var targetId = tab.getAttribute("data-showcase-target");
          var index = slides.findIndex(function (slide) {
            return slide.getAttribute("data-showcase-id") === targetId;
          });
          if (index !== -1) {
            activate(index);
          }
        });
      });

      var prev = showcase.querySelector("[data-showcase-nav='prev']");
      var next = showcase.querySelector("[data-showcase-nav='next']");

      if (prev) {
        prev.addEventListener("click", function () {
          activate(currentIndex - 1);
        });
      }

      if (next) {
        next.addEventListener("click", function () {
          activate(currentIndex + 1);
        });
      }

      activate(0);
    });
  }

  wireCopyButtons();
  wireAnswerButtons();
  wireVideoShowcase();
}());
