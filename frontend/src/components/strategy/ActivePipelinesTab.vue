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
import {
  getActiveStrategies,
  createActiveStrategy,
  updateActiveStrategy,
  deleteActiveStrategy,
  duplicateActiveStrategy,
  testRunActiveStrategy,
  getAiStrategies,
  getCppStrategies
} from '@/api/strategies'
import { getCharts } from '@/api/charts'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import type { ActiveStrategy, Chart, AiStrategy, CppStrategy, Analysis } from '@/types'

const toast = useToast()
const { formatDate, formatTime } = useTimezone()

const pipelines = ref<ActiveStrategy[]>([])
const charts = ref<Chart[]>([])
const aiStrats = ref<AiStrategy[]>([])
const cppStrats = ref<CppStrategy[]>([])

const loading = ref(true)
const testRunning = ref<number | null>(null)
const testResult = ref<Analysis | null>(null)
const showTestResult = ref(false)

const showEdit = ref(false)
const showDelete = ref(false)
const deleteTarget = ref<number | null>(null)
const editTarget = ref<ActiveStrategy | null>(null)
const editLoading = ref(false)

// Form fields
const formName = ref('')
const formMode = ref<'hybrid' | 'ai_only' | 'cpp_only'>('hybrid')
const formChart = ref<number | null>(null)
const formAi = ref<number | null>(null)
const formCpp = ref<number | null>(null)
const formMinScore = ref<number>(8.0)
const formCooldown = ref<number>(15)

const isFormValid = computed(() => {
  if (!formName.value.trim() || !formChart.value) return false
  if (formMode.value === 'hybrid' && (!formAi.value || !formCpp.value)) return false
  if (formMode.value === 'ai_only' && !formAi.value) return false
  if (formMode.value === 'cpp_only' && !formCpp.value) return false
  return true
})

async function load() {
  loading.value = true
  try {
    const [pRes, cRes, aRes, cppRes] = await Promise.all([
      getActiveStrategies(),
      getCharts(),
      getAiStrategies(),
      getCppStrategies()
    ])
    pipelines.value = pRes?.active_strategies || []
    charts.value = Array.isArray(cRes) ? cRes : []
    aiStrats.value = aRes?.strategies || []
    cppStrats.value = cppRes?.strategies || []
  } catch {
    toast.err('Failed to load active pipelines')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function handleToggle(p: ActiveStrategy, enabled: boolean) {
  const previous = p.enabled
  p.enabled = enabled
  try {
    await updateActiveStrategy(p.id, { enabled })
    toast.ok(`Pipeline ${enabled ? 'enabled' : 'disabled'}`)
  } catch {
    p.enabled = previous
    toast.err('Failed to toggle pipeline')
  }
}

async function handleTestRun(id: number) {
  if (testRunning.value) return
  testRunning.value = id
  try {
    const res = await testRunActiveStrategy(id)
    testResult.value = res.result
    showTestResult.value = true
  } catch (e: any) {
    toast.err(e?.message || 'Test run failed')
  } finally {
    testRunning.value = null
  }
}

async function handleDuplicate(id: number) {
  try {
    const copy = await duplicateActiveStrategy(id)
    pipelines.value.push(copy)
    toast.ok('Pipeline duplicated')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to duplicate pipeline')
  }
}

function openCreate() {
  editTarget.value = null
  formName.value = 'New Pipeline'
  formMode.value = 'hybrid'
  formChart.value = charts.value[0]?.id ?? null
  formAi.value = aiStrats.value[0]?.id ?? null
  formCpp.value = cppStrats.value[0]?.id ?? null
  formMinScore.value = 8.0
  formCooldown.value = 15
  showEdit.value = true
}

function openEdit(p: ActiveStrategy) {
  editTarget.value = p
  formName.value = p.name
  formMode.value = p.mode
  formChart.value = p.chart_id
  formAi.value = p.ai_strategy_id
  formCpp.value = p.cpp_strategy_id
  formMinScore.value = p.min_score ?? 8.0
  formCooldown.value = p.cooldown_minutes ?? 15
  showEdit.value = true
}

async function savePipeline() {
  if (!isFormValid.value) return
  editLoading.value = true
  try {
    const payload = {
      name: formName.value.trim(),
      mode: formMode.value,
      chart_id: formChart.value!,
      ai_strategy_id: formMode.value !== 'cpp_only' ? formAi.value : null,
      cpp_strategy_id: formMode.value !== 'ai_only' ? formCpp.value : null,
      min_score: formMinScore.value,
      cooldown_minutes: formCooldown.value,
    }
    
    if (editTarget.value) {
      const updated = await updateActiveStrategy(editTarget.value.id, payload)
      const idx = pipelines.value.findIndex(p => p.id === updated.id)
      if (idx !== -1) pipelines.value[idx] = updated
      toast.ok('Pipeline updated')
    } else {
      const created = await createActiveStrategy(payload)
      pipelines.value.push(created)
      toast.ok('Pipeline created')
    }
    showEdit.value = false
  } catch (e: any) {
    toast.err(e?.message || 'Failed to save pipeline')
  } finally {
    editLoading.value = false
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteActiveStrategy(deleteTarget.value)
    pipelines.value = pipelines.value.filter(p => p.id !== deleteTarget.value)
    toast.ok('Pipeline deleted')
  } catch (e: any) {
    toast.err(e?.message || 'Failed to delete pipeline')
  } finally {
    deleteTarget.value = null
    showDelete.value = false
  }
}

function fmtDate(iso: string | null | undefined) {
  if (!iso) return 'Never'
  return formatDate(iso, { month: 'short', day: 'numeric' }) + ' · ' + formatTime(iso)
}

function getChartName(id: number) {
  return charts.value.find(c => c.id === id)?.name ?? 'Unknown Chart'
}
function getAiName(id: number | null) {
  if (!id) return 'None'
  return aiStrats.value.find(a => a.id === id)?.name ?? 'Unknown AI'
}
function getCppName(id: number | null) {
  if (!id) return 'None'
  return cppStrats.value.find(c => c.id === id)?.name ?? 'Unknown C++'
}
</script>

<template>
  <div class="tab-wrapper">
    <div class="header-actions">
      <BaseButton @click="openCreate" :disabled="loading">
        <AppIcon name="plus" :size="14" :stroke="2.5" />
        New pipeline
      </BaseButton>
    </div>

    <AppLoading v-if="loading" label="Loading pipelines…" />

    <div v-else-if="pipelines.length === 0" class="card empty-card">
      <EmptyState
        icon="strategy"
        title="No Active Pipelines"
        description="Assemble your first trading pipeline by connecting a chart, an AI prompt, and a C++ strategy."
        action="Create pipeline"
        @action="openCreate"
      />
    </div>

    <div v-else class="pipelines-grid">
      <div v-for="p in pipelines" :key="p.id" :class="['card', 'pipeline-card', { disabled: !p.enabled }]">
        <div class="p-head">
          <div class="p-title-box">
            <h3 class="p-title">{{ p.name }}</h3>
            <span class="p-mode-tag mono">{{ p.mode.replace('_', ' ') }}</span>
          </div>
          <BaseToggle :model-value="p.enabled" @update:model-value="(val) => handleToggle(p, val)" />
        </div>
        
        <div class="p-blocks">
          <div class="p-block">
            <AppIcon name="charts" :size="14" class="block-ic" />
            <span class="block-txt mono">{{ getChartName(p.chart_id) }}</span>
          </div>
          <div v-if="p.mode !== 'ai_only'" class="p-block">
            <AppIcon name="engine" :size="14" class="block-ic" />
            <span class="block-txt mono">{{ getCppName(p.cpp_strategy_id) }}</span>
          </div>
          <div v-if="p.mode !== 'cpp_only'" class="p-block">
            <AppIcon name="eye" :size="14" class="block-ic" />
            <span class="block-txt mono">{{ getAiName(p.ai_strategy_id) }}</span>
          </div>
        </div>

        <div class="p-stats mono">
          <div class="stat" title="Score Threshold"><AppIcon name="crosshair" :size="12" /> &ge;{{ p.min_score }}</div>
          <div class="stat" title="Cooldown"><AppIcon name="clock" :size="12" /> {{ p.cooldown_minutes }}m</div>
          <div class="stat grow right">Last: {{ fmtDate((p as any).last_triggered_at) }}</div>
        </div>

        <div class="p-actions">
          <BaseButton variant="ghost" size="sm" @click="handleTestRun(p.id)" :disabled="testRunning === p.id">
            <AppIcon v-if="testRunning !== p.id" name="zap" :size="13" />
            <span v-else class="spinner sm"></span>
            Test Run
          </BaseButton>
          <div class="grow"></div>
          <button class="icon-btn" title="Edit" @click="openEdit(p)">
            <AppIcon name="edit" :size="14" />
          </button>
          <button class="icon-btn" title="Duplicate" @click="handleDuplicate(p.id)">
            <AppIcon name="copy" :size="14" />
          </button>
          <button class="icon-btn danger" title="Delete" @click="(deleteTarget = p.id, showDelete = true)">
            <AppIcon name="trash" :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- Assembly Modal -->
    <BaseModal :show="showEdit" @close="showEdit = false" :width="500">
      <template #title>{{ editTarget ? 'Edit Pipeline' : 'Assemble Pipeline' }}</template>
      <div class="modal-body">
        <div class="field">
          <label class="field-label">Pipeline Name</label>
          <input v-model="formName" class="input mono" type="text" placeholder="e.g. BTC Bollinger + ICT Vision" />
        </div>
        
        <div class="field">
          <label class="field-label">Execution Mode</label>
          <select v-model="formMode" class="input">
            <option value="hybrid">Hybrid (C++ Trigger -> AI Verify)</option>
            <option value="ai_only">AI Only (Periodic Polling)</option>
            <option value="cpp_only">C++ Only (Fast Triggering)</option>
          </select>
        </div>

        <div class="blocks-container">
          <div class="field block-field">
            <label class="field-label"><AppIcon name="charts" :size="12" /> Target Chart</label>
            <select v-model="formChart" class="input mono">
              <option :value="null" disabled>Select chart...</option>
              <option v-for="c in charts" :key="c.id" :value="c.id">{{ c.name }} ({{ c.symbol }})</option>
            </select>
          </div>
          
          <div class="field block-field" v-if="formMode !== 'ai_only'">
            <label class="field-label"><AppIcon name="engine" :size="12" /> C++ Strategy</label>
            <select v-model="formCpp" class="input mono">
              <option :value="null" disabled>Select C++ strategy...</option>
              <option v-for="c in cppStrats" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div class="field block-field" v-if="formMode !== 'cpp_only'">
            <label class="field-label"><AppIcon name="eye" :size="12" /> AI Vision Prompt</label>
            <select v-model="formAi" class="input mono">
              <option :value="null" disabled>Select AI prompt...</option>
              <option v-for="a in aiStrats" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
        </div>

        <div class="row-fields">
          <div class="field">
            <label class="field-label" title="Minimum score to trigger notification">Score Threshold (0-10)</label>
            <input v-model.number="formMinScore" class="input mono" type="number" step="0.1" min="0" max="10" />
          </div>
          <div class="field">
            <label class="field-label" title="Prevent spam by pausing after a signal">Cooldown (minutes)</label>
            <input v-model.number="formCooldown" class="input mono" type="number" min="0" />
          </div>
        </div>
      </div>
      <footer class="modal-foot">
        <BaseButton variant="ghost" @click="showEdit = false">Cancel</BaseButton>
        <BaseButton @click="savePipeline" :disabled="!isFormValid || editLoading">
          <span v-if="editLoading" class="spinner sm"></span>
          {{ editLoading ? 'Saving…' : (editTarget ? 'Save changes' : 'Create Pipeline') }}
        </BaseButton>
      </footer>
    </BaseModal>

    <!-- Test Result Modal -->
    <BaseModal :show="showTestResult" @close="showTestResult = false" :width="500">
      <template #title>Test Run Result</template>
      <div class="modal-body" v-if="testResult">
        <img v-if="testResult.screenshot_url" :src="testResult.screenshot_url" class="res-img" />
        <div class="res-stats mono">
          <div :class="['res-score', testResult.score >= 8 ? 'high' : testResult.score >= 5 ? 'mid' : 'low']">
            Score: {{ testResult.score }}
          </div>
          <div :class="['res-dir', testResult.direction.toLowerCase()]">{{ testResult.direction }}</div>
        </div>
        <div class="res-reason">{{ testResult.reason }}</div>
      </div>
      <footer class="modal-foot">
        <BaseButton @click="showTestResult = false">Close</BaseButton>
      </footer>
    </BaseModal>

    <ConfirmModal
      :show="showDelete"
      title="Delete Pipeline"
      message="Delete this active pipeline? This cannot be undone."
      confirm-label="Delete"
      @confirm="confirmDelete"
      @cancel="showDelete = false"
    />
    <AppToast />
  </div>
</template>

<style scoped>
.tab-wrapper { display: flex; flex-direction: column; gap: 16px; padding-bottom: 40px; }
.header-actions { display: flex; justify-content: flex-end; margin-bottom: 4px; }
.empty-card { padding: 0; }

.pipelines-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }

.pipeline-card {
  padding: 16px; display: flex; flex-direction: column; gap: 14px;
  background: var(--surface); border: 1px solid var(--border);
  transition: opacity 0.2s, border-color 0.2s;
}
.pipeline-card.disabled { opacity: 0.6; filter: grayscale(50%); }
.pipeline-card:not(.disabled):hover { border-color: var(--border-2); }

.p-head { display: flex; justify-content: space-between; align-items: flex-start; }
.p-title-box { display: flex; flex-direction: column; gap: 4px; }
.p-title { font: 600 15px var(--font-sans); color: var(--fg); letter-spacing: -0.01em; margin: 0; }
.p-mode-tag {
  display: inline-block; padding: 2px 6px; border-radius: 4px;
  background: var(--surface-hi); color: var(--fg-2);
  font: 500 10px var(--font-mono); text-transform: uppercase; letter-spacing: 0.05em;
  width: fit-content;
}

.p-blocks {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; background: var(--bg-2); border-radius: 8px; border: 1px solid var(--border);
}
.p-block { display: flex; align-items: center; gap: 8px; }
.block-ic { color: var(--accent); opacity: 0.8; }
.block-txt { font: 500 12px var(--font-mono); color: var(--fg-2); }

.p-stats {
  display: flex; align-items: center; gap: 14px;
  font-size: 11px; color: var(--muted);
}
.stat { display: flex; align-items: center; gap: 4px; }
.stat.right { justify-content: flex-end; }
.grow { flex: 1; }

.p-actions {
  display: flex; align-items: center; gap: 6px;
  padding-top: 14px; border-top: 1px dashed var(--border);
}
.icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  border: 0; background: var(--surface-hi); color: var(--muted); cursor: pointer;
  border-radius: 6px; transition: all .12s;
}
.icon-btn:hover { color: var(--fg); background: var(--surface-2); }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }

.spinner.sm {
  width: 13px; height: 13px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}

.modal-body { padding: 16px 18px 4px; display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font: 600 11px var(--font-mono); letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); display: flex; align-items: center; gap: 6px; }
.blocks-container {
  display: flex; flex-direction: column; gap: 10px;
  padding: 14px; background: var(--bg-2); border-radius: 8px; border: 1px dashed var(--border);
}
.row-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.modal-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid var(--border); background: var(--bg-2); margin-top: 10px; }

.res-img { width: 100%; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 12px; }
.res-stats { display: flex; gap: 12px; font-weight: 600; font-size: 14px; margin-bottom: 8px; }
.res-score.high { color: var(--green); }
.res-score.mid { color: var(--amber); }
.res-score.low { color: var(--red); }
.res-dir.long { color: var(--green); }
.res-dir.short { color: var(--red); }
.res-dir.neutral { color: var(--muted); }
.res-reason { font: 400 13px/1.5 var(--font-sans); color: var(--fg-2); }
</style>
