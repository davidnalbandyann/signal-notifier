import { ref, onMounted, onUnmounted } from 'vue'

export function useCountdown(initialSeconds: () => number) {
  const seconds = ref(initialSeconds())
  let interval: ReturnType<typeof setInterval> | null = null

  function reset() {
    seconds.value = initialSeconds()
  }

  onMounted(() => {
    interval = setInterval(() => {
      if (seconds.value > 0) {
        seconds.value--
      }
    }, 1000)
  })

  onUnmounted(() => {
    if (interval) clearInterval(interval)
  })

  const formatted = ref('')
  const update = () => {
    const m = Math.floor(seconds.value / 60)
    const s = seconds.value % 60
    formatted.value = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  if (interval) {
    const origCb = () => {
      seconds.value--
      update()
    }
    clearInterval(interval)
    interval = setInterval(() => {
      if (seconds.value > 0) seconds.value--
      update()
    }, 1000)
  }

  update()

  return { seconds, formatted, reset }
}
