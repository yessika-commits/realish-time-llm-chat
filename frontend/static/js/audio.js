import { RMS_THRESHOLD, DEFAULT_VAD_SILENCE_MS } from './config.js';
import * as state from './state.js';
import * as ui from './ui.js';

let mediaRecorder = null;
let recordedChunks = [];
let activeStream = null;
let onRecordingStopCallback = null;

// VAD-related variables
let audioContext, vadSource, vadAnalyser, vadDataArray, vadAnimationFrame;

function isRecording() {
    return mediaRecorder && mediaRecorder.state === 'recording';
}

async function getStream(deviceId) {
    if (activeStream) {
        // If we have a stream, check if its tracks are still active.
        const audioTrack = activeStream.getAudioTracks()[0];
        if (audioTrack && audioTrack.readyState === 'live') {
            return activeStream;
        }
    }
    // Otherwise, get a new one.
    activeStream = await navigator.mediaDevices.getUserMedia({
        audio: deviceId ? { deviceId: { exact: deviceId } } : true,
    });
    return activeStream;
}

function beginHandsFreeRecording() {
    if (isRecording() || !mediaRecorder) return;
    recordedChunks = [];
    mediaRecorder.start();
    ui.setRecordingState(true);
}

function setupVAD(stream, callbacks) {
    if (!audioContext || audioContext.state === 'closed') {
        audioContext = new AudioContext();
    }
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }

    vadSource = audioContext.createMediaStreamSource(stream);
    vadAnalyser = audioContext.createAnalyser();
    vadAnalyser.fftSize = 2048;
    vadDataArray = new Float32Array(vadAnalyser.fftSize);
    vadSource.connect(vadAnalyser);

    let lastSpeechTimestamp = Date.now();
    let detectedSpeech = false;
    const vadSilenceMs = state.get('settings')?.audio?.vad_silence_ms ?? DEFAULT_VAD_SILENCE_MS;

    const monitor = () => {
        if (!vadAnalyser) return;
        vadAnalyser.getFloatTimeDomainData(vadDataArray);
        const rms = Math.sqrt(vadDataArray.reduce((sum, val) => sum + val * val, 0) / vadDataArray.length);
        const now = Date.now();

        if (rms > RMS_THRESHOLD) {
            lastSpeechTimestamp = now;
            if (!isRecording() && callbacks.onSpeech) {
                // If we detect speech and are not recording, start.
                callbacks.onSpeech();
            }
            detectedSpeech = true;
        }
        
        if (isRecording() && detectedSpeech && (now - lastSpeechTimestamp) > vadSilenceMs) {
            detectedSpeech = false;
            if (callbacks.onSilence) {
                // If we are recording and detect silence, stop.
                callbacks.onSilence();
            }
        }
        vadAnimationFrame = requestAnimationFrame(monitor);
    };
    monitor();
}

function teardownVAD() {
    if (vadAnimationFrame) cancelAnimationFrame(vadAnimationFrame);
    if (vadSource) vadSource.disconnect();
    vadAnimationFrame = vadSource = vadAnalyser = vadDataArray = null;
}

export function init(onStopCallback) {
    onRecordingStopCallback = onStopCallback;
}

export async function armHandsFreeListener() {
    if (!state.get('handsFreeEnabled') || state.get('audioQueue').length > 0) return;
    try {
        const stream = await getStream(ui.elements.micSelect.value);
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) recordedChunks.push(event.data);
            };
            mediaRecorder.onstop = () => {
                teardownVAD();
                if (onRecordingStopCallback && recordedChunks.length > 0) {
                    const blob = new Blob(recordedChunks, { type: "audio/webm" });
                    onRecordingStopCallback(blob);
                }
                recordedChunks = [];
            };
        }
        setupVAD(stream, { onSpeech: beginHandsFreeRecording, onSilence: stopRecording });
        ui.setChatStatus("Listening...");
    } catch (error) {
        console.error("Failed to arm hands-free listener:", error);
        ui.showAlert("Could not arm listener.", "error");
    }
}

export function teardownHandsFreeListener() {
    teardownVAD();
    if (activeStream) {
        activeStream.getTracks().forEach(track => track.stop());
        activeStream = null;
    }
    if (ui.elements.chatStatus.textContent === "Listening...") {
        ui.setChatStatus("Idle");
    }
}

export async function startRecording() {
    if (isRecording()) return;
    try {
        const stream = await getStream(ui.elements.micSelect.value);
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) recordedChunks.push(event.data);
        };
        mediaRecorder.onstop = () => {
            teardownVAD();
            if (onRecordingStopCallback && recordedChunks.length > 0) {
                const blob = new Blob(recordedChunks, { type: "audio/webm" });
                onRecordingStopCallback(blob);
            }
            recordedChunks = [];
        };
        mediaRecorder.start();
        ui.setRecordingState(true);
        setupVAD(stream, { onSilence: stopRecording });
    } catch (error) {
        console.error("Failed to start recording:", error);
        ui.showAlert("Could not access microphone.", "error");
        ui.setRecordingState(false);
    }
}

export function stopRecording() {
    if (isRecording()) {
        mediaRecorder.stop();
        ui.setRecordingState(false);
    }
}

export async function playAudio(audioPath) {
    if (!state.get('settings')?.audio?.enable_voice_output) return;
    
    stopAllPlayback();
    teardownHandsFreeListener(); // Stop listening while assistant speaks

    const audio = new Audio(ui.makeMediaUrl(audioPath));
    audio.volume = parseFloat(ui.elements.volumeSlider.value);
    
    state.addAudioToQueue(audio);

    audio.onended = () => {
        state.removeAudioFromQueue(audio);
        // **FIXED**: Call the function to re-arm the listener.
        armHandsFreeListener();
    };

    try {
        await audio.play();
    } catch (error) {
        console.error("Audio playback failed:", error);
        ui.showAlert("Audio playback failed.", "error");
        state.removeAudioFromQueue(audio);
        // Also try to re-arm on failure
        armHandsFreeListener();
    }
}

export function stopAllPlayback() {
    state.clearAudioQueue();
    ui.setChatStatus("Idle");
}

export function setPlaybackVolume(volume) {
    state.get('audioQueue').forEach(audio => {
        audio.volume = volume;
    });
}