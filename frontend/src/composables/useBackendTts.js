// This file handles text-to-speech playback through the backend TTS API.
// It keeps one active audio session at a time, caches fetched audio blobs so
// the same text is not requested twice, and pauses new requests for 60 seconds
// when the API quota is exhausted.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// Module-level state for the currently playing audio session.
let currentAudio = null
let currentAudioUrl = null
let currentResolve = null
let currentSessionId = 0

// audioBlobCache stores completed blobs; audioRequestCache holds in-flight promises
// so two callers requesting the same text share one fetch.
const audioBlobCache = new Map()
const audioRequestCache = new Map()
let quotaCooldownUntil = 0

/**
 * Release the current audio element and revoke its object URL.
 * Only runs if the given session ID still matches the active one.
 *
 * @param {number} sessionId - the session to clean up
 */
function cleanup(sessionId = currentSessionId) {
  if (sessionId !== currentSessionId) return
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.onended = null
    currentAudio.onerror = null
    currentAudio.onplaying = null
    currentAudio = null
  }
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl)
    currentAudioUrl = null
  }
}

/**
 * Stop any playing or pending TTS audio immediately.
 * Increments the session ID so any in-flight play call is ignored.
 */
export function stopBackendTTS() {
  currentSessionId += 1
  if (currentResolve) {
    currentResolve('cancelled')
    currentResolve = null
  }
  cleanup()
}

/**
 * Pause the currently playing audio without discarding the session.
 */
export function pauseBackendTTS() {
  if (currentAudio) currentAudio.pause()
}

/**
 * Resume a paused audio session.
 *
 * @returns {Promise<void>}
 */
export async function resumeBackendTTS() {
  if (currentAudio) await currentAudio.play()
}

/**
 * Change the playback speed of the active audio element.
 *
 * @param {number} speed - playback rate, clamped to [0.5, 2]
 */
export function setBackendTTSPlaybackRate(speed = 1) {
  if (!currentAudio) return
  currentAudio.playbackRate = Math.max(0.5, Math.min(2, Number(speed) || 1))
}

/**
 * Fetch and cache the audio blob for a piece of text without playing it.
 * Useful for loading audio in the background before it is needed.
 * Returns null if the text is empty or if the quota cooldown is active.
 *
 * @param {string} text - the text to preload
 * @param {Object} options - voice and volume settings (same as playBackendTTS)
 * @returns {Promise<Blob|null>}
 */
export async function preloadBackendTTS(text, options = {}) {
  const cleanText = String(text || '').trim()
  if (!cleanText) return null
  if (Date.now() < quotaCooldownUntil) return null
  return fetchAudioBlob(cleanText, options)
}

/**
 * Stop any current audio, then fetch and play the given text.
 * Resolves with 'done' when playback finishes, or 'cancelled' if stopped early.
 *
 * @param {string} text - the text to speak
 * @param {Object} options - optional settings
 * @param {string}   [options.voice='default-female'] - voice name sent to the API
 * @param {number}   [options.volume=70]              - volume as 0–100
 * @param {number}   [options.speed=1]                - playback rate
 * @param {Function} [options.onPlaybackStart]        - called when audio actually starts playing
 * @returns {Promise<'done'|'cancelled'>}
 */
export async function playBackendTTS(text, options = {}) {
  stopBackendTTS()

  const cleanText = String(text || '').trim()
  if (!cleanText) return 'done'

  const sessionId = currentSessionId
  const blob = await fetchAudioBlob(cleanText, options)
  if (sessionId !== currentSessionId) return 'cancelled'
  currentAudioUrl = URL.createObjectURL(blob)
  currentAudio = new Audio(currentAudioUrl)
  currentAudio.volume = Math.max(0, Math.min(1, Number(options.volume ?? 70) / 100))
  currentAudio.playbackRate = Math.max(0.5, Math.min(2, Number(options.speed || 1)))
  if (typeof options.onPlaybackStart === 'function') {
    currentAudio.onplaying = options.onPlaybackStart
  }

  return new Promise((resolve, reject) => {
    currentResolve = resolve
    currentAudio.onended = () => {
      currentResolve = null
      cleanup(sessionId)
      resolve('done')
    }
    currentAudio.onerror = () => {
      const error = new Error('Audio playback failed.')
      currentResolve = null
      cleanup(sessionId)
      reject(error)
    }
    currentAudio.play().catch((error) => {
      currentResolve = null
      cleanup(sessionId)
      reject(error)
    })
  })
}

/**
 * Build a cache key string from the text and voice option.
 *
 * @param {string} text
 * @param {Object} options
 * @returns {string}
 */
function cacheKey(text, options = {}) {
  return JSON.stringify({
    text: String(text || '').trim(),
    voice: options.voice || 'default-female',
  })
}

/**
 * Fetch audio from the TTS API and store the result in the blob cache.
 * If a request for the same key is already in flight, returns that promise
 * instead of sending a second request.
 * Sets a 60-second cooldown when the API returns a quota error.
 *
 * @param {string} text
 * @param {Object} options
 * @returns {Promise<Blob>}
 */
async function fetchAudioBlob(text, options = {}) {
  const key = cacheKey(text, options)
  if (audioBlobCache.has(key)) return audioBlobCache.get(key)
  if (audioRequestCache.has(key)) return audioRequestCache.get(key)

  const request = fetch(`${API_BASE_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      voice: options.voice || 'default-female',
      speed: 1,
      volume: Number(options.volume ?? 70),
    }),
  }).then(async (response) => {
    if (!response.ok) {
      let detail = `TTS request failed with HTTP ${response.status}.`
      try {
        const payload = await response.json()
        detail = payload.detail || detail
      } catch {
        // Keep the status-based message when the response body is not JSON.
      }
      if (response.status === 429 || /quota|RESOURCE_EXHAUSTED/i.test(detail)) {
        quotaCooldownUntil = Date.now() + 60_000
      }
      throw new Error(detail)
    }
    const blob = await response.blob()
    audioBlobCache.set(key, blob)
    return blob
  }).finally(() => {
    audioRequestCache.delete(key)
  })

  audioRequestCache.set(key, request)
  return request
}
