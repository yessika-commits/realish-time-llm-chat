import { API_BASE } from './config.js';
import * as state from './state.js';

/**
 * Caches all DOM element references for performance.
 */
export const elements = {
  conversationList: document.getElementById("conversation-list"),
  newConversationBtn: document.getElementById("new-conversation"),
  clearConversationsBtn: document.getElementById("clear-conversations"),
  chatLog: document.getElementById("chat-log"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  chatTitle: document.getElementById("chat-title"),
  chatStatus: document.getElementById("chat-status"),
  imageInput: document.getElementById("image-input"),
  attachImageBtn: document.getElementById("attach-image"),
  micButton: document.getElementById("mic-button"),
  micSelect: document.getElementById("microphone-select"),
  volumeSlider: document.getElementById("volume-slider"),
  handsFreeToggle: document.getElementById("handsfree-toggle"),
  stopAudioBtn: document.getElementById("stop-audio"),
  settingsPanel: document.getElementById("settings-panel"),
  openSettingsBtn: document.getElementById("open-settings"),
  closeSettingsBtn: document.getElementById("close-settings"),
  settingsForm: document.getElementById("settings-form"),
  vadSilenceInput: document.getElementById("vad-silence"),
  enableVoiceOutput: document.getElementById("enable-voice-output"),
  alertContainer: document.getElementById("alert-container"),
};

// **FIXED**: Exported this function so other modules can use it.
export function makeMediaUrl(path) {
    if (!path) return "";
    const safePath = String(path).replace(/\\/g, "/");
    if (safePath.startsWith("http")) return safePath;
    const normalized = safePath.startsWith("/media/") ? safePath : `/media/${safePath}`;
    return `${API_BASE}${normalized}`;
}

function formatTimestamp(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function renderConversationList(onSelect, onDelete) {
  elements.conversationList.innerHTML = "";
  const conversations = state.get('conversations');
  const currentId = state.get('currentConversationId');

  for (const conversation of conversations) {
    const item = document.createElement("li");
    item.className = conversation.id === currentId ? "active" : "";
    item.innerHTML = `
      <div class="conversation-row">
        <span class="conversation-title">${conversation.title}</span>
        <button type="button" class="delete-conversation">✕</button>
      </div>
      <span class="meta">${formatTimestamp(conversation.updated_at || conversation.created_at)}</span>
    `;
    item.addEventListener("click", () => onSelect(conversation.id));
    item.querySelector(".delete-conversation").addEventListener("click", (e) => {
      e.stopPropagation();
      onDelete(conversation.id);
    });
    elements.conversationList.appendChild(item);
  }
}

export function renderMessages(messages) {
  elements.chatLog.innerHTML = "";
  messages.forEach(appendMessage);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

export function appendMessage(message) {
  const bubble = document.createElement("div");
  bubble.classList.add("chat-message", message.role);

  // **FIXED**: Always create a div for text content to ensure `firstElementChild` is never null.
  const sanitizedContent = (message.content || '').replace(/\[voice message\]/g, '');
  let contentHTML = `<div>${sanitizedContent}</div>`;

  if (message.audio_path) {
      const audioSrc = makeMediaUrl(message.audio_path);
      bubble.dataset.audioPath = message.audio_path;
      contentHTML += `<audio controls src="${audioSrc}"></audio>`;
  }
  if (message.image_path) {
      const imgSrc = makeMediaUrl(message.image_path);
      contentHTML += `<img src="${imgSrc}" alt="attachment" class="message-image">`;
  }

  bubble.innerHTML = contentHTML;
  elements.chatLog.appendChild(bubble);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;

  if (message.role === 'assistant') {
      state.set('currentAssistantBubble', bubble);
  }
}

export function appendAssistantDelta(fragment) {
  let bubble = state.get('currentAssistantBubble');
  if (!bubble || bubble.classList.contains("user")) {
    appendMessage({ role: "assistant", content: "" });
    bubble = state.get('currentAssistantBubble');
  }
  // This will now be safe to call because the inner div always exists.
  bubble.firstElementChild.textContent += fragment;
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

export function applyTranscriptionToBubble(audioPath, transcription) {
    const bubble = elements.chatLog.querySelector(`[data-audio-path="${audioPath}"]`);
    if (bubble) {
        let textDiv = bubble.querySelector('div');
        if (!textDiv) {
            textDiv = document.createElement('div');
            bubble.prepend(textDiv);
        }
        textDiv.textContent = transcription;
    }
}


export function updateChatTitle(conversation) {
  elements.chatTitle.textContent = conversation?.title || "Realtime Assistant";
  elements.chatTitle.dataset.conversationId = conversation?.id || "";
}

export function setChatStatus(text) {
  elements.chatStatus.textContent = text;
}

export function setRecordingState(isRecording) {
  if (isRecording) {
    elements.micButton.textContent = "⏹";
    elements.micButton.classList.add("recording");
    setChatStatus("Recording...");
  } else {
    elements.micButton.textContent = "🎤";
    elements.micButton.classList.remove("recording");
    setChatStatus("Idle");
  }
}

export function toggleSettingsPanel(show) {
  elements.settingsPanel.classList.toggle("hidden", !show);
}

export function populateSettingsForm(settings) {
  elements.vadSilenceInput.value = settings.audio.vad_silence_ms;
  elements.enableVoiceOutput.checked = settings.audio.enable_voice_output;
}

export async function populateMicrophoneList() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        elements.micSelect.innerHTML = "";
        devices
            .filter(device => device.kind === "audioinput")
            .forEach(device => {
                const option = document.createElement("option");
                option.value = device.deviceId;
                option.textContent = device.label || `Microphone ${elements.micSelect.length + 1}`;
                elements.micSelect.appendChild(option);
            });
    } catch (error) {
        console.error("Could not list microphones", error);
        showAlert("Could not access microphone devices.", "error");
    }
}

export function showAlert(message, type = "info", timeout = 5000) {
  const alert = document.createElement("div");
  alert.className = `alert ${type}`;
  alert.innerHTML = `<span>${message}</span><button>&times;</button>`;
  alert.querySelector("button").addEventListener("click", () => alert.remove());
  elements.alertContainer.appendChild(alert);
  if (timeout) {
    setTimeout(() => alert.remove(), timeout);
  }
}