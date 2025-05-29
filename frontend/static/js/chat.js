const LOCAL_SOURCE = "web_user_" + Date.now()
const PAGE = 50 // carga inicial
const MAX_CHARS = 150 // máximo de caracteres permitidos
const SCROLL_THRESHOLD = 100 // píxeles desde el fondo para considerar "cerca del final"
const MAX_RECONNECT_DELAY = 5000 // máximo delay para reconexión en ms
const WEBSOCKET_TIMEOUT = 3000 // tiempo antes de considerar la conexión como fallida

/* ---------- DOM ---------- */
const msgsEl = document.getElementById("msgs")
const badgeEl = document.getElementById("unreadBadge") // Corrected ID
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
  '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>'
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
let bridgeNodeId = null // ID del nodo puente

/* ---------- Configuración del contador de caracteres ---------- */
charCountEl.className = "char-count"
charCountEl.textContent = `0/${MAX_CHARS}`
formEl.insertBefore(charCountEl, formEl.querySelector("button"))

const recordAudioBtn = document.createElement("button")
recordAudioBtn.innerHTML = "🎤" // Icono de micrófono
recordAudioBtn.title = "Grabar audio (max 10s)"
recordAudioBtn.type = "button" // Para no enviar el formulario
recordAudioBtn.classList.add("action-btn") // Añadir una clase para estilizar

const uploadImageBtn = document.createElement("input")
uploadImageBtn.type = "file"
uploadImageBtn.accept = "image/*"
uploadImageBtn.style.display = "none" // Oculto, se activa con un botón
const uploadImageLabel = document.createElement("label")
uploadImageLabel.innerHTML = "🖼️" // Icono de imagen
uploadImageLabel.title = "Enviar imagen"
uploadImageLabel.classList.add("action-btn")
uploadImageLabel.htmlFor = "imageUploadInput" // Asociar con el input
uploadImageBtn.id = "imageUploadInput"

// Añadir botones al formulario
// Insertar antes del input de texto
const sendButton = formEl.querySelector("button[type='submit']")
formEl.insertBefore(recordAudioBtn, inputEl)
formEl.insertBefore(uploadImageLabel, inputEl)
formEl.appendChild(uploadImageBtn) // El input oculto

let mediaRecorder
let audioChunks = []
let audioRecordingTimeout
const MAX_AUDIO_DURATION_MS = 10000 // 10 segundos

recordAudioBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop()
    if (audioRecordingTimeout) clearTimeout(audioRecordingTimeout)
    recordAudioBtn.innerHTML = "🎤"
    recordAudioBtn.title = "Grabar audio (max 10s)"
    recordAudioBtn.disabled = false
  } else {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert(
          "La API MediaDevices no está disponible en este navegador o contexto (¿HTTPS?). No se puede grabar audio.",
        )
        recordAudioBtn.disabled = false // Re-enable button
        recordAudioBtn.innerHTML = "🎤"
        return
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" }) // Intentar con opus para mejor compresión si el navegador lo soporta
      audioChunks = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        recordAudioBtn.disabled = false
        recordAudioBtn.innerHTML = "🎤"
        if (audioChunks.length === 0) {
          console.log("No audio data recorded.")
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType })

        // Crear un nombre de archivo único
        const filename = `voice_msg_${Date.now()}.${mediaRecorder.mimeType.split("/")[1].split(";")[0]}`

        const formData = new FormData()
        const metadata = {
          action: "send_lora_audio",
          original_content_type: audioBlob.type,
          filename: `voice_message_${Date.now()}.${audioBlob.type.split("/")[1] || "webm"}`,
          source_id: LOCAL_SOURCE,
        }
        formData.append("metadata_json", JSON.stringify(metadata))
        formData.append("file", audioBlob, metadata.filename)

        try {
          // Mostrar mensaje de "Enviando audio..." en la UI localmente
          const metadataFilename = metadata.filename // Use the filename from the metadata object
          addBubble({
            payload: `Enviando audio: ${metadataFilename}...`,
            source: LOCAL_SOURCE,
            time: new Date().toLocaleTimeString().slice(0, 5),
            content_type: "system_message", // Un tipo especial para mensajes del sistema
          })

          const response = await fetch("/command_bridge/", {
            method: "POST",
            body: formData,
          })
          const result = await response.json()
          if (response.ok) {
            console.log("Audio instruction sent to backend:", result)
            // No añadir burbuja aquí, el mensaje de "Enviando..." ya está.
            // La confirmación real vendría si el puente LoRa ACKs o algo similar (más complejo)
          } else {
            console.error("Error sending audio instruction:", result)
            addBubble({
              payload: `Error enviando audio: ${result.error || "Error desconocido"}`,
              source: LOCAL_SOURCE,
              time: new Date().toLocaleTimeString().slice(0, 5),
              content_type: "error_message",
            })
          }
        } catch (error) {
          console.error("Error enviando audio al backend:", error)
          addBubble({
            payload: `Error de red al enviar audio.`,
            source: LOCAL_SOURCE,
            time: new Date().toLocaleTimeString().slice(0, 5),
            content_type: "error_message",
          })
        }
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.start()
      recordAudioBtn.innerHTML = "🛑"
      recordAudioBtn.title = "Detener grabación"
      recordAudioBtn.disabled = true // Deshabilitar mientras se procesa el stop

      // Iniciar temporizador para detener automáticamente
      audioRecordingTimeout = setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
          mediaRecorder.stop()
          recordAudioBtn.innerHTML = "🎤" // Reset icon
          recordAudioBtn.title = "Grabar audio (max 10s)"
          console.log("Grabación detenida por límite de tiempo.")
        }
      }, MAX_AUDIO_DURATION_MS)
    } catch (err) {
      console.error("Error al acceder al micrófono:", err)
      alert("No se pudo acceder al micrófono. Asegúrate de dar permisos.")
      recordAudioBtn.disabled = false
    }
  }
})

uploadImageBtn.addEventListener("change", async (event) => {
  const file = event.target.files[0]
  if (file) {
    const formData = new FormData()
    const metadata = {
      action: "send_lora_image", // Similar para imágenes
      original_content_type: file.type,
      filename: file.name,
      source_id: LOCAL_SOURCE,
    }
    formData.append("metadata_json", JSON.stringify(metadata))
    formData.append("file", file, file.name)

    try {
      // This is already correct, file.name is the right one here.
      addBubble({
        payload: `Enviando imagen: ${file.name}...`,
        source: LOCAL_SOURCE,
        time: new Date().toLocaleTimeString().slice(0, 5),
        content_type: "system_message",
      })

      const response = await fetch("/command_bridge/", {
        method: "POST",
        body: formData,
      })
      const result = await response.json()
      if (response.ok) {
        console.log("Image instruction sent to backend:", result)
      } else {
        console.error("Error sending image instruction:", result)
        addBubble({
          payload: `Error enviando imagen: ${result.error || "Error desconocido"}`,
          source: LOCAL_SOURCE,
          time: new Date().toLocaleTimeString().slice(0, 5),
          content_type: "error_message",
        })
      }
    } catch (error) {
      console.error("Error enviando imagen al backend:", error)
      addBubble({
        payload: `Error de red al enviar imagen.`,
        source: LOCAL_SOURCE,
        time: new Date().toLocaleTimeString().slice(0, 5),
        content_type: "error_message",
      })
    }
    uploadImageBtn.value = ""
  }
})

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

  // Actualizar estado del nodo puente
  updateBridgeNodeStatus()
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
    console.log("WebSocket received:", data) // Log all incoming messages for debugging

    // Handle node status updates separately
    if (data.type === "nodes_update" || data.type === "all_nodes_status") {
      if (data.nodes && Array.isArray(data.nodes)) {
        // Ensure nodes is an array
        data.nodes.forEach((node) => {
          updateNodeStatus(node.id, {
            rssi: node.rssi,
            snr: node.snr,
            lastSeen: node.last_seen ? node.last_seen * 1000 : Date.now(),
            status: node.status,
            source: node.id, // Ensure source is set for updateNodeStatus
            isBridge: node.is_bridge === true,
          })
        })
      } else if (
        data.nodes &&
        typeof data.nodes === "object" &&
        Object.keys(data.nodes).length === 0 &&
        data.type === "all_nodes_status"
      ) {
        // Handles the case: {"type": "all_nodes_status", "nodes": {}} - no nodes to update
        console.log("Received all_nodes_status with empty nodes object.")
      } else if (data.type === "all_nodes_status" && !data.nodes) {
        console.log("Received all_nodes_status without a nodes field or empty nodes.")
      } else {
        console.warn("Received nodes_update/all_nodes_status with unexpected nodes structure:", data.nodes)
      }
      return // Do not proceed to addBubble for node updates
    }

    // Destructure properties for chat messages, providing defaults
    const {
      payload, // This will be the main text or filename for display
      source = "?",
      rssi,
      snr,
      timestamp,
      type, // General message type from backend if any
      content_type = "text/plain", // Default to text if not specified
      data_b64, // For binary data of audio/image
      node_id_lora, // Actual LoRa node ID that sent the message
      filename, // Filename for audio/image
    } = data

    const effectiveSource = node_id_lora || source

    // Update LoRa node status if it's a message from a LoRa node
    if (node_id_lora && node_id_lora !== "sent" && node_id_lora !== "?") {
      updateNodeStatus(node_id_lora, {
        // Use node_id_lora here
        rssi,
        snr,
        lastSeen: timestamp ? timestamp * 1000 : Date.now(),
        status: "online",
        source: node_id_lora, // Pass node_id_lora as source for consistency
        isBridge: data.is_bridge === true, // Check if this info is available/relevant here
      })
    }

    // Ignore specific non-chat message types if they weren't caught earlier
    if (type === "bridge" || (content_type === "text/plain" && payload === "online")) {
      console.log("Ignoring bridge status or 'online' ping message for chat display.")
      return
    }

    // Determine display payload for addBubble
    let displayPayloadForBubble = payload
    if (filename && (content_type.startsWith("audio/") || content_type.startsWith("image/"))) {
      displayPayloadForBubble = filename // Use filename for display if it's media
    } else if (!payload && filename) {
      // Fallback if payload is missing but filename exists for media
      displayPayloadForBubble = filename
    } else if (!payload && !filename && content_type.startsWith("audio/")) {
      displayPayloadForBubble = "Mensaje de voz"
    } else if (!payload && !filename && content_type.startsWith("image/")) {
      displayPayloadForBubble = "Imagen"
    }

    // Check if the message matches the current search query
    const messageMatchesSearch =
      !searchQuery ||
      (displayPayloadForBubble &&
        typeof displayPayloadForBubble === "string" &&
        displayPayloadForBubble.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (effectiveSource && effectiveSource.toLowerCase().includes(searchQuery.toLowerCase()))

    addBubble({
      payload: displayPayloadForBubble,
      source: effectiveSource,
      time: new Date(timestamp ? timestamp * 1000 : Date.now()).toLocaleTimeString().slice(0, 5),
      metrics: { rssi, snr },
      hidden: searchQuery && !messageMatchesSearch,
      content_type: content_type,
      data_b64: data_b64,
      filename: filename, // Pass filename to addBubble
    })

    lastMessage = { source: effectiveSource, payload: displayPayloadForBubble }

    // Notifications and sounds for messages not from local user
    if (effectiveSource !== LOCAL_SOURCE) {
      if (soundsEnabled) {
        notificationSound.play().catch((e) => console.error("Error reproduciendo sonido:", e))
      }
      if (notificationsEnabled && notificationPermission === "granted" && !document.hasFocus()) {
        showNotification(effectiveSource, displayPayloadForBubble)
      }
      if (!isNearBottom) {
        unread++
        updateUnreadBadge()
      }
    }
  } catch (error) {
    console.error("Error procesando mensaje WebSocket:", error, "Raw Data:", e.data)
  }
}

// Función para actualizar el estado del nodo puente basado en la conexión WebSocket
function updateBridgeNodeStatus() {
  // Actualizar el estado de todos los nodos marcados como puente
  connectedNodes.forEach((node, nodeId) => {
    if (node.isBridge) {
      bridgeNodeId = nodeId // Guardar el ID del nodo puente
      node.status = wsConnected ? "online" : "offline"
      node.lastSeen = new Date()
    }
  })

  // Actualizar la visualización de nodos
  renderNodesList()
}

// Modificar la función updateNodeStatus para manejar el estado online/offline
function updateNodeStatus(nodeId, data) {
  if (!nodeId) return

  const now = new Date()
  const lastSeen = data.lastSeen ? new Date(data.lastSeen) : now
  const isBridge = data.isBridge === true

  // Si es un nodo puente, actualizar el bridgeNodeId
  if (isBridge) {
    bridgeNodeId = nodeId
  }

  // Actualizar o crear entrada del nodo
  connectedNodes.set(nodeId, {
    ...data,
    id: nodeId,
    lastSeen: lastSeen,
    status: data.status || "online",
    isBridge: isBridge,
  })

  // Actualizar la visualización de nodos
  renderNodesList()

  // Configurar un temporizador para marcar los nodos como offline después de un tiempo
  // Solo para nodos que no son puente (los puentes se actualizan con el estado de WebSocket)
  if (!isBridge) {
    setTimeout(() => {
      const node = connectedNodes.get(nodeId)
      if (node && !node.isBridge && now - new Date(node.lastSeen) >= NODE_TIMEOUT) {
        node.status = "offline"
        renderNodesList()
      }
    }, NODE_TIMEOUT)
  }
}

// Modificar la función renderNodesList para usar datos reales
function renderNodesList() {
  const nodesListEl = document.getElementById("nodesList")

  if (connectedNodes.size === 0) {
    nodesListEl.innerHTML = '<div class="no-nodes">No hay nodos conectados</div>'
    return
  }

  let nodesHtml = ""

  // Separar nodos puente de nodos LoRa remotos
  const bridgeNodes = Array.from(connectedNodes.entries()).filter(([nodeId, node]) => node.isBridge)
  const loraNodes = Array.from(connectedNodes.entries()).filter(([nodeId, node]) => !node.isBridge)

  // Mostrar primero el nodo puente
  bridgeNodes.forEach(([nodeId, node]) => {
    const isOnline = node.status === "online"
    const statusClass = isOnline ? "online" : "offline"
    const lastSeen = node.lastSeen ? new Date(node.lastSeen) : new Date()

    nodesHtml += `
      <div class="node-item bridge-node">
        <div class="node-info">
          <span class="node-name">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="bridge-icon">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="17" x2="12" y2="21"></line>
            </svg>
            ${nodeId} (Puente Local)
          </span>
          <span class="status-indicator ${statusClass}"></span>
        </div>
        <div class="node-description">
          Nodo puente conectado a la red local
        </div>
        <div class="node-last-seen">
          Estado: ${isOnline ? "Conectado" : "Desconectado"}
        </div>
      </div>
    `
  })

  // Luego mostrar los nodos LoRa remotos
  loraNodes.forEach(([nodeId, node]) => {
    const isOnline = node.status === "online"
    const statusClass = isOnline ? "online" : "offline"
    const lastSeen = node.lastSeen ? new Date(node.lastSeen) : new Date()

    nodesHtml += `
      <div class="node-item lora-node">
        <div class="node-info">
          <span class="node-name">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lora-icon">
              <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
              <path d="M2 17l10 5 10-5"></path>
              <path d="M2 12l10 5 10-5"></path>
            </svg>
            ${nodeId}
          </span>
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

  // Si no hay nodos, mostrar mensaje
  if (bridgeNodes.length === 0 && loraNodes.length === 0) {
    nodesHtml = '<div class="no-nodes">No hay nodos conectados</div>'
  }

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
function addBubble({
  payload,
  source,
  time,
  metrics = {},
  hidden = false,
  content_type = "text/plain",
  data_b64 = null,
  filename = null, // Add filename here
}) {
  let displayablePayload = payload // This is what's shown as text or alt text
  let dataContent = payload // For dataset.content

  if (filename && (content_type.startsWith("audio/") || content_type.startsWith("image/"))) {
    displayablePayload = filename
    dataContent = filename
  } else if (typeof payload !== "string" && !filename) {
    // Fallback if payload is not a string and no filename (e.g. for old messages)
    if (content_type.startsWith("audio/")) displayablePayload = "Mensaje de voz"
    else if (content_type.startsWith("image/")) displayablePayload = "Imagen"
    else displayablePayload = "Mensaje" // Generic
    dataContent = displayablePayload
  }

  const wrap = document.createElement("div")
  wrap.className = "message"

  wrap.dataset.source = source
  wrap.dataset.content = typeof dataContent === "string" ? dataContent : JSON.stringify(dataContent)

  const senderPrefixText = (source === LOCAL_SOURCE ? "Yo" : source) + ": "

  if (content_type.startsWith("audio/") && data_b64) {
    const audioPlayer = document.createElement("audio")
    audioPlayer.controls = true
    audioPlayer.src = `data:${content_type};base64,${data_b64}`

    const senderSpan = document.createElement("span")
    senderSpan.textContent = senderPrefixText // Use the text prefix
    wrap.appendChild(senderSpan)

    const fileNameSpan = document.createElement("span")
    fileNameSpan.textContent = displayablePayload // Show filename or "Mensaje de voz"
    fileNameSpan.style.marginRight = "5px"
    wrap.appendChild(fileNameSpan)

    wrap.appendChild(audioPlayer)
  } else if (content_type.startsWith("image/") && data_b64) {
    const imgEl = document.createElement("img")
    imgEl.src = `data:${content_type};base64,${data_b64}`
    imgEl.style.maxWidth = "200px"
    imgEl.style.maxHeight = "200px"
    imgEl.alt = displayablePayload // Use filename or "Imagen" as alt

    const senderSpan = document.createElement("span")
    senderSpan.textContent = senderPrefixText
    wrap.appendChild(senderSpan)
    wrap.appendChild(imgEl)

    // Optionally display filename below image
    const fileNameDiv = document.createElement("div")
    fileNameDiv.textContent = displayablePayload
    fileNameDiv.style.fontSize = "0.8em"
    fileNameDiv.style.color = "grey"
    wrap.appendChild(fileNameDiv)
  } else if (content_type === "system_message" || content_type === "error_message") {
    wrap.textContent = displayablePayload
    if (content_type === "error_message") wrap.classList.add("error")
  } else {
    wrap.textContent = senderPrefixText + displayablePayload
  }

  const ts = document.createElement("span")
  ts.className = "time"
  ts.textContent = time
  wrap.appendChild(ts)

  if (
    loraMetricsEnabled &&
    (metrics.rssi !== undefined || metrics.snr !== undefined) &&
    !content_type.startsWith("system") &&
    !content_type.startsWith("error")
  ) {
    const metricsEl = document.createElement("div")
    metricsEl.className = "metrics"

    if (metrics.rssi !== undefined && metrics.rssi !== null) {
      const rssiEl = document.createElement("span")
      rssiEl.className = "rssi"
      rssiEl.textContent = `RSSI: ${metrics.rssi} dBm`
      metricsEl.appendChild(rssiEl)
    }

    if (metrics.snr !== undefined && metrics.snr !== null) {
      const snrEl = document.createElement("span")
      snrEl.className = "snr"
      snrEl.textContent = `SNR: ${metrics.snr} dB`
      metricsEl.appendChild(snrEl)
    }
    if (metricsEl.hasChildNodes()) {
      wrap.appendChild(metricsEl)
    }
  }

  msgsEl.appendChild(wrap)

  if (isNearBottom) {
    scrollToBottom()
  } else {
    scrollDownBtn.classList.remove("hidden")
  }
}

// En handleWebSocketMessage:

// En la carga inicial de mensajes:
// ;(async () => {

/* ---------- enviar ---------- */
formEl.addEventListener("submit", async (e) => {
  e.preventDefault()
  const textMessage = inputEl.value.trim()
  if (!textMessage || textMessage.length > MAX_CHARS) return

  // Mostrar inmediatamente el mensaje enviado en el chat
  const time = new Date().toLocaleTimeString().slice(0, 5)
  addBubble({
    payload: textMessage,
    source: LOCAL_SOURCE,
    time: time,
  })

  // Reproducir sonido de envío si está habilitado
  if (soundsEnabled) {
    messageSentSound.play().catch((e) => console.error("Error reproduciendo sonido:", e))
  }

  // Actualizar el último mensaje para evitar duplicados
  lastMessage = { source: LOCAL_SOURCE, payload: textMessage }

  // Enviar al servidor
  try {
    const payload = { message: textMessage, source_id: LOCAL_SOURCE }
    await fetch("/publish_text", {
      // <--- NEW ENDPOINT
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

// Actualizar estado del nodo puente cada 5 segundos
setInterval(updateBridgeNodeStatus, 5000)

function updateUnreadBadge() {
  badgeEl.textContent = unread.toString()
  badgeEl.classList.toggle("hidden", unread === 0)
}

function scrollToBottom() {
  msgsEl.scrollTop = msgsEl.scrollHeight
  scrollDownBtn.classList.add("hidden")
  isNearBottom = true
  unread = 0
  updateUnreadBadge()
}

function checkIfNearBottom() {
  isNearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < SCROLL_THRESHOLD
  if (isNearBottom) {
    scrollDownBtn.classList.add("hidden")
    unread = 0
    updateUnreadBadge()
  } else {
    scrollDownBtn.classList.remove("hidden")
  }
}

function filterMessages(query) {
  const messages = document.querySelectorAll(".message")
  messages.forEach((message) => {
    const content = message.dataset.content.toLowerCase()
    if (content.includes(query.toLowerCase())) {
      message.classList.remove("hidden")
    } else {
      message.classList.add("hidden")
    }
  })
}
// Cargar mensajes al iniciar
;(async () => {
  const storedMessages = localStorage.getItem("chatMessages")
  let messages = []
  if (storedMessages) {
    try {
      messages = JSON.parse(storedMessages)
    } catch (error) {
      console.error("Error parsing stored messages:", error)
      localStorage.removeItem("chatMessages") // Limpiar si hay error
    }
  }

  // Invertir el orden de los mensajes para mostrar los más recientes primero
  messages.reverse()

  // Limpiar el contenedor de mensajes antes de agregar los mensajes cargados
  msgsEl.innerHTML = ""

  // Variables para evitar duplicados visuales
  // let prevMsg = { source: null, payload: null, timestamp: null };

  messages.forEach((m) => {
    // Evitar duplicados visuales estrictos (podría ser necesario ajustar esta lógica)
    // if (m.source !== prevMsg.source || m.payload !== prevMsg.payload || m.timestamp !== prevMsg.timestamp) {
    let displayPayload = m.payload
    if (m.content_type && m.content_type.startsWith("audio/")) {
      displayPayload = m.filename || "Mensaje de voz"
    } else if (m.content_type && m.content_type.startsWith("image/")) {
      displayPayload = m.filename || "Imagen"
    }

    addBubble({
      payload: displayPayload,
      source: m.source,
      time: new Date(m.timestamp ? m.timestamp * 1000 : Date.now()).toLocaleTimeString().slice(0, 5),
      metrics: m.rssi !== undefined || m.snr !== undefined ? { rssi: m.rssi, snr: m.snr } : {},
      content_type: m.content_type || "text/plain",
      data_b64: m.data_b64,
      filename: m.filename, // Pass filename from stored message
    })
    // prevMsg = { source: m.source, payload: displayPayload, timestamp: m.timestamp }; // Actualizar prevMsg

    if (m.source && m.source !== "sent" && m.source !== "?") {
      updateNodeStatus(m.source, {
        rssi: m.rssi,
        snr: m.snr,
        lastSeen: m.timestamp ? m.timestamp * 1000 : Date.now(),
        status: "online",
        source: m.source,
        isBridge: m.is_bridge === true,
      })
    }
    // }
  })
})()

// Iniciar conexión WebSocket
connectWebSocket()
