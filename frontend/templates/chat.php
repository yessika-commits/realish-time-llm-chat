<div class="sidebar">
    <div class="sidebar-header">
        <h1>Conversations</h1>
        <button id="new-conversation">New</button>
        <button id="clear-conversations" class="secondary">Clear All</button>
    </div>
    <ul id="conversation-list"></ul>
</div>

<div class="chat-panel">
    <header class="chat-header">
        <div class="chat-title" contenteditable="true" id="chat-title">Realtime Assistant</div>
        <div class="chat-status" id="chat-status">Idle</div>
        <button id="open-settings">Settings</button>
    </header>
    <div id="alert-container" class="alerts"></div>
    <div id="chat-log" class="chat-log"></div>
    <footer class="chat-footer">
        <form id="chat-form">
            <input type="text" id="chat-input" placeholder="Type a message" autocomplete="off" />
            <input type="file" id="image-input" accept="image/*" hidden />
            <button type="button" id="attach-image">📎</button>
            <button type="submit">Send</button>
        </form>
        <div class="voice-controls">
            <button id="mic-button">🎤</button>
            <select id="microphone-select"></select>
            <label for="volume-slider">Volume</label>
            <input type="range" id="volume-slider" min="0" max="1.5" step="0.1" value="1.0" />
            <label class="toggle-handsfree">
                <input type="checkbox" id="handsfree-toggle" checked />
                Hands-Free
            </label>
            <button type="button" id="stop-audio" class="secondary">Stop Audio</button>
        </div>
    </footer>
</div>

<div id="settings-panel" class="settings hidden">
    <h2>Configuration</h2>
    <form id="settings-form">
        <label>
            VAD Silence (ms)
            <input type="number" id="vad-silence" min="200" max="5000" step="100" />
        </label>
        <label>
            Voice Output
            <input type="checkbox" id="enable-voice-output" />
        </label>
        <button type="submit">Save</button>
        <button type="button" id="close-settings">Close</button>
    </form>
</div>

