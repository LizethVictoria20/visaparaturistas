// Conectar al servidor Socket.IO con WebSocket y fallback a polling
const socket = io("https://visaparaturistas.onrender.com", {
  transports: ["websocket", "polling"],
});

// Escuchar eventos de conexión
socket.on("connect", () => {
  console.log("Conectado al servidor");
});
