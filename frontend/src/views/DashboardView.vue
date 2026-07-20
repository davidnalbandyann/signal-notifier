<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import StatCard from '@/components/ui/StatCard.vue'
import PulseIndicator from '@/components/ui/PulseIndicator.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { getStatus, triggerScan, pauseScan, resumeScan } from '@/api/dashboard'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import type { DashboardStatus } from '@/types'

const toast = useToast()
const { formatTime, formatDate, isSameDay } = useTimezone()
const status = ref<DashboardStatus | null>(null)
const loading = ref(true)
const actionLoading = ref<null | 'scan' | 'pause'>(null)
let tick: ReturnType<typeof setInterval> | null = null
let poll: ReturnType<typeof setInterval> | null = null

function cppExtra(s: any): Record<string, string> {
  if (!s?.signal_json) return {}
  try {
    const j = typeof s.signal_json === 'string' ? JSON.parse(s.signal_json) : s.signal_json
    const e = j.extra || {}
    const out: Record<string, string> = {}
    if (e.bandwidth != null) out.BW = Number(e.bandwidth).toFixed(4).replace(/^0\./, '.')
    if (e.volume_ratio != null) out.VolR = Number(e.volume_ratio).toFixed(2)
    if (e.rsi != null) out.RSI = Number(e.rsi).toFixed(1)
    return out
  } catch { return {} }
}

async function load() {
  try {
    status.value = await getStatus()
  } catch { /* silent */ } finally { loading.value = false }
}

const systemState = computed<'running' | 'paused'>(() =>
  status.value?.running ? 'running' : 'paused'
)

async function runScan() {
  if (actionLoading.value) return
  actionLoading.value = 'scan'
  try {
    await triggerScan()
    toast.ok('Scan triggered')
    await load()
  } catch { toast.err('Failed to trigger scan') }
  finally { actionLoading.value = null }
}

async function togglePause() {
  if (actionLoading.value) return
  actionLoading.value = 'pause'
  try {
    if (status.value?.running) { await pauseScan(); toast.ok('Scan loop paused') }
    else { await resumeScan(); toast.ok('Scan loop resumed') }
    await load()
  } catch { toast.err('Failed to toggle scan loop') }
  finally { actionLoading.value = null }
}

const nextScanIn = computed(() => {
  if (!status.value) return 0
  if (!status.value.running) return 0
  return Math.max(0, status.value.next_scan_seconds)
})
const nextScanFmt = computed(() => {
  const s = nextScanIn.value
  if (s <= 0) return status.value?.running ? 'NOW' : '\u2014'
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
})
const progressPct = computed(() => {
  if (!status.value) return 0
  return Math.min(100, (1 - nextScanIn.value / Math.max(1, status.value.next_scan_seconds || 1)) * 100)
})

function fmtTime(iso: string) {
  const now = new Date().toISOString()
  if (isSameDay(iso, now)) return formatTime(iso)
  return formatDate(iso, { month: 'short', day: 'numeric' }) + ' \u00b7 ' + formatTime(iso)
}

onMounted(() => {
  load()
  tick = setInterval(() => {}, 1000)
  poll = setInterval(load, 15000)
})
onUnmounted(() => {
  if (tick) clearInterval(tick)
  if (poll) clearInterval(poll)
})
</script>

<template>
  <AppShell>
    <div class="dash">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Dashboard</h1>
          <div class="pg-sub">Real-time monitor overview &middot; updated every 15s</div>
        </div>
        <div class="grow"></div>
        <PulseIndicator :state="systemState" />
      </header>

      <AppLoading v-if="loading" size="lg" label="Loading monitor\u2026" />

      <template v-else-if="status">
        <section :class="['scan-bar', { paused: !status.running }]">
          <div class="scan-meta">
            <div class="scan-label eyebrow">Next automatic scan</div>
            <div class="scan-time mono">
              {{ status.running ? nextScanFmt : 'PAUSED' }}
            </div>
          </div>
          <div class="scan-progress">
            <div class="scan-track">
              <span :style="{ width: status.running ? progressPct + '%' : '0%' }"></span>
            </div>
            <div class="scan-info">
              <span class="mono">{{ status.charts_count }} charts</span>
              <span class="sep">&middot;</span>
              <span class="mono">{{ status.analyses_today }} analyses today</span>
            </div>
          </div>
          <div class="scan-actions">
            <BaseButton
              variant="ghost"
              @click="togglePause"
              :disabled="actionLoading === 'pause'"
            >
              <AppIcon :name="status.running ? 'pause' : 'play'" :size="13" />
              {{ status.running ? 'Pause' : 'Resume' }}
            </BaseButton>
            <BaseButton
              @click="runScan"
              :disabled="actionLoading === 'scan'"
            >
              <AppIcon name="refresh" :size="13" :stroke="2.5" />
              {{ actionLoading === 'scan' ? 'Scanning\u2026' : 'Run scan now' }}
            </BaseButton>
          </div>
        </section>

        <section class="stats">
          <StatCard icon="charts" label="Charts watched" :value="status.charts_count" hint="Active watchlist" />
          <StatCard icon="activity" label="Analyses today" :value="status.analyses_today" hint="Vision passes today" />
          <StatCard icon="bell" label="Signals sent" :value="status.signals_sent" hint="Telegram deliveries" />
          <StatCard icon="bolt" label="Average score" :value="status.avg_score.toFixed(1)" hint="Across all analyses" />
        </section>

        <section class="panels">
          <div class="card panel">
            <div class="card-head">
              <div class="card-title">Recent analyses</div>
              <router-link to="/history" class="card-link">
                View all
                <AppIcon name="arrowRight" :size="12" :stroke="2.5" />
              </router-link>
            </div>
            <EmptyState
              v-if="(status.recent_analyses || []).length === 0"
              icon="activity"
              title="No analyses yet"
              description="Trigger a scan to begin capturing charts"
            />
            <ul v-else class="anal-list">
              <li v-for="(a, i) in (status.recent_analyses || []).slice(0, 6)" :key="a.id" :style="{ animationDelay: i * 0.04 + 's' }" class="anim-in">
                <router-link :to="`/analysis/${a.id}`" class="anal-row">
                  <div class="anal-sym">
                    <span class="sym mono">{{ a.chart_name }}</span>
                    <span class="time mono">{{ fmtTime(a.timestamp) }}</span>
                  </div>
                  <div class="anal-right">
                    <ScoreBar :score="a.score" />
                    <BaseChip :direction="a.direction" dot>{{ a.direction }}</BaseChip>
                  </div>
                </router-link>
              </li>
            </ul>
          </div>

          <div class="card panel">
            <div class="card-head">
              <div class="card-title">Recent signals</div>
              <span class="card-meta mono">score &ge; 7.0</span>
            </div>
            <EmptyState
              v-if="(status.signals || []).length === 0"
              icon="bell"
              title="No signals yet"
              description="Signals appear when an analysis scores &ge; 7.0"
            />
            <ul v-else class="sig-list">
              <li v-for="(s, i) in (status.signals || []).slice(0, 6)" :key="s.id" class="sig-row anim-in" :style="{ animationDelay: i * 0.04 + 's' }">
                <div class="sig-top">
                  <span class="sym mono">{{ s.chart_name }}</span>
                  <BaseChip :direction="s.direction" dot>{{ s.direction }}</BaseChip>
                  <span v-if="s.signal_json" class="cpp-tag" title="C++ engine triggered">
                    <AppIcon name="bolt" :size="10" :stroke="2.5" /> C++
                  </span>
                </div>
                <div class="sig-mid">
                  <ScoreBar :score="s.score" size="md" />
                  <BaseChip :status="s.sent ? 'sent' : 'fail'">{{ s.sent ? 'SENT' : 'FAILED' }}</BaseChip>
                </div>
                <div class="sig-bot">
                  <span class="time mono">{{ fmtTime(s.timestamp) }}</span>
                  <div v-if="cppExtra(s)" class="sig-extra mono">
                    <span v-for="(v, k) in cppExtra(s)" :key="k">
                      <span class="k">{{ k }}</span> <span class="v">{{ v }}</span>
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </section>
      </template>
    </div>
    <AppToast />
  </AppShell>
</template>

<style scoped>
.dash { display: flex; flex-direction: column; gap: 18px; max-width: 1500px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; letter-spacing: 0.02em; }

/* Staggered entry animation */
.anim-in {
  animation: item-in 0.35s var(--ease-out) both;
}
@keyframes item-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.scan-bar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 24px;
  padding: 18px 22px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-lg);
  transition: border-left-color var(--speed-normal), box-shadow var(--speed-normal);
  box-shadow: var(--shadow-sm);
}
.scan-bar:hover { box-shadow: var(--shadow-md); }
.scan-bar.paused { border-left-color: var(--amber); }
.scan-meta { display: flex; flex-direction: column; gap: 4px; }
.scan-label { color: var(--muted); }
.scan-time {
  font: 600 30px var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--fg);
  line-height: 1;
}
.scan-bar.paused .scan-time { color: var(--amber); }

.scan-progress { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.scan-track {
  height: 4px;
  background: var(--surface-3);
  border-radius: 999px;
  overflow: hidden;
}
.scan-track > span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent-3), var(--accent));
  border-radius: 999px;
  transition: width 0.5s var(--ease-out);
}
.scan-info { display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: var(--muted); }
.scan-info .sep { color: var(--muted-2); }

.scan-actions { display: flex; gap: 8px; flex-shrink: 0; }

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.panels {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 14px;
  align-items: start;
}
.panel { overflow: hidden; }
.card-head { padding: 12px 16px; }
.card-title { font: 600 11px var(--font-mono); letter-spacing: 0.08em; color: var(--fg-2); text-transform: uppercase; }
.card-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 500 11.5px var(--font-sans);
  color: var(--accent-2);
  transition: color var(--speed-fast);
}
.card-link:hover { color: var(--accent); }
.card-meta { font: 500 10.5px var(--font-mono); color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase; }

.anal-list { list-style: none; }
.anal-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  border-top: 1px solid var(--border);
  color: inherit;
  text-decoration: none;
  transition: background var(--speed-fast);
}
.anal-row:hover { background: var(--surface-2); }
.anal-sym { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.anal-sym .sym { font: 600 13px var(--font-mono); color: var(--fg); }
.anal-sym .time { font: 400 11px var(--font-mono); color: var(--muted); }
.anal-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.sig-list { list-style: none; }
.sig-row {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sig-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sig-top .sym { font: 600 13px var(--font-mono); color: var(--fg); margin-right: auto; }
.cpp-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--amber-soft);
  color: var(--amber);
  font: 700 9.5px var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.sig-mid { display: flex; align-items: center; gap: 10px; }
.sig-bot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.sig-bot .time { font: 400 11px var(--font-mono); color: var(--muted); }
.sig-extra { display: flex; gap: 12px; font: 500 10.5px var(--font-mono); color: var(--muted); }
.sig-extra .k { color: var(--muted-2); }
.sig-extra .v { color: var(--fg-2); }

@media (max-width: 980px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .panels { grid-template-columns: 1fr; }
  .scan-bar { grid-template-columns: 1fr; gap: 16px; padding: 16px; }
  .scan-actions { justify-content: flex-end; }
}
@media (max-width: 480px) {
  .pg-head { flex-direction: column; align-items: flex-start; }
  .scan-time { font-size: 24px; }
}
</style>