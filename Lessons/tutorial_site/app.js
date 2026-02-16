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

  wireCopyButtons();
  wireAnswerButtons();
}());
