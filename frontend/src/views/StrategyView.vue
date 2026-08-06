<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ActivePipelinesTab from '@/components/strategy/ActivePipelinesTab.vue'
import ChartsTab from '@/components/strategy/ChartsTab.vue'
import CppLibraryTab from '@/components/strategy/CppLibraryTab.vue'
import AiLibraryTab from '@/components/strategy/AiLibraryTab.vue'

const route = useRoute()
const router = useRouter()

type TabKey = 'pipelines' | 'charts' | 'cpp' | 'ai'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'pipelines', label: 'Active Pipelines' },
  { key: 'charts', label: 'Charts & Data' },
  { key: 'cpp', label: 'C++ Library' },
  { key: 'ai', label: 'AI Prompt Library' },
]

const currentTab = ref<TabKey>('pipelines')

// Sync tab state with URL query param
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && tabs.some(t => t.key === newTab)) {
      currentTab.value = newTab as TabKey
    } else {
      currentTab.value = 'pipelines'
      router.replace({ query: { ...route.query, tab: 'pipelines' } })
    }
  },
  { immediate: true }
)

function setTab(key: TabKey) {
  currentTab.value = key
  router.push({ query: { ...route.query, tab: key } })
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Strategy Engine</h1>
          <div class="pg-sub">Manage active pipelines and reusable strategy libraries</div>
        </div>
      </header>

      <div class="tabs-nav" role="tablist">
        <button
          v-for="t in tabs"
          :key="t.key"
          :class="['tab-btn', { active: currentTab === t.key }]"
          @click="setTab(t.key)"
        >
          {{ t.label }}
        </button>
      </div>

      <div class="tab-content">
        <ActivePipelinesTab v-if="currentTab === 'pipelines'" />
        <ChartsTab v-else-if="currentTab === 'charts'" />
        <CppLibraryTab v-else-if="currentTab === 'cpp'" />
        <AiLibraryTab v-else-if="currentTab === 'ai'" />
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 20px; max-width: 1200px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; margin-bottom: 4px; }
.pg-title { font: 600 20px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 13px var(--font-mono); color: var(--muted); margin-top: 4px; }

.tabs-nav {
  display: flex; align-items: center; gap: 4px;
  background: var(--bg-2); padding: 4px; border-radius: 8px;
  border: 1px solid var(--border);
  width: fit-content;
}
.tab-btn {
  padding: 8px 16px; font: 500 13px var(--font-sans); color: var(--muted);
  border: 0; background: transparent; border-radius: 6px; cursor: pointer; transition: all .12s;
}
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { background: var(--surface-hi); color: var(--fg); font-weight: 600; box-shadow: 0 1px 2px oklch(0% 0 0 / 0.1); }

.tab-content { min-height: 500px; }
</style>