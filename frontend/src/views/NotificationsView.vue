<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import Toast from '@/components/ui/Toast.vue'
import { getNotifications, deleteNotification } from '@/api/notifications'
import type { Notification } from '@/types'

const router = useRouter()
const items = ref<Notification[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const pageSize = ref(20)
const toast = ref({ show: false, message: '' })
const actionLoading = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await getNotifications({ page: String(page.value), page_size: String(pageSize.value) })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

load()

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

function goToAnalysis(analysisId: number) {
  if (analysisId) {
    router.push(`/analysis/${analysisId}`)
  }
}

async function handleDelete(e: Event, id: number) {
  e.stopPropagation()
  if (!confirm('Delete this notification?')) return
  actionLoading.value = id
  try {
    await deleteNotification(id)
    toast.value = { show: true, message: 'Notification deleted' }
    load()
  } catch {
    toast.value = { show: true, message: 'Failed to delete' }
  } finally {
    actionLoading.value = null
  }
}
</script>

<template>
  <AppShell :crumbs="['Notifications']">
    <div class="pg">
      <div class="pg-head">
        <h1 class="h1">Notifications</h1>
        <div class="spacer"></div>
        <span class="count mono">{{ total }} total</span>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else-if="items.length === 0" class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--muted)">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <p class="empty-t">No notifications yet</p>
        <p class="empty-d">Notifications appear when a signal is sent</p>
      </div>

      <div v-else class="list">
        <div
          v-for="n in items"
          :key="n.id"
          class="row"
          @click="goToAnalysis(n.analysis_id)"
        >
          <div class="row-left">
            <div class="row-info">
              <span class="title">{{ n.chart_name }} &mdash; {{ n.direction }}</span>
              <span class="body">Score: {{ n.score }} &middot; {{ n.caption || n.status }}</span>
              <span class="meta mono">{{ new Date(n.timestamp).toLocaleString() }}</span>
            </div>
          </div>
          <div class="row-right">
            <StatusPill :status="n.status === 'sent' ? 'ok' : 'error'" />
            <button
              class="link-btn danger"
              @click="(e) => handleDelete(e, n.id)"
              :disabled="actionLoading === n.id"
            >Delete</button>
          </div>
        </div>
      </div>

      <div v-if="totalPages > 1" class="pager">
        <BaseButton variant="ghost" size="sm" :disabled="page <= 1" @click="page--; load()">&larr; Prev</BaseButton>
        <span class="pager-info mono">Page {{ page }} of {{ totalPages }}</span>
        <BaseButton variant="ghost" size="sm" :disabled="page >= totalPages" @click="page++; load()">Next &rarr;</BaseButton>
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
.count { font-size: 12px; color: var(--muted); }
.loading { display: grid; place-items: center; padding: 80px 0; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--surface-3); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 0; color: var(--muted); }
.empty-t { font-size: 14px; font-weight: 600; margin: 12px 0 4px; color: var(--fg-2); }
.empty-d { font-size: 13px; margin: 0; }
.list { display: flex; flex-direction: column; gap: 1px; background: var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--surface);
  cursor: pointer;
  transition: background .1s;
}
.row:hover { background: var(--surface-2); }
.row-left { min-width: 0; flex: 1; }
.row-info { display: flex; flex-direction: column; gap: 4px; }
.title { font-size: 13px; font-weight: 600; }
.body { font-size: 13px; color: var(--fg-2); }
.meta { font-size: 11px; color: var(--muted); }
.row-right { flex-shrink: 0; margin-left: 16px; display: flex; align-items: center; gap: 10px; }
.mono { font-family: var(--font-mono); }
.pager { display: flex; align-items: center; justify-content: center; gap: 12px; }
.pager-info { font-size: 12px; color: var(--muted); }

.link-btn {
  background: none;
  border: 0;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background .12s;
}
.link-btn.danger { color: var(--red); }
.link-btn.danger:hover { background: var(--red-soft); }
.link-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
