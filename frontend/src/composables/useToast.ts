import { ref } from 'vue'

type ToastKind = 'success' | 'error' | 'info'
interface ToastState { show: boolean; message: string; kind: ToastKind }

const state = ref<ToastState>({ show: false, message: '', kind: 'success' })
let hideTimer: ReturnType<typeof setTimeout> | null = null

// Defensive: on full-page unload, drop any pending hide timer so we don't
// fire `state.value = …` into a torn-down reactive tree. The setInterval
// paths in views already clean up via onUnmounted; this covers the SPA
// hard-reload case.
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
  })
}

export function useToast() {
  function show(message: string, kind: ToastKind = 'success') {
    if (hideTimer) clearTimeout(hideTimer)
    state.value = { show: true, message, kind }
    hideTimer = setTimeout(() => dismiss(), 3200)
  }
  function dismiss() {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
    state.value = { ...state.value, show: false }
  }
  const ok = (m: string) => show(m, 'success')
  const err = (m: string) => show(m, 'error')
  const info = (m: string) => show(m, 'info')

  return { state, show, dismiss, ok, err, info }
}
