/**
 * Centralized application state management.
 */
const state = {
  conversations: [],
  currentConversationId: null,
  settings: null,
  socket: null,
  audioQueue: [],
  currentAssistantBubble: null,
  pendingTranscriptions: new Map(),
  handsFreeEnabled: true,
  awaitingHandsFreeRestart: false,
  pendingImageFile: null,
};

export function get(key) {
  return state[key];
}

export function set(key, value) {
  state[key] = value;
}

export function updateConversationTitle(id, title) {
    const conversation = state.conversations.find(c => c.id === id);
    if (conversation) {
        conversation.title = title;
    }
}

export function addConversation(conversation) {
    state.conversations.unshift(conversation);
}

export function removeConversation(id) {
    state.conversations = state.conversations.filter(c => c.id !== id);
}

export function addAudioToQueue(audio) {
  state.audioQueue.push(audio);
}

export function removeAudioFromQueue(audio) {
  state.audioQueue = state.audioQueue.filter((item) => item !== audio);
}

export function clearAudioQueue() {
    for (const audio of state.audioQueue) {
        try {
            audio.pause();
            audio.src = ''; // Release resource
        } catch (e) {
            console.debug("Failed to clear audio source", e);
        }
    }
    state.audioQueue = [];
}