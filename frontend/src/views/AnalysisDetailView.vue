<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import ScoreBar from '@/components/ui/ScoreBar.vue'
import BaseChip from '@/components/ui/BaseChip.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import { getAnalysis, getScreenshot, resendNotification, reanalyze, deleteAnalysis } from '@/api/analyses'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import type { Analysis } from '@/types'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { formatFull } = useTimezone()
const id = Number(route.params.id)

const analysis = ref<Analysis | null>(null)
const loading = ref(true)
const screenshotUrl = ref('')
const actionLoading = ref<null | 'resend' | 'reanalyze' | 'delete'>(null)

async function load() {
  try {
    analysis.value = await getAnalysis(id)
    try {
      const blob = await getScreenshot(id)
      screenshotUrl.value = URL.createObjectURL(blob)
    } catch { screenshotUrl.value = '' }
  } catch { toast.err('Analysis not found') }
  finally { loading.value = false }
}

onMounted(load)
onUnmounted(() => { if (screenshotUrl.value) URL.revokeObjectURL(screenshotUrl.value) })

async function handleResend() {
  actionLoading.value = 'resend'
  try { await resendNotification(id); toast.ok('Notification resent'); await load() }
  catch { toast.err('Failed to resend') }
  finally { actionLoading.value = null }
}
async function handleReanalyze() {
  actionLoading.value = 'reanalyze'
  try { await reanalyze(id); toast.ok('Re-analysis started'); await load() }
  catch { toast.err('Failed to reanalyze') }
  finally { actionLoading.value = null }
}
async function handleDelete() {
  if (!confirm('Delete this analysis? This cannot be undone.')) return
  actionLoading.value = 'delete'
  try { await deleteAnalysis(id); toast.ok('Analysis deleted'); router.push('/history') }
  catch { toast.err('Failed to delete') }
  finally { actionLoading.value = null }
}

function fmtFull(iso: string) {
  return formatFull(iso)
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <AppLoading v-if="loading" label="Loading analysis…" />

      <template v-else-if="analysis">
        <!-- Header -->
        <header class="pg-head">
          <button class="icon-btn bordered" @click="router.back()" title="Back" aria-label="Back">
            <AppIcon name="arrowLeft" :size="15" />
          </button>
          <div class="head-main">
            <div class="head-row">
              <h1 class="pg-title mono">{{ analysis.chart_name }}</h1>
              <StatusPill :status="analysis.sent ? 'ok' : 'skipped'" />
            </div>
            <div class="head-sub mono">
              {{ fmtFull(analysis.timestamp) }} &middot; Analysis #{{ id }}
            </div>
          </div>
          <div class="grow"></div>
          <BaseButton variant="ghost" @click="handleResend" :disabled="actionLoading === 'resend'">
            <AppIcon name="refresh" :size="13" :stroke="2.5" />
            Resend
          </BaseButton>
          <BaseButton @click="handleReanalyze" :disabled="actionLoading === 'reanalyze'">
            <AppIcon name="activity" :size="13" />
            Reanalyze
          </BaseButton>
          <BaseButton variant="danger" @click="handleDelete" :disabled="actionLoading === 'delete'">
            <AppIcon name="trash" :size="13" />
            Delete
          </BaseButton>
        </header>

        <!-- Body: info + screenshot -->
        <div class="body-grid">
          <!-- Info panel -->
          <aside class="card info-card">
            <div class="card-head"><div class="card-title">Signal</div></div>
            <div class="info-body">
              <div class="info-row">
                <span class="k">Direction</span>
                <BaseChip :direction="analysis.direction" dot>{{ analysis.direction }}</BaseChip>
              </div>
              <div class="info-row">
                <span class="k">Score</span>
                <ScoreBar :score="analysis.score" size="md" />
              </div>
              <div class="info-row">
                <span class="k">Created</span>
                <span class="v mono">{{ fmtFull(analysis.timestamp) }}</span>
              </div>
              <div v-if="analysis.notification_id" class="info-row">
                <span class="k">Notif ID</span>
                <span class="v mono">#{{ String(analysis.notification_id).padStart(4, '0') }}</span>
              </div>
              <template v-if="analysis.entry">
                <div class="info-divider"></div>
                <div class="info-row">
                  <span class="k">Entry</span>
                  <span class="v mono accent">{{ analysis.entry }}</span>
                </div>
                <div v-if="analysis.stop_loss" class="info-row">
                  <span class="k">Stop loss</span>
                  <span class="v mono short">{{ analysis.stop_loss }}</span>
                </div>
                <div v-if="analysis.take_profit" class="info-row">
                  <span class="k">Take profit</span>
                  <span class="v mono long">{{ analysis.take_profit }}</span>
                </div>
              </template>
            </div>
          </aside>

          <!-- Screenshot — the visual anchor -->
          <div class="card screenshot-card">
            <div class="card-head">
              <div class="card-title">Captured chart</div>
              <a
                v-if="screenshotUrl"
                :href="screenshotUrl"
                target="_blank"
                rel="noopener"
                class="card-link"
              >
                <AppIcon name="external" :size="11" />
                Open original
              </a>
            </div>
            <div v-if="screenshotUrl" class="shot-wrap">
              <img :src="screenshotUrl" alt="Chart screenshot captured at analysis time" class="shot" />
            </div>
            <div v-else class="no-shot">
              <AppIcon name="image" :size="28" :stroke="1.5" />
              <span>No screenshot available</span>
            </div>
          </div>
        </div>

        <!-- AI reasoning -->
        <section class="card reasoning-card">
          <div class="card-head">
            <div class="card-title">AI reasoning</div>
            <span class="card-meta mono">MiniMax-M3 vision output</span>
          </div>
          <div class="reasoning">{{ analysis.reason }}</div>
        </section>
      </template>
    </div>
    <AppToast />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 16px; max-width: 1500px; }

.pg-head { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.head-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.head-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.pg-title { font: 600 18px var(--font-mono); letter-spacing: -0.01em; }
.head-sub { font: 400 11.5px var(--font-mono); color: var(--muted); }

.body-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 14px;
  align-items: start;
}

.info-card, .screenshot-card, .reasoning-card { padding: 0; overflow: hidden; }
.card-head { padding: 11px 16px; }
.card-title { font: 600 11px var(--font-mono); letter-spacing: 0.08em; color: var(--fg-2); text-transform: uppercase; }
.card-meta { font: 500 10.5px var(--font-mono); color: var(--muted); letter-spacing: 0.04em; text-transform: uppercase; }
.card-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 500 11px var(--font-sans);
  color: var(--accent-2);
}

.info-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 11px; }
.info-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.k { font: 600 10.5px var(--font-mono); color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase; }
.v { font: 500 13px var(--font-mono); color: var(--fg); }
.v.accent { color: var(--accent-2); }
.v.short { color: var(--red); }
.v.long { color: var(--green); }
.info-divider { height: 1px; background: var(--border); margin: 2px 0; }

.shot-wrap { background: var(--bg); padding: 12px; }
.shot {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-sm);
}
.no-shot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 80px 0;
  color: var(--muted);
  font: 500 12.5px var(--font-sans);
}

.reasoning {
  padding: 16px 18px;
  font: 400 13.5px/1.7 var(--font-sans);
  color: var(--fg-2);
  white-space: pre-wrap;
  word-wrap: break-word;
}

.icon-btn.bordered { width: 32px; height: 32px; flex-shrink: 0; margin-top: 2px; }

@media (max-width: 900px) {
  .body-grid { grid-template-columns: 1fr; }
}
</style>
