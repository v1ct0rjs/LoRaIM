/*  chat.js – lógica de frontend
    Se carga con <script defer>, así todo el DOM ya existe
    cuando el script se ejecuta (no necesitamos DOMContentLoaded).  */

/* CONST ------------------------------------------------------ */
const LOCAL_SOURCE = 'sent';
const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') +
              location.hostname + ':8000/ws';
const ws = new WebSocket(wsUrl);

/* ELEMENTOS -------------------------------------------------- */
const msgsEl  = document.getElementById('msgs');
const badgeEl = document.getElementById('unread');
const formEl  = document.getElementById('sendForm');
const inputEl = document.getElementById('msgInput');

let lastId = '';
let unread = 0;

/* WEBSOCKET: llegada de mensajes ----------------------------- */
ws.onmessage = evt => {
  const { payload, source = '?' } = JSON.parse(evt.data);

  /* evita duplicado consecutivo */
  const msgId = source + '|' + payload;
  if (msgId === lastId) return;
  lastId = msgId;

  /* crea la burbuja con texto escapado → ✅ ③ */
  const div  = document.createElement('div');
  div.className = 'message ' + (source === LOCAL_SOURCE ? 'sent' : 'received');
  div.textContent = (source === LOCAL_SOURCE ? 'Yo' : source) + ': ' + payload;

  /* añade timestamp */
  const t = document.createElement('span');
  t.className = 'time';
  t.textContent = new Date().toLocaleTimeString().slice(0, 5);
  div.appendChild(t);

  msgsEl.appendChild(div);

  /* auto-scroll inteligente + contador */
  const nearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 15;
  if (nearBottom) {
    msgsEl.scrollTop = msgsEl.scrollHeight;
  } else {
    unread++;
    badgeEl.textContent = unread;
    badgeEl.classList.remove('hidden');
  }
};

/* FORMULARIO: envío ------------------------------------------ */
formEl.addEventListener('submit', async e => {
  e.preventDefault();
  const txt = inputEl.value.trim();
  if (!txt) return;

  await fetch('/publish', {
    method : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body   : JSON.stringify({ message: txt })
  });
  inputEl.value = '';
  msgsEl.scrollTop = msgsEl.scrollHeight;
});

/* limpiar contador al hacer scroll hasta abajo --------------- */
msgsEl.addEventListener('scroll', () => {
  if (msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 15) {
    unread = 0;
    badgeEl.classList.add('hidden');
  }
});
