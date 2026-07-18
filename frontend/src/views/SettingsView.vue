<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import { getSettings, updateSettings } from '@/api/settings'
import { getStatus, pauseScan, resumeScan, triggerScan } from '@/api/dashboard'
import { useToast } from '@/composables/useToast'
import type { Settings } from '@/types'

const toast = useToast()
const settings = ref<Settings>({})
const loading = ref(true)
const saving = ref<string | null>(null)
const scanRunning = ref(false)
const scanLoading = ref(false)
const activeSection = ref('timing')
const showToken = ref(false)
const showApiKey = ref(false)

const sections = [
  { id: 'timing', label: 'Scan timing', icon: 'clock' },
  { id: 'threshold', label: 'Threshold', icon: 'filter' },
  { id: 'browser', label: 'Browser', icon: 'image' },
  { id: 'ai', label: 'AI provider', icon: 'key' },
  { id: 'telegram', label: 'Telegram', icon: 'external' },
]

onMounted(async () => {
  try {
    settings.value = await getSettings()
    const status = await getStatus()
    scanRunning.value = status.running
  } catch { toast.err('Failed to load settings') }
  finally { loading.value = false }
})

async function toggleScan() {
  scanLoading.value = true
  try {
    if (scanRunning.value) { await pauseScan(); scanRunning.value = false; toast.ok('Scan loop paused') }
    else { await resumeScan(); scanRunning.value = true; toast.ok('Scan loop resumed') }
  } catch { toast.err('Failed to toggle scan') }
  finally { scanLoading.value = false }
}

async function runScanNow() {
  scanLoading.value = true
  try { await triggerScan(); toast.ok('Scan triggered') }
  catch { toast.err('Failed to trigger scan') }
  finally { scanLoading.value = false }
}

function setField<K extends keyof Settings>(key: K, value: Settings[K]) { settings.value[key] = value }
function setNum(key: string, v: string) { settings.value[key] = v === '' ? undefined : Number(v) }
function setBool(key: string, v: boolean) { settings.value[key] = v }

async function saveSection(id: string) {
  saving.value = id
  try {
    await updateSettings(settings.value)
    toast.ok(`${sections.find(s => s.id === id)?.label || 'Settings'} saved`)
  } catch { toast.err('Failed to save settings') }
  finally { saving.value = null }
}

function scrollTo(id: string) {
  activeSection.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <AppShell>
    <div class="pg">
      <header class="pg-head">
        <div>
          <h1 class="pg-title">Settings</h1>
          <div class="pg-sub">All system parameters &middot; changes apply on the next scan cycle</div>
        </div>
      </header>

      <AppLoading v-if="loading" label="Loading settings…" />

      <div v-else class="settings-grid">
        <!-- Sticky section nav -->
        <nav class="subnav">
          <a
            v-for="s in sections"
            :key="s.id"
            :class="{ active: activeSection === s.id }"
            @click="scrollTo(s.id)"
          >
            <AppIcon :name="s.icon" :size="14" />
            <span>{{ s.label }}</span>
          </a>
        </nav>

        <!-- Sections -->
        <div class="sections">
          <!-- Scan timing -->
          <section id="timing" class="card group">
            <header class="group-head">
              <div>
                <div class="group-title">Scan timing</div>
                <div class="group-sub">How often the loop runs and how long it waits between AI calls.</div>
              </div>
              <AppIcon name="clock" :size="16" class="group-ic" />
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl">
                  <div class="k">Check interval</div>
                  <div class="h">Seconds between full watchlist scans.</div>
                </div>
                <div class="ctrl">
                  <input
                    type="number" class="input mono sm" min="1" max="3600" step="1"
                    :value="settings.CHECK_INTERVAL_SECONDS"
                    @input="setNum('CHECK_INTERVAL_SECONDS', ($event.target as HTMLInputElement).value)"
                  />
                  <span class="suf">sec</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">AI call delay</div>
                  <div class="h">Pause between consecutive vision API calls (rate-limit safety).</div>
                </div>
                <div class="ctrl">
                  <input
                    type="number" class="input mono sm" min="0" max="30" step="0.5"
                    :value="settings.AI_CALL_DELAY"
                    @input="setNum('AI_CALL_DELAY', ($event.target as HTMLInputElement).value)"
                  />
                  <span class="suf">sec</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Scanning loop</div>
                  <div class="h">{{ scanRunning ? 'Loop is active — scanning on schedule.' : 'Loop is paused — no automatic scans.' }}</div>
                </div>
                <div class="ctrl row-gap">
                  <BaseToggle :model-value="scanRunning" @update:model-value="toggleScan" :disabled="scanLoading">
                    {{ scanRunning ? 'Running' : 'Paused' }}
                  </BaseToggle>
                  <BaseButton variant="ghost" size="sm" @click="runScanNow" :disabled="scanLoading">Run scan now</BaseButton>
                </div>
              </div>
            </div>
            <footer class="group-foot">
              <span class="foot-hint">Applies to the next cycle.</span>
              <BaseButton size="sm" @click="saveSection('timing')" :disabled="saving === 'timing'">
                <span v-if="saving === 'timing'" class="spinner sm"></span>
                {{ saving === 'timing' ? 'Saving…' : 'Save' }}
              </BaseButton>
            </footer>
          </section>

          <!-- Threshold -->
          <section id="threshold" class="card group">
            <header class="group-head">
              <div>
                <div class="group-title">Notification threshold</div>
                <div class="group-sub">Minimum score required to send a Telegram notification.</div>
              </div>
              <AppIcon name="filter" :size="16" class="group-ic" />
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl">
                  <div class="k">Minimum score</div>
                  <div class="h">Higher = fewer, higher-quality signals.</div>
                </div>
                <div class="ctrl slider-ctrl">
                  <input
                    type="range" min="0" max="10" step="0.1"
                    :value="settings.NOTIFICATION_THRESHOLD || 5"
                    @input="setNum('NOTIFICATION_THRESHOLD', ($event.target as HTMLInputElement).value)"
                  />
                  <span class="slider-v mono">{{ (settings.NOTIFICATION_THRESHOLD || 5).toFixed(1) }}</span>
                  <span class="suf">/ 10</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Direction filter</div>
                  <div class="h">Only notify for these directions.</div>
                </div>
                <div class="ctrl row-gap">
                  <BaseToggle :model-value="settings.NOTIFY_LONG !== false" @update:model-value="(v) => setBool('NOTIFY_LONG', v)">Long</BaseToggle>
                  <BaseToggle :model-value="settings.NOTIFY_SHORT !== false" @update:model-value="(v) => setBool('NOTIFY_SHORT', v)">Short</BaseToggle>
                  <BaseToggle :model-value="!!settings.NOTIFY_NEUTRAL" @update:model-value="(v) => setBool('NOTIFY_NEUTRAL', v)">Neutral</BaseToggle>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">C++ bypass AI gate</div>
                  <div class="h">C++ engine signals always notify regardless of AI score.</div>
                </div>
                <div class="ctrl">
                  <BaseToggle :model-value="!!settings.CPP_BYPASS_AI" @update:model-value="(v) => setBool('CPP_BYPASS_AI', v)">Enabled</BaseToggle>
                </div>
              </div>
            </div>
            <footer class="group-foot">
              <span class="foot-hint">Current threshold: <span class="mono">{{ (settings.NOTIFICATION_THRESHOLD || 5).toFixed(1) }}</span></span>
              <BaseButton size="sm" @click="saveSection('threshold')" :disabled="saving === 'threshold'">
                {{ saving === 'threshold' ? 'Saving…' : 'Save' }}
              </BaseButton>
            </footer>
          </section>

          <!-- Browser -->
          <section id="browser" class="card group">
            <header class="group-head">
              <div>
                <div class="group-title">Browser</div>
                <div class="group-sub">Headless Chrome capture settings.</div>
              </div>
              <AppIcon name="image" :size="16" class="group-ic" />
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl">
                  <div class="k">Headless mode</div>
                  <div class="h">Run the browser without a visible window.</div>
                </div>
                <div class="ctrl">
                  <BaseToggle :model-value="!!settings.HEADLESS" @update:model-value="(v) => setBool('HEADLESS', v)">Enabled</BaseToggle>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Viewport</div>
                  <div class="h">Resolution used to render each chart.</div>
                </div>
                <div class="ctrl">
                  <input type="number" class="input mono sm" min="320" max="7680" step="1"
                    :value="settings.BROWSER_VIEWPORT_WIDTH"
                    @input="setNum('BROWSER_VIEWPORT_WIDTH', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">×</span>
                  <input type="number" class="input mono sm" min="240" max="4320" step="1"
                    :value="settings.BROWSER_VIEWPORT_HEIGHT"
                    @input="setNum('BROWSER_VIEWPORT_HEIGHT', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">px</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Wait time after load</div>
                  <div class="h">Seconds to wait for the chart to fully render.</div>
                </div>
                <div class="ctrl">
                  <input type="number" class="input mono sm" min="0" max="30" step="0.5"
                    :value="settings.PLAYWRIGHT_WAIT_TIME"
                    @input="setNum('PLAYWRIGHT_WAIT_TIME', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">sec</span>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Retry policy</div>
                  <div class="h">Retry failed captures with backoff.</div>
                </div>
                <div class="ctrl">
                  <input type="number" class="input mono sm narrow" min="0" max="10" step="1"
                    :value="settings.BROWSER_RETRY_COUNT"
                    @input="setNum('BROWSER_RETRY_COUNT', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">retries</span>
                  <input type="number" class="input mono sm narrow" min="1" max="60" step="1"
                    :value="settings.BROWSER_RETRY_DELAY"
                    @input="setNum('BROWSER_RETRY_DELAY', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">delay</span>
                </div>
              </div>
            </div>
            <footer class="group-foot">
              <span class="foot-hint">Browser capture settings</span>
              <BaseButton size="sm" @click="saveSection('browser')" :disabled="saving === 'browser'">
                {{ saving === 'browser' ? 'Saving…' : 'Save' }}
              </BaseButton>
            </footer>
          </section>

          <!-- AI provider -->
          <section id="ai" class="card group">
            <header class="group-head">
              <div>
                <div class="group-title">AI provider</div>
                <div class="group-sub">Vision model and authentication.</div>
              </div>
              <AppIcon name="key" :size="16" class="group-ic" />
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl">
                  <div class="k">Model</div>
                  <div class="h">NVIDIA NIM vision model used for analysis.</div>
                </div>
                <div class="ctrl">
                  <input type="text" class="input mono"
                    :value="settings.NVIDIA_MODEL"
                    @input="setField('NVIDIA_MODEL', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">API key</div>
                  <div class="h">Stored securely. Masked by default.</div>
                </div>
                <div class="ctrl">
                  <input :type="showApiKey ? 'text' : 'password'" class="input mono"
                    :value="settings.NVIDIA_API_KEY"
                    @input="setField('NVIDIA_API_KEY', ($event.target as HTMLInputElement).value)" />
                  <button type="button" class="reveal" @click="showApiKey = !showApiKey">
                    <AppIcon :name="showApiKey ? 'eyeOff' : 'eye'" :size="12" />
                    {{ showApiKey ? 'Hide' : 'Show' }}
                  </button>
                </div>
              </div>
            </div>
            <footer class="group-foot">
              <span class="foot-hint">AI vision model settings</span>
              <BaseButton size="sm" @click="saveSection('ai')" :disabled="saving === 'ai'">
                {{ saving === 'ai' ? 'Saving…' : 'Save' }}
              </BaseButton>
            </footer>
          </section>

          <!-- Telegram -->
          <section id="telegram" class="card group">
            <header class="group-head">
              <div>
                <div class="group-title">Telegram</div>
                <div class="group-sub">Bot and target chat for signal delivery.</div>
              </div>
              <AppIcon name="external" :size="16" class="group-ic" />
            </header>
            <div class="group-body">
              <div class="field">
                <div class="lbl">
                  <div class="k">Bot token</div>
                  <div class="h">From @BotFather. Masked by default.</div>
                </div>
                <div class="ctrl">
                  <input :type="showToken ? 'text' : 'password'" class="input mono"
                    :value="settings.TELEGRAM_TOKEN"
                    @input="setField('TELEGRAM_TOKEN', ($event.target as HTMLInputElement).value)" />
                  <button type="button" class="reveal" @click="showToken = !showToken">
                    <AppIcon :name="showToken ? 'eyeOff' : 'eye'" :size="12" />
                    {{ showToken ? 'Hide' : 'Show' }}
                  </button>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Chat ID</div>
                  <div class="h">Numeric chat or channel ID to receive signals.</div>
                </div>
                <div class="ctrl">
                  <input type="text" class="input mono"
                    :value="settings.TELEGRAM_CHAT_ID"
                    @input="setField('TELEGRAM_CHAT_ID', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Send screenshot</div>
                  <div class="h">Attach the chart image to each notification.</div>
                </div>
                <div class="ctrl">
                  <BaseToggle :model-value="settings.TELEGRAM_SEND_SCREENSHOT !== false" @update:model-value="(v) => setBool('TELEGRAM_SEND_SCREENSHOT', v)">Attach PNG</BaseToggle>
                </div>
              </div>
              <div class="field">
                <div class="lbl">
                  <div class="k">Quiet hours</div>
                  <div class="h">Pause notifications during these hours (UTC).</div>
                </div>
                <div class="ctrl">
                  <input type="text" class="input mono narrow" placeholder="22:00"
                    :value="settings.TELEGRAM_QUIET_START"
                    @input="setField('TELEGRAM_QUIET_START', ($event.target as HTMLInputElement).value)" />
                  <span class="suf">to</span>
                  <input type="text" class="input mono narrow" placeholder="06:00"
                    :value="settings.TELEGRAM_QUIET_END"
                    @input="setField('TELEGRAM_QUIET_END', ($event.target as HTMLInputElement).value)" />
                </div>
              </div>
            </div>
            <footer class="group-foot">
              <span class="foot-hint">Telegram notification settings</span>
              <BaseButton size="sm" @click="saveSection('telegram')" :disabled="saving === 'telegram'">
                {{ saving === 'telegram' ? 'Saving…' : 'Save' }}
              </BaseButton>
            </footer>
          </section>
        </div>
      </div>
    </div>
    <AppToast />
  </AppShell>
</template>

<style scoped>
.pg { display: flex; flex-direction: column; gap: 18px; max-width: 1400px; }
.pg-head { display: flex; align-items: flex-end; gap: 12px; }
.pg-title { font: 600 18px var(--font-sans); letter-spacing: -0.015em; }
.pg-sub { font: 400 12px var(--font-mono); color: var(--muted); margin-top: 3px; }

.settings-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 22px;
  align-items: start;
}

/* Subnav */
.subnav {
  position: sticky;
  top: 70px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 6px;
}
.subnav a {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--radius);
  color: var(--fg-2);
  font: 500 12.5px var(--font-sans);
  cursor: pointer;
  transition: background .12s, color .12s;
  white-space: nowrap;
}
.subnav a:hover { background: var(--surface-2); color: var(--fg); }
.subnav a.active { background: var(--accent-soft); color: var(--accent); }
.subnav a.active svg { color: var(--accent); }

/* Group */
.group { margin-bottom: 14px; overflow: hidden; padding: 0; }
.group:last-child { margin-bottom: 0; }
.group-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.group-title { font: 600 13.5px var(--font-sans); letter-spacing: -0.005em; color: var(--fg); }
.group-sub { font: 400 11.5px var(--font-sans); color: var(--muted); margin-top: 3px; line-height: 1.5; max-width: 480px; }
.group-ic { color: var(--muted); flex-shrink: 0; margin-top: 2px; }

.group-body { padding: 14px 18px; display: flex; flex-direction: column; gap: 13px; }

.field {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 18px;
  align-items: start;
}
.lbl { padding-top: 6px; }
.lbl .k { font: 500 12.5px var(--font-sans); color: var(--fg); }
.lbl .h { font: 400 11px var(--font-sans); color: var(--muted); margin-top: 2px; line-height: 1.45; }

.ctrl { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.row-gap { gap: 14px; }
.input.sm { height: 30px; max-width: 140px; }
.input.narrow { max-width: 90px; }
.suf { font: 500 11.5px var(--font-mono); color: var(--muted); }

.slider-ctrl { gap: 10px; }
.slider-ctrl input[type="range"] { flex: 1; max-width: 220px; }
.slider-v { font: 600 14px var(--font-mono); color: var(--accent-2); min-width: 32px; text-align: right; }

.reveal {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
  height: 32px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--fg-2);
  border-radius: var(--radius);
  font: 500 11.5px var(--font-sans);
  cursor: pointer;
  white-space: nowrap;
}
.reveal:hover { background: var(--surface-3); color: var(--fg); }

.group-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-top: 1px solid var(--border);
  background: var(--bg-2);
}
.foot-hint { font: 400 11.5px var(--font-sans); color: var(--muted); }
.foot-hint .mono { color: var(--fg-2); }

.spinner.sm {
  width: 13px; height: 13px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}

@media (max-width: 860px) {
  .settings-grid { grid-template-columns: 1fr; }
  .subnav {
    position: static;
    flex-direction: row;
    overflow-x: auto;
    padding: 4px;
  }
  .subnav a { flex-shrink: 0; }
  .field { grid-template-columns: 1fr; gap: 6px; }
  .lbl { padding-top: 0; }
}
</style>
