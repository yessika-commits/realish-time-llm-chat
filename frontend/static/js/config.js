/**
 * Application-wide configuration.
 */
export const API_BASE = "http://127.0.0.1:8000";
export const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/chat";

/**
 * VAD (Voice Activity Detection) settings.
 */
export const RMS_THRESHOLD = 0.015; // Sensitivity for speech detection.
export const DEFAULT_VAD_SILENCE_MS = 1500; // Default silence duration to stop recording.