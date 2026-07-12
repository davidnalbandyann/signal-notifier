<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { pauseScan, resumeScan, triggerScan, getStatus } from '@/api/dashboard'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const app = useAppStore()
const running = ref(true)
const actionLoading = ref(false)

onMounted(async () => {
  try {
    const status = await getStatus()
    running.value = status.running
  } catch {}
})

const navItems = [
  { path: '/', label: 'Dashboard', icon: 'dashboard' },
  { path: '/charts', label: 'Charts', icon: 'charts' },
  { path: '/history', label: 'History', icon: 'history' },
  { path: '/notifications', label: 'Notifications', icon: 'notifications' },
  { path: '/strategy', label: 'Strategy', icon: 'strategy' },
  { path: '/settings', label: 'Settings', icon: 'settings' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function togglePause() {
  try {
    if (running.value) {
      await pauseScan()
      running.value = false
    } else {
      await resumeScan()
      running.value = true
    }
  } catch (e) {
    console.error(e)
  }
}

async function runScan() {
  actionLoading.value = true
  try {
    await triggerScan()
  } catch (e) {
    console.error(e)
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <aside :class="['sidebar', { collapsed: app.sidebarCollapsed }]">
    <div class="side-brand">
      <div class="side-mark">T</div>
      <div class="side-name">Trading Chart AI Monitor</div>
    </div>
    <nav class="side-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :class="['nav-item', { active: isActive(item.path) }]"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <template v-if="item.icon === 'dashboard'">
            <rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>
            <rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>
          </template>
          <template v-else-if="item.icon === 'charts'">
            <polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/>
          </template>
          <template v-else-if="item.icon === 'history'">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </template>
          <template v-else-if="item.icon === 'notifications'">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </template>
          <template v-else-if="item.icon === 'strategy'">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </template>
          <template v-else-if="item.icon === 'settings'">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </template>
        </svg>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <button class="toggle-btn" @click="app.toggleSidebar()" title="Toggle sidebar">
      <svg class="toggle-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 6 15 12 9 18" />
      </svg>
    </button>

    <div class="side-foot">
      <BaseButton variant="warn" size="sm" full @click="togglePause">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <rect v-if="running" x="6" y="5" width="4" height="14"/><rect v-if="running" x="14" y="5" width="4" height="14"/>
          <polygon v-else points="6 4 20 12 6 20"/>
        </svg>
        <span class="nav-label">{{ running ? 'Pause loop' : 'Resume loop' }}</span>
      </BaseButton>
      <BaseButton size="sm" full @click="runScan" :disabled="actionLoading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20"/></svg>
        <span class="nav-label">Run scan now</span>
      </BaseButton>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  background: var(--bg-2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  width: var(--sidebar-w);
  transition: width .25s cubic-bezier(0.4, 0, 0.2, 1);
}
.sidebar:not(.collapsed) { width: var(--sidebar-w-h); }

.side-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: var(--topbar-h);
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.side-mark {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--accent), oklch(48% 0.20 280));
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: var(--accent-fg);
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
}
.side-name {
  font-weight: 600;
  font-size: 13px;
  letter-spacing: -0.01em;
  white-space: nowrap;
  opacity: 0;
  transition: opacity .2s .05s;
}
.sidebar:not(.collapsed) .side-name { opacity: 1; }

.side-nav {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--radius);
  color: var(--fg-2);
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
  position: relative;
  transition: background .12s, color .12s;
}
.nav-item:hover { background: var(--surface); color: var(--fg); }
.nav-item.active { background: var(--accent-soft); color: var(--fg); }
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: var(--muted);
}
.nav-item.active .nav-icon,
.nav-item:hover .nav-icon { color: var(--accent); }
.nav-label {
  opacity: 0;
  overflow: hidden;
  max-width: 0;
  white-space: nowrap;
  transition: opacity .2s .05s, max-width .25s cubic-bezier(0.4, 0, 0.2, 1);
}
.sidebar:not(.collapsed) .nav-label {
  opacity: 1;
  max-width: 160px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 32px;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--border);
  color: var(--muted);
  cursor: pointer;
  transition: background .12s, color .12s;
  flex-shrink: 0;
}
.toggle-btn:hover { background: var(--surface); color: var(--fg); }
.toggle-chevron {
  transition: transform .3s cubic-bezier(0.4, 0, 0.2, 1);
}
.sidebar:not(.collapsed) .toggle-chevron { transform: rotate(180deg); }

.side-foot {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
