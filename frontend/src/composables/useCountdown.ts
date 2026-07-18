import { ref, onMounted, onUnmounted, computed } from 'vue'

export function useCountdown(getSeconds: () => number) {
  const seconds = ref(getSeconds())
  let timer: ReturnType<typeof setInterval> | null = null

  const formatted = computed(() => {
    const s = Math.max(0, seconds.value)
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const r = s % 60
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
    return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
  })

  function resync() {
    seconds.value = getSeconds()
  }

  onMounted(() => {
    timer = setInterval(() => {
      if (seconds.value > 0) seconds.value--
    }, 1000)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { seconds, formatted, resync }
}
