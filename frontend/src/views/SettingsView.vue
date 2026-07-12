<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import Toast from '@/components/ui/Toast.vue'
import { getSettings, updateSettings } from '@/api/settings'
import { getStatus, pauseScan, resumeScan, triggerScan } from '@/api/dashboard'
import type { Settings } from '@/types'

const settings = ref<Settings>({})
const loading = ref(true)
const saving = ref(false)
const scanRunning = ref(false)
const scanLoading = ref(false)
const toast = ref({ show: false, message: '' })

const activeSection = ref('timing')
const showToken = ref(false)
const showApiKey = ref(false)

onMounted(async () => {
  try {
    settings.value = await getSettings()
    const status = await getStatus()
    scanRunning.value = status.running
  } finally {
    loading.value = false
  }
})

async function toggleScan() {
  scanLoading.value = true
  try {
    if (scanRunning.value) {
      await pauseScan()
      scanRunning.value = false
      toast.value = { show: true, message: 'Scan loop paused' }
    } else {
      await resumeScan()
      scanRunning.value = true
      toast.value = { show: true, message: 'Scan loop resumed' }
    }
  } catch {
    toast.value = { show: true, message: 'Failed to toggle scan' }
  } finally {
    scanLoading.value = false
  }
}

async function runScanNow() {
  scanLoading.value = true
  try {
    await triggerScan()
    toast.value = { show: true, message: 'Scan triggered' }
  } catch {
    toast.value = { show: true, message: 'Failed to trigger scan' }
  } finally {
    scanLoading.value = false
  }
}

function updateField(key: string, value: any) {
  settings.value[key] = value
}

function updateBoolField(key: string, event: Event) {
  settings.value[key] = (event.target as HTMLInputElement).checked
}

async function save() {
  saving.value = true
  try {
    await updateSettings(settings.value)
    toast.value = { show: true, message: 'Settings saved' }
  } catch {
    toast.value = { show: true, message: 'Failed to save settings' }
  } finally {
    saving.value = false
  }
}

function scrollTo(id: string) {
  activeSection.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function toggleShow(field: 'token' | 'apiKey') {
  if (field === 'token') showToken.value = !showToken.value
  else showApiKey.value = !showApiKey.value
}
</script>

<template>
  <AppShell :crumbs="['Settings']">
    <div class="pg">
      <div class="page-head">
        <div>
          <h1 class="page-title">Settings</h1>
          <div class="page-sub">config.yaml · manage all system settings</div>
        </div>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else class="settings-grid">
        <nav class="subnav">
          <a :class="{ active: activeSection === 'timing' }" @click="scrollTo('timing')">
            <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Scan timing
          </a>
          <a :class="{ active: activeSection === 'threshold' }" @click="scrollTo('threshold')">
            <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
            Threshold
          </a>
          <a :class="{ active: activeSection === 'browser' }" @click="scrollTo('browser')">
            <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            Browser
          </a>
          <a :class="{ active: activeSection === 'ai' }" @click="scrollTo('ai')">
            <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            AI provider
          </a>
          <a :class="{ active: activeSection === 'telegram' }" @click="scrollTo('telegram')">
            <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Telegram
          </a>
        </nav>

        <div>
          <section class="group" id="timing">
            <header class="group-head">
              <div>
                <div class="group-title">Scan timing</div>
                <div class="group-sub">How often the loop runs and how long it waits between AI calls.</div>
              </div>
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl"><div class="k">Check interval</div><div class="h">Seconds between full watchlist scans.</div></div>
                <div class="ctrl">
                  <input type="number" class="mono" :value="settings.CHECK_INTERVAL_SECONDS" @input="updateField('CHECK_INTERVAL_SECONDS', Number(($event.target as HTMLInputElement).value))" min="1" max="3600" step="1" />
                  <span class="suf">seconds</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">AI call delay</div><div class="h">Pause between consecutive vision API calls (rate limit safety).</div></div>
                <div class="ctrl">
                  <input type="number" class="mono" :value="settings.AI_CALL_DELAY" @input="updateField('AI_CALL_DELAY', Number(($event.target as HTMLInputElement).value))" min="0" max="30" step="0.5" />
                  <span class="suf">seconds</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Scanning loop</div><div class="h">{{ scanRunning ? 'Loop is active — scanning on schedule.' : 'Loop is paused — no automatic scans.' }}</div></div>
                <div class="ctrl" style="gap:12px">
                  <label class="toggle">
                    <input type="checkbox" :checked="scanRunning" @change="toggleScan" :disabled="scanLoading" />
                    <span class="sw"></span>
                    <span class="tl">{{ scanRunning ? 'Running' : 'Paused' }}</span>
                  </label>
                  <button class="btn sm ghost" @click="runScanNow" :disabled="scanLoading">Run scan now</button>
                </div>
              </div>
            </div>
            <div class="group-foot">
              <span style="color:var(--muted); font-size:12px">Changes apply to the next cycle.</span>
              <button class="btn sm" @click="save" :disabled="saving">Save</button>
            </div>
          </section>

          <section class="group" id="threshold">
            <header class="group-head">
              <div>
                <div class="group-title">Notification threshold</div>
                <div class="group-sub">Minimum score required to send a Telegram notification.</div>
              </div>
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl"><div class="k">Minimum score to notify</div><div class="h">Higher = fewer, higher-quality signals.</div></div>
                <div class="ctrl slider-wrap">
                  <input type="range" min="0" max="10" step="0.1" :value="settings.NOTIFICATION_THRESHOLD || 5" @input="updateField('NOTIFICATION_THRESHOLD', Number(($event.target as HTMLInputElement).value))" />
                  <span class="v">{{ (settings.NOTIFICATION_THRESHOLD || 5).toFixed(1) }}</span>
                  <span class="h">/ 10</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Direction filter</div><div class="h">Only notify for these directions.</div></div>
                <div class="ctrl" style="gap:16px">
                  <label class="toggle">
                    <input type="checkbox" :checked="settings.NOTIFY_LONG !== false" @change="updateBoolField('NOTIFY_LONG', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Long</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" :checked="settings.NOTIFY_SHORT !== false" @change="updateBoolField('NOTIFY_SHORT', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Short</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" :checked="!!settings.NOTIFY_NEUTRAL" @change="updateBoolField('NOTIFY_NEUTRAL', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Neutral</span>
                  </label>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">C++ bypass AI gate</div><div class="h">When enabled, C++ engine signals always trigger a notification regardless of AI score.</div></div>
                <div class="ctrl">
                  <label class="toggle">
                    <input type="checkbox" :checked="!!settings.CPP_BYPASS_AI" @change="updateBoolField('CPP_BYPASS_AI', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Enabled</span>
                  </label>
                </div>
              </div>
            </div>
            <div class="group-foot">
              <span style="color:var(--muted); font-size:12px">Current threshold: {{ (settings.NOTIFICATION_THRESHOLD || 5).toFixed(1) }}</span>
              <button class="btn sm" @click="save" :disabled="saving">Save</button>
            </div>
          </section>

          <section class="group" id="browser">
            <header class="group-head">
              <div>
                <div class="group-title">Browser</div>
                <div class="group-sub">Headless Chrome capture settings.</div>
              </div>
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl"><div class="k">Headless mode</div><div class="h">Run the browser without a visible window.</div></div>
                <div class="ctrl">
                  <label class="toggle">
                    <input type="checkbox" :checked="!!settings.HEADLESS" @change="updateBoolField('HEADLESS', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Enabled</span>
                  </label>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Viewport</div><div class="h">Resolution used to render each chart.</div></div>
                <div class="ctrl">
                  <input type="number" class="mono" :value="settings.BROWSER_VIEWPORT_WIDTH" @input="updateField('BROWSER_VIEWPORT_WIDTH', Number(($event.target as HTMLInputElement).value))" min="320" max="7680" step="1" />
                  <span class="suf">&times;</span>
                  <input type="number" class="mono" :value="settings.BROWSER_VIEWPORT_HEIGHT" @input="updateField('BROWSER_VIEWPORT_HEIGHT', Number(($event.target as HTMLInputElement).value))" min="240" max="4320" step="1" />
                  <span class="suf">px</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Wait time after load</div><div class="h">Seconds to wait for the chart to fully render before capture.</div></div>
                <div class="ctrl">
                  <input type="number" class="mono" :value="settings.PLAYWRIGHT_WAIT_TIME" @input="updateField('PLAYWRIGHT_WAIT_TIME', Number(($event.target as HTMLInputElement).value))" min="0" max="30" step="0.5" />
                  <span class="suf">seconds</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Retry policy</div><div class="h">Retry failed captures with backoff.</div></div>
                <div class="ctrl">
                  <input type="number" class="mono" style="max-width:80px" :value="settings.BROWSER_RETRY_COUNT" @input="updateField('BROWSER_RETRY_COUNT', Number(($event.target as HTMLInputElement).value))" min="0" max="10" step="1" />
                  <span class="suf">retries</span>
                  <input type="number" class="mono" style="max-width:80px" :value="settings.BROWSER_RETRY_DELAY" @input="updateField('BROWSER_RETRY_DELAY', Number(($event.target as HTMLInputElement).value))" min="1" max="60" step="1" />
                  <span class="suf">delay (s)</span>
                </div>
              </div>
            </div>
            <div class="group-foot">
              <span style="color:var(--muted); font-size:12px">Browser capture settings</span>
              <button class="btn sm" @click="save" :disabled="saving">Save</button>
            </div>
          </section>

          <section class="group" id="ai">
            <header class="group-head">
              <div>
                <div class="group-title">AI provider</div>
                <div class="group-sub">Vision model and authentication.</div>
              </div>
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl"><div class="k">Model</div><div class="h">NVIDIA NIM vision model used for analysis.</div></div>
                <div class="ctrl">
                  <input type="text" class="mono" :value="settings.NVIDIA_MODEL" @input="updateField('NVIDIA_MODEL', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">API key</div><div class="h">Stored securely. Masked by default.</div></div>
                <div class="ctrl">
                  <input :type="showApiKey ? 'text' : 'password'" class="mono" :value="settings.NVIDIA_API_KEY" @input="updateField('NVIDIA_API_KEY', ($event.target as HTMLInputElement).value)" />
                  <button class="reveal" @click="toggleShow('apiKey')">{{ showApiKey ? 'Hide' : 'Show' }}</button>
                </div>
              </div>
            </div>
            <div class="group-foot">
              <span style="color:var(--muted); font-size:12px">AI vision model settings</span>
              <button class="btn sm" @click="save" :disabled="saving">Save</button>
            </div>
          </section>

          <section class="group" id="telegram">
            <header class="group-head">
              <div>
                <div class="group-title">Telegram</div>
                <div class="group-sub">Bot and target chat for signal delivery.</div>
              </div>
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl"><div class="k">Bot token</div><div class="h">From @BotFather. Masked by default.</div></div>
                <div class="ctrl">
                  <input :type="showToken ? 'text' : 'password'" class="mono" :value="settings.TELEGRAM_TOKEN" @input="updateField('TELEGRAM_TOKEN', ($event.target as HTMLInputElement).value)" />
                  <button class="reveal" @click="toggleShow('token')">{{ showToken ? 'Hide' : 'Show' }}</button>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Chat ID</div><div class="h">Numeric chat or channel ID to receive signals.</div></div>
                <div class="ctrl">
                  <input type="text" class="mono" :value="settings.TELEGRAM_CHAT_ID" @input="updateField('TELEGRAM_CHAT_ID', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Send screenshot</div><div class="h">Attach the chart image to each notification.</div></div>
                <div class="ctrl">
                  <label class="toggle">
                    <input type="checkbox" :checked="settings.TELEGRAM_SEND_SCREENSHOT !== false" @change="updateBoolField('TELEGRAM_SEND_SCREENSHOT', $event)" />
                    <span class="sw"></span>
                    <span class="tl">Attach PNG</span>
                  </label>
                </div>
              </div>
              <div class="field">
                <div class="lbl"><div class="k">Quiet hours</div><div class="h">Pause notifications during these hours (UTC).</div></div>
                <div class="ctrl">
                  <input type="text" class="mono" style="max-width:90px" placeholder="22:00" :value="settings.TELEGRAM_QUIET_START" @input="updateField('TELEGRAM_QUIET_START', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">to</span>
                  <input type="text" class="mono" style="max-width:90px" placeholder="06:00" :value="settings.TELEGRAM_QUIET_END" @input="updateField('TELEGRAM_QUIET_END', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
            </div>
            <div class="group-foot">
              <span style="color:var(--muted); font-size:12px">Telegram notification settings</span>
              <button class="btn sm" @click="save" :disabled="saving">Save</button>
            </div>
          </section>
        </div>
      </div>
    </div>
    <Toast :show="toast.show" :message="toast.message" @dismiss="toast.show = false" />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: end; justify-content: space-between; margin-bottom: 0; gap: 16px; }
.page-title { font-size: 22px; font-weight: 600; letter-spacing: -0.015em; }
.page-sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.loading { display: grid; place-items: center; padding: 80px 0; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--surface-3); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.settings-grid { display: grid; grid-template-columns: 220px 1fr; gap: 24px; }
.subnav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: sticky;
  top: 76px;
  align-self: start;
}
.subnav a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius);
  color: var(--fg-2);
  text-decoration: none;
  font-size: 13px;
  transition: background .12s, color .12s;
  cursor: pointer;
}
.subnav a:hover { background: var(--surface); color: var(--fg); }
.subnav a.active { background: var(--accent-soft); color: var(--fg); }
.subnav .ic { width: 14px; height: 14px; color: var(--muted); flex-shrink: 0; }
.subnav a.active .ic { color: var(--accent); }

.group {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
  overflow: hidden;
}
.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.group-title { font-size: 14px; font-weight: 600; letter-spacing: -0.005em; }
.group-sub { color: var(--muted); font-size: 12px; margin-top: 2px; }
.group-body { padding: 16px 18px; display: flex; flex-direction: column; gap: 14px; }
.group-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
}

.field { display: grid; grid-template-columns: 220px 1fr; gap: 16px; align-items: start; }
.field > .lbl { padding-top: 8px; }
.field > .lbl .k { font-size: 13px; font-weight: 500; }
.field > .lbl .h { font-size: 11px; color: var(--muted); margin-top: 2px; line-height: 1.5; }
.field > .ctrl { display: flex; align-items: center; gap: 8px; }
.field input[type="text"],
.field input[type="number"],
.field input[type="password"] {
  flex: 1;
  height: 36px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: var(--radius);
  padding: 0 12px;
  font: 13px var(--font-mono);
  font-variant-numeric: tabular-nums;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.field input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--ring); }
.field input.mono { font-family: var(--font-mono); }
.field input[type="number"] { max-width: 140px; }
.field .suf { color: var(--muted); font-size: 12px; font-family: var(--font-mono); }

.toggle { position: relative; display: inline-flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
.toggle input { display: none; }
.toggle .sw { width: 36px; height: 20px; background: var(--surface-3); border-radius: 999px; transition: background .15s; position: relative; }
.toggle .sw::after { content: ''; position: absolute; left: 2px; top: 2px; width: 16px; height: 16px; background: var(--fg); border-radius: 50%; transition: transform .15s; }
.toggle input:checked + .sw { background: var(--accent); }
.toggle input:checked + .sw::after { transform: translateX(16px); background: white; }
.toggle .tl { font-size: 12px; color: var(--fg-2); }
.toggle .ts { font-size: 12px; color: var(--muted); font-family: var(--font-mono); }

.slider-wrap { display: flex; align-items: center; gap: 10px; flex: 1; }
.slider-wrap input[type="range"] { flex: 1; accent-color: var(--accent); }
.slider-wrap .v { font-family: var(--font-mono); font-size: 14px; font-weight: 600; color: var(--accent-2); min-width: 36px; text-align: right; }
.slider-wrap .h { font-size: 11px; color: var(--muted); }

.reveal {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--fg-2);
  border-radius: var(--radius);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.reveal:hover { background: var(--surface-3); color: var(--fg); }
</style>
