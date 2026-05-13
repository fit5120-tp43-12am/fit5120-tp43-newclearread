const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

let currentAudio = null
let currentAudioUrl = null
let currentResolve = null
let currentSessionId = 0
const audioBlobCache = new Map()
const audioRequestCache = new Map()
let quotaCooldownUntil = 0

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

export function stopBackendTTS() {
  currentSessionId += 1
  if (currentResolve) {
    currentResolve('cancelled')
    currentResolve = null
  }
  cleanup()
}

export function pauseBackendTTS() {
  if (currentAudio) currentAudio.pause()
}

export async function resumeBackendTTS() {
  if (currentAudio) await currentAudio.play()
}

export function setBackendTTSPlaybackRate(speed = 1) {
  if (!currentAudio) return
  currentAudio.playbackRate = Math.max(0.5, Math.min(2, Number(speed) || 1))
}

export async function preloadBackendTTS(text, options = {}) {
  const cleanText = String(text || '').trim()
  if (!cleanText) return null
  if (Date.now() < quotaCooldownUntil) return null
  return fetchAudioBlob(cleanText, options)
}

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

function cacheKey(text, options = {}) {
  return JSON.stringify({
    text: String(text || '').trim(),
    voice: options.voice || 'default-female',
  })
}

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
