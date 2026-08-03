<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import SignalQualification from '@/components/ui/SignalQualification.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import { getAnalyses, resendNotification, reanalyze, deleteAnalysis } from '@/api/analyses'
import { getCharts } from '@/api/charts'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import { useThreshold } from '@/composables/useThreshold'
import type { Analysis, Chart } from '@/types'

const router = useRouter()
const toast = useToast()
const { formatTime, formatDate, isSameDay } = useTimezone()
const { threshold, load: loadThreshold } = useThreshold()
const items = ref<Analysis[]>([])
const charts = ref<Chart[]>([])
const total = ref(0)
const loading = ref(true)

const page = ref(1)
const pageSize = ref(25)
const searchQuery = ref('')
const filterDirection = ref('')
const filterChart = ref('')
const filterChartType = ref('')
const filterMinScore = ref(0)
const filterDateFrom = ref('')
const filterDateTo = ref('')
const filterSignalsOnly = ref(false)
const sortField = ref('timestamp')
const sortDir = ref<'asc' | 'desc'>('desc')
const actionLoading = ref<number | null>(null)
const deleteTarget = ref<number | null>(null)

let searchDebounce: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    applyFilters()
  }, 300)
}

const chartTypeOptions = [
  { value: 'crypto', label: 'Crypto' },
  { value: 'forex', label: 'Forex' },
  { value: 'stocks', label: 'Stocks' },
  { value: 'indices', label: 'Indices' },
  { value: 'commodities', label: 'Commodities' },
  { value: 'other', label: 'Other' },
]

onMounted(async () => {
  try { charts.value = await getCharts() } catch { /* silent */ }
  loadThreshold()
  await load()
})

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = {
      page: String(page.value),
      page_size: String(pageSize.value),
      sort: sortField.value,
      sort_dir: sortDir.value,
    }
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    if (filterDirection.value) params.direction = filterDirection.value
    if (filterChart.value) params.chart = filterChart.value
    if (filterChartType.value) params.chart_type = filterChartType.value
    if (filterMinScore.value > 0) params.min_score = String(filterMinScore.value)
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    if (filterSignalsOnly.value) params.signals_only = '1'
    const res = await getAnalyses(params)
    items.value = res.items
    total.value = res.total
  } catch { toast.err('Failed to load analyses') }
  finally { loading.value = false }
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const startItem = computed(() => total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1)
const endItem = computed(() => Math.min(page.value * pageSize.value, total.value))

const sortLabel = computed(() => {
  const names: Record<string, string> = { timestamp: 'time', chart_name: 'chart', direction: 'direction', score: 'score' }
  const name = names[sortField.value] || sortField.value
  if (sortField.value === 'timestamp') return `${name}, ${sortDir.value === 'desc' ? 'newest first' : 'oldest first'}`
  return `${name}, ${sortDir.value === 'desc' ? 'descending' : 'ascending'}`
})

const pageRange = computed(() => {
  const max = 5, half = 2
  let start = Math.max(1, page.value - half)
  const end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) start = Math.max(1, end - max + 1)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

function goPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  load()
}

function applyFilters() { page.value = 1; load() }
function onPageSize() { page.value = 1; load() }

function applyQuickPreset(preset: 'all' | 'high_score' | 'signals' | 'long' | 'short') {
  if (preset === 'all') {
    searchQuery.value = ''
    filterDirection.value = ''
    filterMinScore.value = 0
    filterSignalsOnly.value = false
  } else if (preset === 'high_score') {
    filterMinScore.value = 7.0
  } else if (preset === 'signals') {
    filterSignalsOnly.value = true
  } else if (preset === 'long') {
    filterDirection.value = 'LONG'
  } else if (preset === 'short') {
    filterDirection.value = 'SHORT'
  }
  applyFilters()
}

function toggleSort(field: string) {
  if (sortField.value === field) sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  else { sortField.value = field; sortDir.value = 'desc' }
  load()
}
function sortArrow(field: string) {
  if (sortField.value !== field) return ''
  return sortDir.value === 'desc' ? '▼' : '▲'
}

function goAnalysis(id: number) { router.push(`/analysis/${id}`) }

async function handleResend(e: Event, id: number) {
  e.stopPropagation()
  actionLoading.value = id
  try { await resendNotification(id); toast.ok('Notification resent'); load() }
  catch { toast.err('Failed to resend') }
  finally { actionLoading.value = null }
}
async function handleReanalyze(e: Event, id: number) {
  e.stopPropagation()
  actionLoading.value = id
  try { await reanalyze(id); toast.ok('Re-analysis started'); load() }
  catch { toast.err('Failed to reanalyze') }
  finally { actionLoading.value = null }
}
async function handleDelete(e: Event, id: number) {
  e.stopPropagation()
  deleteTarget.value = id
}

async function confirmDelete() {
  const id = deleteTarget.value
  if (id == null) return
  actionLoading.value = id
  try { await deleteAnalysis(id); toast.ok('Analysis deleted'); deleteTarget.value = null; load() }
  catch { toast.err('Failed to delete') }
  finally { actionLoading.value = null }
}

const fmtCache = new Map<string, [string, string]>()
let fmtCacheEpoch = 0

function fmtTs(iso: string): [string, string] {
  const hit = fmtCache.get(iso)
  if (hit) return hit
  const time = formatTime(iso)
  const now = cachedNow.value
  const yesterday = cachedYesterday.value
  let result: [string, string]
  if (isSameDay(iso, now)) result = ['Today', time]
  else if (isSameDay(iso, yesterday)) result = ['Yesterday', time]
  else result = [formatDate(iso, { month: 'short', day: 'numeric', year: '2-digit' }), time]
  fmtCache.set(iso, result)
  return result
}

const cachedNow = ref(new Date().toISOString())
const cachedYesterday = ref(new Date(Date.now() - 86400000).toISOString())
let nowTick: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  nowTick = setInterval(() => {
    cachedNow.value = new Date().toISOString()
    cachedYesterday.value = new Date(Date.now() - 86400000).toISOString()
    fmtCacheEpoch++
    if (fmtCacheEpoch > 60) { fmtCache.clear(); fmtCacheEpoch = 0 }
  }, 60000)
})
onUnmounted(() => { if (nowTick) clearInterval(nowTick) })

const activeFilters = computed(() =>
  (searchQuery.value.trim() ? 1 : 0) +
  (filterDirection.value ? 1 : 0) +
  (filterChart.value ? 1 : 0) +
  (filterChartType.value ? 1 : 0) +
  (filterMinScore.value > 0 ? 1 : 0) +
  (filterDateFrom.value ? 1 : 0) +
  (filterDateTo.value ? 1 : 0) +
  (filterSignalsOnly.value ? 1 : 0)
)
function clearFilters() {
  searchQuery.value = ''
  filterDirection.value = ''
  filterChart.value = ''
  filterChartType.value = ''
  filterMinScore.value = 0
  filterDateFrom.value = ''
  filterDateTo.value = ''
  filterSignalsOnly.value = false
  applyFilters()
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Analysis history</h1>
          <div class="pg-sub">{{ total.toLocaleString() }} rows &middot; sorted by {{ sortLabel }}</div>
        </div>
        <div class="grow"></div>
      </header>

      <!-- Search Bar Box (Standalone) -->
      <div class="search-bar-card card">
        <div class="search-field">
          <label class="field-label">Search</label>
          <div class="search-input-wrap">
            <AppIcon name="search" :size="14" class="search-ic" />
            <input
              v-model="searchQuery"
              @input="onSearchInput"
              type="text"
              class="input search-input mono"
              placeholder="Search symbol, reason, levels..."
            />
            <button v-if="searchQuery" class="clear-icon-btn" @click="searchQuery = ''; applyFilters()" title="Clear search">
              <AppIcon name="x" :size="12" />
            </button>
          </div>
        </div>
      </div>

      <!-- Filters Box (Presets + Categorical Controls) -->
      <div class="filters-card card">
        <!-- Quick Preset Filter Chips -->
        <div class="quick-presets">
          <span class="preset-label">Quick filters:</span>
          <button :class="['chip-btn', { active: activeFilters === 0 }]" @click="applyQuickPreset('all')">All</button>
          <button :class="['chip-btn', { active: filterMinScore >= 7 }]" @click="applyQuickPreset('high_score')">Score &ge; 7.0</button>
          <button :class="['chip-btn', { active: filterSignalsOnly }]" @click="applyQuickPreset('signals')">Signals Only</button>
          <button :class="['chip-btn', { active: filterDirection === 'LONG' }]" @click="applyQuickPreset('long')">Long Only</button>
          <button :class="['chip-btn', { active: filterDirection === 'SHORT' }]" @click="applyQuickPreset('short')">Short Only</button>
        </div>

        <div class="filters-grid">
          <div class="filter">
            <label class="field-label">Chart</label>
            <select v-model="filterChart" @change="applyFilters" class="select">
              <option value="">All charts</option>
              <option v-for="c in charts" :key="c.id" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
          <div class="filter">
            <label class="field-label">Asset Type</label>
            <select v-model="filterChartType" @change="applyFilters" class="select">
              <option value="">All types</option>
              <option v-for="t in chartTypeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>

          <div class="filter">
            <label class="field-label">Direction</label>
            <select v-model="filterDirection" @change="applyFilters" class="select">
              <option value="">All</option>
              <option value="LONG">Long</option>
              <option value="SHORT">Short</option>
              <option value="NEUTRAL">Neutral</option>
            </select>
          </div>
          <div class="filter slider-filter">
            <label class="field-label">Min score</label>
            <div class="slider-row">
              <input type="range" min="0" max="10" step="0.5" v-model.number="filterMinScore" @change="applyFilters" />
              <span class="slider-val mono">{{ filterMinScore.toFixed(1) }}</span>
            </div>
          </div>
          <div class="filter">
            <label class="field-label">From</label>
            <input type="date" v-model="filterDateFrom" @change="applyFilters" class="input mono" />
          </div>
          <div class="filter">
            <label class="field-label">To</label>
            <input type="date" v-model="filterDateTo" @change="applyFilters" class="input mono" />
          </div>
          <div class="filter toggle-filter">
            <label class="field-label">Filter</label>
            <BaseToggle v-model="filterSignalsOnly" @update:modelValue="applyFilters">Signals only</BaseToggle>
          </div>
          <button v-if="activeFilters > 0" class="link-btn clear-btn" @click="clearFilters">
            <AppIcon name="x" :size="11" />
            Clear ({{ activeFilters }})
          </button>
        </div>
      </div>



      <AppLoading v-if="loading" label="Loading analyses…" />

      <div v-else-if="items.length === 0" class="card empty-card">
        <EmptyState
          icon="history"
          title="No analyses found"
          :description="filterSignalsOnly
            ? (threshold != null
                ? `No signals above threshold (${threshold.toFixed(1)}) — adjust filters or trigger a scan`
                : 'No signals found — adjust filters or trigger a scan')
            : 'Try adjusting your filters or trigger a scan'"
        />
      </div>

      <div v-else class="card table-card">
        <table>
          <thead>
            <tr>
              <th @click="toggleSort('timestamp')" class="th-sort">
                Timestamp <span class="arr">{{ sortArrow('timestamp') }}</span>
              </th>
              <th @click="toggleSort('chart_name')" class="th-sort">
                Chart <span class="arr">{{ sortArrow('chart_name') }}</span>
              </th>
              <th @click="toggleSort('score')" class="th-sort">
                Qualification <span class="arr">{{ sortArrow('score') }}</span>
              </th>
              <th>Notification</th>
              <th class="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="a in items"
              :key="a.id"
              class="data-row"
              @click="goAnalysis(a.id)"
            >
              <td class="mono ts-cell">
                <template v-for="(part, i) in fmtTs(a.timestamp)" :key="i">
                  <div :class="i === 0 ? 'ts-main' : 'ts-sub'">{{ part }}</div>
                </template>
              </td>
              <td><span class="sym mono">{{ a.chart_name }}</span></td>
              <td class="qual-cell">
                <SignalQualification
                  :score="a.score"
                  :threshold="threshold"
                  :direction="a.direction"
                  :sent="a.sent"
                  density="compact"
                />
              </td>
              <td class="mono id-cell">
                <template v-if="a.notification_id">#{{ String(a.notification_id).padStart(4, '0') }}</template>
                <template v-else>—</template>
              </td>
              <td class="actions-cell" @click.stop>
                <button class="link-btn accent" @click="handleResend($event, a.id)" :disabled="actionLoading === a.id">Resend</button>
                <button class="link-btn" @click="handleReanalyze($event, a.id)" :disabled="actionLoading === a.id">Reanalyze</button>
                <button class="link-btn danger" @click="handleDelete($event, a.id)" :disabled="actionLoading === a.id">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="pager">
          <div class="pager-info">
            Showing <span class="mono">{{ startItem }}–{{ endItem }}</span> of <span class="mono">{{ total.toLocaleString() }}</span>
          </div>
          <div class="pager-controls">
            <select v-model.number="pageSize" @change="onPageSize" class="select pager-size">
              <option :value="12">12 / page</option>
              <option :value="25">25 / page</option>
              <option :value="50">50 / page</option>
              <option :value="100">100 / page</option>
            </select>
            <button class="pag-btn" :disabled="page <= 1" @click="goPage(page - 1)" aria-label="Previous page">
              <AppIcon name="chevronLeft" :size="14" :stroke="2.5" />
            </button>
            <button
              v-for="p in pageRange"
              :key="p"
              :class="['pag-btn', { active: p === page }]"
              @click="goPage(p)"
            >{{ p }}</button>
            <button class="pag-btn" :disabled="page >= totalPages" @click="goPage(page + 1)" aria-label="Next page">
              <AppIcon name="chevronRight" :size="14" :stroke="2.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
    <AppToast />
    <ConfirmModal
      :show="deleteTarget !== null"
      title="Delete analysis"
      message="Delete this analysis? This cannot be undone."
      confirm-label="Delete"
      :loading="actionLoading === deleteTarget"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 16px; max-width: 1500px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

/* Quick Presets */
/* Search Bar Card */
.search-bar-card {
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.search-field { display: flex; flex-direction: column; gap: 5px; }
.search-input-wrap { position: relative; width: 100%; display: flex; align-items: center; }
.search-ic { position: absolute; left: 10px; color: var(--muted); pointer-events: none; }
.search-input { width: 100%; height: 34px; padding: 0 28px 0 32px; font-size: 13px; }
.clear-icon-btn {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  border: 0; background: transparent; color: var(--muted); cursor: pointer; padding: 3px;
  display: flex; align-items: center; justify-content: center; border-radius: 4px;
}
.clear-icon-btn:hover { color: var(--fg); background: var(--surface-2); }

/* Filters Card */
.filters-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.quick-presets {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--border);
}
.preset-label {
  font: 600 11px var(--font-mono);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 2px;
}
.chip-btn {
  padding: 4px 10px;
  font: 500 12px var(--font-sans);
  color: var(--muted);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 99px;
  cursor: pointer;
  transition: all .12s;
}
.chip-btn:hover { color: var(--fg); border-color: var(--accent); }
.chip-btn.active {
  background: var(--surface-hi);
  color: var(--accent-2);
  border-color: var(--accent-2);
  font-weight: 600;
}

.filters-grid {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
.filter { display: flex; flex-direction: column; gap: 5px; }
.filter .select, .filter .input { height: 30px; min-width: 120px; font-size: 12.5px; }
.filter .select { padding-right: 26px; }
.slider-filter .slider-row { display: flex; align-items: center; gap: 10px; height: 30px; min-width: 180px; }
.slider-filter input[type="range"] { width: 120px; }

.slider-val { font: 600 12px var(--font-mono); color: var(--accent-2); min-width: 32px; }
.toggle-filter { padding-bottom: 6px; }
.filters .link-btn { margin-left: auto; align-self: flex-end; margin-bottom: 4px; }
.clear-btn { color: var(--red); font-weight: 500; }



/* Empty */
.empty-card { padding: 0; }

/* Table */
.table-card { overflow: hidden; padding: 0; }
table { width: 100%; border-collapse: collapse; }
thead th {
  text-align: left;
  font: 600 11px var(--font-mono);
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-2);
  white-space: nowrap;
}
.th-sort { cursor: pointer; user-select: none; transition: color .12s; }
.th-sort:hover { color: var(--fg); }
.th-sort .arr { color: var(--muted-2); font-size: 11px; margin-left: 4px; }
.th-actions { text-align: right; }

tbody td {
  padding: 10px 14px;
  border-top: 1px solid var(--border);
  font-size: 12.5px;
  vertical-align: middle;
  white-space: nowrap;
}
tbody tr:first-child td { border-top: 0; }
.data-row { cursor: pointer; transition: background .1s; }
.data-row:hover { background: var(--surface-2); }

.ts-cell { line-height: 1.3; }
.ts-main { font: 500 12px var(--font-mono); color: var(--fg); }
.ts-sub { font: 400 11px var(--font-mono); color: var(--muted); }

.sym { font: 600 12.5px var(--font-mono); color: var(--fg); }

.id-cell { font-size: 11.5px; color: var(--muted); }
.qual-cell { padding: 8px 14px; min-width: 280px; }
.muted { color: var(--muted-2); }

.actions-cell { white-space: nowrap; text-align: right; }
.actions-cell .link-btn { margin-left: 4px; }

/* Pager */
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
  flex-wrap: wrap;
}
.pager-info { font: 400 12px var(--font-sans); color: var(--muted); }
.pager-controls { display: flex; align-items: center; gap: 4px; }
.pager-size { height: 28px; min-width: 100px; font-size: 11.5px; }
.pag-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg-2);
  border-radius: var(--radius-sm);
  font: 600 12px var(--font-mono);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background .12s, color .12s, border-color .12s;
}
.pag-btn:hover:not(:disabled):not(.active) { background: var(--surface-2); color: var(--fg); border-color: var(--border-2); }
.pag-btn.active { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.pag-btn:disabled { opacity: 0.35; cursor: not-allowed; }

@media (max-width: 980px) {
  thead { display: none; }
  tbody td { border-top: 0; }
  .data-row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 6px 12px;
    padding: 12px 14px;
    border-top: 1px solid var(--border);
  }
  .ts-cell { grid-column: 1; }
  .sym { grid-column: 2; text-align: right; align-self: center; }
  .qual-cell { grid-column: 1 / -1; }
  .id-cell { grid-column: 1; }
  .actions-cell { grid-column: 1 / -1; text-align: left; padding-top: 6px; border-top: 1px dashed var(--border); }
  .pager { flex-direction: column; align-items: stretch; }
}
</style>
