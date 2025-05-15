const LOCAL_SOURCE = 'sent';
const PAGE         = 50;   // mensajes iniciales

/* ---------- DOM ---------- */
const msgsEl   = document.getElementById('msgs');
const badgeEl  = document.getElementById('unread');
const formEl   = document.getElementById('sendForm');
const inputEl  = document.getElementById('msgInput');
const headerEl = document.querySelector('.chat-header');

/* ---------- estado ---------- */
let unread = 0;

/* ---------- util ---------- */
function addBubble({payload, source, time}){
  const wrap = document.createElement('div');
  wrap.className = 'message ' + (source === LOCAL_SOURCE ? 'sent' : 'received');
  wrap.textContent = (source === LOCAL_SOURCE ? 'Yo' : source) + ': ' + payload;

  const ts = document.createElement('span');
  ts.className = 'time';
  ts.textContent = time;
  wrap.appendChild(ts);

  msgsEl.appendChild(wrap);
}

/* ---------- carga inicial ---------- */
(async () => {
  const res = await fetch(`/messages?limit=${PAGE}`);
  const {messages} = await res.json();
  messages.forEach(m => addBubble({
    payload: m.payload,
    source : m.source,
    time   : new Date().toLocaleTimeString().slice(0,5)
  }));
  msgsEl.scrollTop = msgsEl.scrollHeight; // al fondo
  inputEl.focus();
})();

/* ---------- WebSocket ---------- */
const lastShown = Object.create(null);     // {source: payload}

ws.onmessage = e => {
  const {payload, source='?'} = JSON.parse(e.data);

  /* ── filtro de repetidos consecutivos ───────────────────── */
  if (lastShown[source] === payload){
    // ya se mostró este mismo texto justo antes: ignoramos
    return;
  }
  lastShown[source] = payload;             // guarda el último de ese nodo
  /* ───────────────────────────────────────────────────────── */

  addBubble({
    payload,
    source,
    time: new Date().toLocaleTimeString().slice(0,5)
  });

  const wasBottom =
        msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 25;

  if (wasBottom){
    msgsEl.scrollTop = msgsEl.scrollHeight;
    unread = 0; badgeEl.classList.add('hidden');
  }else{
    unread++;
    badgeEl.textContent = unread;
    badgeEl.classList.remove('hidden');
  }
};


/* ---------- enviar ---------- */
formEl.addEventListener('submit', async e => {
  e.preventDefault();
  const txt = inputEl.value.trim();
  if (!txt) return;
  await fetch('/publish', {
    method : 'POST',
    headers: {'Content-Type':'application/json'},
    body   : JSON.stringify({ message: txt })
  });
  inputEl.value = '';
  msgsEl.scrollTop = msgsEl.scrollHeight;
});

/* atajo Ctrl + Enter */
formEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) formEl.requestSubmit();
});

/* ---------- badge reset ---------- */
msgsEl.addEventListener('scroll', () => {
  if (msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 20){
    unread = 0;
    badgeEl.classList.add('hidden');
  }
});
