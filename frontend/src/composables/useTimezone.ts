import { ref } from 'vue'

const STORAGE_KEY = 'tcm_timezone'

export function useTimezone() {
  const tz = ref(getStoredOrDefault())

  function getStoredOrDefault(): string {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) return stored
    } catch {}
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  }

  function setTimezone(value: string) {
    tz.value = value
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {}
  }

  function formatDate(iso: string, options?: Intl.DateTimeFormatOptions) {
    try {
      return new Intl.DateTimeFormat(undefined, {
        ...options,
        timeZone: tz.value,
      }).format(new Date(iso))
    } catch {
      return new Date(iso).toLocaleString()
    }
  }

  function formatTime(iso: string) {
    try {
      return new Intl.DateTimeFormat(undefined, {
        hour: '2-digit', minute: '2-digit',
        timeZone: tz.value,
      }).format(new Date(iso))
    } catch {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  }

  function formatFull(iso: string) {
    try {
      return new Intl.DateTimeFormat(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        timeZone: tz.value,
      }).format(new Date(iso))
    } catch {
      return new Date(iso).toLocaleString()
    }
  }

  function isSameDay(isoA: string, isoB: string) {
    try {
      const fmt = new Intl.DateTimeFormat(undefined, {
        year: 'numeric', month: '2-digit', day: '2-digit',
        timeZone: tz.value,
      })
      return fmt.format(new Date(isoA)) === fmt.format(new Date(isoB))
    } catch {
      return new Date(isoA).toDateString() === new Date(isoB).toDateString()
    }
  }

  return { tz, setTimezone, formatDate, formatTime, formatFull, isSameDay }
}
