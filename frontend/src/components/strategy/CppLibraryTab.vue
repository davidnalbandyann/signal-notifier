<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import { getCppStrategies, createCppStrategy, updateCppStrategy, deleteCppStrategy, getCppCatalog } from '@/api/strategies'
import { useToast } from '@/composables/useToast'
import type { CppStrategy, CppStrategyDefinition, StrategyParamSchema } from '@/types'

const toast = useToast()
const strategies = ref<CppStrategy[]>([])
const catalog = ref<CppStrategyDefinition[]>([])
const loading = ref(true)
const saving = ref(false)
const selectedId = ref<number | null>(null)

const selected = computed(() => strategies.value.find(s => s.id === selectedId.value) ?? null)

// Editor state
const name = ref('')
const originalName = ref('')
const cppParams = ref<Record<string, any>>({})
const cppOriginalParams = ref<Record<string, any>>({})

const cppDef = computed<CppStrategyDefinition | null>(() =>
  catalog.value.find(c => c.key === selected.value?.engine_type) ?? null)

const isDirty = computed(() =>
  !selected.value || name.value !== originalName.value ||
  JSON.stringify(cppParams.value) !== JSON.stringify(cppOriginalParams.value))
const savingDisabled = computed(() => !isDirty.value || saving.value || !selected.value)

const showDiscard = ref(false)
const showDelete = ref(false)
const showCreate = ref(false)
const newName = ref('')
const newEngine = ref('')
const creating = ref(false)

const fmtLabel = (key: string) => key.split('_').map(w => w[0]!.toUpperCase() + w.slice(1)).join(' ')

function select(s: CppStrategy) {
  selectedId.value = s.id
  loadEditor(s)
}

function loadEditor(s: CppStrategy) {
  name.value = s.name
  originalName.value = s.name
  const def = catalog.value.find(c => c.key === s.engine_type) ?? null
  const merged: Record<string, any> = {}
  if (def) {
    for (const [k, schema] of Object.entries(def.params)) {
      merged[k] = s.params[k] ?? schema.default
    }
  } else {
    Object.assign(merged, s.params)
  }
  cppParams.value = merged
  cppOriginalParams.value = JSON.parse(JSON.stringify(merged))
}

async function load() {
  loading.value = true
  try {
    const [strats, cat] = await Promise.all([getCppStrategies(), getCppCatalog()])
    strategies.value = strats?.strategies || []
    catalog.value = cat?.catalog || []
    if (strategies.value.length > 0 && !selectedId.value) {
      select(strategies.value[0])
    }
  } catch {
    toast.err('Failed to load C++ library')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function save() {
  if (!selected.value || saving.value) return
  saving.value = true
  try {
    const payload = {
      name: name.value.trim() || selected.value.name,
      params: cppParams.value
    }
    const updated = await updateCppStrategy(selected.value.id, payload)
    const idx = strategies.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) strategies.value[idx] = updated
    loadEditor(updated)
    toast.ok('Strategy saved')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to save strategy')
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!selected.value) return
  try {
    await deleteCppStrategy(selected.value.id)
    strategies.value = strategies.value.filter(s => s.id !== selected.value!.id)
    selectedId.value = null
    showDelete.value = false
    if (strategies.value.length > 0) select(strategies.value[0])
    toast.ok('Strategy deleted')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to delete strategy')
    showDelete.value = false
  }
}

function openCreate() {
  newName.value = 'New C++ strategy'
  newEngine.value = catalog.value[0]?.key ?? ''
  showCreate.value = true
}

async function confirmCreate() {
  if (!newName.value.trim() || !newEngine.value) return
  creating.value = true
  try {
    const payload: Partial<CppStrategy> = {
      name: newName.value.trim(),
      engine_type: newEngine.value,
      params: Object.fromEntries(
        Object.entries(catalog.value.find(c => c.key === newEngine.value)?.params ?? {})
          .map(([k, schema]) => [k, schema.default])
      )
    }
    const created = await createCppStrategy(payload)
    strategies.value.push(created)
    showCreate.value = false
    select(created)
    toast.ok('Strategy created')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to create strategy')
  } finally {
    creating.value = false
  }
}

function onParamChange(key: string, schema: StrategyParamSchema, raw: any, kind: 'int' | 'float') {
  if (raw === '' || raw === null || raw === undefined) {
    cppParams.value[key] = schema.default
    return
  }
  const n = Number(raw)
  cppParams.value[key] = Number.isFinite(n) ? (kind === 'int' ? Math.round(n) : n) : schema.default
}

const paramEntries = computed(() => cppDef.value ? Object.entries(cppDef.value.params) : [])
</script>

<template>
  <div class="tab-wrapper">
    <div class="header-actions">
      <BaseButton @click="openCreate" :disabled="loading">
        <AppIcon name="plus" :size="14" :stroke="2.5" />
        New C++ strategy
      </BaseButton>
    </div>

    <AppLoading v-if="loading" label="Loading C++ library…" />

    <div v-else-if="strategies.length === 0" class="card empty-card">
      <EmptyState
        icon="engine"
        title="No C++ strategies"
        description="Create a C++ strategy from the built-in library."
        action="Create strategy"
        @action="openCreate"
      />
    </div>

    <div v-else class="split">
      <section class="card list-card">
        <div class="list-head">
          <span>Strategies ({{ strategies.length }})</span>
        </div>
        <div
          v-for="s in strategies"
          :key="s.id"
          :class="['list-row', { sel: selectedId === s.id }]"
          @click="select(s)"
        >
          <div class="row-main">
            <div class="row-name mono">{{ s.name }}</div>
            <div class="row-sub mono">{{ s.engine_type }}</div>
          </div>
          <div class="row-actions">
            <button class="icon-btn danger" title="Delete" aria-label="Delete" @click.stop="(selectedId = s.id, showDelete = true)">
              <AppIcon name="trash" :size="13" />
            </button>
          </div>
        </div>
      </section>

      <section class="card detail-card">
        <template v-if="selected">
          <div class="detail">
            <div class="detail-head">
              <label class="field-label">Strategy name</label>
              <input v-model="name" class="input name-input mono" type="text" spellcheck="false" />
            </div>

            <div v-if="cppDef" class="param-block">
              <div class="param-intro">
                <div class="param-title mono">{{ cppDef.label }}</div>
                <p class="param-desc">{{ cppDef.description }}</p>
              </div>
              <div class="param-grid">
                <div v-for="[key, schema] in paramEntries" :key="key" class="param-row">
                  <div class="param-label">
                    <span class="mono param-key">{{ fmtLabel(key) }}</span>
                    <span v-if="schema.hint" class="param-hint">{{ schema.hint }}</span>
                  </div>
                  <div class="param-input">
                    <BaseToggle
                      v-if="schema.type === 'bool'"
                      :model-value="Boolean(cppParams[key])"
                      @update:model-value="val => (cppParams[key] = val)"
                    />
                    <select
                      v-else-if="schema.type === 'str' && schema.options"
                      v-model="cppParams[key]"
                      class="input select-input"
                    >
                      <option v-for="o in schema.options" :key="o" :value="o">{{ o }}</option>
                    </select>
                    <input
                      v-else-if="schema.type === 'int' || schema.type === 'float'"
                      class="input num-input mono"
                      type="number"
                      :value="cppParams[key]"
                      :min="schema.min"
                      :max="schema.max"
                      :step="schema.step ?? (schema.type === 'int' ? 1 : 'any')"
                      @input="onParamChange(key, schema as any, ($event.target as HTMLInputElement).value, schema.type as 'int' | 'float')"
                    />
                    <input
                      v-else
                      v-model="cppParams[key]"
                      class="input num-input mono"
                      type="text"
                      spellcheck="false"
                    />
                  </div>
                </div>
              </div>
              <div v-if="isDirty" class="param-dirty mono">&#9679; unsaved changes</div>
            </div>
            <EmptyState
              v-else
              icon="alert"
              title="Unknown engine type"
              description="This strategy references a C++ type that is not in the catalog."
            />
          </div>
        </template>
        <EmptyState v-else icon="engine" title="Select a strategy" description="Choose a strategy from the list to edit it" />
      </section>
    </div>

    <div class="save-bar" v-if="isDirty && selected && !loading">
      <div class="save-hint mono">unsaved changes</div>
      <div class="grow"></div>
      <BaseButton variant="ghost" @click="(showDiscard = true)">Discard</BaseButton>
      <BaseButton @click="save" :disabled="savingDisabled">
        <span v-if="saving" class="spinner sm"></span>
        <AppIcon v-else name="check" :size="13" :stroke="2.5" />
        {{ saving ? 'Saving…' : 'Save strategy' }}
      </BaseButton>
    </div>

    <AppToast />

    <BaseModal :show="showCreate" @close="showCreate = false" :width="440">
      <template #title>New C++ strategy</template>
      <div class="modal-body">
        <div class="field">
          <label class="field-label">Name</label>
          <input v-model="newName" class="input mono" type="text" spellcheck="false" autofocus />
        </div>
        <div class="field">
          <label class="field-label">Engine type</label>
          <select v-model="newEngine" class="input" @change="newName = newEngine + ' (default)'">
            <option v-for="c in catalog" :key="c.key" :value="c.key">{{ c.label }} ({{ c.key }})</option>
          </select>
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showCreate = false">Cancel</BaseButton>
        <BaseButton @click="confirmCreate" :disabled="creating || !newName.trim() || !newEngine">
          <span v-if="creating" class="spinner sm"></span>
          {{ creating ? 'Creating…' : 'Create strategy' }}
        </BaseButton>
      </footer>
    </BaseModal>

    <ConfirmModal
      :show="showDiscard"
      title="Discard changes"
      message="Discard unsaved changes to this strategy?"
      confirm-label="Discard"
      :danger="false"
      @confirm="() => { if (selected) loadEditor(selected); showDiscard = false }"
      @cancel="showDiscard = false"
    />
    <ConfirmModal
      :show="showDelete"
      title="Delete strategy"
      :message="`Delete &quot;${selected?.name ?? ''}&quot;?`"
      confirm-label="Delete"
      @confirm="confirmDelete"
      @cancel="showDelete = false"
    />
  </div>
</template>

<style scoped>
.tab-wrapper { position: relative; padding-bottom: 60px; }
.header-actions { display: flex; justify-content: flex-end; margin-bottom: 14px; }
.split { display: grid; grid-template-columns: 320px 1fr; gap: 14px; align-items: start; }

.list-card { overflow: hidden; padding: 0; }
.list-head {
  padding: 10px 14px; background: var(--bg-2); border-bottom: 1px solid var(--border);
  font: 600 11px var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
}
.list-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 10px 14px; border-top: 1px solid var(--border);
  cursor: pointer; transition: background .12s;
}
.list-row:first-of-type { border-top: 0; }
.list-row:hover { background: var(--surface-2); }
.list-row.sel { background: var(--surface-hi); box-shadow: inset 2px 0 0 var(--accent); }

.row-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.row-name { font: 600 12.5px var(--font-mono); color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-sub { font: 400 10.5px var(--font-mono); color: var(--muted-2); }

.row-actions { display: flex; gap: 3px; }
.icon-btn {
  display: flex; align-items: center; justify-content: center;
  border: 0; background: transparent; color: var(--muted); cursor: pointer;
  padding: 5px; border-radius: 5px; transition: all .12s;
}
.icon-btn:hover { color: var(--fg); background: var(--surface-2); }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }

.detail-card { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.detail { display: flex; flex-direction: column; min-height: 480px; }
.detail-head { padding: 14px 16px; border-bottom: 1px solid var(--border); background: var(--bg-2); display: flex; flex-direction: column; gap: 6px;}
.field-label { font: 600 10.5px var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.name-input { max-width: 420px; }

.param-block { display: flex; flex-direction: column; gap: 14px; padding: 16px 18px; }
.param-intro { display: flex; flex-direction: column; gap: 3px; }
.param-title { font: 600 14px var(--font-sans); color: var(--fg); }
.param-desc { font: 400 12px var(--font-sans); color: var(--muted); line-height: 1.5; }

.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.param-row {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface);
}
.param-label { display: flex; flex-direction: column; gap: 2px; }
.param-key { font: 600 11.5px var(--font-mono); color: var(--fg-2); }
.param-hint { font: 400 10.5px var(--font-sans); color: var(--muted-2); }

.param-input .input { border: 1px solid var(--border); }
.num-input { width: 100%; max-width: 180px; height: 30px; font-size: 12px; padding: 0 8px; }

.param-dirty {
  display: inline-flex; align-items: center; gap: 6px;
  font: 600 11px var(--font-mono); color: var(--amber);
}

.save-bar {
  position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px 8px 16px; border-radius: 10px;
  background: var(--surface-hi); border: 1px solid var(--border);
  box-shadow: 0 8px 30px oklch(0% 0 0 / 0.3);
  z-index: 40;
}
.grow { flex: 1; }

.modal-body { padding: 16px 18px 4px; display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid var(--border); background: var(--bg-2); }

@media (max-width: 900px) {
  .split { grid-template-columns: 1fr; }
  .param-grid { grid-template-columns: 1fr; }
}
</style>
