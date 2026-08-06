<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import { getCharts, addChart, updateChart, deleteChart, seedCharts } from '@/api/charts'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import type { Chart, ChartType } from '@/types'

const toast = useToast()
const { formatDate, formatTime } = useTimezone()
const charts = ref<Chart[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterTab = ref<'all' | 'active' | 'paused'>('all')
const filterType = ref<'all' | ChartType>('all')

const showAdd = ref(false)
const newUrl = ref('')
const newName = ref('')
const newType = ref<ChartType>('crypto')
const typeTouched = ref(false)
const addLoading = ref(false)
const seedLoading = ref(false)

const showEdit = ref(false)
const editing = ref<Chart | null>(null)
const editName = ref('')
const editUrl = ref('')
const editType = ref<ChartType>('crypto')
const editEnabled = ref(true)
const deleteTarget = ref<Chart | null>(null)
const editLoading = ref(false)

const typeOptions: { value: ChartType; label: string }[] = [
  { value: 'crypto', label: 'Crypto' },
  { value: 'forex', label: 'Forex' },
  { value: 'stocks', label: 'Stocks' },
  { value: 'indices', label: 'Indices' },
  { value: 'commodities', label: 'Commodities' },
  { value: 'other', label: 'Other' },
]

const activeCount = computed(() => charts.value.filter(c => c.enabled).length)
const pausedCount = computed(() => charts.value.filter(c => !c.enabled).length)

const typeCounts = computed(() => {
  const counts: Record<string, number> = { all: charts.value.length }
  typeOptions.forEach(t => {
    counts[t.value] = charts.value.filter(c => c.type === t.value).length
  })
  return counts
})

const filteredCharts = computed(() => {
  return charts.value.filter(c => {
    if (filterTab.value === 'active' && !c.enabled) return false
    if (filterTab.value === 'paused' && c.enabled) return false
    if (filterType.value !== 'all' && c.type !== filterType.value) return false
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim()
      return c.name.toLowerCase().includes(q) || c.url.toLowerCase().includes(q) || (c.type && c.type.toLowerCase().includes(q))
    }
    return true
  })
})

function autoDetectType(url: string, name: string): ChartType {
  const u = (url || '').toUpperCase()
  const n = (name || '').toUpperCase()
  if (u.includes('SYMBOL=FX:') || ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF', 'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY'].some(f => n.includes(f))) return 'forex'
  if (u.includes('XAUUSD') || u.includes('XAGUSD') || u.includes('USOIL') || u.includes('GLD') || u.includes('SLV') || u.includes('USO') || n.includes('GOLD') || n.includes('SILVER') || n.includes('OIL')) return 'commodities'
  if (u.includes('SYMBOL=INDEX:') || u.includes('SPXUSD') || u.includes('NSXUSD') || u.includes('DJI') || u.includes('DEU40') || n.includes('S&P 500') || n.includes('NASDAQ 100') || n.includes('DOW JONES') || n.includes('DAX 40') || n.includes('SPY') || n.includes('QQQ')) return 'indices'
  if (u.includes('SYMBOL=NASDAQ:') || u.includes('SYMBOL=NYSE:') || u.includes('SYMBOL=AMEX:')) return 'stocks'
  return 'crypto'
}

watch([newUrl, newName], () => {
  if (!typeTouched.value && newUrl.value) {
    newType.value = autoDetectType(newUrl.value, newName.value)
  }
})

async function load() {
  loading.value = true
  try {
    const res = await getCharts()
    charts.value = Array.isArray(res) ? res : []
  }
  catch { toast.err('Failed to load charts') }
  finally { loading.value = false }
}
load()

async function handleSeed() {
  seedLoading.value = true
  try {
    const res = await seedCharts()
    toast.ok(`Seeded ${res.inserted} default chart(s)`)
    await load()
  } catch (e: any) {
    toast.err(e?.message || 'Failed to seed charts')
  } finally { seedLoading.value = false }
}

async function handleToggle(c: Chart, enabled: boolean) {
  const previousState = c.enabled
  c.enabled = enabled
  try {
    await updateChart(c.id, { enabled })
    toast.ok(`${c.name} ${enabled ? 'active' : 'paused'}`)
  } catch (e: any) {
    c.enabled = previousState
    toast.err(e?.message || 'Failed to update chart status')
  }
}

function openAdd() {
  newUrl.value = ''
  newName.value = ''
  newType.value = 'crypto'
  typeTouched.value = false
  showAdd.value = true
}

async function handleAdd() {
  if (!newUrl.value.trim()) return
  addLoading.value = true
  try {
    await addChart({
      name: newName.value.trim() || newUrl.value.trim(),
      url: newUrl.value.trim(),
      type: newType.value,
    })
    toast.ok('Chart added to watchlist')
    showAdd.value = false
    await load()
  } catch (e: any) {
    toast.err(e?.message || 'Failed to add chart')
  } finally { addLoading.value = false }
}

function openEdit(c: Chart) {
  editing.value = c
  editName.value = c.name
  editUrl.value = c.url
  editType.value = c.type || 'crypto'
  editEnabled.value = c.enabled
  showEdit.value = true
}

async function handleEdit() {
  if (!editing.value) return
  editLoading.value = true
  try {
    await updateChart(editing.value.id, {
      name: editName.value,
      url: editUrl.value,
      type: editType.value,
      enabled: editEnabled.value,
    })
    toast.ok('Chart updated')
    showEdit.value = false
    await load()
  } catch (e: any) {
    toast.err(e?.message || 'Failed to update chart')
  } finally { editLoading.value = false }
}

async function handleDelete(c: Chart) {
  deleteTarget.value = c
}

async function confirmDelete() {
  const c = deleteTarget.value
  if (!c) return
  try {
    await deleteChart(c.id)
    toast.ok('Chart removed')
    deleteTarget.value = null
    await load()
  } catch (e: any) {
    toast.err(e?.message || 'Failed to delete chart')
  }
}

function favicon(url: string) {
  try {
    const u = new URL(url)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch { return '' }
}

function fmtDate(iso: string | null) {
  if (!iso) return 'never'
  return formatDate(iso, { month: 'short', day: 'numeric' }) + ' · ' + formatTime(iso)
}

function typeBadgeLabel(type: ChartType) {
  switch (type) {
    case 'crypto': return 'Crypto'
    case 'forex': return 'Forex'
    case 'stocks': return 'Stocks'
    case 'indices': return 'Indices'
    case 'commodities': return 'Commodities'
    default: return 'Other'
  }
}

const hasActiveChartFilters = computed(() => filterTab.value !== 'all' || filterType.value !== 'all' || searchQuery.value.trim() !== '')

function resetChartFilters() {
  filterTab.value = 'all'
  filterType.value = 'all'
  searchQuery.value = ''
}
</script>

<template>
  <div class="tab-wrapper">
    <div class="header-actions">
      <BaseButton variant="ghost" @click="handleSeed" :disabled="seedLoading">
        <AppIcon v-if="!seedLoading" name="refresh" :size="13" />
        <span v-else class="spinner sm"></span>
        {{ seedLoading ? 'Seeding…' : 'Seed default charts' }}
      </BaseButton>
      <BaseButton @click="openAdd">
        <AppIcon name="plus" :size="14" :stroke="2.5" />
        Add chart
      </BaseButton>
    </div>

    <!-- Search Bar Section -->
    <div v-if="charts.length > 0" class="search-card card">
      <div class="search-box">
        <AppIcon name="search" :size="14" class="search-ic" />
        <input
          v-model="searchQuery"
          type="text"
          class="input search-input mono"
          placeholder="Search symbols, types, URLs..."
        />
        <button v-if="searchQuery" class="clear-search-btn" @click="searchQuery = ''" title="Clear search">
          <AppIcon name="x" :size="12" />
        </button>
      </div>
    </div>

    <!-- Filter Tabs Section -->
    <div v-if="charts.length > 0" class="filter-card card">
      <div class="filter-groups">
        <div class="tab-grp">
          <button :class="['tab-btn', { active: filterTab === 'all' }]" @click="filterTab = 'all'">
            All <span class="badge">{{ charts.length }}</span>
          </button>
          <button :class="['tab-btn', { active: filterTab === 'active' }]" @click="filterTab = 'active'">
            Active <span class="badge green">{{ activeCount }}</span>
          </button>
          <button :class="['tab-btn', { active: filterTab === 'paused' }]" @click="filterTab = 'paused'">
            Paused <span class="badge muted">{{ pausedCount }}</span>
          </button>
        </div>

        <div class="tab-grp type-grp">
          <button :class="['tab-btn', { active: filterType === 'all' }]" @click="filterType = 'all'">
            All Types
          </button>
          <button
            v-for="t in typeOptions"
            :key="t.value"
            v-show="typeCounts[t.value] > 0 || filterType === t.value"
            :class="['tab-btn', { active: filterType === t.value }]"
            @click="filterType = t.value"
          >
            {{ t.label }} <span class="badge type-count">{{ typeCounts[t.value] }}</span>
          </button>
        </div>

        <button v-if="hasActiveChartFilters" class="link-btn reset-btn" @click="resetChartFilters">
          <AppIcon name="x" :size="12" /> Clear filters
        </button>
      </div>
    </div>


    <AppLoading v-if="loading" label="Loading watchlist…" />

    <div v-else-if="charts.length === 0" class="card empty-card">
      <EmptyState
        icon="charts"
        title="No charts in the watchlist"
        description="Add a TradingView chart URL or seed default charts to begin monitoring"
        action="Add your first chart"
        @action="openAdd"
      />
      <div class="empty-seed-bar">
        <BaseButton variant="ghost" @click="handleSeed" :disabled="seedLoading">
          <AppIcon v-if="!seedLoading" name="refresh" :size="13" />
          <span v-else class="spinner sm"></span>
          {{ seedLoading ? 'Seeding default charts…' : 'Seed default charts' }}
        </BaseButton>
      </div>
    </div>

    <div v-else class="card list-card">
      <div class="list-head">
        <div class="col-sym">Chart ({{ filteredCharts.length }})</div>
        <div class="col-type">Type</div>
        <div class="col-score">Last score</div>
        <div class="col-scan">Last scanned</div>
        <div class="col-status">Status</div>
        <div class="col-actions"></div>
      </div>
      <div v-for="c in filteredCharts" :key="c.id" class="list-row">
        <div class="col-sym">
          <img v-if="favicon(c.url)" :src="favicon(c.url)" width="14" height="14" class="fav" alt="" />
          <div class="sym-text">
            <div class="sym mono">{{ c.name }}</div>
            <div class="url mono" :title="c.url">{{ c.url }}</div>
          </div>
        </div>
        <div class="col-type">
          <span :class="['type-badge', c.type || 'crypto']">{{ typeBadgeLabel(c.type || 'crypto') }}</span>
        </div>
        <div class="col-score">
          <span v-if="c.last_score !== null" :class="['score-num', 'mono', c.last_score >= 7 ? 'high' : c.last_score >= 5 ? 'mid' : 'low']">
            {{ c.last_score.toFixed(1) }}
          </span>
          <span v-else class="muted mono">—</span>
        </div>
        <div class="col-scan mono">{{ fmtDate(c.last_scanned) }}</div>
        <div class="col-status">
          <BaseToggle :model-value="c.enabled" @update:model-value="(val) => handleToggle(c, val)">
            <span :class="['status-lbl', c.enabled ? 'on' : 'off']">{{ c.enabled ? 'Active' : 'Paused' }}</span>
          </BaseToggle>
        </div>
        <div class="col-actions">
          <button class="icon-btn" @click="openEdit(c)" title="Edit chart" aria-label="Edit">
            <AppIcon name="edit" :size="14" />
          </button>
          <button class="icon-btn danger" @click="handleDelete(c)" title="Delete chart" aria-label="Delete">
            <AppIcon name="trash" :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- Add modal -->
    <BaseModal :show="showAdd" @close="showAdd = false" :width="460">
      <template #title>Add chart</template>
      <div class="modal-body">
        <p class="modal-desc">Paste a TradingView chart URL. The chart will be captured on every scan cycle.</p>
        <div class="field">
          <label class="field-label">Chart URL</label>
          <input
            v-model="newUrl"
            class="input mono"
            type="url"
            required
            placeholder="https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT"
            autofocus
          />
        </div>
        <div class="field">
          <label class="field-label">Friendly name (optional)</label>
          <input
            v-model="newName"
            class="input mono"
            type="text"
            placeholder="BTC/USD 15m"
          />
        </div>
        <div class="field">
          <label class="field-label">Chart Type</label>
          <select v-model="newType" class="input type-select" @change="typeTouched = true">
            <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showAdd = false">Cancel</BaseButton>
        <BaseButton @click="handleAdd" :disabled="addLoading || !newUrl.trim()">
          <AppIcon v-if="!addLoading" name="plus" :size="13" :stroke="2.5" />
          <span v-else class="spinner sm"></span>
          {{ addLoading ? 'Adding…' : 'Add chart' }}
        </BaseButton>
      </footer>
    </BaseModal>

    <!-- Edit modal -->
    <BaseModal :show="showEdit" @close="showEdit = false" :width="460">
      <template #title>Edit chart</template>
      <div class="modal-body">
        <div class="field">
          <label class="field-label">Name</label>
          <input v-model="editName" class="input mono" type="text" />
        </div>
        <div class="field">
          <label class="field-label">Chart URL</label>
          <input v-model="editUrl" class="input mono" type="url" required />
        </div>
        <div class="field">
          <label class="field-label">Chart Type</label>
          <select v-model="editType" class="input type-select">
            <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="field toggle-field">
          <BaseToggle v-model="editEnabled">Active (include in scan loop)</BaseToggle>
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showEdit = false">Cancel</BaseButton>
        <BaseButton @click="handleEdit" :disabled="editLoading">
          <span v-if="editLoading" class="spinner sm"></span>
          {{ editLoading ? 'Saving…' : 'Save changes' }}
        </BaseButton>
      </footer>
    </BaseModal>

    <AppToast />
    <ConfirmModal
      :show="deleteTarget !== null"
      title="Remove chart"
      :message="`Remove &quot;${deleteTarget?.name ?? ''}&quot; from the watchlist?`"
      confirm-label="Remove"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.tab-wrapper { display: flex; flex-direction: column; gap: 18px; }
.header-actions { display: flex; justify-content: flex-end; gap: 12px; }

.empty-card { padding: 0; }
.empty-seed-bar { padding: 12px; display: flex; justify-content: center; border-top: 1px solid var(--border); }

.list-card { overflow: hidden; padding: 0; }
.list-head, .list-row {
  display: grid;
  grid-template-columns: 1fr 110px 100px 170px 130px 88px;
  gap: 12px;
  align-items: center;
  padding: 11px 16px;
}
.list-head {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  font: 600 11px var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.list-row {
  border-top: 1px solid var(--border);
  transition: background .12s;
}
.list-row:hover { background: var(--surface-2); }
.list-row:first-of-type { border-top: 0; }

.col-sym { display: flex; align-items: center; gap: 10px; min-width: 0; }
.fav { border-radius: 3px; flex-shrink: 0; }
.sym-text { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.sym { font: 600 13px var(--font-mono); color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.url { font: 400 11px var(--font-mono); color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.col-type { display: flex; align-items: center; }
.type-badge {
  font: 600 10.5px var(--font-sans);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  text-transform: capitalize;
}
.type-badge.crypto { background: oklch(35% 0.14 280 / 0.25); color: oklch(75% 0.16 280); border: 1px solid oklch(45% 0.14 280 / 0.3); }
.type-badge.forex { background: oklch(35% 0.14 240 / 0.25); color: oklch(75% 0.16 240); border: 1px solid oklch(45% 0.14 240 / 0.3); }
.type-badge.stocks { background: oklch(35% 0.14 150 / 0.25); color: oklch(75% 0.16 150); border: 1px solid oklch(45% 0.14 150 / 0.3); }
.type-badge.indices { background: oklch(35% 0.14 60 / 0.25); color: oklch(75% 0.16 60); border: 1px solid oklch(45% 0.14 60 / 0.3); }
.type-badge.commodities { background: oklch(35% 0.14 90 / 0.25); color: oklch(75% 0.16 90); border: 1px solid oklch(45% 0.14 90 / 0.3); }
.type-badge.other { background: var(--surface-2); color: var(--muted); border: 1px solid var(--border); }

.col-score .score-num { font: 600 14px var(--font-mono); }
.col-score .score-num.high { color: var(--green); }
.col-score .score-num.mid { color: var(--amber); }
.col-score .score-num.low { color: var(--red); }
.col-score .muted { color: var(--muted-2); }

.col-scan { font: 500 12px var(--font-mono); color: var(--fg-2); }

.col-status { display: flex; align-items: center; gap: 7px; }
.status-lbl { font: 600 11.5px var(--font-sans); }
.status-lbl.on { color: var(--green); }
.status-lbl.off { color: var(--muted); }

.col-actions { display: flex; gap: 4px; justify-content: flex-end; }
.icon-btn { display: flex; align-items: center; justify-content: center; border: 0; background: transparent; color: var(--muted); cursor: pointer; padding: 5px; border-radius: 5px; transition: all .12s; }
.icon-btn:hover { color: var(--fg); background: var(--surface-2); }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }

.modal-body { padding: 16px 18px 4px; display: flex; flex-direction: column; gap: 14px; }
.modal-desc { font: 400 12.5px var(--font-sans); color: var(--muted); margin: -2px 0 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.type-select { height: 36px; padding: 0 10px; border-radius: 6px; background: var(--bg); color: var(--fg); border: 1px solid var(--border); }
.toggle-field { padding-top: 4px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid var(--border); background: var(--bg-2); }
.spinner.sm { width: 13px; height: 13px; border: 2px solid oklch(99% 0.003 250 / 0.3); border-top-color: var(--accent-fg); }

.search-card, .filter-card { padding: 10px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); }
.search-box { position: relative; width: 100%; display: flex; align-items: center; }
.search-ic { position: absolute; left: 10px; color: var(--muted); pointer-events: none; }
.search-input { width: 100%; height: 34px; font-size: 12.5px; padding: 0 28px 0 32px; border: 0; background: transparent; color: var(--fg); outline: none; }
.clear-search-btn { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); border: 0; background: transparent; color: var(--muted); cursor: pointer; padding: 3px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }
.clear-search-btn:hover { color: var(--fg); background: var(--surface-2); }

.filter-groups { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.tab-grp { display: flex; align-items: center; gap: 4px; background: var(--bg-2); padding: 3px; border-radius: 6px; border: 1px solid var(--border); }
.tab-btn { display: flex; align-items: center; gap: 6px; padding: 5px 10px; font: 500 12px var(--font-sans); color: var(--muted); border: 0; background: transparent; border-radius: 4px; cursor: pointer; transition: all .12s; }
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { background: var(--surface-hi); color: var(--fg); font-weight: 600; }
.badge { font: 600 10px var(--font-mono); padding: 1px 5px; border-radius: 99px; background: var(--surface-2); color: var(--muted); }
.badge.green { background: oklch(40% 0.15 145 / 0.2); color: var(--green); }
.badge.muted { background: var(--surface-2); color: var(--muted); }
.badge.type-count { background: var(--surface-hi); color: var(--fg-2); }
.reset-btn { font-size: 12px; color: var(--red); display: flex; align-items: center; gap: 4px; padding: 4px 8px; margin-left: auto; border: 0; background: transparent; cursor: pointer; }

@media (max-width: 840px) {
  .list-head { display: none; }
  .list-row { grid-template-columns: 1fr auto; gap: 8px 12px; padding: 12px 14px; }
  .col-sym { grid-column: 1; }
  .col-actions { grid-column: 2; flex-direction: row; }
  .col-type, .col-score, .col-scan, .col-status { grid-column: 1 / -1; padding-left: 24px; }
}
</style>
