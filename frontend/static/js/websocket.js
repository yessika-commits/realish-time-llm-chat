import { WEBSOCKET_URL } from './config.js';

let socket = null;
let messageHandler = null;

function ensureSocket() {
  return new Promise((resolve, reject) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      return resolve(socket);
    }

    if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.CLOSING)) {
        // Wait for the connection to resolve
        const checkState = () => {
            if (socket.readyState === WebSocket.OPEN) resolve(socket);
            else if (socket.readyState === WebSocket.CLOSED) reject(new Error("Socket closed before opening."));
            else setTimeout(checkState, 100);
        };
        checkState();
        return;
    }

    socket = new WebSocket(WEBSOCKET_URL);

    socket.onmessage = (event) => {
      if (messageHandler) {
        try {
          const payload = JSON.parse(event.data);
          messageHandler(payload);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      }
    };

    socket.onopen = () => {
      console.log("WebSocket connected");
      resolve(socket);
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      reject(error);
      socket = null; // Allow reconnection
    };

    socket.onclose = () => {
      console.log("WebSocket closed");
      socket = null; // Allow reconnection
    };
  });
}

/**
 * Sets a single callback function to handle incoming WebSocket messages.
 * @param {function} handler - The function to call with the parsed message payload.
 */
export function onMessage(handler) {
  messageHandler = handler;
}

/**
 * Sends a JSON payload over the WebSocket.
 * @param {object} payload - The data to send.
 */
export async function sendMessage(payload) {
  try {
    const connectedSocket = await ensureSocket();
    connectedSocket.send(JSON.stringify(payload));
  } catch (error) {
    console.error("Failed to send WebSocket message:", error);
    // Optionally re-throw or show an alert to the user
    throw new Error("Connection failed. Please try again.");
  }
}

/**
 * Closes the WebSocket connection if it's open.
 */
export function close() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
}