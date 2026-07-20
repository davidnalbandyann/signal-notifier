<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const username = ref('admin')
const password = ref('')
const showPass = ref(false)
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    toast.ok('Signed in')
    router.push('/')
  } catch {
    error.value = 'Invalid credentials. Try admin / admin123'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="orbital-bg"></div>
    <div class="login-inner">
      <div class="brand-row">
        <div class="brand-mark">TC</div>
        <div class="brand-text">
          <div class="brand-name">Trading Chart AI Monitor</div>
          <div class="brand-sub">Vision-driven signal desk</div>
        </div>
      </div>

      <form @submit.prevent="submit" class="card">
        <div class="card-head">
          <div class="card-title">Sign in</div>
          <div class="card-sub">Access the control panel</div>
        </div>

        <div class="field">
          <label class="field-label" for="lu">Username</label>
          <input
            id="lu"
            v-model="username"
            class="input input-lg mono"
            type="text"
            autocomplete="username"
            required
            spellcheck="false"
          />
        </div>

        <div class="field">
          <label class="field-label" for="lp">Password</label>
          <div class="pass-wrap">
            <input
              id="lp"
              v-model="password"
              :type="showPass ? 'text' : 'password'"
              class="input input-lg mono"
              autocomplete="current-password"
              required
              placeholder="••••••••"
            />
            <button
              type="button"
              class="pass-toggle"
              @click="showPass = !showPass"
              :aria-label="showPass ? 'Hide password' : 'Show password'"
              tabindex="-1"
            >
              <AppIcon :name="showPass ? 'eyeOff' : 'eye'" :size="15" />
            </button>
          </div>
        </div>

        <div v-if="error" class="error">
          <AppIcon name="alert" :size="13" :stroke="2" />
          <span>{{ error }}</span>
        </div>

        <button class="btn primary lg full submit" type="submit" :disabled="loading">
          <AppIcon v-if="!loading" name="arrowRight" :size="15" :stroke="2.5" />
          <span v-if="loading" class="spinner sm"></span>
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>

        <div class="hint">
          <AppIcon name="info" :size="12" :stroke="2" />
          <span>Default: <span class="mono">admin / admin123</span></span>
        </div>
      </form>

      <div class="footnote">
        TradingView &middot; NVIDIA MiniMax-M3 &middot; Telegram delivery
      </div>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse at top, oklch(20% 0.05 264 / 0.5), transparent 60%),
    var(--bg);
  position: relative;
  overflow: hidden;
}
[data-theme="light"] .login {
  background:
    radial-gradient(ellipse at top, oklch(94% 0.03 264 / 0.6), transparent 60%),
    var(--bg);
}

.orbital-bg {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, oklch(64% 0.19 263 / 0.06), transparent 70%);
  top: -200px;
  right: -200px;
  pointer-events: none;
  animation: orbital-float 8s ease-in-out infinite alternate;
}
[data-theme="light"] .orbital-bg {
  background: radial-gradient(circle, oklch(50% 0.21 263 / 0.04), transparent 70%);
}
@keyframes orbital-float {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(-40px, 30px) scale(1.1); }
}

.login-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
  animation: login-in 0.6s var(--ease-out);
}
@keyframes login-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  width: 40px;
  height: 40px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 10px;
  display: grid;
  place-items: center;
  font: 700 14px var(--font-mono);
  letter-spacing: 0.04em;
  box-shadow: 0 8px 24px oklch(64% 0.19 263 / 0.3);
}
.brand-name { font: 600 15px var(--font-sans); letter-spacing: -0.01em; color: var(--fg); }
.brand-sub { font: 500 11px var(--font-mono); color: var(--muted); letter-spacing: 0.05em; margin-top: 2px; }

.card {
  width: 380px;
  max-width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 22px 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 24px 60px oklch(0% 0 0 / 0.4);
  animation: card-in 0.5s var(--ease-out) 0.15s both;
}
@keyframes card-in {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.card-head { display: flex; flex-direction: column; gap: 3px; }
.card-title { font: 600 16px var(--font-sans); letter-spacing: -0.01em; }
.card-sub { font: 400 12.5px var(--font-sans); color: var(--muted); }

.field { display: flex; flex-direction: column; gap: 6px; }
.pass-wrap { position: relative; }
.pass-wrap .input { padding-right: 38px; }
.pass-toggle {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  display: grid;
  place-items: center;
  border-radius: 4px;
  transition: color var(--speed-fast), background var(--speed-fast);
}
.pass-toggle:hover { color: var(--fg-2); background: var(--surface-2); }

.error {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 12px;
  background: var(--red-soft);
  border: 1px solid oklch(70% 0.20 25 / 0.3);
  border-radius: var(--radius);
  color: var(--red);
  font: 500 12.5px var(--font-sans);
  animation: shake 0.3s var(--ease);
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

.submit { margin-top: 2px; }
.submit .spinner.sm {
  width: 14px; height: 14px;
  border: 2px solid oklch(99% 0.003 250 / 0.3);
  border-top-color: var(--accent-fg);
}

.hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font: 400 11.5px var(--font-sans);
  color: var(--muted);
}
.hint .mono { color: var(--fg-2); }

.footnote {
  font: 500 10.5px var(--font-mono);
  color: var(--muted-2);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  animation: card-in 0.5s var(--ease-out) 0.3s both;
}

@media (max-width: 480px) {
  .login { padding: 16px; justify-content: flex-start; padding-top: 60px; }
  .card { box-shadow: none; }
}
</style>