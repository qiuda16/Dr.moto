const JOURNEY_KEY = 'drmoto_customer_active_journey'
const JOURNEY_HISTORY_KEY = 'drmoto_customer_journey_history'
const AI_SEED_KEY = 'mp_customer_ai_seed'

export function saveJourney(payload) {
  if (!payload || typeof payload !== 'object') {
    return null
  }
  const nextJourney = {
    id: payload.id || '',
    title: payload.title || '',
    desc: payload.desc || '',
    source: payload.source || '',
    aiPrompt: payload.aiPrompt || '',
    appointmentSubject: payload.appointmentSubject || '',
    serviceKind: payload.serviceKind || '',
    notes: payload.notes || '',
    shopKind: payload.shopKind || '',
    shopQuery: payload.shopQuery || '',
    vehicleId: payload.vehicleId || null,
    updatedAt: Date.now(),
  }
  uni.setStorageSync(JOURNEY_KEY, nextJourney)
  return nextJourney
}

export function getJourney() {
  return uni.getStorageSync(JOURNEY_KEY) || null
}

export function clearJourney() {
  uni.removeStorageSync(JOURNEY_KEY)
}

export function getHistory() {
  return uni.getStorageSync(JOURNEY_HISTORY_KEY) || []
}

export function addHistory(payload) {
  if (!payload || typeof payload !== 'object') {
    return getHistory()
  }
  const current = getHistory()
  const next = [
    {
      id: payload.id || '',
      title: payload.title || '',
      desc: payload.desc || '',
      source: payload.source || '',
      status: payload.status || 'done',
      vehicleId: payload.vehicleId || null,
      draftId: payload.draftId || null,
      updatedAt: payload.updatedAt || Date.now(),
    },
    ...current,
  ].slice(0, 8)
  uni.setStorageSync(JOURNEY_HISTORY_KEY, next)
  return next
}

export function setAiSeed(payload) {
  if (!payload || typeof payload !== 'object') {
    return
  }
  uni.setStorageSync(AI_SEED_KEY, payload)
}

export function consumeAiSeed() {
  const seed = uni.getStorageSync(AI_SEED_KEY) || null
  if (seed) {
    uni.removeStorageSync(AI_SEED_KEY)
  }
  return seed
}
