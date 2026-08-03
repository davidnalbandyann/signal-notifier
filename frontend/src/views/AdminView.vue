<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  fetchAdminList,
  createAdminRecord,
  updateAdminRecord,
  deleteAdminRecord,
  bulkDeleteAdminRecords,
  type AdminListResponse,
} from '@/api/admin'
import { useToast } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppShell from '@/components/layout/AppShell.vue'

const toast = useToast()

interface ModelConfig {
  id: string
  label: string
  icon: string
  pk: string
  description: string
}

const models: ModelConfig[] = [
  { id: 'charts', label: 'Charts', icon: 'charts', pk: 'id', description: 'TradingView chart targets and monitoring settings' },
  { id: 'analyses', label: 'Analyses', icon: 'history', pk: 'id', description: 'AI analysis results, setups, scores, and signals' },
  { id: 'notifications', label: 'Notifications', icon: 'bell', pk: 'id', description: 'Dispatched alert notifications and captions' },
  { id: 'settings', label: 'Settings', icon: 'settings', pk: 'key', description: 'System configuration parameters and runtime settings' },
]

const currentModel = ref<ModelConfig>(models[0])
const loading = ref(false)
const search = ref('')
const page = ref(1)
const pageSize = ref(20)
const sortBy = ref('')
const sortDir = ref<'asc' | 'desc'>('desc')

const data = ref<AdminListResponse | null>(null)
const selectedKeys = ref<Set<string | number>>(new Set())

// Modal states
const showEditModal = ref(false)
const showJsonModal = ref(false)
const isEditing = ref(false)
const modalTitle = ref('')
const formData = ref<Record<string, any>>({})
const jsonValue = ref('')
const jsonFieldTitle = ref('')
const saving = ref(false)

const items = computed(() => data.value?.items || [])

const modelDefaultColumns: Record<string, string[]> = {
  charts: ['id', 'name', 'url', 'type', 'enabled', 'created_at'],
  analyses: ['id', 'chart_name', 'timestamp', 'score', 'direction', 'reason', 'entry', 'stop_loss', 'take_profit', 'screenshot', 'error', 'sent', 'signal_json', 'created_at'],
  notifications: ['id', 'analysis_id', 'chart_name', 'timestamp', 'score', 'direction', 'status', 'caption', 'created_at'],
  settings: ['key', 'value', 'updated_at'],
}


const columns = computed(() => {
  if (data.value?.columns && data.value.columns.length > 0) {
    return data.value.columns
  }
  return modelDefaultColumns[currentModel.value.id] || []
})
const pkField = computed(() => data.value?.pk || currentModel.value.pk)
const formColumns = computed(() => {
  return columns.value.filter((col) => {
    if (col === 'created_at' || col === 'updated_at') return false
    if (!isEditing.value && col === 'id') return false
    return true
  })
})

const allSelected = computed(() => {
  if (items.value.length === 0) return false
  return items.value.every((item) => selectedKeys.value.has(getItemPk(item)))
})

function getItemPk(item: Record<string, any>): string | number {
  return item[pkField.value]
}

async function loadData() {
  loading.value = true
  selectedKeys.value.clear()
  try {
    const res = await fetchAdminList(currentModel.value.id, {
      search: search.value.trim(),
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value || undefined,
      sort_dir: sortDir.value,
    })
    data.value = res
  } catch (err: any) {
    toast.err(err.message || `Failed to load ${currentModel.value.label}`)
  } finally {
    loading.value = false
  }
}

function switchModel(model: ModelConfig) {
  if (currentModel.value.id === model.id) return
  currentModel.value = model
  search.value = ''
  page.value = 1
  sortBy.value = ''
  sortDir.value = 'desc'
  loadData()
}

function toggleSort(col: string) {
  if (sortBy.value === col) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = col
    sortDir.value = 'asc'
  }
  loadData()
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedKeys.value.clear()
  } else {
    items.value.forEach((item) => selectedKeys.value.add(getItemPk(item)))
  }
}

function toggleSelectRow(pk: string | number) {
  if (selectedKeys.value.has(pk)) {
    selectedKeys.value.delete(pk)
  } else {
    selectedKeys.value.add(pk)
  }
}

function getSingularLabel(label: string): string {
  if (label === 'Analyses') return 'Analysis'
  if (label.endsWith('s')) return label.slice(0, -1)
  return label
}

function openCreateModal() {
  isEditing.value = false
  modalTitle.value = `Create ${getSingularLabel(currentModel.value.label)} Record`
  const initial: Record<string, any> = {}
  columns.value.forEach((col) => {
    if (col !== 'id' && col !== 'created_at' && col !== 'updated_at') {
      initial[col] = ''
    }
  })
  formData.value = initial
  showEditModal.value = true
}

function openEditModal(item: Record<string, any>) {
  isEditing.value = true
  modalTitle.value = `Edit ${getSingularLabel(currentModel.value.label)}: ${getItemPk(item)}`
  formData.value = { ...item }
  showEditModal.value = true
}

function openJsonViewer(title: string, value: any) {
  jsonFieldTitle.value = title
  if (typeof value === 'object') {
    jsonValue.value = JSON.stringify(value, null, 2)
  } else {
    try {
      const parsed = JSON.parse(value)
      jsonValue.value = JSON.stringify(parsed, null, 2)
    } catch {
      jsonValue.value = String(value || '')
    }
  }
  showJsonModal.value = true
}

async function handleSaveRecord() {
  saving.value = true
  try {
    if (isEditing.value) {
      const pkVal = formData.value[pkField.value]
      await updateAdminRecord(currentModel.value.id, pkVal, formData.value)
      toast.ok('Record updated successfully')
    } else {
      await createAdminRecord(currentModel.value.id, formData.value)
      toast.ok('Record created successfully')
    }
    showEditModal.value = false
    await loadData()
  } catch (err: any) {
    toast.err(err.message || 'Failed to save record')
  } finally {
    saving.value = false
  }
}

async function handleDeleteRow(item: Record<string, any>) {
  const pkVal = getItemPk(item)
  if (!confirm(`Are you sure you want to delete record ${pkVal}?`)) return
  try {
    await deleteAdminRecord(currentModel.value.id, pkVal)
    toast.ok('Record deleted')
    await loadData()
  } catch (err: any) {
    toast.err(err.message || 'Failed to delete record')
  }
}

async function handleBulkDelete() {
  const keys = Array.from(selectedKeys.value)
  if (keys.length === 0) return
  if (!confirm(`Are you sure you want to delete ${keys.length} selected record(s)?`)) return
  try {
    const res = await bulkDeleteAdminRecords(currentModel.value.id, keys)
    toast.ok(`Deleted ${res.deleted_count} record(s)`)
    selectedKeys.value.clear()
    await loadData()
  } catch (err: any) {
    toast.err(err.message || 'Failed to delete records')
  }
}

function formatCell(val: any, col: string): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'boolean') return val ? 'True' : 'False'
  if (col === 'value' && formData.value?.key?.includes('KEY') || col === 'value' && String(val).startsWith('sk-')) {
    return '••••••••••••'
  }
  return String(val)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <AppShell>
    <div class="admin-view">
    <!-- Header -->
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">
          <AppIcon name="shield" :size="24" class="header-icon" />
          Admin Data Control Panel
        </h1>
        <p class="page-sub">
          Manage all underlying database models (Charts, Analyses, Notifications, Settings) with raw record inspection and bulk control.
        </p>
      </div>

      <div class="header-actions">
        <BaseButton variant="ghost" size="sm" @click="loadData" :disabled="loading">
          <AppIcon name="refresh" :size="14" />
          Refresh
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click="openCreateModal">
          <AppIcon name="plus" :size="14" />
          New {{ getSingularLabel(currentModel.label) }}
        </BaseButton>
      </div>
    </header>

    <!-- Model Switcher Tabs -->
    <nav class="model-tabs" aria-label="Database Models">
      <button
        v-for="model in models"
        :key="model.id"
        :class="['tab-btn', { active: currentModel.id === model.id }]"
        @click="switchModel(model)"
      >
        <AppIcon :name="model.icon" :size="16" />
        <span class="tab-label">{{ model.label }}</span>
      </button>
    </nav>

    <!-- Standalone Search Bar Section -->
    <div class="search-card card">
      <div class="search-box">
        <AppIcon name="search" :size="15" class="search-ic" />
        <input
          v-model="search"
          type="text"
          placeholder="Search records by keyword..."
          class="search-input"
        />
        <button v-if="search" class="clear-btn" @click="search = ''">
          <AppIcon name="close" :size="12" />
        </button>
      </div>
    </div>

    <!-- Model Meta & Table Controls -->
    <div class="toolbar-card card">
      <div class="model-meta">
        <span class="meta-desc">{{ currentModel.description }}</span>
        <span class="meta-count" v-if="data">Total: <strong>{{ data.total }}</strong> records</span>
      </div>

      <div class="toolbar-controls">
        <div class="page-size-box">
          <label for="pageSizeSelect" class="size-lbl">Page size:</label>
          <select id="pageSizeSelect" v-model="pageSize" @change="loadData" class="size-select">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>

        <BaseButton
          v-if="selectedKeys.size > 0"
          variant="danger"
          size="sm"
          @click="handleBulkDelete"
        >
          <AppIcon name="trash" :size="14" />
          Delete Selected ({{ selectedKeys.size }})
        </BaseButton>
      </div>
    </div>


    <!-- Data Table / Grid -->
    <div class="table-container card">
      <AppLoading v-if="loading" message="Loading records..." />

      <EmptyState
        v-else-if="items.length === 0"
        icon="charts"
        title="No Records Found"
        :message="search ? 'No records matching search filter' : 'Table is currently empty.'"
      />

      <div v-else class="table-scroll">
        <table class="admin-table">
          <thead>
            <tr>
              <th class="th-chk">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  @change="toggleSelectAll"
                  title="Select All"
                />
              </th>
              <th
                v-for="col in columns"
                :key="col"
                class="th-sortable"
                @click="toggleSort(col)"
              >
                <div class="th-content">
                  <span>{{ col }}</span>
                  <span v-if="sortBy === col" class="sort-indicator">
                    {{ sortDir === 'asc' ? '↑' : '↓' }}
                  </span>
                </div>
              </th>
              <th class="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in items"
              :key="getItemPk(item)"
              :class="{ selected: selectedKeys.has(getItemPk(item)) }"
            >
              <td class="td-chk">
                <input
                  type="checkbox"
                  :checked="selectedKeys.has(getItemPk(item))"
                  @change="toggleSelectRow(getItemPk(item))"
                />
              </td>
              <td v-for="col in columns" :key="col" class="td-cell">
                <template v-if="col === 'signal_json' && item[col]">
                  <button class="json-badge" @click="openJsonViewer(col, item[col])">
                    <AppIcon name="terminal" :size="12" /> JSON Data
                  </button>
                </template>
                <template v-else-if="col === 'enabled'">
                  <span :class="['status-chip', item[col] ? 'active' : 'inactive']">
                    {{ item[col] ? 'Active' : 'Disabled' }}
                  </span>
                </template>
                <template v-else-if="col === 'type'">
                  <span :class="['type-badge', item[col] || 'crypto']">
                    {{ item[col] || 'crypto' }}
                  </span>
                </template>
                <template v-else>
                  <span class="cell-text" :title="String(item[col] || '')">
                    {{ formatCell(item[col], col) }}
                  </span>
                </template>
              </td>
              <td class="td-actions">
                <button
                  class="action-btn edit"
                  title="Edit Record"
                  @click="openEditModal(item)"
                >
                  <AppIcon name="edit" :size="14" />
                </button>
                <button
                  class="action-btn danger"
                  title="Delete Record"
                  @click="handleDeleteRow(item)"
                >
                  <AppIcon name="trash" :size="14" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <footer v-if="data && data.total_pages > 1" class="table-footer">
        <div class="page-info">
          Page <strong>{{ page }}</strong> of <strong>{{ data.total_pages }}</strong>
        </div>

        <div class="page-controls">
          <BaseButton
            variant="ghost"
            size="sm"
            :disabled="page <= 1"
            @click="page--; loadData()"
          >
            Previous
          </BaseButton>

          <span class="page-nums">
            <button
              v-for="p in data.total_pages"
              :key="p"
              :class="['page-num-btn', { active: page === p }]"
              @click="page = p; loadData()"
            >
              {{ p }}
            </button>
          </span>

          <BaseButton
            variant="ghost"
            size="sm"
            :disabled="page >= data.total_pages"
            @click="page++; loadData()"
          >
            Next
          </BaseButton>
        </div>
      </footer>
    </div>

    <!-- Create / Edit Record Modal -->
    <BaseModal
      :show="showEditModal"
      :title="modalTitle"
      :width="540"
      @close="showEditModal = false"
    >
      <form @submit.prevent="handleSaveRecord" class="modal-form">
        <div v-for="col in formColumns" :key="col" class="form-group">
          <label :for="`field-${col}`" class="form-label">
            {{ col }}
            <span v-if="col === pkField" class="pk-badge">Primary Key</span>
          </label>

          <!-- Primary Key Read-only if editing -->
          <input
            v-if="isEditing && col === pkField"
            :id="`field-${col}`"
            type="text"
            :value="formData[col]"
            disabled
            class="form-input disabled"
          />

          <!-- Number / Boolean / Text inputs -->
          <template v-else-if="col === 'enabled'">
            <select :id="`field-${col}`" v-model.number="formData[col]" class="form-select">
              <option :value="1">Enabled (1)</option>
              <option :value="0">Disabled (0)</option>
            </select>
          </template>

          <template v-else-if="col === 'type'">
            <select :id="`field-${col}`" v-model="formData[col]" class="form-select">
              <option value="crypto">Crypto</option>
              <option value="forex">Forex</option>
              <option value="stocks">Stocks</option>
              <option value="indices">Indices</option>
              <option value="commodities">Commodities</option>
              <option value="other">Other</option>
            </select>
          </template>


          <template v-else-if="col === 'reason' || col === 'caption' || col === 'signal_json'">
            <textarea
              :id="`field-${col}`"
              v-model="formData[col]"
              rows="3"
              class="form-textarea"
            ></textarea>
          </template>

          <template v-else>
            <input
              :id="`field-${col}`"
              v-model="formData[col]"
              type="text"
              class="form-input"
            />
          </template>
        </div>

        <div class="modal-actions">
          <BaseButton variant="ghost" type="button" @click="showEditModal = false">
            Cancel
          </BaseButton>
          <BaseButton variant="primary" type="submit" :disabled="saving">
            {{ saving ? 'Saving...' : 'Save Record' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <!-- JSON Viewer / Editor Modal -->
    <BaseModal
      :show="showJsonModal"
      :title="`JSON Inspector: ${jsonFieldTitle}`"
      :width="600"
      @close="showJsonModal = false"
    >
      <div class="json-modal-body">
        <pre class="json-code"><code>{{ jsonValue }}</code></pre>
        <div class="modal-actions">
          <BaseButton variant="ghost" @click="showJsonModal = false">Close</BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
  </AppShell>
</template>

<style scoped>
.admin-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1400px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font: 700 20px var(--font-sans);
  color: var(--fg);
}

.header-icon {
  color: var(--accent);
}

.page-sub {
  font: 400 13px var(--font-sans);
  color: var(--muted);
  margin-top: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Tabs */
.model-tabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg-2);
  font: 600 13px var(--font-sans);
  cursor: pointer;
  transition: all var(--speed-fast);
}

.tab-btn:hover {
  background: var(--surface-2);
  color: var(--fg);
}

.tab-btn.active {
  background: var(--accent-soft);
  color: var(--accent-2);
  border-color: var(--accent);
}

/* Toolbar Card */
.toolbar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  padding: 12px 16px;
  border-radius: var(--radius);
  flex-wrap: wrap;
}

.meta-desc {
  font: 400 12.5px var(--font-sans);
  color: var(--muted);

}

.meta-count {
  font: 400 12.5px var(--font-mono);
  color: var(--fg-2);
  margin-left: 12px;
}

.toolbar-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Standalone Search Card */
.search-card {
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}
.search-ic {
  position: absolute;
  left: 10px;
  color: var(--muted);
}
.search-input {
  padding: 6px 30px 6px 32px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  font: 400 12.5px var(--font-sans);
  width: 100%;
}


.clear-btn {
  position: absolute;
  right: 8px;
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
}

.page-size-box {
  display: flex;
  align-items: center;
  gap: 6px;
  font: 400 12px var(--font-mono);
  color: var(--muted);
}

.size-select {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: var(--radius);
  padding: 4px 8px;
  font: 400 12px var(--font-mono);
}

/* Table */
.table-container {
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.table-scroll {
  overflow-x: auto;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font: 400 13px var(--font-sans);
}

.admin-table th {
  background: var(--surface);
  color: var(--fg-2);
  padding: 10px 14px;
  font: 600 12px var(--font-mono);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.th-chk, .td-chk {
  width: 40px;
  text-align: center;
}

.th-sortable {
  cursor: pointer;
}

.th-sortable:hover {
  color: var(--fg);
}

.th-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sort-indicator {
  color: var(--accent);
}

.admin-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--fg);
}

.admin-table tr:hover {
  background: var(--surface);
}

.admin-table tr.selected {
  background: var(--accent-soft);
}

.cell-text {
  display: inline-block;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-chip {
  padding: 2px 8px;
  border-radius: 12px;
  font: 600 11px var(--font-mono);
}

.status-chip.active {
  background: var(--green-soft);
  color: var(--green);
}

.status-chip.inactive {
  background: var(--red-soft);
  color: var(--red);
}

.json-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius);
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--accent-2);
  font: 500 11px var(--font-mono);
  cursor: pointer;
}

.td-actions {
  white-space: nowrap;
}

.action-btn {
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: color var(--speed-fast);
}

.action-btn.edit:hover { color: var(--accent-2); }
.action-btn.danger:hover { color: var(--red); }

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


/* Footer */
.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  font: 400 12px var(--font-mono);
}

.page-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-nums {
  display: flex;
  gap: 4px;
}

.page-num-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--muted);
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font: 500 11px var(--font-mono);
}

.page-num-btn.active {
  background: var(--accent);
  color: var(--accent-fg);
}

/* Modal Form */
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font: 600 12px var(--font-sans);
  color: var(--fg-2);
  display: flex;
  align-items: center;
  gap: 6px;
}

.pk-badge {
  font: 500 10px var(--font-mono);
  color: var(--accent-2);
  background: var(--accent-soft);
  padding: 1px 6px;
  border-radius: 4px;
}

.form-input, .form-select, .form-textarea {
  padding: 8px 12px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  font: 400 13px var(--font-sans);
}

.form-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.json-modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.json-code {
  background: var(--surface-2);
  padding: 12px;
  border-radius: var(--radius);
  font: 400 12px var(--font-mono);
  max-height: 400px;
  overflow: auto;
  color: var(--fg);
}
</style>
