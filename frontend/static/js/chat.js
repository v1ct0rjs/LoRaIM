/* chat.js con animación (CSS) + historial infinito */

const LOCAL_SOURCE = 'sent';
const PAGE = 20;                 // mensajes por página

/* ---------- elementos ---------- */
const msgsEl   = document.getElementById('msgs');
const badgeEl  = document.getElementById('unread');
const formEl   = document.getElementById('sendForm');
const inputEl  = document.getElementById('msgInput');
const headerEl = document.querySelector('.chat-header');

let lastId = '';
let unread = 0;
let offset = 0;                  // cuánto llevamos cargado ya

/* ---------- util ---------- */
function addBubble({payload, source, time}, prepend=false){
  const wrap = document.createElement('div');
  wrap.className = 'message ' +
    (source===LOCAL_SOURCE ? 'sent':'received');
  wrap.textContent = (source===LOCAL_SOURCE?'Yo':source)+': '+payload;

  const t = document.createElement('span');
  t.className = 'time';
  t.textContent = time;
  wrap.appendChild(t);

  if(prepend){
    msgsEl.prepend(wrap);
  }else{
    msgsEl.appendChild(wrap);
  }
}

/* ---------- inicial: última página ---------- */
async function loadNewest(){
  const r = await fetch(`/messages?limit=${PAGE}`);
  const {messages} = await r.json();
  messages.forEach(m=>{
    addBubble({
      payload : m.payload,
      source  : m.source,
      time    : new Date().toLocaleTimeString().slice(0,5)
    });
  });
  offset = messages.length;
  msgsEl.scrollTop = msgsEl.scrollHeight;      // al fondo
}
loadNewest();

/* ---------- paginar hacia arriba ---------- */
let loadingOld=false;
async function loadOlder(){
  if(loadingOld) return;
  loadingOld=true;

  const oldScroll = msgsEl.scrollHeight;       // para mantener posición
  const r = await fetch(`/messages?limit=${PAGE}&offset=${offset}`);
  const {messages} = await r.json();
  messages.forEach(m=>{
    addBubble({
      payload : m.payload,
      source  : m.source,
      time    : new Date().toLocaleTimeString().slice(0,5)
    }, /*prepend*/ true);
  });
  offset += messages.length;
  /* mantiene la posición para que el texto no “salte” */
  msgsEl.scrollTop = msgsEl.scrollHeight - oldScroll;
  loadingOld=false;
}

/* trigger cuando el usuario llega arriba */
msgsEl.addEventListener('scroll',()=>{
  if(msgsEl.scrollTop < 40){      // casi arriba
    loadOlder();
  }
});

/* ---------- WebSocket ---------- */
const wsUrl = (location.protocol==='https:'?'wss://':'ws://')+
              location.hostname+':8000/ws';
const ws = new WebSocket(wsUrl);
ws.onopen  = ()=> headerEl.classList.add('online');
ws.onclose = ()=> headerEl.classList.remove('online');

ws.onmessage = e=>{
  const {payload, source='?'} = JSON.parse(e.data);
  const id = source+'|'+payload;
  if(id===lastId) return; lastId=id;

  addBubble({
    payload, source,
    time: new Date().toLocaleTimeString().slice(0,5)
  });

  const nearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 15;
  if(nearBottom){
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }else{
    unread++; badgeEl.textContent=unread; badgeEl.classList.remove('hidden');
  }
};

/* ---------- enviar ---------- */
async function sendMessage(txt){
  await fetch('/publish',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:txt})
  });
}

formEl.addEventListener('submit', async e=>{
  e.preventDefault();
  const txt=inputEl.value.trim(); if(!txt) return;
  await sendMessage(txt); inputEl.value='';
});

/* atajo Ctrl+Enter */
formEl.addEventListener('keydown', e=>{
  if(e.key==='Enter' && e.ctrlKey) formEl.requestSubmit();
});
