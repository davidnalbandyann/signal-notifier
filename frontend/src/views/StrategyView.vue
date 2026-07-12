<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import Toast from '@/components/ui/Toast.vue'
import { getStrategy, updateStrategy } from '@/api/strategy'

const content = ref('')
const loading = ref(true)
const saving = ref(false)
const toast = ref({ show: false, message: '' })

onMounted(async () => {
  try {
    const res = await getStrategy()
    content.value = res.content
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await updateStrategy(content.value)
    toast.value = { show: true, message: 'Strategy updated' }
  } catch {
    toast.value = { show: true, message: 'Failed to save strategy' }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppShell :crumbs="['Strategy']">
    <div class="pg">
      <div class="pg-head">
        <h1 class="h1">Strategy prompt</h1>
        <div class="spacer"></div>
        <BaseButton @click="save" :disabled="saving">{{ saving ? 'Saving…' : 'Save strategy' }}</BaseButton>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else class="editor-card">
        <div class="editor-hint">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent)">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <span>This is the system prompt sent to the AI model for every chart analysis. Edit with care.</span>
        </div>
        <textarea
          v-model="content"
          class="editor mono"
          rows="28"
          spellcheck="false"
        ></textarea>
      </div>
    </div>
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
.editor-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.editor-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
  padding: 10px 12px;
  background: var(--accent-soft);
  border: 1px solid oklch(60% 0.18 262 / 0.3);
  border-radius: var(--radius);
}
.editor {
  width: 100%;
  min-height: 480px;
  padding: 16px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--fg);
  font-size: 13px;
  font-family: var(--font-mono);
  line-height: 1.7;
  resize: vertical;
  tab-size: 2;
}
.editor:focus { outline: none; border-color: var(--accent); }
.mono { font-family: var(--font-mono); }
</style>
