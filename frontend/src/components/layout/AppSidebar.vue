<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { getStatus, pauseScan, resumeScan, triggerScan } from '@/api/dashboard'
import { useToast } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const route = useRoute()
const app = useAppStore()
const toast = useToast()
const running = ref(true)
const actionLoading = ref<null | 'pause' | 'scan'>(null)
let poll: ReturnType<typeof setInterval> | null = null

const nav = [
  { path: '/',        label: 'Dashboard',    icon: 'dashboard' },
  { path: '/charts',  label: 'Charts',       icon: 'charts' },
  { path: '/history', label: 'History',      icon: 'history' },
  { path: '/notifications', label: 'Signals', icon: 'bell' },
  { path: '/engine',  label: 'C++ Engine',   icon: 'engine' },
  { path: '/strategy', label: 'Strategy',    icon: 'strategy' },
  { path: '/settings', label: 'Settings',    icon: 'settings' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function syncRun() {
  try {
    const s = await getStatus()
    running.value = s.running
  } catch { /* silent */ }
}

async function togglePause() {
  if (actionLoading.value) return
  actionLoading.value = 'pause'
  try {
    if (running.value) { await pauseScan(); running.value = false; toast.ok('Scan loop paused') }
    else { await resumeScan(); running.value = true; toast.ok('Scan loop resumed') }
  } catch { toast.err('Failed to toggle scan loop') }
  finally { actionLoading.value = null }
}

async function runScan() {
  if (actionLoading.value) return
  actionLoading.value = 'scan'
  try {
    await triggerScan()
    toast.ok('Scan triggered')
  } catch { toast.err('Failed to trigger scan') }
  finally { actionLoading.value = null }
}

function onNavClick() {
  app.closeMobileSidebar()
}

onMounted(() => {
  syncRun()
  poll = setInterval(syncRun, 8000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<template>
  <Teleport to="body" v-if="app.mobileSidebarOpen">
    <div class="mobile-backdrop" @click="app.closeMobileSidebar()"></div>
  </Teleport>
  <aside :class="['sidebar', { collapsed: app.sidebarCollapsed, 'mobile-open': app.mobileSidebarOpen }]">
    <div class="brand">
      <div class="mark">TC</div>
      <div class="brand-text">
        <div class="brand-name">Trading Monitor</div>
        <div class="brand-sub">AI chart control</div>
      </div>
    </div>

    <nav class="nav">
      <router-link
        v-for="item in nav"
        :key="item.path"
        :to="item.path"
        :class="['nav-item', { active: isActive(item.path) }]"
        :title="item.label"
        @click="onNavClick"
      >
        <AppIcon :name="item.icon" :size="18" class="nav-ic" />
        <span class="nav-lbl">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="foot">
      <button
        :class="['foot-btn', { live: running }]"
        @click="togglePause"
        :disabled="actionLoading === 'pause'"
        :title="running ? 'Pause scan loop' : 'Resume scan loop'"
      >
        <AppIcon :name="running ? 'pause' : 'play'" :size="13" />
        <span class="foot-lbl">{{ running ? 'Pause loop' : 'Resume loop' }}</span>
        <span v-if="running" class="foot-dot"></span>
      </button>
      <button
        class="foot-btn primary"
        @click="runScan"
        :disabled="actionLoading === 'scan'"
        title="Run a scan now"
      >
        <AppIcon name="refresh" :size="13" :stroke="2.5" />
        <span class="foot-lbl">Run scan now</span>
      </button>
      <button
        class="foot-toggle"
        @click="app.toggleSidebar()"
        :title="app.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-label="app.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <AppIcon name="chevronLeft" :size="14" :stroke="2.5" />
        <span class="foot-lbl">Collapse</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-2);
  border-right: 1px solid var(--border);
  overflow: hidden;
  width: var(--sidebar-w);
  transition: width var(--speed-slow) var(--ease);
  flex-shrink: 0;
}
.sidebar.collapsed { width: var(--sidebar-w-c); }

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: var(--topbar-h);
  padding: 0 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  overflow: hidden;
}
.mark {
  width: 28px;
  height: 28px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 7px;
  display: grid;
  place-items: center;
  font: 700 11px var(--font-mono);
  letter-spacing: 0.04em;
  flex-shrink: 0;
  box-shadow: 0 2px 8px oklch(64% 0.19 263 / 0.25);
}
.brand-text { min-width: 0; overflow: hidden; }
.brand-name {
  font: 600 12.5px var(--font-sans);
  color: var(--fg);
  letter-spacing: -0.005em;
  white-space: nowrap;
}
.brand-sub {
  font: 500 10.5px var(--font-mono);
  color: var(--muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.nav {
  flex: 1;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow-y: auto;
  overflow-x: hidden;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 11px;
  border-radius: var(--radius);
  color: var(--fg-2);
  text-decoration: none;
  font: 500 13px var(--font-sans);
  white-space: nowrap;
  position: relative;
  transition: background var(--speed-fast) var(--ease), color var(--speed-fast);
}
.nav-item:hover { background: var(--surface); color: var(--fg); }
.nav-item.active { background: var(--accent-soft); color: var(--accent); }
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.nav-ic { color: var(--muted); flex-shrink: 0; transition: color var(--speed-fast); }
.nav-item:hover .nav-ic { color: var(--fg-2); }
.nav-item.active .nav-ic { color: var(--accent); }

.nav-lbl, .brand-text, .foot-lbl {
  opacity: 1;
  transition: opacity 0.15s var(--ease);
}
.sidebar.collapsed .nav-lbl,
.sidebar.collapsed .brand-text,
.sidebar.collapsed .foot-lbl {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.foot {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.foot-btn {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 32px;
  padding: 0 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--fg-2);
  font: 600 12px var(--font-sans);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--speed-fast), border-color var(--speed-fast), color var(--speed-fast);
  width: 100%;
  position: relative;
}
.foot-btn:hover { background: var(--surface-2); color: var(--fg); border-color: var(--border-2); }
.foot-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.foot-btn.primary {
  background: var(--accent);
  border-color: transparent;
  color: var(--accent-fg);
}
.foot-btn.primary:hover { background: var(--accent-2); }
.foot-btn.live { color: var(--green); border-color: oklch(74% 0.17 152 / 0.3); }
.foot-btn.live:hover { color: var(--green); background: var(--green-soft); }
.foot-dot {
  margin-left: auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse 2.2s infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0.5); }
  70%  { box-shadow: 0 0 0 6px oklch(74% 0.17 152 / 0); }
  100% { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0); }
}

.foot-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 26px;
  background: transparent;
  border: 0;
  color: var(--muted-2);
  cursor: pointer;
  border-radius: var(--radius);
  font: 500 11px var(--font-mono);
  letter-spacing: 0.04em;
  transition: color var(--speed-fast), background var(--speed-fast);
  white-space: nowrap;
}
.foot-toggle:hover { color: var(--fg-2); background: var(--surface); }
.sidebar.collapsed .foot-toggle svg { transform: rotate(180deg); }
.foot-toggle svg { transition: transform var(--speed-slow) var(--ease); }

/* Mobile overlay */
.mobile-backdrop {
  position: fixed;
  inset: 0;
  z-index: 55;
  background: oklch(0% 0 0 / 0.5);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  animation: backdrop-in 0.25s var(--ease-out);
}
@keyframes backdrop-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 60;
    transform: translateX(-100%);
    transition: transform var(--speed-slow) var(--ease-out);
    box-shadow: var(--shadow-lg);
  }
  .sidebar.mobile-open {
    transform: translateX(0);
  }
}
</style>