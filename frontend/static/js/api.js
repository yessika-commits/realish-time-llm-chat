import { API_BASE } from './config.js';

/**
 * A wrapper for the fetch API to handle JSON responses and errors.
 * @param {string} url - The URL to fetch.
 * @param {object} options - Fetch options (method, headers, body, etc.).
 * @returns {Promise<any>} - The JSON response.
 */
async function fetchJSON(url, options) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error("API call failed:", error);
    throw error;
  }
}

/**
 * API methods for managing conversations.
 */
export const conversations = {
  getAll: () => fetchJSON(`${API_BASE}/api/conversations`),
  getById: (id) => fetchJSON(`${API_BASE}/api/conversations/${id}`),
  create: (payload) => fetchJSON(`${API_BASE}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }),
  update: (id, payload) => fetchJSON(`${API_BASE}/api/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }),
  delete: (id) => fetchJSON(`${API_BASE}/api/conversations/${id}`, { method: 'DELETE' }),
  deleteAll: () => fetchJSON(`${API_BASE}/api/conversations`, { method: 'DELETE' }),
};

/**
 * API methods for managing settings.
 */
export const settings = {
  get: () => fetchJSON(`${API_BASE}/api/settings`),
  update: (payload) => fetchJSON(`${API_BASE}/api/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }),
};

/**
 * API methods for uploading media files.
 */
export const media = {
  uploadAudio: async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, "audio.webm");
    return await fetchJSON(`${API_BASE}/api/media/audio`, {
      method: 'POST',
      body: formData,
    });
  },
  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return await fetchJSON(`${API_BASE}/api/media/images`, {
      method: 'POST',
      body: formData,
    });
  },
};