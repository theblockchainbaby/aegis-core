// Aegis Core observer — minimal SSE client.
// Anthropological tone: chronological prepending, no charts, no streaks.

(function () {
  const list = document.getElementById("events");
  if (!list) return;

  const src = new EventSource("/sse/events");
  src.onmessage = (msg) => {
    let data;
    try { data = JSON.parse(msg.data); } catch (e) { return; }
    const li = document.createElement("li");
    const time = document.createElement("time");
    const ts = data.timestamp || "";
    time.textContent = ts.slice(11, 19);
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
  };
  src.onerror = () => {
    // Browser will auto-reconnect; nothing to do.
  };
})();
