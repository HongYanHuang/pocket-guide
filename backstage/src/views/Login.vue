<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-section">
        <h1>Pocket Guide</h1>
        <p class="subtitle">Backstage Admin Panel</p>
      </div>

      <div class="login-content">
        <p class="welcome-text">Sign in to manage POIs, tours, and content</p>

        <el-button
          type="primary"
          size="large"
          @click="handleLogin"
          :loading="loading"
          :disabled="loading"
          class="google-login-btn"
        >
          <svg v-if="!loading" class="google-icon" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          <span>Sign in with Google</span>
        </el-button>

        <p class="info-text">
          Only authorized Google accounts can access this panel
        </p>

        <el-alert
          v-if="error"
          type="error"
          :closable="false"
          show-icon
          class="error-alert"
        >
          {{ error }}
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../auth/useAuth'
import { ElMessage } from 'element-plus'

const { login } = useAuth()
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    await login()
  } catch (err) {
    console.error('Login error:', err)
    error.value = err.message || 'Failed to start login process. Please try again.'
    loading.value = false
    ElMessage.error('Login failed: ' + error.value)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  padding: 48px 40px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 440px;
  width: 100%;
  text-align: center;
}

.logo-section {
  margin-bottom: 32px;
}

.logo-section h1 {
  font-size: 32px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
  font-weight: 500;
}

.login-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-text {
  font-size: 15px;
  color: #555;
  margin: 0;
  line-height: 1.5;
}

.google-login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.google-login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 126, 234, 0.4);
}

.google-icon {
  width: 20px;
  height: 20px;
}

.info-text {
  font-size: 13px;
  color: #888;
  margin: 0;
  line-height: 1.5;
}

.error-alert {
  margin-top: 8px;
}

@media (max-width: 480px) {
  .login-card {
    padding: 36px 24px;
  }

  .logo-section h1 {
    font-size: 28px;
  }

  .google-login-btn {
    height: 44px;
    font-size: 15px;
  }
}
</style>
