<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import { getAiStrategies, createAiStrategy, updateAiStrategy, deleteAiStrategy } from '@/api/strategies'
import { useToast } from '@/composables/useToast'
import type { AiStrategy } from '@/types'

const toast = useToast()
const strategies = ref<AiStrategy[]>([])
const loading = ref(true)
const saving = ref(false)
const selectedId = ref<number | null>(null)

const selected = computed(() => strategies.value.find(s => s.id === selectedId.value) ?? null)

// Editor state
const name = ref('')
const originalName = ref('')
const content = ref('')
const originalContent = ref('')

const isDirty = computed(() => !selected.value || name.value !== originalName.value || content.value !== originalContent.value)
const savingDisabled = computed(() => !isDirty.value || saving.value || !selected.value)
const lineCount = computed(() => content.value.split('\n').length)
const charCount = computed(() => content.value.length)

const showDiscard = ref(false)
const showDelete = ref(false)
const showCreate = ref(false)
const newName = ref('')
const creating = ref(false)

function select(s: AiStrategy) {
  selectedId.value = s.id
  loadEditor(s)
}

function loadEditor(s: AiStrategy) {
  name.value = s.name
  originalName.value = s.name
  content.value = s.content
  originalContent.value = s.content
}

async function load() {
  loading.value = true
  try {
    const res = await getAiStrategies()
    strategies.value = res?.strategies || []
    if (strategies.value.length > 0 && !selectedId.value) {
      select(strategies.value[0])
    }
  } catch {
    toast.err('Failed to load AI prompts')
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
      content: content.value
    }
    const updated = await updateAiStrategy(selected.value.id, payload)
    const idx = strategies.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) strategies.value[idx] = updated
    loadEditor(updated)
    toast.ok('Prompt saved')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to save prompt')
  } finally {
    saving.value = false
  }
}

async function duplicate(s: AiStrategy) {
  try {
    const copy = await createAiStrategy({ name: `${s.name} (Copy)`, content: s.content })
    strategies.value.push(copy)
    select(copy)
    toast.ok('Prompt duplicated')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to duplicate')
  }
}

async function confirmDelete() {
  if (!selected.value) return
  try {
    await deleteAiStrategy(selected.value.id)
    strategies.value = strategies.value.filter(s => s.id !== selected.value!.id)
    selectedId.value = null
    showDelete.value = false
    if (strategies.value.length > 0) select(strategies.value[0])
    toast.ok('Prompt deleted')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to delete prompt')
    showDelete.value = false
  }
}

function openCreate() {
  newName.value = 'New prompt'
  showCreate.value = true
}

async function confirmCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const created = await createAiStrategy({ name: newName.value.trim(), content: '# AI Strategy\n' })
    strategies.value.push(created)
    showCreate.value = false
    select(created)
    toast.ok('Prompt created')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to create prompt')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="tab-wrapper">
    <div class="header-actions">
      <BaseButton @click="openCreate" :disabled="loading">
        <AppIcon name="plus" :size="14" :stroke="2.5" />
        New prompt
      </BaseButton>
    </div>

    <AppLoading v-if="loading" label="Loading AI library…" />

    <div v-else-if="strategies.length === 0" class="card empty-card">
      <EmptyState
        icon="strategy"
        title="No AI prompts"
        description="Create your first reusable AI prompt for analyzing charts."
        action="Create prompt"
        @action="openCreate"
      />
    </div>

    <div v-else class="split">
      <section class="card list-card">
        <div class="list-head">
          <span>AI Prompts ({{ strategies.length }})</span>
        </div>
        <div
          v-for="s in strategies"
          :key="s.id"
          :class="['list-row', { sel: selectedId === s.id }]"
          @click="select(s)"
        >
          <div class="row-main">
            <div class="row-name mono">{{ s.name }}</div>
            <div class="row-sub mono">{{ s.content.split('\n').length }} lines</div>
          </div>
          <div class="row-actions">
            <button class="icon-btn" title="Duplicate" aria-label="Duplicate" @click.stop="duplicate(s)">
              <AppIcon name="copy" :size="13" />
            </button>
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
              <label class="field-label">Prompt name</label>
              <input v-model="name" class="input name-input mono" type="text" spellcheck="false" />
            </div>
            <div class="editor-head">
              <div class="editor-stats mono">
                <span>{{ lineCount }} lines</span>
                <span class="sep">·</span>
                <span>{{ charCount.toLocaleString() }} chars</span>
                <span v-if="isDirty" class="dirty"><span class="dirty-dot"></span> unsaved</span>
              </div>
            </div>
            <textarea
              v-model="content"
              class="editor"
              spellcheck="false"
              wrap="off"
              placeholder="# Trading strategy prompt..."
            ></textarea>
          </div>
        </template>
        <EmptyState v-else icon="strategy" title="Select a prompt" description="Choose a prompt from the list to edit it" />
      </section>
    </div>

    <div class="save-bar" v-if="isDirty && selected && !loading">
      <div class="save-hint mono">unsaved changes</div>
      <div class="grow"></div>
      <BaseButton variant="ghost" @click="(showDiscard = true)">Discard</BaseButton>
      <BaseButton @click="save" :disabled="savingDisabled">
        <span v-if="saving" class="spinner sm"></span>
        <AppIcon v-else name="check" :size="13" :stroke="2.5" />
        {{ saving ? 'Saving…' : 'Save prompt' }}
      </BaseButton>
    </div>

    <AppToast />

    <BaseModal :show="showCreate" @close="showCreate = false" :width="400">
      <template #title>New AI prompt</template>
      <div class="modal-body">
        <div class="field">
          <label class="field-label">Name</label>
          <input v-model="newName" class="input mono" type="text" spellcheck="false" autofocus />
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showCreate = false">Cancel</BaseButton>
        <BaseButton @click="confirmCreate" :disabled="creating || !newName.trim()">
          <span v-if="creating" class="spinner sm"></span>
          {{ creating ? 'Creating…' : 'Create prompt' }}
        </BaseButton>
      </footer>
    </BaseModal>

    <ConfirmModal
      :show="showDiscard"
      title="Discard changes"
      message="Discard unsaved changes to this prompt?"
      confirm-label="Discard"
      :danger="false"
      @confirm="() => { if (selected) loadEditor(selected); showDiscard = false }"
      @cancel="showDiscard = false"
    />
    <ConfirmModal
      :show="showDelete"
      title="Delete prompt"
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

.dirty { display: inline-flex; align-items: center; gap: 5px; color: var(--amber); margin-left: 6px; }
.dirty-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); }

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
}
</style>
