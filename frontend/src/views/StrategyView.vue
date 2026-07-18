<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import { getStrategy, updateStrategy } from '@/api/strategy'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const content = ref('')
const original = ref('')
const loading = ref(true)
const saving = ref(false)

onMounted(async () => {
  try {
    const res = await getStrategy()
    content.value = res.content
    original.value = res.content
  } catch { toast.err('Failed to load strategy') }
  finally { loading.value = false }
})

const dirty = computed(() => content.value !== original.value)
const lineCount = computed(() => content.value.split('\n').length)
const charCount = computed(() => content.value.length)

async function save() {
  saving.value = true
  try {
    await updateStrategy(content.value)
    original.value = content.value
    toast.ok('Strategy updated')
  } catch { toast.err('Failed to save strategy') }
  finally { saving.value = false }
}

function reset() {
  if (!dirty.value || !confirm('Discard unsaved changes?')) return
  content.value = original.value
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Strategy prompt</h1>
          <div class="pg-sub">System prompt sent to the vision model on every analysis</div>
        </div>
        <div class="grow"></div>
        <BaseButton variant="ghost" @click="reset" :disabled="!dirty || saving">
          <AppIcon name="refresh" :size="13" />
          Discard
        </BaseButton>
        <BaseButton @click="save" :disabled="!dirty || saving">
          <span v-if="saving" class="spinner sm"></span>
          <AppIcon v-else name="check" :size="13" :stroke="2.5" />
          {{ saving ? 'Saving…' : 'Save strategy' }}
        </BaseButton>
      </header>

      <div class="card info-banner">
        <AppIcon name="info" :size="14" :stroke="2" class="info-ic" />
        <div class="info-text">
          <div class="info-title">Edit with care</div>
          <div class="info-sub">This prompt is hot-reloaded on every cycle. Plain markdown is supported.</div>
        </div>
      </div>

      <AppLoading v-if="loading" label="Loading strategy…" />

      <div v-else class="card editor-card">
        <div class="editor-head">
          <div class="editor-stats mono">
            <span>{{ lineCount }} lines</span>
            <span class="sep">·</span>
            <span>{{ charCount.toLocaleString() }} chars</span>
            <span v-if="dirty" class="dirty">
              <span class="dirty-dot"></span> unsaved
            </span>
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
    </div>
    <AppToast />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 14px; max-width: 1100px; }

.pg-head { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.info-banner {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 12px 16px;
  border-left: 3px solid var(--accent);
}
.info-ic { color: var(--accent); flex-shrink: 0; }
.info-title { font: 600 13px var(--font-sans); color: var(--fg); }
.info-sub { font: 400 11.5px var(--font-sans); color: var(--muted); margin-top: 1px; }

.editor-card { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.editor-head {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 9px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-2);
}
.editor-stats {
  display: flex;
  align-items: center;
  gap: 7px;
  font: 500 11px var(--font-mono);
  color: var(--muted);
}
.editor-stats .sep { color: var(--muted-2); }
.dirty {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--amber);
  margin-left: 6px;
}
.dirty-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); }

.editor {
  width: 100%;
  min-height: 540px;
  padding: 16px 18px;
  background: var(--bg);
  border: 0;
  color: var(--fg);
  font: 500 13px/1.7 var(--font-mono);
  resize: vertical;
  tab-size: 2;
  outline: none;
}
.editor::placeholder { color: var(--muted-2); }
.editor:focus { background: var(--bg-2); }

.spinner.sm {
  width: 13px; height: 13px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}
</style>
