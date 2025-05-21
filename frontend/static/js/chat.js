const LOCAL_SOURCE = "sent"
const PAGE = 50 // carga inicial
const MAX_CHARS = 150 // máximo de caracteres permitidos
const SCROLL_THRESHOLD = 100 // píxeles desde el fondo para considerar "cerca del final"

/* ---------- DOM ---------- */
const msgsEl = document.getElementById("msgs")
const badgeEl = document.getElementById("unread")
const formEl = document.getElementById("sendForm")
const inputEl = document.getElementById("msgInput")
const headerEl = document.querySelector(".chat-header")
const charCountEl = document.createElement("span") // Contador de caracteres
const scrollDownBtn = document.createElement("button") // Botón para ir al final

// Crear contenedor para acciones del header
const headerActions = document.createElement("div")
headerActions.className = "header-actions"
headerEl.appendChild(headerActions)

// Crear botón de cambio de tema
const themeToggle = document.createElement("button")
themeToggle.className = "theme-toggle"
themeToggle.innerHTML = "🌓"
themeToggle.title = "Cambiar tema"
headerActions.appendChild(themeToggle)

// Mover el badge al contenedor de acciones
if (badgeEl) {
  headerActions.appendChild(badgeEl)
}

/* ---------- estado ---------- */
let lastMessage = { source: "", payload: "" }
let unread = 0
let isNearBottom = true
let isDarkTheme = false

/* ---------- Configuración del contador de caracteres ---------- */
charCountEl.className = "char-count"
charCountEl.textContent = `0/${MAX_CHARS}`
formEl.insertBefore(charCountEl, formEl.querySelector("button"))

/* ---------- Configuración del botón de scroll ---------- */
scrollDownBtn.className = "scroll-down-btn hidden"
scrollDownBtn.innerHTML = "↓"
scrollDownBtn.title = "Ir al último mensaje"
document.querySelector(".chat-container").appendChild(scrollDownBtn)

/* ---------- Funciones de tema ---------- */
// Cargar tema guardado
function loadSavedTheme() {
  const savedTheme = localStorage.getItem("theme")
  if (savedTheme === "dark") {
    setDarkTheme()
  } else {
    setLightTheme()
  }
}

// Establecer tema oscuro
function setDarkTheme() {
  document.documentElement.setAttribute("data-theme", "dark")
  themeToggle.innerHTML = "☀️"
  themeToggle.title = "Cambiar a tema claro"
  isDarkTheme = true
  localStorage.setItem("theme", "dark")
}

// Establecer tema claro
function setLightTheme() {
  document.documentElement.removeAttribute("data-theme")
  themeToggle.innerHTML = "🌙"
  themeToggle.title = "Cambiar a tema oscuro"
  isDarkTheme = false
  localStorage.setItem("theme", "light")
}

// Alternar tema
function toggleTheme() {
  if (isDarkTheme) {
    setLightTheme()
  } else {
    setDarkTheme()
  }
}

// Evento para cambiar tema
themeToggle.addEventListener("click", toggleTheme)

// Cargar tema al iniciar
loadSavedTheme()

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

  // Hacer scroll solo si estamos cerca del final
  if (isNearBottom) {
    scrollToBottom()
  } else {
    // Mostrar botón de scroll y actualizar contador
    scrollDownBtn.classList.remove("hidden")
  }
}

// Función para hacer scroll al último mensaje
function scrollToBottom() {
  msgsEl.scrollTop = msgsEl.scrollHeight
  scrollDownBtn.classList.add("hidden")
  unread = 0
  badgeEl.classList.add("hidden")
  isNearBottom = true
}

// Función para verificar si estamos cerca del final
function checkIfNearBottom() {
  isNearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < SCROLL_THRESHOLD
  if (isNearBottom) {
    scrollDownBtn.classList.add("hidden")
    unread = 0
    badgeEl.classList.add("hidden")
  } else {
    scrollDownBtn.classList.remove("hidden")
  }
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

    // Si no estamos cerca del final, incrementar contador de no leídos
    if (!isNearBottom && source !== LOCAL_SOURCE) {
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
  scrollToBottom() // Siempre hacer scroll al enviar un mensaje
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

/* ---------- Eventos de scroll ---------- */
msgsEl.addEventListener("scroll", () => {
  checkIfNearBottom()
})

/* ---------- Botón de scroll down ---------- */
scrollDownBtn.addEventListener("click", () => {
  scrollToBottom()
})
