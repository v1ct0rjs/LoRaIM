const LOCAL_SOURCE = "sent"
const PAGE = 50 // carga inicial
const MAX_CHARS = 150 // máximo de caracteres permitidos

/* ---------- DOM ---------- */
const msgsEl = document.getElementById("msgs")
const badgeEl = document.getElementById("unread")
const formEl = document.getElementById("sendForm")
const inputEl = document.getElementById("msgInput")
const headerEl = document.querySelector(".chat-header")
const charCountEl = document.createElement("span") // Contador de caracteres

/* ---------- estado ---------- */
let lastMessage = { source: "", payload: "" }
let unread = 0

/* ---------- Configuración del contador de caracteres ---------- */
charCountEl.className = "char-count"
charCountEl.textContent = `0/${MAX_CHARS}`
formEl.insertBefore(charCountEl, formEl.querySelector("button"))

// Estilo para el contador de caracteres
const style = document.createElement("style")
style.textContent = `
  .char-count {
    font-size: 0.8rem;
    color: #aaa;
    margin-right: 0.5rem;
    align-self: center;
  }
  .char-count.limit {
    color: #e53e3e;
  }
`
document.head.appendChild(style)

/* ---------- util ---------- */
function addBubble({ payload, source, time }) {
  const wrap = document.createElement("div")
  wrap.className = "message " + (source === LOCAL_SOURCE ? "sent" : "received")
  wrap.textContent = (source === LOCAL_SOURCE ? "Yo" : source) + ": " + payload

  const ts = document.createElement("span")
  ts.className = "time"
  ts.textContent = time
  wrap.appendChild(ts)

  msgsEl.appendChild(wrap)

  // Siempre hacer scroll al último mensaje
  scrollToBottom()
}

// Función para hacer scroll al último mensaje
function scrollToBottom() {
  msgsEl.scrollTop = msgsEl.scrollHeight
}
/* ---------- carga inicial (últimos PAGE) ---------- */
;(async () => {
  const res = await fetch(`/messages?limit=${PAGE}`)
  const { messages } = await res.json()

  // Para la carga inicial, filtramos mensajes duplicados consecutivos
  let prevMsg = { source: "", payload: "" }

  messages.forEach((m) => {
    // Solo añadir si es diferente al mensaje anterior
    if (m.source !== prevMsg.source || m.payload !== prevMsg.payload) {
      addBubble({
        payload: m.payload,
        source: m.source,
        time: new Date().toLocaleTimeString().slice(0, 5),
      })

      // Actualizar el mensaje anterior
      prevMsg = { source: m.source, payload: m.payload }
    }
  })

  // Guardar el último mensaje para comparar con nuevos WebSocket
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    lastMessage = { source: lastMsg.source, payload: lastMsg.payload }
  }

  scrollToBottom() // Asegurar scroll al fondo
  inputEl.focus()
})()

/* ---------- WebSocket ---------- */
const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.hostname + ":8000/ws"
const ws = new WebSocket(wsUrl)

ws.onopen = () => headerEl.classList.add("online")
ws.onclose = () => headerEl.classList.remove("online")

ws.onmessage = (e) => {
  const { payload, source = "?" } = JSON.parse(e.data)

  // Solo añadir burbuja si el mensaje es diferente al último
  if (source !== lastMessage.source || payload !== lastMessage.payload) {
    addBubble({
      payload,
      source,
      time: new Date().toLocaleTimeString().slice(0, 5),
    })

    // Actualizar el último mensaje
    lastMessage = { source, payload }

    /* auto-scroll y badge */
    const wasBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 25
    if (wasBottom) {
      scrollToBottom()
      unread = 0
      badgeEl.classList.add("hidden")
    } else {
      unread++
      badgeEl.textContent = unread
      badgeEl.classList.remove("hidden")
    }
  }
}

/* ---------- enviar ---------- */
formEl.addEventListener("submit", async (e) => {
  e.preventDefault()
  const txt = inputEl.value.trim()
  if (!txt || txt.length > MAX_CHARS) return

  // Mostrar inmediatamente el mensaje enviado en el chat
  const time = new Date().toLocaleTimeString().slice(0, 5)
  addBubble({
    payload: txt,
    source: LOCAL_SOURCE,
    time: time,
  })

  // Actualizar el último mensaje para evitar duplicados
  lastMessage = { source: LOCAL_SOURCE, payload: txt }

  // Enviar al servidor
  try {
    await fetch("/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: txt }),
    })
  } catch (error) {
    console.error("Error al enviar mensaje:", error)
  }

  inputEl.value = ""
  updateCharCount(0)
  scrollToBottom()
})

/* ---------- Contador de caracteres ---------- */
function updateCharCount(length) {
  charCountEl.textContent = `${length}/${MAX_CHARS}`
  if (length > MAX_CHARS) {
    charCountEl.classList.add("limit")
  } else {
    charCountEl.classList.remove("limit")
  }
}

inputEl.addEventListener("input", () => {
  const length = inputEl.value.length
  updateCharCount(length)
})

/* atajo Ctrl+Enter */
formEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.ctrlKey) formEl.requestSubmit()
})

/* ---------- badge reset al llegar al fondo ---------- */
msgsEl.addEventListener("scroll", () => {
  if (msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 20) {
    unread = 0
    badgeEl.classList.add("hidden")
  }
})
