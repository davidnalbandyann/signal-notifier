// Shared live threshold for signal qualification.
//
// Single source of truth across all views: the configured NOTIFICATION_THRESHOLD
// from the backend settings. Cached at module scope so History, Notifications,
// and AnalysisDetail don't each trigger their own settings fetch.
//
// DashboardView can also seed the cache via setThreshold() from getStatus().

import { ref } from 'vue'
import { getSettings } from '@/api/settings'

const threshold = ref<number | null>(null)
let inflight: Promise<void> | null = null

async function load(): Promise<void> {
  if (threshold.value !== null) return
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const s = await getSettings()
      const t = Number(s.NOTIFICATION_THRESHOLD)
      if (!Number.isNaN(t)) threshold.value = t
    } catch {
      /* silent — view falls back to bare ScoreBar */
    } finally {
      inflight = null
    }
  })()
  return inflight
}

function setThreshold(value: number | null | undefined) {
  if (value == null) return
  const t = Number(value)
  if (!Number.isNaN(t)) threshold.value = t
}

export function useThreshold() {
  return { threshold, load, setThreshold }
}