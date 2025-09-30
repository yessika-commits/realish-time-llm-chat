import * as api from './api.js';
import * as state from './state.js';
import * as ui from './ui.js';
import * as audio from './audio.js';
import * as websocket from './websocket.js';

// --- Event Handlers ---

async function handleChatSubmit(event) {
  event.preventDefault();
  audio.teardownHandsFreeListener(); // Stop listening after manual send
  const text = ui.elements.chatInput.value.trim();
  const imageFile = state.get('pendingImageFile');

  if (!text && !imageFile) return;

  if (!state.get('currentConversationId')) {
    await createNewConversation();
  }

  ui.setChatStatus("Thinking...");
  ui.elements.chatInput.value = "";
  state.set('pendingImageFile', null);

  const payload = {
    conversation_id: state.get('currentConversationId'),
    type: "text",
    text: text || "[image]",
  };

  if (imageFile) {
    try {
      const imageData = await api.media.uploadImage(imageFile);
      payload.image_path = imageData.relative_path;
    } catch (error) {
      ui.showAlert("Failed to upload image.", "error");
      ui.setChatStatus("Idle");
      return;
    }
  }

  ui.appendMessage({ role: 'user', content: payload.text, image_path: payload.image_path });
  state.set('currentAssistantBubble', null);
  websocket.sendMessage(payload);
}

async function handleAudioUpload(audioBlob) {
    if (!state.get('currentConversationId')) {
        await createNewConversation();
    }
    ui.setChatStatus("Transcribing...");
    try {
        const { relative_path } = await api.media.uploadAudio(audioBlob);
        ui.appendMessage({ role: 'user', content: '[voice message]', audio_path: relative_path });
        state.set('currentAssistantBubble', null);
        websocket.sendMessage({
            type: 'audio',
            conversation_id: state.get('currentConversationId'),
            audio_path: relative_path,
        });
    } catch (error) {
        ui.showAlert("Failed to upload audio.", "error");
        ui.setChatStatus("Idle");
        audio.armHandsFreeListener(); // Re-arm on failure
    }
}

function handleSocketMessage(payload) {
    if (payload.error) {
        ui.showAlert(`Connection error: ${payload.error}`, "error");
        ui.setChatStatus("Error");
        audio.armHandsFreeListener(); // Re-arm on error
        return;
    }

    switch (payload.type) {
        case "transcription":
            ui.setChatStatus("Thinking...");
            ui.applyTranscriptionToBubble(payload.data.audio_path, payload.data.content);
            break;
        case "assistant_delta":
            ui.setChatStatus("Responding...");
            ui.appendAssistantDelta(payload.data.content || "");
            break;
        case "assistant_audio":
            audio.playAudio(payload.data.audio_path);
            break;
        case "conversation_title":
            state.updateConversationTitle(payload.data.conversation_id, payload.data.title);
            if (state.get('currentConversationId') === payload.data.conversation_id) {
                ui.updateChatTitle(payload.data);
            }
            ui.renderConversationList(selectConversation, deleteConversation);
            break;
    }
}

async function createNewConversation() {
  try {
    const newConvo = await api.conversations.create({ title: "New Conversation" });
    state.addConversation(newConvo);
    await selectConversation(newConvo.id);
  } catch (error) {
    ui.showAlert("Failed to create conversation.", "error");
  }
}

async function selectConversation(id) {
    if (!id || state.get('currentConversationId') === id) return;
    
    state.set('currentConversationId', id);
    state.set('currentAssistantBubble', null);
    state.set('pendingImageFile', null);
    ui.elements.imageInput.value = '';

    audio.stopRecording();
    audio.teardownHandsFreeListener();
    websocket.close();

    ui.renderConversationList(selectConversation, deleteConversation);
    try {
        const conversation = await api.conversations.getById(id);
        ui.updateChatTitle(conversation);
        ui.renderMessages(conversation.messages);
        ui.setChatStatus("Idle");
        audio.armHandsFreeListener(); // Arm listener for the new conversation
    } catch (error) {
        ui.showAlert("Failed to load conversation.", "error");
    }
}

async function deleteConversation(id) {
    if (confirm("Are you sure you want to delete this conversation?")) {
        try {
            await api.conversations.delete(id);
            state.removeConversation(id);
            if (state.get('currentConversationId') === id) {
                state.set('currentConversationId', null);
                const conversations = state.get('conversations');
                if (conversations.length > 0) {
                    await selectConversation(conversations[0].id);
                } else {
                    ui.renderMessages([]);
                    ui.updateChatTitle(null);
                }
            }
            ui.renderConversationList(selectConversation, deleteConversation);
        } catch (error) {
            ui.showAlert("Failed to delete conversation.", "error");
        }
    }
}

function toggleRecording() {
    audio.teardownHandsFreeListener(); // Manual interaction disables passive listening
    if (ui.elements.micButton.classList.contains("recording")) {
        audio.stopRecording();
    } else {
        if (!state.get('currentConversationId')) {
            createNewConversation().then(() => audio.startRecording());
        } else {
            audio.startRecording();
        }
    }
}

async function saveSettings(event) {
    event.preventDefault();
    const payload = {
        audio: {
            vad_silence_ms: parseInt(ui.elements.vadSilenceInput.value, 10),
            enable_voice_output: ui.elements.enableVoiceOutput.checked,
        },
    };
    try {
        const newSettings = await api.settings.update(payload);
        state.set('settings', newSettings);
        ui.toggleSettingsPanel(false);
        ui.showAlert("Settings saved.", "info");
    } catch (error) {
        ui.showAlert("Failed to save settings.", "error");
    }
}

// --- Initialization ---

function bindEvents() {
  ui.elements.chatForm.addEventListener("submit", handleChatSubmit);
  ui.elements.newConversationBtn.addEventListener("click", createNewConversation);
  ui.elements.clearConversationsBtn.addEventListener("click", async () => {
    if (confirm("Delete all conversations?")) {
        await api.conversations.deleteAll();
        state.set('conversations', []);
        state.set('currentConversationId', null);
        ui.renderConversationList(selectConversation, deleteConversation);
        ui.renderMessages([]);
        ui.updateChatTitle(null);
    }
  });
  ui.elements.micButton.addEventListener("click", toggleRecording);
  ui.elements.stopAudioBtn.addEventListener("click", () => {
      audio.stopAllPlayback();
      audio.armHandsFreeListener(); // Re-arm after manually stopping
  });
  ui.elements.volumeSlider.addEventListener("input", (e) => audio.setPlaybackVolume(parseFloat(e.target.value)));
  ui.elements.attachImageBtn.addEventListener("click", () => ui.elements.imageInput.click());
  ui.elements.imageInput.addEventListener("change", (e) => {
    if (e.target.files.length) state.set('pendingImageFile', e.target.files[0]);
  });
  
  // **FIXED**: Added event listener for the hands-free toggle
  ui.elements.handsFreeToggle.addEventListener("change", (e) => {
      state.set('handsFreeEnabled', e.target.checked);
      if (e.target.checked) {
          audio.armHandsFreeListener();
      } else {
          audio.teardownHandsFreeListener();
      }
  });
  
  // Settings Panel
  ui.elements.openSettingsBtn.addEventListener("click", () => ui.toggleSettingsPanel(true));
  ui.elements.closeSettingsBtn.addEventListener("click", () => ui.toggleSettingsPanel(false));
  ui.elements.settingsForm.addEventListener("submit", saveSettings);
}

async function bootstrap() {
  bindEvents();
  websocket.onMessage(handleSocketMessage);
  audio.init(handleAudioUpload);
  
  try {
    const settingsData = await api.settings.get();
    state.set('settings', settingsData);
    ui.populateSettingsForm(settingsData);

    // Set initial hands-free state from the checkbox default
    state.set('handsFreeEnabled', ui.elements.handsFreeToggle.checked);

    const conversationsData = await api.conversations.getAll();
    state.set('conversations', conversationsData);
    
    if (conversationsData.length > 0) {
        await selectConversation(conversationsData[0].id);
    } else {
        ui.renderConversationList(selectConversation, deleteConversation);
        audio.armHandsFreeListener(); // Arm listener if no conversations exist
    }
    
    await ui.populateMicrophoneList();
  } catch (error) {
    ui.showAlert("Failed to initialize the application.", "error");
  }
}

// Start the application
bootstrap();