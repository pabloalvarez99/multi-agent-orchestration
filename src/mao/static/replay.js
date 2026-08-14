/**
 * Client-side schema-1 trace loader.
 * No server round-trip after the file is chosen — works after Vercel recycle.
 */
(function () {
  "use strict";

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function normalizeEnvelope(raw) {
    if (Array.isArray(raw)) {
      return { trace_schema: 1, run_id: "file-replay", events: raw };
    }
    if (!isObject(raw)) {
      throw new Error("trace JSON root must be an object or events array");
    }
    if (Array.isArray(raw.events) && (raw.trace_schema !== undefined || raw.run_id)) {
      return {
        trace_schema: raw.trace_schema === undefined ? 1 : raw.trace_schema,
        run_id: raw.run_id || "file-replay",
        events: raw.events,
      };
    }
    if (isObject(raw.trace) && Array.isArray(raw.trace.events)) {
      return normalizeEnvelope(raw.trace);
    }
    if (Array.isArray(raw.events)) {
      var runId = raw.run_id;
      if (!runId && isObject(raw.run) && raw.run.run_id) {
        runId = raw.run.run_id;
      }
      return {
        trace_schema: raw.trace_schema === undefined ? 1 : raw.trace_schema,
        run_id: runId || "file-replay",
        events: raw.events,
      };
    }
    throw new Error("trace JSON must include an events array");
  }

  function validateEnvelope(envelope) {
    if (envelope.trace_schema !== 1) {
      throw new Error("unsupported trace_schema (expected 1)");
    }
    if (!envelope.run_id || typeof envelope.run_id !== "string") {
      throw new Error("run_id must be a non-empty string");
    }
    if (!Array.isArray(envelope.events) || envelope.events.length === 0) {
      throw new Error("events must be a non-empty array");
    }
    for (var i = 0; i < envelope.events.length; i += 1) {
      var event = envelope.events[i];
      if (!isObject(event)) {
        throw new Error("each event must be an object");
      }
      if (event.sequence !== i) {
        throw new Error("event sequence must be contiguous from 0");
      }
      if (typeof event.event !== "string" || !event.event) {
        throw new Error("event.event is required");
      }
      if (typeof event.actor !== "string" || !event.actor) {
        throw new Error("event.actor is required");
      }
      if (typeof event.ts_offset_ms !== "number") {
        throw new Error("event.ts_offset_ms must be a number");
      }
    }
    return envelope;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatPayload(payload) {
    try {
      return JSON.stringify(payload === undefined ? {} : payload, null, 2);
    } catch (error) {
      return String(payload);
    }
  }

  function padSequence(value) {
    return String(value).padStart(2, "0");
  }

  function renderEnvelope(envelope, root) {
    var actors = envelope.events.map(function (event) {
      return event.actor;
    });
    var listItems = envelope.events
      .map(function (event) {
        return (
          "<li>" +
          '<span class="sequence">' +
          escapeHtml(padSequence(event.sequence)) +
          "</span>" +
          '<div class="event-card"><div class="event-title"><h3>' +
          escapeHtml(String(event.event).replace(/_/g, " ")) +
          "</h3><span>+" +
          escapeHtml(String(event.ts_offset_ms)) +
          " ms · " +
          escapeHtml(event.actor) +
          "</span></div><pre>" +
          escapeHtml(formatPayload(event.payload)) +
          "</pre></div></li>"
        );
      })
      .join("");

    root.innerHTML =
      '<section class="replay-panel file-replay-panel" aria-labelledby="file-replay-heading">' +
      '<p class="section-label">Offline replay</p>' +
      '<h3 id="file-replay-heading">Loaded from file</h3>' +
      "<p>Rendered entirely in the browser. No server lookup after load — this survives " +
      "Vercel recycle and FIFO eviction.</p>" +
      '<dl class="replay-meta">' +
      "<div><dt>Trace schema</dt><dd><code>" +
      escapeHtml(String(envelope.trace_schema)) +
      "</code></dd></div>" +
      "<div><dt>Run ID</dt><dd><code>" +
      escapeHtml(envelope.run_id) +
      "</code></dd></div>" +
      "<div><dt>Events</dt><dd><code>" +
      escapeHtml(String(envelope.events.length)) +
      "</code></dd></div>" +
      "<div><dt>Actors</dt><dd><code>" +
      escapeHtml(actors.join(" → ")) +
      "</code></dd></div>" +
      "</dl>" +
      "</section>" +
      '<details class="trace file-replay-trace" open>' +
      "<summary>Ordered execution trace <span>" +
      escapeHtml(String(envelope.events.length)) +
      " events</span></summary>" +
      "<ol>" +
      listItems +
      "</ol></details>";
  }

  function showError(root, message) {
    root.innerHTML =
      '<section class="replay-panel file-replay-error" role="alert">' +
      '<p class="section-label">Offline replay</p>' +
      "<h3>Invalid trace file</h3>" +
      "<p class=\"error-label\">" +
      escapeHtml(message) +
      "</p>" +
      "<p>Expected a schema-1 envelope " +
      "(<code>trace_schema</code>, <code>run_id</code>, <code>events</code>) " +
      "or a bare events array from this console.</p>" +
      "</section>";
  }

  function bindLoader(input, root) {
    if (!input || !root) {
      return;
    }
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) {
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var raw = JSON.parse(String(reader.result || ""));
          var envelope = validateEnvelope(normalizeEnvelope(raw));
          renderEnvelope(envelope, root);
        } catch (error) {
          showError(root, error && error.message ? error.message : String(error));
        }
      };
      reader.onerror = function () {
        showError(root, "could not read the selected file");
      };
      reader.readAsText(file);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindLoader(
      document.getElementById("trace-file"),
      document.getElementById("file-replay-root")
    );
  });
})();
