<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PulseIndicator from '@/components/ui/PulseIndicator.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import Toast from '@/components/ui/Toast.vue'
import {
  getEngineStatus, startEngine, stopEngine, getEngineLogs,
} from '@/api/cpp-engine'

const toast = ref({ show: false, message: '' })
const engineStatus = ref<Awaited<ReturnType<typeof getEngineStatus>> | null>(null)
const engineLoading = ref(false)
const logLines = ref<string[]>([])
const logContainer = ref<HTMLElement | null>(null)
let logTimer: ReturnType<typeof setInterval> | null = null

// C++ signal history
const signals = ref<any[]>([])
const signalsLoading = ref(false)

function formatUptime(s: number): string {
  const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); const r = s % 60
  if (h > 0) return `${h}h ${m}m ${r}s`
  if (m > 0) return `${m}m ${r}s`
  return `${r}s`
}

function cppExtra(s: any): Record<string, any> {
  if (!s.signal_json) return {}
  try {
    const j = typeof s.signal_json === 'string' ? JSON.parse(s.signal_json) : s.signal_json
    const e = j.extra || {}
    const out: Record<string, any> = {}
    if (e.bandwidth) out.BW = Number(e.bandwidth).toFixed(4).replace(/^0\./, '.')
    if (e.volume_ratio) out.VolR = Number(e.volume_ratio).toFixed(2)
    if (e.rsi) out.RSI = Number(e.rsi).toFixed(1)
    return out
  } catch { return {} }
}

async function loadStatus() {
  try { engineStatus.value = await getEngineStatus() } catch { /* silent */ }
}

async function toggleEngine() {
  engineLoading.value = true
  try {
    if (engineStatus.value?.running) { await stopEngine() } else { await startEngine() }
    await loadStatus()
    toast.value = { show: true, message: engineStatus.value?.running ? 'Engine started' : 'Engine stopped' }
  } catch (e: any) {
    toast.value = { show: true, message: e?.message || 'Failed to toggle engine' }
  } finally { engineLoading.value = false }
}

async function loadLogs() {
  try {
    const r = await getEngineLogs()
    logLines.value = r.lines
    if (logContainer.value) {
      await nextTick()
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  } catch { /* silent */ }
}

async function loadSignals() {
  signalsLoading.value = true
  try {
    const r = await (await fetch('/api/cpp-engine/signals', {
      headers: { Authorization: 'Bearer ' + (localStorage.getItem('tcm_token') || '') },
    })).json()
    signals.value = r.signals || []
  } catch { /* silent */ } finally { signalsLoading.value = false }
}

watch(() => engineStatus.value?.running, (running) => {
  if (running) {
    logTimer = setInterval(loadLogs, 2000)
    loadLogs()
  } else if (logTimer) {
    clearInterval(logTimer); logTimer = null
  }
})

onUnmounted(() => { if (logTimer) clearInterval(logTimer) })

loadStatus()
loadSignals()
</script>

<template>
  <AppShell :crumbs="['C++ Engine']">
    <div class="page-layout">
      <div class="status-bar">
        <PulseIndicator :state="engineStatus?.running ? 'running' : 'stopped'" />
        <span class="status-label">C++ Signal Engine</span>
        <span v-if="engineStatus?.pid" class="status-detail mono">PID {{ engineStatus.pid }}</span>
        <span v-if="engineStatus?.uptime_seconds" class="status-detail mono">{{ formatUptime(engineStatus.uptime_seconds) }}</span>
        <div class="spacer"></div>
        <BaseButton
          :variant="engineStatus?.running ? 'warn' : 'primary'"
          :disabled="engineLoading"
          @click="toggleEngine"
        >{{ engineLoading ? '...' : engineStatus?.running ? 'Stop Engine' : 'Start Engine' }}</BaseButton>
      </div>

      <div class="last-signal" v-if="engineStatus?.last_signal">
        <span class="ls-label">Last C++ Signal:</span>
        <span class="ls-sym mono">{{ engineStatus.last_signal.chart_name }}</span>
        <BaseChip :direction="(engineStatus.last_signal.direction as any)">{{ engineStatus.last_signal.direction }}</BaseChip>
        <span v-if="engineStatus.last_signal.entry" class="ls-entry mono">@ {{ engineStatus.last_signal.entry }}</span>
        <span class="ls-score mono">{{ engineStatus.last_signal.score }}</span>
      </div>

      <div class="log-section">
        <div class="section-title">Engine Logs <span class="log-hint" v-if="engineStatus?.running">(polling every 2s)</span></div>
        <div class="log-viewport" ref="logContainer">
          <div v-if="logLines.length === 0" class="log-empty">Waiting for logs...</div>
          <div v-for="(line, i) in logLines" :key="i" class="log-line mono">{{ line }}</div>
        </div>
      </div>

      <div class="signals-section">
        <div class="section-title">C++ Signal History</div>
        <div v-if="signalsLoading && signals.length === 0" class="empty-state">Loading...</div>
        <div v-else-if="signals.length === 0" class="empty-state">No C++ signals yet</div>
        <div v-else class="signal-table">
          <div class="st-header">
            <span class="st-col sym">Symbol</span>
            <span class="st-col dir">Dir</span>
            <span class="st-col entry">Entry</span>
            <span class="st-col num">BW</span>
            <span class="st-col num">VolR</span>
            <span class="st-col num">RSI</span>
            <span class="st-col num">Score</span>
            <span class="st-col time">Time</span>
            <span class="st-col status">Status</span>
          </div>
          <div v-for="s in signals" :key="s.id" class="st-row">
            <span class="st-col sym mono">{{ s.chart_name }}</span>
            <span class="st-col dir"><BaseChip :direction="s.direction">{{ s.direction }}</BaseChip></span>
            <span class="st-col entry mono">{{ s.entry || '—' }}</span>
            <span v-for="(v, k) in cppExtra(s)" :key="k" class="st-col num mono">{{ v }}</span>
            <span v-for="n in (3 - Object.keys(cppExtra(s)).length)" :key="'e'+n" class="st-col num mono">—</span>
            <span class="st-col num mono">{{ s.score.toFixed(1) }}</span>
            <span class="st-col time mono">{{ new Date(s.timestamp).toLocaleTimeString() }}</span>
            <span class="st-col status"><BaseChip :status="s.sent ? 'sent' : 'fail'">{{ s.sent ? 'SENT' : 'FAILED' }}</BaseChip></span>
          </div>
        </div>
      </div>
    </div>
    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.page-layout { display: flex; flex-direction: column; gap: 20px; }
.spacer { flex: 1; }

/* Status bar */
.status-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
}
.status-label { font-size: 14px; font-weight: 600; }
.status-detail { font-size: 12px; color: var(--muted); }

/* Last signal banner */
.last-signal {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 18px;
  background: var(--accent-soft); border: 1px solid var(--border); border-radius: var(--radius-lg);
}
.ls-label { font-size: 12px; font-weight: 600; color: var(--fg-2); }
.ls-sym { font-size: 14px; font-weight: 600; }
.ls-entry { font-size: 13px; font-weight: 600; }
.ls-score { font-size: 13px; color: var(--muted); }

/* Section titles */
.section-title { font-size: 13px; font-weight: 600; color: var(--fg-2); margin-bottom: 8px; }
.log-hint { font-weight: 400; font-size: 11px; color: var(--muted); }

/* Log viewer */
.log-viewport {
  max-height: 400px; overflow-y: auto;
  padding: 12px 16px;
  background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--radius-lg);
  font-size: 11px; line-height: 1.7;
}
.log-line { white-space: pre; word-break: break-all; color: var(--fg-2); }
.log-line:nth-child(even) { background: oklch(0 0 0 / 0.02); }
.log-empty { color: var(--muted); font-style: italic; }
.empty-state { color: var(--muted); font-size: 13px; padding: 24px 0; text-align: center; }

/* Signal table */
.signal-table {
  display: flex; flex-direction: column;
  border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden;
}
.st-header, .st-row {
  display: grid;
  grid-template-columns: 1.2fr 0.6fr 0.8fr 0.5fr 0.5fr 0.5fr 0.5fr 0.9fr 0.7fr;
  gap: 8px;
  padding: 10px 16px;
  align-items: center;
}
.st-header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
.st-row {
  background: var(--surface); font-size: 13px;
  border-bottom: 1px solid var(--border);
}
.st-row:last-child { border-bottom: 0; }
.st-row:hover { background: var(--surface-2); }
.st-col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.st-col.num { text-align: right; font-family: var(--font-mono); }
.st-col.time { font-size: 12px; color: var(--muted); }
</style>
