<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import Toast from '@/components/ui/Toast.vue'
import { getCharts, addChart, updateChart, deleteChart } from '@/api/charts'
import type { Chart } from '@/types'

const charts = ref<Chart[]>([])
const loading = ref(true)
const toast = ref({ show: false, message: '' })

const showAdd = ref(false)
const newUrl = ref('')
const newName = ref('')
const addLoading = ref(false)

const showEdit = ref(false)
const editId = ref(0)
const editName = ref('')
const editUrl = ref('')
const editEnabled = ref(true)
const editLoading = ref(false)

async function load() {
  try {
    charts.value = await getCharts()
  } finally {
    loading.value = false
  }
}

load()

async function handleAdd() {
  if (!newUrl.value.trim()) return
  addLoading.value = true
  try {
    await addChart({
      name: newName.value.trim() || newUrl.value.trim(),
      url: newUrl.value.trim(),
    })
    toast.value = { show: true, message: 'Chart added' }
    showAdd.value = false
    newUrl.value = ''
    newName.value = ''
    charts.value = await getCharts()
  } catch {
    toast.value = { show: true, message: 'Failed to add chart' }
  } finally {
    addLoading.value = false
  }
}

function openEdit(c: Chart) {
  editId.value = c.id
  editName.value = c.name
  editUrl.value = c.url
  editEnabled.value = c.enabled
  showEdit.value = true
}

async function handleEdit() {
  editLoading.value = true
  try {
    await updateChart(editId.value, {
      name: editName.value,
      url: editUrl.value,
      enabled: editEnabled.value,
    })
    toast.value = { show: true, message: 'Chart updated' }
    showEdit.value = false
    charts.value = await getCharts()
  } catch {
    toast.value = { show: true, message: 'Failed to update chart' }
  } finally {
    editLoading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('Delete this chart?')) return
  try {
    await deleteChart(id)
    toast.value = { show: true, message: 'Chart deleted' }
    charts.value = await getCharts()
  } catch {
    toast.value = { show: true, message: 'Failed to delete chart' }
  }
}

function favicon(url: string) {
  try {
    const u = new URL(url)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch {
    return ''
  }
}
</script>

<template>
  <AppShell :crumbs="['Charts']">
    <div class="pg">
      <div class="pg-head">
        <h1 class="h1">Charts</h1>
        <div class="spacer"></div>
        <BaseButton @click="showAdd = true">+ Add chart</BaseButton>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else-if="charts.length === 0" class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--muted)">
          <polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/>
        </svg>
        <p class="empty-t">No charts yet</p>
        <p class="empty-d">Add a TradingView chart URL to start monitoring</p>
      </div>

      <div v-else class="list">
        <div v-for="c in charts" :key="c.id" class="row">
          <div class="row-left">
            <img v-if="favicon(c.url)" :src="favicon(c.url)" width="16" height="16" class="fav" />
            <div class="row-info">
              <span class="sym mono">{{ c.name }}</span>
              <span class="lbl">{{ c.url }}</span>
            </div>
          </div>
          <div class="row-right">
            <span class="ts mono">{{ c.last_score !== null ? c.last_score.toFixed(1) : '—' }}</span>
            <span class="ts mono">{{ c.last_scanned ? new Date(c.last_scanned).toLocaleDateString() : 'never' }}</span>
            <span class="ts" :class="c.enabled ? 'on' : 'off'">{{ c.enabled ? 'Active' : 'Paused' }}</span>
            <BaseButton variant="ghost" size="sm" @click="openEdit(c)">Edit</BaseButton>
            <BaseButton variant="danger" size="sm" @click="handleDelete(c.id)">Delete</BaseButton>
          </div>
        </div>
      </div>
    </div>

    <BaseModal :show="showAdd" @close="showAdd = false">
      <div class="modal-head">
        <h2 class="modal-h">Add chart</h2>
        <button class="close-x" @click="showAdd = false">&times;</button>
      </div>
      <p class="modal-desc">Paste a TradingView chart URL to start monitoring</p>
      <form @submit.prevent="handleAdd" class="form">
        <div class="field">
          <label class="label">Chart URL *</label>
          <input v-model="newUrl" class="input" type="url" required placeholder="https://www.tradingview.com/chart/..." />
        </div>
        <div class="field">
          <label class="label">Name</label>
          <input v-model="newName" class="input" type="text" placeholder="BTC/USD 15m" />
        </div>
        <div class="modal-foot">
          <BaseButton variant="ghost" @click="showAdd = false">Cancel</BaseButton>
          <BaseButton type="submit" :disabled="addLoading">
            {{ addLoading ? 'Adding…' : 'Add chart' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <BaseModal :show="showEdit" @close="showEdit = false">
      <div class="modal-head">
        <h2 class="modal-h">Edit chart</h2>
        <button class="close-x" @click="showEdit = false">&times;</button>
      </div>
      <form @submit.prevent="handleEdit" class="form">
        <div class="field">
          <label class="label">Name</label>
          <input v-model="editName" class="input" type="text" />
        </div>
        <div class="field">
          <label class="label">Chart URL *</label>
          <input v-model="editUrl" class="input" type="url" required />
        </div>
        <div class="field">
          <label class="toggle">
            <input type="checkbox" v-model="editEnabled" />
            <span class="sw"></span>
            <span class="tl">Enabled</span>
          </label>
        </div>
        <div class="modal-foot">
          <BaseButton variant="ghost" @click="showEdit = false">Cancel</BaseButton>
          <BaseButton type="submit" :disabled="editLoading">
            {{ editLoading ? 'Saving…' : 'Save changes' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 20px; }
.pg-head { display: flex; align-items: center; gap: 16px; }
.h1 { font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.015em; }
.spacer { flex: 1; }
.loading { display: grid; place-items: center; padding: 80px 0; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--surface-3); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 0; color: var(--muted); }
.empty-t { font-size: 14px; font-weight: 600; margin: 12px 0 4px; color: var(--fg-2); }
.empty-d { font-size: 13px; margin: 0; }
.list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--surface);
}
.row-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.fav { border-radius: 2px; flex-shrink: 0; }
.row-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.sym { font-size: 13px; font-weight: 600; }
.lbl { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.ts { font-size: 12px; color: var(--muted); }
.ts.on { color: var(--green); }
.ts.off { color: var(--muted-2); }
.mono { font-family: var(--font-mono); }

.modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.modal-h { font-size: 16px; font-weight: 700; margin: 0; }
.close-x { background: none; border: 0; color: var(--muted); cursor: pointer; font-size: 16px; }
.modal-desc { font-size: 13px; color: var(--muted); margin: 0 0 16px; }
.form { display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 5px; }
.label { font-size: 11px; font-weight: 600; color: var(--fg-2); text-transform: uppercase; letter-spacing: 0.06em; font-family: var(--font-mono); }
.input { height: 36px; padding: 0 10px; background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--fg); font-size: 13px; font-family: var(--font-mono); }
.input:focus { outline: none; border-color: var(--accent); }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }

.toggle { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; margin-top: 4px; }
.toggle input { display: none; }
.toggle .sw { width: 36px; height: 20px; background: var(--surface-3); border-radius: 999px; transition: background .15s; position: relative; }
.toggle .sw::after { content: ''; position: absolute; left: 2px; top: 2px; width: 16px; height: 16px; background: var(--fg); border-radius: 50%; transition: transform .15s; }
.toggle input:checked + .sw { background: var(--accent); }
.toggle input:checked + .sw::after { transform: translateX(16px); background: white; }
.toggle .tl { font-size: 12px; color: var(--fg-2); }
</style>
