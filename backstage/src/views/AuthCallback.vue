<template>
  <div class="callback-container" style="background: red;">
    <h1 style="color: white; font-size: 48px;">CALLBACK PAGE LOADED!</h1>
    <div class="callback-card">
      <el-icon :size="64" class="loading-icon">
        <Loading />
      </el-icon>

      <h2>{{ status }}</h2>

      <p v-if="!error" class="info-text">
        Please wait while we complete your sign-in...
      </p>

      <el-alert
        v-if="error"
        type="error"
        :closable="false"
        show-icon
        class="error-alert"
      >
        <template #title>Authentication Failed</template>
        {{ error }}
      </el-alert>

      <el-button
        v-if="error"
        type="primary"
        @click="goToLogin"
        class="retry-btn"
      >
        Back to Login
      </el-button>
    </div>
  </div>
</template>

<script setup>
console.log('🟣 AuthCallback.vue script LOADED')

import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../auth/useAuth'
import { Loading } from '@element-plus/icons-vue'

console.log('🟣 AuthCallback.vue imports completed')

const route = useRoute()
const router = useRouter()
const { handleCallback } = useAuth()

const status = ref('Completing sign-in...')
const error = ref('')

console.log('🟣 AuthCallback.vue setup running, route.path:', route.path)

onMounted(async () => {
  console.log('🔵 AuthCallback component mounted')
  console.log('🔵 Route query params:', route.query)

  try {
    // Get code and state from URL params
    const { code, state, error: oauthError } = route.query

    console.log('🔵 Code:', code ? 'EXISTS' : 'MISSING')
    console.log('🔵 State:', state ? 'EXISTS' : 'MISSING')

    if (oauthError) {
      throw new Error(`OAuth error: ${oauthError}`)
    }

    if (!code || !state) {
      throw new Error('Missing authorization code or state parameter')
    }

    // Handle OAuth callback
    console.log('🔵 Calling handleCallback...')
    status.value = 'Verifying credentials...'
    await handleCallback(code, state)

    console.log('🔵 handleCallback completed successfully')
    status.value = 'Success! Redirecting...'
    // Router push is handled in useAuth.handleCallback
  } catch (err) {
    console.error('🔴 OAuth callback error:', err)
    console.error('🔴 Error details:', err.message, err.stack)
    error.value = err.message || 'An unexpected error occurred'
    status.value = 'Sign-in failed'
  }
})

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.callback-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.callback-card {
  background: white;
  padding: 48px 40px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 440px;
  width: 100%;
  text-align: center;
}

.loading-icon {
  color: #667eea;
  margin-bottom: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

h2 {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px 0;
}

.info-text {
  font-size: 15px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.error-alert {
  margin-top: 24px;
  text-align: left;
}

.retry-btn {
  margin-top: 24px;
}

@media (max-width: 480px) {
  .callback-card {
    padding: 36px 24px;
  }

  h2 {
    font-size: 20px;
  }
}
</style>
