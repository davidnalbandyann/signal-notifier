<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('admin')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = 'Invalid credentials. Try admin / admin123'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="login-box">
      <div class="brand">
        <div class="logo">T</div>
        <h1>Trading Chart AI Monitor</h1>
        <p>Sign in to access the control panel</p>
      </div>
      <form @submit.prevent="submit" class="form">
        <div class="field">
          <label class="label">Username</label>
          <input v-model="username" class="input" type="text" autocomplete="username" required />
        </div>
        <div class="field">
          <label class="label">Password</label>
          <input v-model="password" class="input" type="password" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="err">{{ error }}</p>
        <button class="btn primary full lg" type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}
.login-box {
  width: 360px;
  max-width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px 28px;
}
.brand {
  text-align: center;
  margin-bottom: 24px;
}
.logo {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--accent), oklch(48% 0.20 280));
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: white;
  font-weight: 700;
  font-size: 16px;
  margin: 0 auto 12px;
}
.brand h1 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 4px;
}
.brand p {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-2);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: var(--font-mono);
}
.input {
  height: 40px;
  padding: 0 12px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--fg);
  font-size: 14px;
  font-family: var(--font-sans);
  transition: border-color .12s;
}
.input:focus {
  outline: none;
  border-color: var(--accent);
}
.err {
  color: var(--red);
  font-size: 13px;
  margin: 0;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 36px;
  padding: 0 14px;
  background: var(--accent);
  color: var(--accent-fg);
  border: 0;
  border-radius: var(--radius);
  font: 600 13px var(--font-sans);
  cursor: pointer;
  transition: background .12s;
}
.btn:hover { background: var(--accent-2); }
.btn.lg { height: 44px; font-size: 14px; }
.btn.full { width: 100%; }
</style>
