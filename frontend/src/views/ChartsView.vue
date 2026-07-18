<script setup lang="ts">
import { ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { getCharts, addChart, updateChart, deleteChart } from '@/api/charts'
import { useToast } from '@/composables/useToast'
import type { Chart } from '@/types'

const toast = useToast()
const charts = ref<Chart[]>([])
const loading = ref(true)

const showAdd = ref(false)
const newUrl = ref('')
const newName = ref('')
const addLoading = ref(false)

const showEdit = ref(false)
const editing = ref<Chart | null>(null)
const editName = ref('')
const editUrl = ref('')
const editEnabled = ref(true)
const editLoading = ref(false)

async function load() {
  loading.value = true
  try { charts.value = await getCharts() }
  catch { toast.err('Failed to load charts') }
  finally { loading.value = false }
}
load()

function openAdd() {
  newUrl.value = ''
  newName.value = ''
  showAdd.value = true
}

async function handleAdd() {
  if (!newUrl.value.trim()) return
  addLoading.value = true
  try {
    await addChart({
      name: newName.value.trim() || newUrl.value.trim(),
      url: newUrl.value.trim(),
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
  if (!confirm(`Delete "${c.name}" from the watchlist?`)) return
  try {
    await deleteChart(c.id)
    toast.ok('Chart removed')
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
  const d = new Date(iso)
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' · ' +
    d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Charts</h1>
          <div class="pg-sub">{{ charts.length }} watched &middot; TradingView URLs captured on each scan</div>
        </div>
        <div class="grow"></div>
        <BaseButton @click="openAdd">
          <AppIcon name="plus" :size="14" :stroke="2.5" />
          Add chart
        </BaseButton>
      </header>

      <AppLoading v-if="loading" label="Loading watchlist…" />

      <div v-else-if="charts.length === 0" class="card empty-card">
        <EmptyState
          icon="charts"
          title="No charts in the watchlist"
          description="Add a TradingView chart URL to begin monitoring"
          action="Add your first chart"
          @action="openAdd"
        />
      </div>

      <div v-else class="card list-card">
        <div class="list-head">
          <div class="col-sym">Chart</div>
          <div class="col-score">Last score</div>
          <div class="col-scan">Last scanned</div>
          <div class="col-status">Status</div>
          <div class="col-actions"></div>
        </div>
        <div v-for="c in charts" :key="c.id" class="list-row">
          <div class="col-sym">
            <img v-if="favicon(c.url)" :src="favicon(c.url)" width="14" height="14" class="fav" alt="" />
            <div class="sym-text">
              <div class="sym mono">{{ c.name }}</div>
              <div class="url mono" :title="c.url">{{ c.url }}</div>
            </div>
          </div>
          <div class="col-score">
            <span v-if="c.last_score !== null" :class="['score-num', 'mono', c.last_score >= 7 ? 'high' : c.last_score >= 5 ? 'mid' : 'low']">
              {{ c.last_score.toFixed(1) }}
            </span>
            <span v-else class="muted mono">—</span>
          </div>
          <div class="col-scan mono">{{ fmtDate(c.last_scanned) }}</div>
          <div class="col-status">
            <span :class="['status-dot', c.enabled ? 'on' : 'off']"></span>
            <span :class="['status-lbl', c.enabled ? 'on' : 'off']">{{ c.enabled ? 'Active' : 'Paused' }}</span>
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
            placeholder="https://www.tradingview.com/chart/XXXX/"
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
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 18px; max-width: 1200px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.empty-card { padding: 0; }

.list-card { overflow: hidden; padding: 0; }
.list-head, .list-row {
  display: grid;
  grid-template-columns: 1fr 120px 180px 140px 88px;
  gap: 12px;
  align-items: center;
  padding: 11px 16px;
}
.list-head {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  font: 600 10.5px var(--font-mono);
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

.col-score .score-num { font: 600 14px var(--font-mono); }
.col-score .score-num.high { color: var(--green); }
.col-score .score-num.mid { color: var(--amber); }
.col-score .score-num.low { color: var(--red); }
.col-score .muted { color: var(--muted-2); }

.col-scan { font: 500 12px var(--font-mono); color: var(--fg-2); }

.col-status { display: flex; align-items: center; gap: 7px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-dot.on { background: var(--green); }
.status-dot.off { background: var(--muted-2); }
.status-lbl { font: 600 11.5px var(--font-sans); }
.status-lbl.on { color: var(--green); }
.status-lbl.off { color: var(--muted); }

.col-actions { display: flex; gap: 4px; justify-content: flex-end; }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }

.modal-body { padding: 16px 18px 4px; display: flex; flex-direction: column; gap: 14px; }
.modal-desc { font: 400 12.5px var(--font-sans); color: var(--muted); margin: -2px 0 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.toggle-field { padding-top: 4px; }
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
}
.spinner.sm {
  width: 13px; height: 13px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}

@media (max-width: 760px) {
  .list-head { display: none; }
  .list-row {
    grid-template-columns: 1fr auto;
    gap: 8px 12px;
    padding: 12px 14px;
  }
  .col-sym { grid-column: 1; }
  .col-actions { grid-column: 2; flex-direction: row; }
  .col-score, .col-scan, .col-status {
    grid-column: 1 / -1;
    padding-left: 24px;
  }
}
</style>
