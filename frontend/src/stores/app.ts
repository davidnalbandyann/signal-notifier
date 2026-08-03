import { defineStore } from 'pinia'
import { ref, watch, computed, onScopeDispose } from 'vue'

export const useAppStore = defineStore('app', () => {
  const theme = ref<'dark' | 'light'>(
    (localStorage.getItem('tcm:theme') as 'dark' | 'light') || 'dark'
  )
  const sidebarCollapsed = ref(
    localStorage.getItem('tcm:sidebar') !== 'expanded'
  )
  const mobileSidebarOpen = ref(false)

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function openMobileSidebar() {
    mobileSidebarOpen.value = true
  }

  function closeMobileSidebar() {
    mobileSidebarOpen.value = false
  }

  // isMobile needs to update on resize/rotation. window.innerWidth reads
  // were previously reactive on the FIRST render only — value went stale
  // after the user resized the window or rotated a tablet.
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
  if (typeof window !== 'undefined') {
    const onResize = () => { windowWidth.value = window.innerWidth }
    window.addEventListener('resize', onResize, { passive: true })
    onScopeDispose(() => window.removeEventListener('resize', onResize))
  }
  const isMobile = computed(() => windowWidth.value <= 768)

  watch(theme, (val) => {
    localStorage.setItem('tcm:theme', val)
    document.documentElement.setAttribute('data-theme', val)
  }, { immediate: true })

  watch(sidebarCollapsed, (val) => {
    localStorage.setItem('tcm:sidebar', val ? 'collapsed' : 'expanded')
  })

  return {
    theme, toggleTheme,
    sidebarCollapsed, toggleSidebar,
    mobileSidebarOpen, openMobileSidebar, closeMobileSidebar,
    isMobile,
  }
})
