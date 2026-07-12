<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import Toast from '@/components/ui/Toast.vue'
import { getAnalysis, getScreenshot, resendNotification, reanalyze } from '@/api/analyses'
import type { Analysis } from '@/types'

const route = useRoute()
const id = Number(route.params.id)
const analysis = ref<Analysis | null>(null)
const loading = ref(true)
const toast = ref({ show: false, message: '' })
const screenshotUrl = ref('')
const actionLoading = ref(false)

onMounted(async () => {
  try {
    analysis.value = await getAnalysis(id)
    try {
      const blob = await getScreenshot(id)
      screenshotUrl.value = URL.createObjectURL(blob)
    } catch {}
  } finally {
    loading.value = false
  }
})

async function handleResend() {
  actionLoading.value = true
  try {
    await resendNotification(id)
    toast.value = { show: true, message: 'Notification resent' }
    analysis.value = await getAnalysis(id)
  } catch {
    toast.value = { show: true, message: 'Failed to resend' }
  } finally {
    actionLoading.value = false
  }
}

async function handleReanalyze() {
  actionLoading.value = true
  try {
    await reanalyze(id)
    toast.value = { show: true, message: 'Re-analysis started' }
    analysis.value = await getAnalysis(id)
  } catch {
    toast.value = { show: true, message: 'Failed to reanalyze' }
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <AppShell :crumbs="['History', `Analysis #${id}`]">
    <div class="pg">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>
      <template v-else-if="analysis">
        <div class="pg-head">
          <div>
            <h1 class="h1">{{ analysis.chart_name }}</h1>
            <div class="pg-sub mono">{{ new Date(analysis.timestamp).toLocaleString() }} &middot; Analysis #{{ id }}</div>
          </div>
          <div class="spacer"></div>
          <StatusPill :status="analysis.sent ? 'ok' : 'skipped'" />
        </div>

        <div class="grid">
          <div class="card info-card">
            <div class="card-title">Details</div>
            <div class="info-row">
              <span class="k">Direction</span>
              <BaseChip :direction="analysis.direction">{{ analysis.direction }}</BaseChip>
            </div>
            <div class="info-row">
              <span class="k">Score</span>
              <ScoreBar :score="analysis.score" size="md" />
            </div>
            <div class="info-row">
              <span class="k">Created</span>
              <span class="v mono">{{ new Date(analysis.timestamp).toLocaleString() }}</span>
            </div>
            <div v-if="analysis.notification_id" class="info-row">
              <span class="k">Notif ID</span>
              <span class="v mono">#NT-{{ String(analysis.notification_id).padStart(4, '0') }}</span>
            </div>
            <template v-if="analysis.entry">
              <div class="info-divider"></div>
              <div class="info-row">
                <span class="k">Entry</span>
                <span class="v mono">{{ analysis.entry }}</span>
              </div>
              <div class="info-row" v-if="analysis.stop_loss">
                <span class="k">Stop Loss</span>
                <span class="v mono">{{ analysis.stop_loss }}</span>
              </div>
              <div class="info-row" v-if="analysis.take_profit">
                <span class="k">Take Profit</span>
                <span class="v mono">{{ analysis.take_profit }}</span>
              </div>
            </template>
          </div>

          <div class="screenshot-area">
            <div v-if="screenshotUrl" class="screenshot-wrap">
              <img :src="screenshotUrl" alt="Analysis screenshot" class="screenshot" />
            </div>
            <div v-else class="no-screenshot">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--muted)">
                <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
              <span>No screenshot available</span>
            </div>
          </div>
        </div>

        <div class="card summary-card">
          <div class="card-title">AI Analysis</div>
          <div class="summary-text">{{ analysis.reason }}</div>
        </div>

        <div class="actions-row">
          <BaseButton variant="ghost" @click="$router.back()">← Back</BaseButton>
          <div class="spacer"></div>
          <BaseButton variant="ghost" @click="handleResend" :disabled="actionLoading">Resend notification</BaseButton>
          <BaseButton @click="handleReanalyze" :disabled="actionLoading">Reanalyze</BaseButton>
        </div>
      </template>
    </div>
    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 20px; }
.pg-head { display: flex; align-items: flex-start; gap: 16px; }
.h1 { font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.015em; }
.pg-sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.spacer { flex: 1; }
.loading { display: grid; place-items: center; padding: 80px 0; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--surface-3); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  align-items: start;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
}
.card-title { font-size: 13px; font-weight: 600; color: var(--fg-2); margin-bottom: 14px; }

.info-card { display: flex; flex-direction: column; gap: 14px; }
.info-row { display: flex; align-items: center; justify-content: space-between; }
.k { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-family: var(--font-mono); }
.v { font-size: 14px; color: var(--fg); }
.mono { font-family: var(--font-mono); }
.info-divider { height: 1px; background: var(--border); margin: 2px 0; }

.screenshot-area {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.screenshot-wrap { width: 100%; }
.screenshot { width: 100%; height: auto; display: block; }
.no-screenshot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px 0;
  color: var(--muted);
  font-size: 13px;
}

.summary-card .summary-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--fg-2);
  white-space: pre-wrap;
}

.actions-row { display: flex; align-items: center; gap: 10px; }
</style>
