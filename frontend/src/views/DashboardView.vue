<script setup lang="ts">
import { ref, computed } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import StatCard from '@/components/ui/StatCard.vue'
import PulseIndicator from '@/components/ui/PulseIndicator.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import Toast from '@/components/ui/Toast.vue'
import { getStatus, triggerScan, pauseScan, resumeScan } from '@/api/dashboard'

const loading = ref(true)
const status = ref<Awaited<ReturnType<typeof getStatus>> | null>(null)
const error = ref('')
const toast = ref({ show: false, message: '' })
const scanLoading = ref(false)

async function load() {
  try {
    status.value = await getStatus()
    loading.value = false
  } catch (e) {
    error.value = 'Failed to load dashboard'
    loading.value = false
  }
}

load()

const systemState = computed(() => {
  if (!status.value) return 'paused'
  return status.value.running ? 'running' : 'paused'
})

async function runScan() {
  scanLoading.value = true
  try {
    await triggerScan()
    toast.value = { show: true, message: 'Scan triggered' }
    status.value = await getStatus()
  } catch (e) {
    toast.value = { show: true, message: 'Failed to trigger scan' }
  } finally {
    scanLoading.value = false
  }
}

async function togglePause() {
  try {
    if (status.value?.running) {
      await pauseScan()
    } else {
      await resumeScan()
    }
    status.value = await getStatus()
  } catch (e) {
    toast.value = { show: true, message: 'Failed to toggle scan' }
  }
}

const countdown = ref(0)
setInterval(() => {
  if (status.value && status.value.running && status.value.next_scan_seconds > 0) {
    status.value.next_scan_seconds--
  }
}, 1000)

const nextScanFormatted = computed(() => {
  if (!status.value) return '—'
  const s = status.value.next_scan_seconds
  if (s <= 0) return 'Now'
  return `00:${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
</script>

<template>
  <AppShell :crumbs="['Dashboard']">
    <div class="dash">
      <div class="dash-head">
        <h1 class="h1">Dashboard</h1>
        <div class="spacer"></div>
        <PulseIndicator :state="systemState" />
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <template v-else-if="status">
        <div class="stats-row">
          <StatCard label="Charts" :value="status.charts_count" delta="+2 today" :delta-up="true" />
          <StatCard label="Analyses today" :value="status.analyses_today" delta="+5 since yesterday" :delta-up="true" />
          <StatCard label="Signals sent" :value="status.signals_sent" delta="All successful" :delta-up="true" />
          <StatCard label="Average score" :value="status.avg_score" delta="Strong buy zone" :delta-up="true" />
        </div>

        <div class="timer-row">
          <div class="timer-card">
            <span class="timer-label">NEXT SCAN IN</span>
            <span class="timer-val">{{ nextScanFormatted }}</span>
          </div>
          <div class="spacer"></div>
          <BaseButton variant="ghost" @click="togglePause">
            {{ status.running ? 'Pause scan' : 'Resume scan' }}
          </BaseButton>
          <BaseButton @click="runScan" :disabled="scanLoading">
            Run scan now
          </BaseButton>
        </div>

        <div class="grid">
          <div class="card recent">
            <div class="card-head">
              <h2 class="card-title">Recent analyses</h2>
              <router-link to="/history" class="link">View all</router-link>
            </div>
            <div v-if="status.recent_analyses?.length === 0" class="empty">
              <p class="empty-t">No analyses yet</p>
              <p class="empty-d">Trigger a scan to begin</p>
            </div>
            <div v-else class="anal-list">
              <router-link
                v-for="a in (status.recent_analyses || []).slice(0, 5)"
                :key="a.id"
                :to="`/analysis/${a.id}`"
                class="anal-row"
              >
                <div class="anal-left">
                  <span class="anal-sym mono">{{ a.chart_name }}</span>
                  <span class="anal-name">{{ new Date(a.timestamp).toLocaleString() }}</span>
                </div>
                <div class="anal-right">
                  <ScoreBar :score="a.score" />
                  <BaseChip :direction="a.direction">{{ a.direction }}</BaseChip>
                </div>
              </router-link>
            </div>
          </div>

          <div class="card signals">
            <div class="card-head">
              <h2 class="card-title">Recent signals</h2>
            </div>
            <div v-if="status.signals?.length === 0" class="empty">
              <p class="empty-t">No signals yet</p>
              <p class="empty-d">Signals appear when analysis score ≥ 7.0</p>
            </div>
            <div v-else class="sig-list">
              <div v-for="s in (status.signals || []).slice(0, 5)" :key="s.id" class="sig-row">
                <div class="sig-left">
                  <span class="sig-sym mono">{{ s.chart_name }}</span>
                  <span class="sig-score mono" :class="{ ok: s.sent }">{{ s.score.toFixed(1) }}</span>
                </div>
                <div class="sig-right">
                  <span class="sig-time mono">{{ new Date(s.timestamp).toLocaleTimeString() }}</span>
                  <BaseChip :status="s.sent ? 'sent' : 'fail'">{{ s.sent ? 'SENT' : 'FAILED' }}</BaseChip>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.dash-head {
  display: flex;
  align-items: center;
  gap: 16px;
}
.h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.015em;
}
.spacer { flex: 1; }
.loading {
  display: grid;
  place-items: center;
  padding: 80px 0;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--surface-3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.timer-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.timer-card {
  display: flex;
  align-items: center;
  gap: 10px;
}
.timer-label {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--muted);
  text-transform: uppercase;
}
.timer-val {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
  color: var(--fg-2);
}
.link {
  font-size: 12px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}
.link:hover { text-decoration: underline; }
.empty {
  text-align: center;
  padding: 24px 0;
  color: var(--muted);
}
.empty-t { font-size: 13px; margin: 0 0 4px; font-weight: 500; }
.empty-d { font-size: 12px; margin: 0; }

.anal-list {
  display: flex;
  flex-direction: column;
}
.anal-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
  transition: background .1s;
}
.anal-row:last-child { border-bottom: 0; }
.anal-row:hover { background: var(--surface-2); }
.anal-left { display: flex; flex-direction: column; gap: 3px; }
.anal-sym { font-size: 14px; font-weight: 600; }
.anal-name { font-size: 12px; color: var(--muted); }
.anal-right { display: flex; align-items: center; gap: 10px; }

.sig-list { display: flex; flex-direction: column; }
.sig-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.sig-row:last-child { border-bottom: 0; }
.sig-left { display: flex; align-items: center; gap: 10px; }
.sig-sym { font-size: 14px; font-weight: 600; }
.sig-score { font-size: 13px; color: var(--muted); }
.sig-score.ok { color: var(--green); }
.sig-right { display: flex; align-items: center; gap: 10px; }
.sig-time { font-size: 12px; color: var(--muted); }
.mono { font-family: var(--font-mono); }
</style>
