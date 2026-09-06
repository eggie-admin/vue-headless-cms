(function ($) {
  "use strict";

  var currentCast = "";

  function show(value) {
    $("#out").text(typeof value === "string" ? value : JSON.stringify(value, null, 2));
  }

  function badge(name, ok) {
    return $("<span>")
      .addClass("badge")
      .addClass(ok ? "green" : "red")
      .text(name + ": " + (ok ? "GREEN" : "OFFLINE"));
  }

  function post(path, body) {
    return $.ajax({
      url: path,
      method: "POST",
      contentType: "application/json",
      dataType: "json",
      data: JSON.stringify(body || {})
    });
  }

  function refreshHealth() {
    $.getJSON("/health")
      .done(function (data) {
        var box = $("#serviceBadges").empty();
        $.each(data.services || {}, function (name, ok) {
          box.append(badge(name, ok));
        });
        $("#runtimeLine").text(
          "APK " + data.version +
          " · Python " + data.python +
          " · altar " + data.altar +
          " · credentials stay out of APK"
        );
      })
      .fail(function (xhr) {
        show(xhr.responseJSON || { ok: false, detail: "APK health check failed" });
      });
  }

  function loadSpells() {
    $.getJSON("/api/magic/spells")
      .done(function (data) {
        var select = $("#spell").empty();
        var spells = data.spells || data;
        if ($.isArray(spells)) {
          $.each(spells, function (_, item) {
            var name = typeof item === "string" ? item : item.name || item.spell;
            if (name) select.append($("<option>").val(name).text(name));
          });
        } else {
          $.each(spells || {}, function (name) {
            select.append($("<option>").val(name).text(name));
          });
        }
        if (!select.children().length) {
          ["INSPECT", "READ_FILE", "SEARCH_TEXT", "PYTHON_CHECK", "GIT_DIFF", "WRITE_FILE", "ULTIMA"]
            .forEach(function (name) {
              select.append($("<option>").val(name).text(name));
            });
        }
      })
      .fail(function () {
        var select = $("#spell").empty();
        ["INSPECT", "READ_FILE", "SEARCH_TEXT", "PYTHON_CHECK", "GIT_DIFF", "WRITE_FILE", "ULTIMA"]
          .forEach(function (name) {
            select.append($("<option>").val(name).text(name));
          });
      });
  }

  function argsJson() {
    try {
      return JSON.parse($("#spellArgs").val() || "{}");
    } catch (err) {
      throw new Error("Spell args must be valid JSON");
    }
  }

  $("#chatSend").on("click", function () {
    var message = $("#chatPrompt").val().trim();
    if (!message) return;
    show("Casting chat…");
    post("/api/magic/chat", { message: message })
      .done(show)
      .fail(function (xhr) { show(xhr.responseJSON || xhr.statusText); });
  });

  $("#prepare").on("click", function () {
    var args;
    try {
      args = argsJson();
    } catch (err) {
      show({ ok: false, detail: err.message });
      return;
    }
    show("Preparing cast…");
    post("/api/magic/cast/prepare", { spell: $("#spell").val(), args: args })
      .done(function (data) {
        currentCast = data.cast_id || "";
        $("#castId").val(currentCast);
        show(data);
      })
      .fail(function (xhr) { show(xhr.responseJSON || xhr.statusText); });
  });

  $("#approve").on("click", function () {
    currentCast = $("#castId").val().trim();
    if (!currentCast) return show({ ok: false, detail: "Prepare a cast first" });
    post("/api/magic/cast/" + encodeURIComponent(currentCast) + "/approve", { approved: true })
      .done(show)
      .fail(function (xhr) { show(xhr.responseJSON || xhr.statusText); });
  });

  $("#execute").on("click", function () {
    currentCast = $("#castId").val().trim();
    if (!currentCast) return show({ ok: false, detail: "Prepare a cast first" });
    post("/api/magic/cast/" + encodeURIComponent(currentCast) + "/execute", {})
      .done(show)
      .fail(function (xhr) { show(xhr.responseJSON || xhr.statusText); });
  });

  $("#rollback").on("click", function () {
    currentCast = $("#castId").val().trim();
    if (!currentCast) return show({ ok: false, detail: "No cast selected" });
    post("/api/magic/cast/" + encodeURIComponent(currentCast) + "/rollback", { approved: true })
      .done(show)
      .fail(function (xhr) { show(xhr.responseJSON || xhr.statusText); });
  });

  $(function () {
    refreshHealth();
    loadSpells();
    window.setInterval(refreshHealth, 10000);
  });
})(jQuery);
