import { ref } from 'vue'

type ToastKind = 'success' | 'error' | 'info'
interface ToastState { show: boolean; message: string; kind: ToastKind }

const state = ref<ToastState>({ show: false, message: '', kind: 'success' })
let hideTimer: ReturnType<typeof setTimeout> | null = null

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
