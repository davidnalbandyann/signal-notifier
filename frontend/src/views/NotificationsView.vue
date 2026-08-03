<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import SignalQualification from '@/components/ui/SignalQualification.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import { getNotifications, deleteNotification } from '@/api/notifications'
import { useToast } from '@/composables/useToast'
import { useTimezone } from '@/composables/useTimezone'
import { useThreshold } from '@/composables/useThreshold'
import type { Notification } from '@/types'

const router = useRouter()
const toast = useToast()
const { formatDate } = useTimezone()
const { threshold, load: loadThreshold } = useThreshold()
const items = ref<Notification[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const actionLoading = ref<number | null>(null)
const deleteTarget = ref<number | null>(null)

let searchDebounce: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = { page: String(page.value), page_size: String(pageSize.value) }
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    const res = await getNotifications(params)
    items.value = res.items
    total.value = res.total
  } catch { toast.err('Failed to load notifications') }
  finally { loading.value = false }
}
onMounted(() => {
  load()
  loadThreshold()
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

function go(analysisId: number) {
  if (analysisId) router.push(`/analysis/${analysisId}`)
}

async function handleDelete(e: Event, id: number) {
  e.stopPropagation()
  deleteTarget.value = id
}

async function confirmDelete() {
  const id = deleteTarget.value
  if (id == null) return
  actionLoading.value = id
  try { await deleteNotification(id); toast.ok('Notification deleted'); deleteTarget.value = null; await load() }
  catch { toast.err('Failed to delete') }
  finally { actionLoading.value = null }
}

function fmt(iso: string) {
  return formatDate(iso, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Signals</h1>
          <div class="pg-sub">{{ total.toLocaleString() }} Telegram deliveries &middot; audit trail</div>
        </div>
        <div class="grow"></div>
      </header>

      <!-- Standalone Search Bar Section -->
      <div v-if="items.length > 0 || searchQuery" class="search-card card">
        <div class="search-box">
          <AppIcon name="search" :size="14" class="search-ic" />
          <input
            v-model="searchQuery"
            @input="onSearchInput"
            type="text"
            class="input search-input mono"
            placeholder="Search signals by symbol or message..."
          />
          <button v-if="searchQuery" class="clear-search-btn" @click="searchQuery = ''; page = 1; load()" title="Clear search">
            <AppIcon name="x" :size="12" />
          </button>
        </div>
      </div>


      <AppLoading v-if="loading" label="Loading signals…" />


      <div v-else-if="items.length === 0" class="card empty-card">
        <EmptyState
          icon="bell"
          title="No signals sent yet"
          :description="threshold != null
            ? `Notifications appear here when an analysis score crosses the threshold (${threshold.toFixed(1)})`
            : 'Notifications appear here when an analysis score crosses the configured threshold'"
        />
      </div>

      <div v-else class="card list-card">
        <div class="list-head">
          <div class="col-msg">Message</div>
          <div class="col-qual">Qualification</div>
          <div class="col-time">Sent at</div>
          <div class="col-actions"></div>
        </div>
        <div
          v-for="n in items"
          :key="n.id"
          class="list-row"
          @click="go(n.analysis_id)"
        >
          <div class="col-msg">
            <div class="msg-top">
              <span class="sym mono">{{ n.chart_name }}</span>
            </div>
            <div class="msg-body">{{ n.caption || n.status }}</div>
          </div>
          <div class="col-qual">
            <SignalQualification
              :score="n.score"
              :threshold="threshold"
              :direction="n.direction"
              :sent="n.status === 'sent'"
              density="compact"
            />
          </div>
          <div class="col-time mono">{{ fmt(n.timestamp) }}</div>
          <div class="col-actions" @click.stop>
            <button
              class="icon-btn danger"
              @click="handleDelete($event, n.id)"
              :disabled="actionLoading === n.id"
              title="Delete notification"
              aria-label="Delete"
            >
              <AppIcon name="trash" :size="14" />
            </button>
          </div>
        </div>

        <div v-if="totalPages > 1" class="pager">
          <BaseButton variant="ghost" size="sm" :disabled="page <= 1" @click="page--; load()">
            <AppIcon name="chevronLeft" :size="13" :stroke="2.5" />
            Prev
          </BaseButton>
          <span class="pager-info mono">Page {{ page }} / {{ totalPages }}</span>
          <BaseButton variant="ghost" size="sm" :disabled="page >= totalPages" @click="page++; load()">
            Next
            <AppIcon name="chevronRight" :size="13" :stroke="2.5" />
          </BaseButton>
        </div>
      </div>
    </div>
    <AppToast />
    <ConfirmModal
      :show="deleteTarget !== null"
      title="Delete notification"
      message="Delete this notification record? This cannot be undone."
      confirm-label="Delete"
      :loading="actionLoading === deleteTarget"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 18px; max-width: 1300px; }

.pg-head { display: flex; align-items: flex-end; gap: 12px; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.search-card {
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.search-box { position: relative; width: 100%; display: flex; align-items: center; }
.search-ic { position: absolute; left: 10px; color: var(--muted); pointer-events: none; }
.search-input { width: 100%; height: 34px; font-size: 12.5px; padding: 0 28px 0 32px; }
.clear-search-btn {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  border: 0; background: transparent; color: var(--muted); cursor: pointer; padding: 3px;
  display: flex; align-items: center; justify-content: center; border-radius: 4px;
}
.clear-search-btn:hover { color: var(--fg); background: var(--surface-2); }

.empty-card { padding: 0; }



.list-card { padding: 0; overflow: hidden; }
.list-head, .list-row {
  display: grid;
  grid-template-columns: 1fr 320px 160px 64px;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
}
.list-head {
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  font: 600 11px var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.list-row {
  border-top: 1px solid var(--border);
  cursor: pointer;
  transition: background .12s;
}
.list-row:hover { background: var(--surface-2); }

.col-msg { min-width: 0; }
.msg-top { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.sym { font: 600 13px var(--font-mono); color: var(--fg); }
.msg-body {
  font: 400 12.5px var(--font-sans);
  color: var(--fg-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-time { font: 500 12px var(--font-mono); color: var(--muted); }
.col-actions { display: flex; justify-content: flex-end; gap: 4px; }
.icon-btn.danger:hover { color: var(--red); background: var(--red-soft); }

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 11px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
}
.pager-info { font: 600 12px var(--font-mono); color: var(--muted); }

@media (max-width: 720px) {
  .list-head { display: none; }
  .list-row {
    grid-template-columns: 1fr auto;
    gap: 6px 12px;
  }
  .col-msg { grid-column: 1; }
  .col-actions { grid-column: 2; }
  .col-qual, .col-time { grid-column: 1 / -1; }
}
</style>
