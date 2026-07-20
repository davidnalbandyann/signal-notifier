<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PulseIndicator from '@/components/ui/PulseIndicator.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import {
  getEngineStatus, startEngine, stopEngine, getEngineLogs,
} from '@/api/cpp-engine'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import type { CppEngineStatus } from '@/types'

const toast = useToast()
const { formatTime } = useTimezone()
const status = ref<CppEngineStatus | null>(null)
const loading = ref(true)
const engineLoading = ref(false)
const logLines = ref<string[]>([])
const logBox = ref<HTMLElement | null>(null)
const signals = ref<any[]>([])
const signalsLoading = ref(true)
let logTimer: ReturnType<typeof setInterval> | null = null

function fmtUptime(s: number | null) {
  if (s == null) return '\u2014'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = Math.floor(s % 60)
  if (h > 0) return `${h}h ${m}m ${r}s`
  if (m > 0) return `${m}m ${r}s`
  return `${r}s`
}

function cppExtra(s: any): string[] {
  if (!s?.signal_json) return ['\u2014', '\u2014', '\u2014']
  try {
    const j = typeof s.signal_json === 'string' ? JSON.parse(s.signal_json) : s.signal_json
    const e = j.extra || {}
    return [
      e.bandwidth != null ? Number(e.bandwidth).toFixed(4).replace(/^0\./, '.') : '\u2014',
      e.volume_ratio != null ? Number(e.volume_ratio).toFixed(2) : '\u2014',
      e.rsi != null ? Number(e.rsi).toFixed(1) : '\u2014',
    ]
  } catch { return ['\u2014', '\u2014', '\u2014'] }
}

async function loadStatus() {
  try { status.value = await getEngineStatus() }
  catch { /* silent */ } finally { loading.value = false }
}

async function toggleEngine() {
  engineLoading.value = true
  try {
    if (status.value?.running) { await stopEngine(); toast.ok('Engine stopped') }
    else { await startEngine(); toast.ok('Engine started') }
    await loadStatus()
  } catch (e: any) { toast.err(e?.message || 'Failed to toggle engine') }
  finally { engineLoading.value = false }
}

async function loadLogs() {
  try {
    const r = await getEngineLogs()
    logLines.value = r.lines
    if (logBox.value) {
      await nextTick()
      logBox.value.scrollTop = logBox.value.scrollHeight
    }
  } catch { /* silent */ }
}

async function loadSignals() {
  signalsLoading.value = true
  try {
    const token = localStorage.getItem('tcm_token') || ''
    const res = await fetch('/api/cpp-engine/signals', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (res.ok) {
      const r = await res.json()
      signals.value = r.signals || []
    }
  } catch { /* silent */ } finally { signalsLoading.value = false }
}

watch(() => status.value?.running, (running) => {
  if (running) { logTimer = setInterval(loadLogs, 2000); loadLogs() }
  else if (logTimer) { clearInterval(logTimer); logTimer = null }
}, { immediate: false })

onUnmounted(() => { if (logTimer) clearInterval(logTimer) })

const lastSignal = computed(() => status.value?.last_signal || null)

loadStatus()
loadSignals()
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">C++ signal engine</h1>
          <div class="pg-sub">External signal process &middot; real-time log streaming</div>
        </div>
        <div class="grow"></div>
        <PulseIndicator :state="status?.running ? 'running' : 'stopped'" />
      </header>

      <AppLoading v-if="loading" label="Loading engine status\u2026" />

      <template v-else>
        <section class="card status-bar">
          <div class="status-left">
            <PulseIndicator :state="status?.running ? 'running' : 'stopped'" />
            <div class="status-meta">
              <span class="status-label">C++ Signal Engine</span>
              <div class="status-stats mono">
                <span v-if="status?.pid">PID {{ status.pid }}</span>
                <span v-if="status?.uptime_seconds" class="sep">&middot;</span>
                <span v-if="status?.uptime_seconds">up {{ fmtUptime(status.uptime_seconds) }}</span>
                <span v-if="!status?.pid" class="muted">not running</span>
              </div>
            </div>
          </div>
          <div class="grow"></div>
          <BaseButton
            :variant="status?.running ? 'warn' : 'primary'"
            @click="toggleEngine"
            :disabled="engineLoading"
          >
            <AppIcon :name="status?.running ? 'pause' : 'play'" :size="13" />
            <span v-if="engineLoading">&hellip;</span>
            <span v-else>{{ status?.running ? 'Stop engine' : 'Start engine' }}</span>
          </BaseButton>
        </section>

        <section v-if="lastSignal" class="card last-sig">
          <div class="ls-label eyebrow">Last C++ signal</div>
          <div class="ls-body">
            <span class="ls-sym mono">{{ lastSignal.chart_name }}</span>
            <BaseChip :direction="(lastSignal.direction as any)" dot>{{ lastSignal.direction }}</BaseChip>
            <span v-if="lastSignal.entry" class="ls-entry mono">@ {{ lastSignal.entry }}</span>
            <span class="ls-sep">&middot;</span>
            <span class="ls-score mono">score {{ lastSignal.score }}</span>
            <span class="ls-time mono">{{ formatTime(lastSignal.timestamp) }}</span>
          </div>
        </section>

        <section class="card log-card">
          <div class="card-head">
            <div class="card-title">Engine logs</div>
            <span v-if="status?.running" class="live-tag mono">
              <span class="live-dot"></span> polling every 2s
            </span>
            <span v-else class="card-meta mono">paused</span>
          </div>
          <div ref="logBox" class="log-viewport">
            <div v-if="logLines.length === 0" class="log-empty">
              <AppIcon name="terminal" :size="22" :stroke="1.5" />
              <span>{{ status?.running ? 'Waiting for log output\u2026' : 'Start the engine to see logs' }}</span>
            </div>
            <pre v-else class="log-pre"><div v-for="(line, i) in logLines" :key="i" class="log-line">{{ line }}</div></pre>
          </div>
        </section>

        <section class="card sig-card">
          <div class="card-head">
            <div class="card-title">Signal history</div>
            <span class="card-meta mono">{{ signals.length }} records</span>
          </div>
          <AppLoading v-if="signalsLoading" size="sm" />
          <EmptyState
            v-else-if="signals.length === 0"
            icon="activity"
            title="No C++ signals recorded"
            description="Signals produced by the C++ engine will appear here"
          />
          <div v-else class="sig-table">
            <div class="sig-head">
              <span class="c-sym">Symbol</span>
              <span class="c-dir">Dir</span>
              <span class="c-num">BW</span>
              <span class="c-num">VolR</span>
              <span class="c-num">RSI</span>
              <span class="c-entry">Entry</span>
              <span class="c-num">Score</span>
              <span class="c-time">Time</span>
              <span class="c-status">Status</span>
            </div>
            <div v-for="s in signals" :key="s.id" class="sig-row">
              <span class="c-sym mono">{{ s.chart_name }}</span>
              <span class="c-dir"><BaseChip :direction="s.direction" dot>{{ s.direction }}</BaseChip></span>
              <span class="c-num mono">{{ cppExtra(s)[0] }}</span>
              <span class="c-num mono">{{ cppExtra(s)[1] }}</span>
              <span class="c-num mono">{{ cppExtra(s)[2] }}</span>
              <span class="c-entry mono">{{ s.entry || '\u2014' }}</span>
              <span class="c-num mono" :class="s.score >= 7 ? 'high' : s.score >= 5 ? 'mid' : 'low'">{{ s.score.toFixed(1) }}</span>
              <span class="c-time mono">{{ formatTime(s.timestamp) }}</span>
              <span class="c-status"><BaseChip :status="s.sent ? 'sent' : 'fail'">{{ s.sent ? 'SENT' : 'FAILED' }}</BaseChip></span>
            </div>
          </div>
        </section>
      </template>
    </div>
    <AppToast />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 16px; max-width: 1500px; }
.pg-head { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.status-bar { display: flex; align-items: center; gap: 12px; padding: 14px 18px; }
.status-left { display: flex; align-items: center; gap: 14px; }
.status-meta { display: flex; flex-direction: column; gap: 2px; }
.status-label { font: 600 13.5px var(--font-sans); color: var(--fg); }
.status-stats { display: flex; align-items: center; gap: 6px; font: 500 11.5px var(--font-mono); color: var(--fg-2); }
.status-stats .sep, .status-stats .muted { color: var(--muted-2); }

.last-sig { padding: 12px 18px; display: flex; flex-direction: column; gap: 6px; border-left: 3px solid var(--amber); }
.ls-label { color: var(--muted); }
.ls-body { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ls-sym { font: 600 14px var(--font-mono); color: var(--fg); }
.ls-entry { font: 600 13px var(--font-mono); color: var(--accent-2); }
.ls-sep { color: var(--muted-2); }
.ls-score { font: 500 12.5px var(--font-mono); color: var(--fg-2); }
.ls-time { font: 400 11.5px var(--font-mono); color: var(--muted); margin-left: auto; }

.log-card { padding: 0; overflow: hidden; }
.card-head { padding: 11px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-title { font: 600 11px var(--font-mono); letter-spacing: 0.08em; color: var(--fg-2); text-transform: uppercase; }
.card-meta { font: 500 10.5px var(--font-mono); color: var(--muted); letter-spacing: 0.04em; text-transform: uppercase; }
.live-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: 600 10.5px var(--font-mono);
  color: var(--green);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0.5); }
  70%  { box-shadow: 0 0 0 6px oklch(74% 0.17 152 / 0); }
  100% { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0); }
}

.log-viewport {
  max-height: 380px;
  overflow-y: auto;
  padding: 10px 14px;
  background: oklch(0% 0 0 / 0.18);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.7;
}
[data-theme="light"] .log-viewport { background: oklch(0% 0 0 / 0.03); }
.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--muted);
  font: 400 12px var(--font-sans);
}
.log-pre { margin: 0; font-family: inherit; }
.log-line {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--fg-2);
}
.log-line:hover { background: oklch(100% 0 0 / 0.03); }

.sig-card { padding: 0; overflow: hidden; }
.sig-table { display: flex; flex-direction: column; }
.sig-head, .sig-row {
  display: grid;
  grid-template-columns: 1.2fr 0.7fr 0.7fr 0.7fr 0.7fr 1fr 0.7fr 1fr 0.9fr;
  gap: 10px;
  padding: 9px 16px;
  align-items: center;
}
.sig-head {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  font: 600 10px var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.sig-row {
  font: 500 12px var(--font-mono);
  border-top: 1px solid var(--border);
  transition: background var(--speed-fast);
}
.sig-row:hover { background: var(--surface-2); }
.c-sym { color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-num { text-align: right; color: var(--fg-2); }
.c-num.high { color: var(--green); }
.c-num.mid { color: var(--amber); }
.c-num.low { color: var(--red); }
.c-entry { color: var(--fg-2); }
.c-time { color: var(--muted); font-size: 11px; }

@media (max-width: 980px) {
  .sig-head { display: none; }
  .sig-row {
    grid-template-columns: 1fr auto;
    gap: 4px 10px;
    padding: 10px 14px;
  }
  .c-sym { grid-column: 1; }
  .c-status { grid-column: 2; }
  .c-dir, .c-entry, .c-num, .c-time { grid-column: auto; }
}
</style>