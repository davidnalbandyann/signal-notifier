<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import Toast from '@/components/ui/Toast.vue'
import { getAnalyses, resendNotification, reanalyze } from '@/api/analyses'
import { getCharts } from '@/api/charts'
import type { Analysis, Chart } from '@/types'

const router = useRouter()
const items = ref<Analysis[]>([])
const charts = ref<Chart[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const pageSize = ref(12)
const filterDirection = ref('')
const filterChart = ref('')
const filterMinScore = ref(0)
const filterDateFrom = ref('')
const filterDateTo = ref('')
const filterSignalsOnly = ref(false)
const sortField = ref('timestamp')
const sortDir = ref<'asc' | 'desc'>('desc')
const toast = ref({ show: false, message: '' })
const actionLoading = ref<number | null>(null)

onMounted(async () => {
  try {
    charts.value = await getCharts()
  } catch {}
  load()
})

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = { page: String(page.value), page_size: String(pageSize.value) }
    if (filterDirection.value) params.direction = filterDirection.value
    if (filterChart.value) params.chart = filterChart.value
    if (filterMinScore.value > 0) params.min_score = String(filterMinScore.value)
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    if (filterSignalsOnly.value) params.signals_only = '1'
    const res = await getAnalyses(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const pageRange = computed(() => {
  const max = 5
  const half = Math.floor(max / 2)
  let start = Math.max(1, page.value - half)
  let end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) {
    start = Math.max(1, end - max + 1)
  }
  return { start, end }
})

function goPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  load()
}

function applyFilters() {
  page.value = 1
  load()
}

function toggleSort(field: string) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
  load()
}

function sortArrow(field: string) {
  if (sortField.value !== field) return '▽'
  return sortDir.value === 'desc' ? '▼' : '▲'
}

function goToAnalysis(id: number) {
  router.push(`/analysis/${id}`)
}

async function handleResend(e: Event, id: number) {
  e.stopPropagation()
  actionLoading.value = id
  try {
    await resendNotification(id)
    toast.value = { show: true, message: 'Notification resent' }
    load()
  } catch {
    toast.value = { show: true, message: 'Failed to resend' }
  } finally {
    actionLoading.value = null
  }
}

async function handleReanalyze(e: Event, id: number) {
  e.stopPropagation()
  actionLoading.value = id
  try {
    await reanalyze(id)
    toast.value = { show: true, message: 'Re-analysis started' }
    load()
  } catch {
    toast.value = { show: true, message: 'Failed to reanalyze' }
  } finally {
    actionLoading.value = null
  }
}

const startItem = computed(() => total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1)
const endItem = computed(() => Math.min(page.value * pageSize.value, total.value))
</script>

<template>
  <AppShell :crumbs="['History']">
    <div class="pg">
      <div class="page-head">
        <div>
          <h1 class="page-title">Analysis history</h1>
          <div class="page-sub">{{ total.toLocaleString() }} rows · sorted by {{ sortField }} {{ sortDir }}</div>
        </div>
        <div class="page-actions">
          <button class="btn ghost sm" disabled>Export CSV</button>
        </div>
      </div>

      <div class="filters">
        <div class="filter">
          <label>Chart</label>
          <select v-model="filterChart" @change="applyFilters">
            <option value="">All charts</option>
            <option v-for="c in charts" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div class="filter">
          <label>Direction</label>
          <select v-model="filterDirection" @change="applyFilters">
            <option value="">All</option>
            <option value="LONG">Long</option>
            <option value="SHORT">Short</option>
            <option value="NEUTRAL">Neutral</option>
          </select>
        </div>
        <div class="filter">
          <label>Min score</label>
          <div class="slider-wrap">
            <input type="range" min="0" max="10" step="0.5" v-model.number="filterMinScore" @change="applyFilters" />
            <span class="v mono">{{ filterMinScore.toFixed(1) }}</span>
          </div>
        </div>
        <div class="filter">
          <label>From</label>
          <input type="date" v-model="filterDateFrom" @change="applyFilters" />
        </div>
        <div class="filter">
          <label>To</label>
          <input type="date" v-model="filterDateTo" @change="applyFilters" />
        </div>
        <label class="toggle">
          <input type="checkbox" v-model="filterSignalsOnly" @change="applyFilters" />
          <span class="sw"></span>
          <span class="tl">Signals only</span>
        </label>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else-if="items.length === 0" class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--muted)">
          <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
        <p class="empty-t">No analyses found</p>
        <p class="empty-d">Try adjusting your filters</p>
      </div>

      <div v-else class="table-card">
        <table>
          <thead>
            <tr>
              <th @click="toggleSort('timestamp')">Timestamp <span class="arr">{{ sortArrow('timestamp') }}</span></th>
              <th @click="toggleSort('chart_name')">Chart <span class="arr">{{ sortArrow('chart_name') }}</span></th>
              <th @click="toggleSort('direction')">Direction <span class="arr">{{ sortArrow('direction') }}</span></th>
              <th @click="toggleSort('score')">Score <span class="arr">{{ sortArrow('score') }}</span></th>
              <th>Sent?</th>
              <th>Notif ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="a in items"
              :key="a.id"
              @click="goToAnalysis(a.id)"
            >
              <td class="mono" style="font-size:12px; color:var(--muted)">{{ a.timestamp }}</td>
              <td><b>{{ a.chart_name }}</b></td>
              <td>
                <span :class="['chip', a.direction]">{{ a.direction }}</span>
              </td>
              <td>
                <div :class="['score-cell', a.score >= 7 ? 'high' : a.score >= 5 ? 'mid' : 'low']">
                  <div class="bar"><span :class="a.score >= 7 ? 'high' : a.score >= 5 ? 'mid' : 'low'" :style="{ width: (a.score * 10) + '%' }"></span></div>
                  <span>{{ a.score?.toFixed(1) }}</span>
                </div>
              </td>
              <td>
                <span v-if="a.sent" class="sent-yes">&#10003; Telegram</span>
                <span v-else class="sent-no">—</span>
              </td>
              <td class="mono" style="font-size:12px; color:var(--muted)">
                <template v-if="a.notification_id">#NT-{{ String(a.notification_id).padStart(4, '0') }}</template>
                <template v-else>—</template>
              </td>
              <td class="actions-col">
                <button
                  class="link-btn"
                  @click="(e) => handleResend(e, a.id)"
                  :disabled="actionLoading === a.id"
                >Resend</button>
                <button
                  class="link-btn"
                  @click="(e) => handleReanalyze(e, a.id)"
                  :disabled="actionLoading === a.id"
                >Reanalyze</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pag">
          <div class="pag-info">Showing {{ startItem }}–{{ endItem }} of {{ total.toLocaleString() }}</div>
          <div class="pag-controls">
            <button class="pag-btn" :disabled="page <= 1" @click="goPage(page - 1)">&lsaquo; Prev</button>
            <button
              v-for="p in (pageRange.end - pageRange.start + 1)"
              :key="pageRange.start + p - 1"
              :class="['pag-btn', { active: page === pageRange.start + p - 1 }]"
              @click="goPage(pageRange.start + p - 1)"
            >{{ pageRange.start + p - 1 }}</button>
            <button class="pag-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">Next &rsaquo;</button>
            <select class="pag-select" v-model.number="pageSize" @change="applyFilters">
              <option :value="12">12 / page</option>
              <option :value="25">25 / page</option>
              <option :value="50">50 / page</option>
              <option :value="100">100 / page</option>
            </select>
          </div>
        </div>
      </div>
    </div>
    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 18px; }
.page-head { display: flex; align-items: end; justify-content: space-between; margin-bottom: 0; gap: 16px; }
.page-title { font-size: 22px; font-weight: 600; letter-spacing: -0.015em; }
.page-sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.page-actions { display: flex; gap: 8px; }

.filters {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.filter { display: flex; flex-direction: column; gap: 4px; }
.filter label {
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  font-family: var(--font-mono);
}
.filter select, .filter input {
  height: 32px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: var(--radius);
  padding: 0 10px;
  font: 12px var(--font-sans);
  outline: none;
  min-width: 140px;
}
.filter select:focus, .filter input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--ring); }
.filter input[type="date"] { font-family: var(--font-mono); }
.slider-wrap { display: flex; align-items: center; gap: 8px; min-width: 220px; }
.slider-wrap input[type="range"] { width: 120px; accent-color: var(--accent); }
.slider-wrap .v { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--accent-2); min-width: 28px; }
.toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  padding-top: 16px;
}
.toggle input { display: none; }
.toggle .sw {
  width: 32px;
  height: 18px;
  background: var(--surface-3);
  border-radius: 999px;
  transition: background .15s;
  position: relative;
}
.toggle .sw::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 14px;
  height: 14px;
  background: var(--fg);
  border-radius: 50%;
  transition: transform .15s;
}
.toggle input:checked + .sw { background: var(--accent); }
.toggle input:checked + .sw::after { transform: translateX(14px); background: white; }
.toggle .tl { font-size: 12px; color: var(--fg-2); }

.loading { display: grid; place-items: center; padding: 80px 0; }
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--surface-3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 0; color: var(--muted); }
.empty-t { font-size: 14px; font-weight: 600; margin: 12px 0 4px; color: var(--fg-2); }
.empty-d { font-size: 12px; color: var(--muted); margin: 0; }

.table-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
table { width: 100%; border-collapse: collapse; }
thead th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-2);
  cursor: pointer;
  user-select: none;
}
thead th:hover { color: var(--fg); }
thead th .arr { color: var(--muted-2); margin-left: 4px; font-size: 9px; }
tbody td { padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; height: 40px; }
tbody tr { transition: background .1s; cursor: pointer; }
tbody tr:hover { background: var(--surface-2); }
tbody tr:last-child td { border-bottom: 0; }

.actions-col { white-space: nowrap; }
.actions-col .link-btn {
  margin-right: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.chip.LONG { background: var(--green-soft); color: var(--green); }
.chip.SHORT { background: var(--red-soft); color: var(--red); }
.chip.NEUTRAL { background: var(--surface-3); color: var(--fg-2); }
.sent-yes { color: var(--accent-2); font-size: 11px; font-weight: 600; }
.sent-no { color: var(--muted); font-size: 11px; }

.score-cell { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 12px; }
.score-cell .bar { width: 50px; height: 4px; background: var(--surface-3); border-radius: 999px; overflow: hidden; }
.score-cell .bar > span { display: block; height: 100%; }
.score-cell .bar > span.high { background: var(--green); }
.score-cell .bar > span.mid { background: var(--amber); }
.score-cell .bar > span.low { background: var(--red); }
.score-cell.high { color: var(--green); }
.score-cell.mid { color: var(--amber); }
.score-cell.low { color: var(--red); }

.link-btn {
  background: none;
  border: 0;
  color: var(--accent);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background .12s;
}
.link-btn:hover { background: var(--accent-soft); }
.link-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.pag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
}
.pag-info { color: var(--muted); font-size: 12px; font-family: var(--font-mono); }
.pag-controls { display: flex; align-items: center; gap: 4px; }
.pag-btn {
  min-width: 30px;
  height: 30px;
  padding: 0 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg-2);
  border-radius: var(--radius-sm);
  font: 12px var(--font-mono);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.pag-btn:hover { background: var(--surface-2); color: var(--fg); }
.pag-btn.active { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.pag-btn[disabled] { opacity: 0.3; cursor: not-allowed; }
.pag-select {
  margin-left: 12px;
  height: 30px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: var(--radius-sm);
  padding: 0 8px;
  font: 12px var(--font-mono);
}
.mono { font-family: var(--font-mono); }
</style>
