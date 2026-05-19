// Aegis Core observer — minimal SSE client.
// Anthropological tone: chronological prepending, no charts, no streaks.
// The Now panel updates live off the SSE stream; all times render in the
// viewer's local zone, never UTC.

(function () {
  const list = document.getElementById("events");

  function localTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }

  // Reformat any server rendered timestamps to local time on load.
  document.querySelectorAll("time[datetime]").forEach((el) => {
    el.textContent = localTime(el.getAttribute("datetime"));
  });

  function updateNow(data) {
    if (data.subject === "state.changed" && data.payload && data.payload.current) {
      const el = document.getElementById("presence-value");
      if (el) {
        el.textContent = data.payload.current;
        el.classList.remove("muted");
      }
    }
    if (data.subject === "mood.changed" && data.payload) {
      const el = document.getElementById("mood-value");
      if (el) {
        const p = data.payload;
        el.textContent =
          p.palette +
          " · breath " +
          p.breath_cadence_seconds +
          "s · warmth " +
          p.warmth;
        el.classList.remove("muted");
      }
    }
  }

  const src = new EventSource("/sse/events");
  src.onmessage = (msg) => {
    let data;
    try { data = JSON.parse(msg.data); } catch (e) { return; }

    updateNow(data);

    if (list) {
      const li = document.createElement("li");
      const time = document.createElement("time");
      const ts = data.timestamp || "";
      time.setAttribute("datetime", ts);
      time.textContent = localTime(ts);
      const subj = document.createElement("span");
      subj.className = "event-subject";
      subj.textContent = data.subject;
      li.appendChild(time);
      li.appendChild(subj);
      list.prepend(li);
      // Cap visible list at 200 to keep DOM small.
      while (list.children.length > 200) {
        list.removeChild(list.lastChild);
      }
    }
  };
  src.onerror = () => {
    // Browser will auto-reconnect; nothing to do.
  };
})();
