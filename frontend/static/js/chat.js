/* chat.js  – versión avanzada (mejoras 4-5-6-8)  */

const LOCAL_SOURCE = 'sent';
const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') +
              location.hostname + ':8000/ws';
const ws = new WebSocket(wsUrl);

/* ELEMENTOS DOM --------------------------------------------------------- */
const msgsEl   = document.getElementById('msgs');
const badgeEl  = document.getElementById('unread');
const formEl   = document.getElementById('sendForm');
const inputEl  = document.getElementById('msgInput');
const headerEl = document.querySelector('.chat-header');

let lastId  = '';                               // evita duplicados inmediatos
let unread  = Number(sessionStorage.unread || 0);

/* ---------- restaurar estado scroll y contador (mejora 5) ------------- */
window.addEventListener('load', () => {
  const saved = Number(sessionStorage.scrollTop || 0);
  if (saved) msgsEl.scrollTop = saved;
  if (unread) {
    badgeEl.textContent = unread;
    badgeEl.classList.remove('hidden');
  }
  inputEl.focus();                              // mejora 6
});

/* ---------- indicador conexión (mejora 4) ----------------------------- */
ws.onopen  = () => headerEl.classList.add('online');
ws.onclose = () => headerEl.classList.remove('online');

/* ---------- recibir mensajes ------------------------------------------ */
ws.onmessage = evt => {
  const { payload, source='?' } = JSON.parse(evt.data);
  const msgId = source + '|' + payload;
  if (msgId === lastId) return;
  lastId = msgId;

  const div  = document.createElement('div');
  div.className = 'message ' + (source === LOCAL_SOURCE ? 'sent' : 'received');
  div.textContent = (source === LOCAL_SOURCE ? 'Yo' : source) + ': ' + payload;

  const t = document.createElement('span');     // timestamp
  t.className = 'time';
  t.textContent = new Date().toLocaleTimeString().slice(0, 5);
  div.appendChild(t);
  msgsEl.appendChild(div);

  const nearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 15;
  if (nearBottom) {
    msgsEl.scrollTop = msgsEl.scrollHeight;
  } else {
    unread++;
    badgeEl.textContent = unread;
    badgeEl.classList.remove('hidden');
  }
};

/* ---------- enviar mensaje -------------------------------------------- */
async function sendMessage(txt){
  await fetch('/publish', {
    method : 'POST',
    headers: {'Content-Type':'application/json'},
    body   : JSON.stringify({ message: txt })
  });
}

formEl.addEventListener('submit', async e => {
  e.preventDefault();
  const txt = inputEl.value.trim();
  if (!txt) return;
  await sendMessage(txt);
  inputEl.value = '';
  msgsEl.scrollTop = msgsEl.scrollHeight;
});

/* atajo Ctrl+Enter (mejora 8) */
formEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) {
    formEl.requestSubmit();
  }
});

/* ---------- scroll / foco / persistencia ------------------------------ */
msgsEl.addEventListener('scroll', () => {
  /* guarda la posición (mejora 5) */
  sessionStorage.scrollTop = msgsEl.scrollTop;

  /* quita badge cuando llegas al fondo */
  if (msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 15) {
    unread = 0;
    badgeEl.classList.add('hidden');
  }

  /* si el usuario sube a leer, quita el foco (mejora 6) */
  if (msgsEl.scrollTop < msgsEl.scrollHeight - msgsEl.clientHeight - 100) {
    if (document.activeElement === inputEl) inputEl.blur();
  }
});

/* ---------- guarda contador al salir (mejora 5) ----------------------- */
window.addEventListener('beforeunload', () => {
  sessionStorage.unread = unread;
});
