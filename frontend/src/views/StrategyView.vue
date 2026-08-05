<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import SideAccentCard from '@/components/ui/SideAccentCard.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import {
  getStrategies, createStrategy, updateStrategy, deleteStrategy,
  activateStrategy, duplicateStrategy, getCppCatalog,
} from '@/api/strategies'
import { useToast } from '@/composables/useToast'
import type { Strategy, CppStrategyDefinition, StrategyParamSchema } from '@/types'

const toast = useToast()
const tab = ref<'prompt' | 'cpp'>('prompt')
const strategies = ref<Strategy[]>([])
const catalog = ref<CppStrategyDefinition[]>([])
const loading = ref(true)
const saving = ref(false)
const selectedId = ref<number | null>(null)

const promptList = computed(() => strategies.value.filter(s => s.type === 'prompt'))
const cppList = computed(() => strategies.value.filter(s => s.type === 'cpp'))
const selected = computed(() => strategies.value.find(s => s.id === selectedId.value) ?? null)

// ── editor state ──────────────────────────────────────────────
const name = ref('')
const originalName = ref('')
const content = ref('')
const originalContent = ref('')
const cppParams = ref<Record<string, any>>({})
const cppOriginalParams = ref<Record<string, any>>({})

const cppDef = computed<CppStrategyDefinition | null>(() =>
  catalog.value.find(c => c.key === selected.value?.engine_type) ?? null)

const promptDirty = computed(() =>
  !selected.value || name.value !== originalName.value || content.value !== originalContent.value)
const cppDirty = computed(() =>
  !selected.value || name.value !== originalName.value ||
  JSON.stringify(cppParams.value) !== JSON.stringify(cppOriginalParams.value))
const savingDisabled = computed(() =>
  (tab.value === 'prompt' ? !promptDirty.value : !cppDirty.value) || saving.value || !selected.value)

const showDiscard = ref(false)
const showDelete = ref(false)
const showCreate = ref(false)
const newName = ref('')
const newEngine = ref('')
const creating = ref(false)

const fmtLabel = (key: string) => key.split('_').map(w => w[0]!.toUpperCase() + w.slice(1)).join(' ')

function ensureSelection() {
  const list = tab.value === 'prompt' ? promptList.value : cppList.value
  if (!list.length) { selectedId.value = null; return }
  if (!list.some(s => s.id === selectedId.value)) {
    select(list[0])
  } else {
    const cur = list.find(s => s.id === selectedId.value)!
    loadEditor(cur)
  }
}

function select(s: Strategy) {
  selectedId.value = s.id
  loadEditor(s)
}

function loadEditor(s: Strategy) {
  name.value = s.name
  originalName.value = s.name
  if (s.type === 'prompt') {
    content.value = s.content
    originalContent.value = s.content
  } else {
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
}

async function load() {
  loading.value = true
  try {
    const [strats, cat] = await Promise.all([getStrategies(), getCppCatalog()])
    strategies.value = strats.strategies
    catalog.value = cat.catalog
    ensureSelection()
  } catch { toast.err('Failed to load strategies') }
  finally { loading.value = false }
}

onMounted(load)

watch(tab, () => ensureSelection())

async function save() {
  if (!selected.value || saving.value) return
  saving.value = true
  try {
    const payload: Partial<Strategy> = { name: name.value.trim() || selected.value.name }
    if (tab.value === 'prompt') payload.content = content.value
    else payload.params = cppParams.value
    const updated = await updateStrategy(selected.value.id, payload)
    const idx = strategies.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) strategies.value[idx] = updated
    loadEditor(updated)
    toast.ok(tab.value === 'cpp' && updated.active ? 'Strategy saved · engine will restart' : 'Strategy saved')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to save strategy')
  } finally { saving.value = false }
}

async function activate(s: Strategy) {
  try {
    const updated = await activateStrategy(s.id)
    const idx = strategies.value.findIndex(x => x.id === updated.id)
    if (idx !== -1) strategies.value[idx] = updated
    toast.ok(s.type === 'cpp' ? 'Strategy activated · engine will restart' : 'Strategy activated')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to activate strategy')
  }
}

async function duplicate(s: Strategy) {
  try {
    const copy = await duplicateStrategy(s.id)
    strategies.value.push(copy)
    select(copy)
    toast.ok('Strategy duplicated')
  } catch (e: any) { toast.err(e?.message || 'Failed to duplicate') }
}

async function confirmDelete() {
  if (!selected.value) return
  try {
    await deleteStrategy(selected.value.id)
    strategies.value = strategies.value.filter(s => s.id !== selected.value!.id)
    selectedId.value = null
    showDelete.value = false
    ensureSelection()
    toast.ok('Strategy deleted')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to delete strategy')
    showDelete.value = false
  }
}

function openCreate() {
  newName.value = tab.value === 'cpp' ? 'New C++ strategy' : 'New prompt'
  newEngine.value = catalog.value[0]?.key ?? ''
  showCreate.value = true
}

async function confirmCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const payload: any = { name: newName.value.trim(), type: tab.value }
    if (tab.value === 'cpp') {
      payload.engine_type = newEngine.value
      payload.params = Object.fromEntries(
        Object.entries(catalog.value.find(c => c.key === newEngine.value)?.params ?? {})
          .map(([k, schema]) => [k, schema.default]))
    }
    const created = await createStrategy(payload)
    strategies.value.push(created)
    showCreate.value = false
    select(created)
    toast.ok('Strategy created')
  } catch (e: any) { toast.err(e?.message || 'Failed to create strategy') }
  finally { creating.value = false }
}

function reset() {
  if (selected.value) loadEditor(selected.value)
  showDiscard.value = false
}

function confirmDiscard() {
  reset()
}

const paramEntries = computed(() =>
  cppDef.value ? Object.entries(cppDef.value.params) : [])

const promptLineCount = computed(() => content.value.split('\n').length)
const promptCharCount = computed(() => content.value.length)

function onParamChange(key: string, schema: StrategyParamSchema, raw: any, kind: 'int' | 'float') {
  if (raw === '' || raw === null || raw === undefined) {
    cppParams.value[key] = schema.default
    return
  }
  const n = Number(raw)
  cppParams.value[key] = Number.isFinite(n) ? (kind === 'int' ? Math.round(n) : n) : schema.default
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Strategies</h1>
          <div class="pg-sub">{{ promptList.length }} AI prompts · {{ cppList.length }} C++ engine strategies</div>
        </div>
        <div class="grow"></div>
        <div class="tab-grp" role="tablist">
          <button :class="['tab-btn', { active: tab === 'prompt' }]" @click="tab = 'prompt'">
            AI prompts <span class="badge">{{ promptList.length }}</span>
          </button>
          <button :class="['tab-btn', { active: tab === 'cpp' }]" @click="tab = 'cpp'">
            C++ strategies <span class="badge">{{ cppList.length }}</span>
          </button>
        </div>
        <BaseButton @click="openCreate" :disabled="loading">
          <AppIcon name="plus" :size="14" :stroke="2.5" />
          {{ tab === 'prompt' ? 'New prompt' : 'New C++ strategy' }}
        </BaseButton>
      </header>

      <SideAccentCard v-if="tab === 'prompt'" class="info-banner">
        <AppIcon name="strategy" :size="15" :stroke="2" class="info-ic" />
        <div class="info-text">
          <div class="info-title">One active AI prompt at a time</div>
          <div class="info-sub">The active prompt is hot-reloaded on every scan — edits apply immediately, no restart needed.</div>
        </div>
      </SideAccentCard>

      <SideAccentCard v-else accent="amber" class="info-banner">
        <AppIcon name="engine" :size="15" :stroke="2" class="info-ic amber" />
        <div class="info-text">
          <div class="info-title">C++ engine strategies</div>
          <div class="info-sub">The active strategy is written to config.json. Activating or saving it restarts the engine automatically if it is running.</div>
        </div>
      </SideAccentCard>

      <AppLoading v-if="loading" :label="tab === 'prompt' ? 'Loading strategies…' : 'Loading engine strategies…'" />

      <div v-else-if="(tab === 'prompt' ? promptList : cppList).length === 0" class="card empty-card">
        <EmptyState
          :icon="tab === 'prompt' ? 'strategy' : 'engine'"
          :title="tab === 'prompt' ? 'No AI prompt strategies' : 'No C++ strategies'"
          :description="tab === 'prompt' ? 'Create your first strategy prompt — a new strategy appears here' : 'Create a C++ strategy from the built-in catalog'"
          :action="tab === 'prompt' ? 'Create your first prompt' : 'Create a C++ strategy'"
          @action="openCreate"
        />
      </div>

      <div v-else class="split">
        <section class="card list-card">
          <div class="list-head">
            <span>Strategies ({{ tab === 'prompt' ? promptList.length : cppList.length }})</span>
            <span class="grow"></span>
            <span>Active</span>
            <span></span>
          </div>
          <div
            v-for="s in (tab === 'prompt' ? promptList : cppList)"
            :key="s.id"
            :class="['list-row', { sel: selectedId === s.id }]"
            @click="select(s)"
          >
            <div class="row-main">
              <div class="row-name mono">{{ s.name }}</div>
              <div v-if="s.type === 'cpp'" class="row-sub mono">{{ s.engine_type }}</div>
              <div v-else class="row-sub mono">{{ promptLineCount ? s.content.split('\n').length + ' lines' : 'empty' }}</div>
            </div>
            <div class="row-active">
              <button
                v-if="!s.active"
                class="mini-btn"
                title="Set as active"
                aria-label="Activate strategy"
                @click.stop="activate(s)"
              >
                <AppIcon name="power" :size="13" />
              </button>
              <span v-else class="active-tag mono">
                <span class="active-dot"></span> ACTIVE
              </span>
            </div>
            <div class="row-actions">
              <button class="icon-btn" title="Duplicate" aria-label="Duplicate" @click.stop="duplicate(s)">
                <AppIcon name="copy" :size="13" />
              </button>
              <button
                class="icon-btn danger"
                title="Delete"
                aria-label="Delete"
                :disabled="s.active"
                @click.stop="s.active ? null : (selectedId = s.id, showDelete = true)"
              >
                <AppIcon name="trash" :size="13" />
              </button>
            </div>
          </div>
        </section>

        <section class="card detail-card">
          <template v-if="selected">
            <div v-if="tab === 'prompt'" class="detail">
              <div class="detail-head">
                <label class="field-label">Strategy name</label>
                <input v-model="name" class="input name-input mono" type="text" spellcheck="false" />
              </div>
              <div class="editor-head">
                <div class="editor-stats mono">
                  <span>{{ promptLineCount }} lines</span>
                  <span class="sep">·</span>
                  <span>{{ promptCharCount.toLocaleString() }} chars</span>
                  <span v-if="promptDirty" class="dirty"><span class="dirty-dot"></span> unsaved</span>
                </div>
              </div>
              <textarea
                v-model="content"
                class="editor"
                spellcheck="false"
                wrap="off"
                placeholder="# Trading strategy prompt
Define the rules the AI uses to score charts and decide direction…"
              ></textarea>
            </div>

            <div v-else class="detail">
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
                <div v-if="cppDirty" class="param-dirty mono">&#9679; unsaved changes</div>
              </div>
              <EmptyState
                v-else
                icon="alert"
                title="Unknown engine type"
                description="This strategy references a C++ type that is not in the catalog."
              />
            </div>
          </template>
          <EmptyState
            v-else
            :icon="tab === 'prompt' ? 'strategy' : 'engine'"
            title="Select a strategy"
            description="Choose a strategy from the list to edit it"
          />
        </section>
      </div>
    </div>

    <div class="save-bar" v-if="(tab === 'prompt' ? promptDirty : cppDirty) && selected && !loading">
      <div class="save-hint mono">unsaved changes</div>
      <div class="grow"></div>
      <BaseButton variant="ghost" @click="showDiscard = true">Discard</BaseButton>
      <BaseButton @click="save" :disabled="saving">
        <span v-if="saving" class="spinner sm"></span>
        <AppIcon v-else name="check" :size="13" :stroke="2.5" />
        {{ saving ? 'Saving…' : 'Save strategy' }}
      </BaseButton>
    </div>

    <AppToast />

    <BaseModal :show="showCreate" @close="showCreate = false" :width="440">
      <template #title>{{ tab === 'prompt' ? 'New prompt strategy' : 'New C++ strategy' }}</template>
      <div class="modal-body">
        <p class="modal-desc">
          {{ tab === 'prompt'
            ? 'Create a new markdown prompt. It will be used by the vision model when activated.'
            : 'Create a C++ strategy with default parameters for the chosen engine type.' }}
        </p>
        <div class="field">
          <label class="field-label">Name</label>
          <input v-model="newName" class="input mono" type="text" spellcheck="false" autofocus />
        </div>
        <div v-if="tab === 'cpp'" class="field">
          <label class="field-label">Engine type</label>
          <select v-model="newEngine" class="input" @change="newName = newEngine + ' (default)'">
            <option v-for="c in catalog" :key="c.key" :value="c.key">{{ c.label }} ({{ c.key }})</option>
          </select>
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showCreate = false">Cancel</BaseButton>
        <BaseButton @click="confirmCreate" :disabled="creating || !newName.trim() || (tab === 'cpp' && !newEngine)">
          <span v-if="creating" class="spinner sm"></span>
          <AppIcon v-else name="plus" :size="13" :stroke="2.5" />
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
      @confirm="confirmDiscard"
      @cancel="showDiscard = false"
    />
    <ConfirmModal
      :show="showDelete"
      title="Delete strategy"
      :message="`Delete &quot;${selected?.name ?? ''}&quot;? This cannot be undone.`"
      confirm-label="Delete"
      @confirm="confirmDelete"
      @cancel="showDelete = false"
    />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 14px; max-width: 1320px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.tab-grp { display: flex; align-items: center; gap: 4px; background: var(--bg-2); padding: 3px; border-radius: 8px; border: 1px solid var(--border); }
.tab-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; font: 500 12.5px var(--font-sans); color: var(--muted);
  border: 0; background: transparent; border-radius: 6px; cursor: pointer; transition: all .12s;
}
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { background: var(--surface-hi); color: var(--fg); font-weight: 600; }
.badge {
  font: 600 10px var(--font-mono); padding: 1px 5px; border-radius: 99px;
  background: var(--surface-2); color: var(--muted);
}

.info-banner { display: flex; align-items: center; gap: 11px; padding: 12px 16px; }
.info-ic { color: var(--accent); flex-shrink: 0; }
.info-ic.amber { color: var(--amber); }
.info-title { font: 600 13px var(--font-sans); color: var(--fg); }
.info-sub { font: 400 11.5px var(--font-sans); color: var(--muted); margin-top: 1px; }

.split { display: grid; grid-template-columns: 320px 1fr; gap: 14px; align-items: start; margin-bottom: 56px; }

.list-card { overflow: hidden; padding: 0; }
.list-head {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--bg-2); border-bottom: 1px solid var(--border);
  font: 600 11px var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
}
.list-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-top: 1px solid var(--border);
  cursor: pointer; transition: background .12s;
}
.list-row:first-of-type { border-top: 0; }
.list-row:hover { background: var(--surface-2); }
.list-row.sel { background: var(--surface-hi); box-shadow: inset 2px 0 0 var(--accent); }

.row-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.row-name { font: 600 12.5px var(--font-mono); color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-sub { font: 400 10.5px var(--font-mono); color: var(--muted-2); }
.row-grow, .row-active { display: flex; align-items: center; }
.grow { flex: 1; }

.active-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font: 600 10px var(--font-mono); letter-spacing: 0.06em;
  color: var(--green); white-space: nowrap;
}
.active-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }

.mini-btn {
  display: flex; align-items: center; justify-content: center;
  border: 0; background: transparent; color: var(--muted); cursor: pointer;
  padding: 5px; border-radius: 5px;
}
.mini-btn:hover { color: var(--green); background: oklch(45% 0.15 145 / 0.15); }

.row-actions { display: flex; gap: 3px; }
.icon-btn {
  display: flex; align-items: center; justify-content: center;
  border: 0; background: transparent; color: var(--muted); cursor: pointer;
  padding: 5px; border-radius: 5px; transition: all .12s;
}
.icon-btn:hover { color: var(--fg); background: var(--surface-2); }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }
.icon-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.detail-card { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.detail { display: flex; flex-direction: column; min-height: 480px; }
.detail-head {
  display: flex; flex-direction: column; gap: 6px;
  padding: 14px 16px; border-bottom: 1px solid var(--border); background: var(--bg-2);
}
.field-label { font: 600 10.5px var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.name-input { max-width: 420px; }

.editor-head {
  display: flex; align-items: center; justify-content: flex-end;
  padding: 8px 16px; border-bottom: 1px solid var(--border); background: var(--bg-2);
}
.editor-stats { display: flex; align-items: center; gap: 7px; font: 500 11px var(--font-mono); color: var(--muted); }
.editor-stats .sep { color: var(--muted-2); }

.editor {
  width: 100%; min-height: 420px; flex: 1;
  padding: 16px 18px; background: var(--bg); border: 0;
  color: var(--fg); font: 500 13px/1.7 var(--font-mono);
  resize: vertical; tab-size: 2; outline: none;
}
.editor::placeholder { color: var(--muted-2); }
.editor:focus { background: var(--bg-2); }

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

.dirty {
  display: inline-flex; align-items: center; gap: 5px;
  color: var(--amber); margin-left: 6px;
}
.dirty-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); }

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

.spinner.sm {
  width: 13px; height: 13px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}

.modal-body { padding: 16px 18px 4px; display: flex; flex-direction: column; gap: 14px; }
.modal-desc { font: 400 12.5px var(--font-sans); color: var(--muted); margin: -2px 0 4px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 18px; border-top: 1px solid var(--border); background: var(--bg-2);
}

@media (max-width: 900px) {
  .split { grid-template-columns: 1fr; }
  .param-grid { grid-template-columns: 1fr; }
}
</style>