const LOCAL_SOURCE = "sent"
const PAGE = 50 // carga inicial
const MAX_CHARS = 150 // máximo de caracteres permitidos
const SCROLL_THRESHOLD = 100 // píxeles desde el fondo para considerar "cerca del final"
const MAX_RECONNECT_DELAY = 5000 // máximo delay para reconexión en ms
const WEBSOCKET_TIMEOUT = 3000 // tiempo antes de considerar la conexión como fallida

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

// Crear botón de settings/menú
const settingsButton = document.createElement("button")
settingsButton.className = "settings-button"
settingsButton.innerHTML =
  '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'
settingsButton.title = "Configuración"
headerActions.appendChild(settingsButton)

// Crear menú desplegable
const settingsMenu = document.createElement("div")
settingsMenu.className = "settings-menu hidden"
document.querySelector(".chat-container").appendChild(settingsMenu)

// Crear contenedor de opciones en el menú
const settingsOptions = document.createElement("div")
settingsOptions.className = "settings-options"
settingsMenu.appendChild(settingsOptions)

// Añadir opción de métricas LoRa
const loraMetricsOption = document.createElement("label")
loraMetricsOption.className = "settings-option"
loraMetricsOption.innerHTML = `
  <input type="checkbox" id="loraMetricsToggle"> 
  <span>Mostrar métricas LoRa</span>
`
settingsOptions.appendChild(loraMetricsOption)

// Añadir opción de notificaciones
const notificationsOption = document.createElement("label")
notificationsOption.className = "settings-option"
notificationsOption.innerHTML = `
  <input type="checkbox" id="notificationsToggle" checked> 
  <span>Notificaciones del navegador</span>
`
settingsOptions.appendChild(notificationsOption)

// Añadir opción de sonidos
const soundsOption = document.createElement("label")
soundsOption.className = "settings-option"
soundsOption.innerHTML = `
  <input type="checkbox" id="soundsToggle" checked> 
  <span>Sonidos de notificación</span>
`
settingsOptions.appendChild(soundsOption)

// Añadir sección de búsqueda
const searchSection = document.createElement("div")
searchSection.className = "search-section"
searchSection.innerHTML = `
  <input type="text" id="searchInput" placeholder="Buscar mensajes...">
  <button id="searchButton">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
  </button>
`
settingsMenu.appendChild(searchSection)

// Añadir sección de visualización de nodos conectados
const nodesSection = document.createElement("div")
nodesSection.className = "nodes-section"
nodesSection.innerHTML = `
  <h3>Estado de Nodos</h3>
  <div id="nodesList" class="nodes-list">
    <div class="no-nodes">No hay nodos conectados</div>
  </div>
`
settingsMenu.appendChild(nodesSection)

// Crear botón de tema
const themeToggle = document.createElement("button")
themeToggle.className = "theme-toggle"
themeToggle.innerHTML = "🌓"
themeToggle.title = "Cambiar tema"
headerActions.appendChild(themeToggle)

// Crear indicador de conexión
const connectionStatus = document.createElement("div")
connectionStatus.className = "connection-status"
connectionStatus.innerHTML = `
  <span class="status-indicator offline"></span>
  <span class="status-text">Desconectado</span>
`
headerEl.querySelector(".header-title").appendChild(connectionStatus)

// Crear badge para mensajes no leídos
const unreadBadgeContainer = document.createElement("div")
unreadBadgeContainer.className = "unread-badge-container"
const unreadBadge = document.createElement("span")
unreadBadge.id = "unreadBadge"
unreadBadge.className = "unread-badge hidden"
unreadBadge.textContent = "0"
unreadBadgeContainer.appendChild(unreadBadge)
headerActions.appendChild(unreadBadgeContainer)

// Crear sonidos de notificación
const notificationSound = new Audio("/static/sounds/notification.mp3")
const messageSentSound = new Audio("/static/sounds/message-sent.mp3")

/* ---------- estado ---------- */
// Añadir después de la definición de variables globales (línea ~50)
const NODES_TOPIC = "lorachat/nodes"
const NODE_TIMEOUT = 60000 // 60 segundos para considerar un nodo offline
let lastMessage = { source: "", payload: "" }
let unread = 0
let isNearBottom = true
let isDarkTheme = true // Tema oscuro por defecto
let reconnectAttempts = 0
let reconnectTimeout = null
let ws = null
let wsConnected = false
const connectedNodes = new Map() // Mapa para almacenar el estado de los nodos
let notificationsEnabled = localStorage.getItem("notificationsEnabled") !== "false"
let soundsEnabled = localStorage.getItem("soundsEnabled") !== "false"
let loraMetricsEnabled = localStorage.getItem("loraMetricsEnabled") === "true"
let searchTimeout = null
let searchQuery = ""
let notificationPermission = "default"

/* ---------- Configuración del contador de caracteres ---------- */
charCountEl.className = "char-count"
charCountEl.textContent = `0/${MAX_CHARS}`
formEl.insertBefore(charCountEl, formEl.querySelector("button"))

/* ---------- Configuración del botón de scroll ---------- */
scrollDownBtn.className = "scroll-down-btn hidden"
scrollDownBtn.innerHTML = "↓"
scrollDownBtn.title = "Ir al último mensaje"
document.querySelector(".chat-container").appendChild(scrollDownBtn)

/* ---------- Inicialización ---------- */
// Comprobar permisos de notificación al cargar
function checkNotificationPermission() {
  if (!("Notification" in window)) {
    console.log("Este navegador no soporta notificaciones")
    notificationsEnabled = false
    document.getElementById("notificationsToggle").checked = false
    document.getElementById("notificationsToggle").disabled = true
  } else if (Notification.permission === "granted") {
    notificationPermission = "granted"
  }
}

checkNotificationPermission()

// Actualizar estados de los checkboxes
document.getElementById("notificationsToggle").checked = notificationsEnabled
document.getElementById("soundsToggle").checked = soundsEnabled
document.getElementById("loraMetricsToggle").checked = loraMetricsEnabled

/* ---------- Funciones de tema ---------- */
// Cargar tema guardado
function loadSavedTheme() {
  const savedTheme = localStorage.getItem("theme")
  // Si no hay tema guardado o es "dark", usar tema oscuro (predeterminado)
  if (!savedTheme || savedTheme === "dark") {
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

/* ---------- WebSocket Reconnection ---------- */
function connectWebSocket() {
  const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.hostname + ":8000/ws"

  // Limpiar cualquier timeout pendiente
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }

  // Crear nueva conexión WebSocket
  ws = new WebSocket(wsUrl)

  // Establecer un timeout para detectar conexiones fallidas
  const connectionTimeout = setTimeout(() => {
    if (ws && ws.readyState !== WebSocket.OPEN) {
      ws.close()
      updateConnectionStatus(false)
      scheduleReconnect()
    }
  }, WEBSOCKET_TIMEOUT)

  ws.onopen = () => {
    clearTimeout(connectionTimeout)
    console.log("WebSocket conectado")
    updateConnectionStatus(true)
    reconnectAttempts = 0 // Resetear los intentos de reconexión
  }

  ws.onclose = () => {
    clearTimeout(connectionTimeout)
    console.log("WebSocket desconectado")
    updateConnectionStatus(false)
    scheduleReconnect()
  }

  ws.onerror = (error) => {
    console.error("Error de WebSocket:", error)
    ws.close()
  }

  ws.onmessage = handleWebSocketMessage
}

function updateConnectionStatus(connected) {
  wsConnected = connected
  const statusIndicator = document.querySelector(".status-indicator")
  const statusText = document.querySelector(".status-text")

  if (connected) {
    statusIndicator.classList.remove("offline")
    statusIndicator.classList.add("online")
    statusText.textContent = "Conectado"
    headerEl.classList.add("online")
  } else {
    statusIndicator.classList.remove("online")
    statusIndicator.classList.add("offline")
    statusText.textContent = "Desconectado"
    headerEl.classList.remove("online")
  }
}

function scheduleReconnect() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
  }

  // Calcular delay con backoff exponencial
  const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts), MAX_RECONNECT_DELAY)
  reconnectAttempts++

  console.log(`Intentando reconectar en ${delay}ms (intento ${reconnectAttempts})`)
  reconnectTimeout = setTimeout(connectWebSocket, delay)
}

// Modificar la función handleWebSocketMessage para procesar actualizaciones de nodos
function handleWebSocketMessage(e) {
  try {
    const data = JSON.parse(e.data)

    // Comprobar si es una actualización de nodos
    if (data.type === "nodes_update" && data.nodes) {
      // Actualizar la lista de nodos
      data.nodes.forEach((node) => {
        updateNodeStatus(node.id, {
          rssi: node.rssi,
          snr: node.snr,
          lastSeen: node.last_seen * 1000, // Convertir a milisegundos
          status: node.status,
          source: node.id,
        })
      })
      return
    }

    const { payload, source = "?", rssi, snr, nodeId, timestamp } = data

    // Actualizar estado del nodo si se proporciona un ID de nodo
    if (source && source !== "sent" && source !== "?") {
      updateNodeStatus(source, {
        rssi,
        snr,
        lastSeen: timestamp ? timestamp * 1000 : Date.now(),
        status: "online",
        source,
      })
    }

    // Solo añadir burbuja si el mensaje es diferente al último
    if (source !== lastMessage.source || payload !== lastMessage.payload) {
      // Comprobar si el mensaje coincide con la búsqueda actual
      const messageMatchesSearch =
        !searchQuery ||
        payload.toLowerCase().includes(searchQuery.toLowerCase()) ||
        source.toLowerCase().includes(searchQuery.toLowerCase())

      addBubble({
        payload,
        source,
        time: new Date().toLocaleTimeString().slice(0, 5),
        metrics: { rssi, snr },
        hidden: searchQuery && !messageMatchesSearch,
      })

      // Actualizar el último mensaje
      lastMessage = { source, payload }

      // Notificaciones y sonidos solo si no es un mensaje enviado por nosotros
      if (source !== LOCAL_SOURCE) {
        // Reproducir sonido de notificación si está habilitado
        if (soundsEnabled) {
          notificationSound.play().catch((e) => console.error("Error reproduciendo sonido:", e))
        }

        // Enviar notificación del navegador si está habilitado y la ventana no está enfocada
        if (notificationsEnabled && notificationPermission === "granted" && !document.hasFocus()) {
          showNotification(source, payload)
        }

        // Si no estamos cerca del final, incrementar contador de no leídos
        if (!isNearBottom) {
          unread++
          updateUnreadBadge()
        }
      }
    }
  } catch (error) {
    console.error("Error procesando mensaje WebSocket:", error)
  }
}

// Modificar la función updateNodeStatus para manejar el estado online/offline
function updateNodeStatus(nodeId, data) {
  if (!nodeId) return

  const now = new Date()
  const lastSeen = data.lastSeen ? new Date(data.lastSeen) : now

  // Actualizar o crear entrada del nodo
  connectedNodes.set(nodeId, {
    ...data,
    id: nodeId,
    lastSeen: lastSeen,
    status: data.status || "online",
  })

  // Actualizar la visualización de nodos
  renderNodesList()

  // Configurar un temporizador para marcar los nodos como offline después de un tiempo
  setTimeout(() => {
    const node = connectedNodes.get(nodeId)
    if (node && now - new Date(node.lastSeen) >= NODE_TIMEOUT) {
      node.status = "offline"
      renderNodesList()
    }
  }, NODE_TIMEOUT)
}

// Modificar la función renderNodesList para usar datos reales
function renderNodesList() {
  const nodesListEl = document.getElementById("nodesList")

  if (connectedNodes.size === 0) {
    nodesListEl.innerHTML = '<div class="no-nodes">No hay nodos conectados</div>'
    return
  }

  let nodesHtml = ""

  connectedNodes.forEach((node, nodeId) => {
    const isOnline = node.status === "online"
    const statusClass = isOnline ? "online" : "offline"
    const lastSeen = node.lastSeen ? new Date(node.lastSeen * 1000) : new Date()

    nodesHtml += `
      <div class="node-item">
        <div class="node-info">
          <span class="node-name">${nodeId || node.id || "Nodo desconocido"}</span>
          <span class="status-indicator ${statusClass}"></span>
        </div>
        ${
          loraMetricsEnabled && node.rssi !== undefined
            ? `
          <div class="node-metrics">
            <span class="rssi">RSSI: ${node.rssi !== null ? node.rssi.toFixed(1) : "N/A"} dBm</span>
            <span class="snr">SNR: ${node.snr !== null ? node.snr.toFixed(1) : "N/A"} dB</span>
          </div>
        `
            : ""
        }
        <div class="node-last-seen">
          Última actividad: ${formatTimeDiff(lastSeen)}
        </div>
      </div>
    `
  })

  nodesListEl.innerHTML = nodesHtml
}

function formatTimeDiff(date) {
  if (!date) return "Desconocido"

  const now = new Date()
  const diff = now - date

  if (diff < 60000) return "Hace menos de 1 minuto"
  if (diff < 3600000) return `Hace ${Math.floor(diff / 60000)} minutos`
  if (diff < 86400000) return `Hace ${Math.floor(diff / 3600000)} horas`
  return `Hace ${Math.floor(diff / 86400000)} días`
}

/* ---------- Notificaciones ---------- */
function showNotification(sender, message) {
  if (!("Notification" in window)) return

  try {
    new Notification("Nuevo mensaje de LoRaIM", {
      body: `${sender}: ${message}`,
      icon: "/static/img/logo.png",
    })
  } catch (error) {
    console.error("Error mostrando notificación:", error)
  }
}

function requestNotificationPermission() {
  if (!("Notification" in window)) return

  Notification.requestPermission().then((permission) => {
    notificationPermission = permission
    if (permission === "granted") {
      console.log("Permisos de notificación concedidos")
    }
  })
}

/* ---------- util ---------- */
function addBubble({ payload, source, time, metrics = {}, hidden = false }) {
  const wrap = document.createElement("div")
  wrap.className = "message " + (source === LOCAL_SOURCE ? "sent" : "received")
  if (hidden) wrap.classList.add("hidden")

  wrap.dataset.source = source
  wrap.dataset.content = payload

  wrap.textContent = (source === LOCAL_SOURCE ? "Yo" : source) + ": " + payload

  const ts = document.createElement("span")
  ts.className = "time"
  ts.textContent = time
  wrap.appendChild(ts)

  // Añadir métricas LoRa si están habilitadas y disponibles
  if (loraMetricsEnabled && (metrics.rssi !== undefined || metrics.snr !== undefined)) {
    const metricsEl = document.createElement("div")
    metricsEl.className = "metrics"

    if (metrics.rssi !== undefined) {
      const rssiEl = document.createElement("span")
      rssiEl.className = "rssi"
      rssiEl.textContent = `RSSI: ${metrics.rssi} dBm`
      metricsEl.appendChild(rssiEl)
    }

    if (metrics.snr !== undefined) {
      const snrEl = document.createElement("span")
      snrEl.className = "snr"
      snrEl.textContent = `SNR: ${metrics.snr} dB`
      metricsEl.appendChild(snrEl)
    }

    wrap.appendChild(metricsEl)
  }

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
  unreadBadge.textContent = "0"
  unreadBadge.classList.add("hidden")
  isNearBottom = true
}

// Función para verificar si estamos cerca del final
function checkIfNearBottom() {
  isNearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < SCROLL_THRESHOLD
  if (isNearBottom) {
    scrollDownBtn.classList.add("hidden")
    unread = 0
    unreadBadge.textContent = "0"
    unreadBadge.classList.add("hidden")
  } else {
    scrollDownBtn.classList.remove("hidden")
  }
}

// Función para actualizar el contador de mensajes no leídos
function updateUnreadBadge() {
  if (unread > 0) {
    unreadBadge.textContent = unread.toString()
    unreadBadge.classList.remove("hidden")
    scrollDownBtn.setAttribute("data-count", unread.toString())
  } else {
    unreadBadge.classList.add("hidden")
    scrollDownBtn.removeAttribute("data-count")
  }
}

// Función para filtrar mensajes
function filterMessages(query) {
  const messages = msgsEl.querySelectorAll(".message")

  if (!query) {
    // Mostrar todos los mensajes si no hay consulta
    messages.forEach((msg) => msg.classList.remove("hidden"))
    return
  }

  query = query.toLowerCase()

  // Filtrar mensajes que coincidan con la consulta
  messages.forEach((msg) => {
    const source = msg.dataset.source || ""
    const content = msg.dataset.content || ""

    if (source.toLowerCase().includes(query) || content.toLowerCase().includes(query)) {
      msg.classList.remove("hidden")
    } else {
      msg.classList.add("hidden")
    }
  })
}
/* ---------- carga inicial (últimos PAGE) ---------- */
// Modificar la función de carga inicial para cargar también los nodos
;(async () => {
  // Cargar mensajes
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
        metrics: m.rssi !== undefined || m.snr !== undefined ? { rssi: m.rssi, snr: m.snr } : {},
      })

      // Actualizar el mensaje anterior
      prevMsg = { source: m.source, payload: m.payload }

      // Actualizar el estado del nodo si hay un ID de nodo
      if (m.source && m.source !== "sent" && m.source !== "?") {
        updateNodeStatus(m.source, {
          rssi: m.rssi,
          snr: m.snr,
          lastSeen: m.timestamp ? m.timestamp * 1000 : Date.now(),
          status: "online",
          source: m.source,
        })
      }
    }
  })

  // Cargar nodos
  try {
    const nodesRes = await fetch("/nodes")
    const { nodes } = await nodesRes.json()

    if (nodes && nodes.length > 0) {
      nodes.forEach((node) => {
        updateNodeStatus(node.id, {
          rssi: node.rssi,
          snr: node.snr,
          lastSeen: node.last_seen * 1000, // Convertir a milisegundos
          status: node.status,
          source: node.id,
        })
      })
    }
  } catch (error) {
    console.error("Error cargando nodos:", error)
  }

  // Guardar el último mensaje para comparar con nuevos WebSocket
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    lastMessage = { source: lastMsg.source, payload: lastMsg.payload }
  }

  scrollToBottom() // Asegurar scroll al fondo
  inputEl.focus()

  // Iniciar conexión WebSocket
  connectWebSocket()
})()

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

  // Reproducir sonido de envío si está habilitado
  if (soundsEnabled) {
    messageSentSound.play().catch((e) => console.error("Error reproduciendo sonido:", e))
  }

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

/* ---------- Eventos de opciones ---------- */
// Toggle para mostrar/ocultar el menú
settingsButton.addEventListener("click", (e) => {
  e.stopPropagation()
  settingsMenu.classList.toggle("hidden")
})

// Cerrar menú al hacer clic fuera
document.addEventListener("click", (e) => {
  if (!settingsMenu.contains(e.target) && e.target !== settingsButton) {
    settingsMenu.classList.add("hidden")
  }
})

// Toggle de notificaciones
document.getElementById("notificationsToggle").addEventListener("change", (e) => {
  notificationsEnabled = e.target.checked
  localStorage.setItem("notificationsEnabled", notificationsEnabled)

  if (notificationsEnabled && Notification.permission !== "granted") {
    requestNotificationPermission()
  }
})

// Toggle de sonidos
document.getElementById("soundsToggle").addEventListener("change", (e) => {
  soundsEnabled = e.target.checked
  localStorage.setItem("soundsEnabled", soundsEnabled)
})

// Toggle de métricas LoRa
document.getElementById("loraMetricsToggle").addEventListener("change", (e) => {
  loraMetricsEnabled = e.target.checked
  localStorage.setItem("loraMetricsEnabled", loraMetricsEnabled)

  // Actualizar la visualización de métricas en los mensajes existentes
  const metricsElements = document.querySelectorAll(".metrics")
  metricsElements.forEach((el) => {
    el.style.display = loraMetricsEnabled ? "flex" : "none"
  })

  // Actualizar la visualización de nodos
  renderNodesList()
})

/* ---------- Búsqueda de mensajes ---------- */
const searchInput = document.getElementById("searchInput")
const searchButton = document.getElementById("searchButton")

searchInput.addEventListener("input", (e) => {
  const query = e.target.value.trim()

  // Cancelar cualquier búsqueda pendiente
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }

  // Aplicar la búsqueda después de un pequeño retraso para evitar
  // muchas actualizaciones durante la escritura rápida
  searchTimeout = setTimeout(() => {
    searchQuery = query
    filterMessages(query)
  }, 300)
})

searchButton.addEventListener("click", () => {
  const query = searchInput.value.trim()
  searchQuery = query
  filterMessages(query)
})

// Permitir limpiar la búsqueda con la tecla ESC
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    searchInput.value = ""
    searchQuery = ""
    filterMessages("")
  }
})

// Actualizar la lista de nodos cada minuto
setInterval(renderNodesList, 60000)
