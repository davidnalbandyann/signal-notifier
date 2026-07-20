import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'

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

  const isMobile = computed(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= 768
  })

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
