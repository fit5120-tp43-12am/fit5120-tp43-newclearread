<script setup>
import { computed, ref } from 'vue'

const VALID_USERNAME = 'tp43_goodjob'
const VALID_PASSWORD = 'tp43_clearead'

const isAuthenticated = ref(false)
const username = ref('')
const password = ref('')
const isPasswordVisible = ref(false)
const errorMessage = ref('')

const canSubmit = computed(() => username.value.trim() && password.value)

function handleLogin() {
  if (
    username.value.trim() === VALID_USERNAME &&
    password.value === VALID_PASSWORD
  ) {
    isAuthenticated.value = true
    errorMessage.value = ''
    return
  }

  errorMessage.value = 'Incorrect username or password.'
  password.value = ''
}
</script>

<template>
  <RouterView v-if="isAuthenticated" />

  <div v-else class="auth-gate">
    <div class="auth-gate__blob auth-gate__blob--blue"></div>
    <div class="auth-gate__blob auth-gate__blob--peach"></div>

    <section class="auth-card">
      <div class="auth-brand">
        <div class="auth-brand__logo" aria-hidden="true">
          <svg width="30" height="30" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
            <rect x="9" y="10" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="13" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="16" width="2" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
          </svg>
        </div>
        <p class="auth-brand__eyebrow">Protected Course Demo</p>
        <h1 class="auth-brand__title">Welcome to Clearead</h1>
        <p class="auth-brand__copy">
          This project is protected for coursework review. Enter the assigned username and password to continue.
        </p>
      </div>

      <form class="auth-form" @submit.prevent="handleLogin">
        <label class="auth-field">
          <span class="auth-field__label">Username</span>
          <input
            v-model="username"
            class="auth-field__input"
            type="text"
            autocomplete="username"
            placeholder="Enter username"
          />
        </label>

        <label class="auth-field">
          <span class="auth-field__label">Password</span>
          <div class="auth-password">
            <input
              v-model="password"
              class="auth-field__input auth-password__input"
              :type="isPasswordVisible ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="Enter password"
            />
            <button
              class="auth-password__toggle"
              type="button"
              :aria-label="isPasswordVisible ? 'Hide password' : 'Show password'"
              @click="isPasswordVisible = !isPasswordVisible"
            >
              <svg v-if="isPasswordVisible" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M2 12C3.7 8.4 7.4 6 12 6C16.6 6 20.3 8.4 22 12C20.3 15.6 16.6 18 12 18C7.4 18 3.7 15.6 2 12Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M2 12C3.7 8.4 7.4 6 12 6C16.6 6 20.3 8.4 22 12C20.3 15.6 16.6 18 12 18C7.4 18 3.7 15.6 2 12Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8"/>
                <path d="M4 4L20 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </label>

        <p v-if="errorMessage" class="auth-form__error">{{ errorMessage }}</p>

        <button class="auth-form__submit" type="submit" :disabled="!canSubmit">
          Enter Site
        </button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.auth-gate {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  overflow: hidden;
  background:
    radial-gradient(ellipse 55% 80% at 15% 55%, rgba(147, 167, 255, 0.45) 0%, transparent 65%),
    radial-gradient(ellipse 45% 65% at 85% 40%, rgba(255, 200, 150, 0.4) 0%, transparent 60%),
    radial-gradient(ellipse 30% 40% at 50% 80%, rgba(255, 220, 180, 0.25) 0%, transparent 55%),
    #f8f9ff;
}

.auth-gate__blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.auth-gate__blob--blue {
  width: 520px;
  height: 520px;
  top: -80px;
  left: -70px;
  background: rgba(99, 120, 255, 0.18);
}

.auth-gate__blob--peach {
  width: 420px;
  height: 420px;
  right: -70px;
  bottom: -80px;
  background: rgba(255, 165, 100, 0.15);
}

.auth-card {
  position: relative;
  z-index: 1;
  width: min(100%, 520px);
  padding: 36px;
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 18px 60px rgba(15, 23, 42, 0.12);
}

.auth-brand {
  margin-bottom: 28px;
}

.auth-brand__logo {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.14);
}

.auth-brand__eyebrow {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #2563eb;
}

.auth-brand__title {
  margin-bottom: 12px;
  font-size: clamp(32px, 6vw, 42px);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.05;
}

.auth-brand__copy {
  color: #4b5563;
  font-size: 15px;
  line-height: 1.7;
}

.auth-form {
  display: grid;
  gap: 16px;
}

.auth-field {
  display: grid;
  gap: 8px;
}

.auth-field__label {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.auth-field__input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  color: #0d1117;
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.auth-field__input:focus {
  border-color: rgba(37, 99, 235, 0.6);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
  background: #fff;
  outline: none;
}

.auth-field__input::placeholder {
  color: #9ca3af;
}

.auth-password {
  position: relative;
}

.auth-password__input {
  padding-right: 52px;
}

.auth-password__toggle {
  position: absolute;
  top: 50%;
  right: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 999px;
  background: transparent;
  color: #6b7280;
  transform: translateY(-50%);
  transition: background 0.2s, color 0.2s;
}

.auth-password__toggle:hover {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.auth-form__error {
  padding: 12px 14px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 14px;
  background: rgba(254, 242, 242, 0.95);
  color: #b91c1c;
  font-size: 14px;
}

.auth-form__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  margin-top: 4px;
  padding: 14px 20px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 10px 26px rgba(37, 99, 235, 0.28);
  transition: transform 0.15s, box-shadow 0.2s, background 0.2s;
}

.auth-form__submit:hover:enabled {
  transform: translateY(-2px);
  background: #1d4ed8;
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.34);
}

.auth-form__submit:disabled {
  cursor: not-allowed;
  background: #93c5fd;
  box-shadow: none;
}

@media (max-width: 640px) {
  .auth-card {
    padding: 28px 22px;
    border-radius: 24px;
  }

  .auth-brand__title {
    font-size: 30px;
  }
}
</style>
