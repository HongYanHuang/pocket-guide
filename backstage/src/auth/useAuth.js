/**
 * useAuth Composable
 *
 * Vue 3 Composition API hook for authentication state management
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import authService from './authService'
import tokenManager from './tokenManager'

// Shared state across all components
const isAuthenticated = ref(false)
const user = ref(null)
const loading = ref(true)
let refreshInterval = null

export function useAuth() {
  const router = useRouter()

  /**
   * Check if user is authenticated
   * Tries to refresh access token if expired
   */
  const checkAuth = async () => {
    console.log('🟡 checkAuth() called')
    loading.value = true
    try {
      const accessToken = tokenManager.getAccessToken()
      console.log('🟡 Access token:', accessToken ? 'EXISTS' : 'MISSING')

      if (!accessToken) {
        // No access token, try refreshing
        console.log('🟡 No access token, trying to refresh...')
        const refreshed = await refreshAccessToken()
        if (!refreshed) {
          console.log('🟡 Refresh failed, calling logout()')
          logout()
          return false
        }
      }

      // Get user info
      const currentAccessToken = tokenManager.getAccessToken()
      console.log('🟡 Getting user info...')
      const userInfo = await authService.getCurrentUser(currentAccessToken)
      user.value = userInfo
      isAuthenticated.value = true
      startTokenRefresh()
      console.log('🟡 checkAuth SUCCESS, user:', userInfo.email)
      return true
    } catch (error) {
      console.error('🔴 Auth check failed:', error)
      console.log('🔴 Calling logout() due to error')
      logout()
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Start login flow - redirects to Google OAuth
   */
  const login = async () => {
    try {
      // Generate PKCE code verifier and challenge
      const codeVerifier = generateCodeVerifier()
      const codeChallenge = await generateCodeChallenge(codeVerifier)

      // Store code verifier for callback
      sessionStorage.setItem('pkce_code_verifier', codeVerifier)

      // Get Google OAuth URL
      const redirectUri = `${window.location.origin}/auth/callback`
      const { auth_url } = await authService.getGoogleAuthUrl(redirectUri, codeChallenge)

      // Redirect to Google
      window.location.href = auth_url
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  /**
   * Handle OAuth callback
   * @param {string} code - Authorization code from Google
   * @param {string} state - State parameter
   */
  const handleCallback = async (code, state) => {
    console.log('🟢 handleCallback called with code:', code ? 'EXISTS' : 'MISSING')
    console.log('🟢 handleCallback called with state:', state ? 'EXISTS' : 'MISSING')

    try {
      // Get stored code verifier
      const codeVerifier = sessionStorage.getItem('pkce_code_verifier')
      console.log('🟢 Code verifier from storage:', codeVerifier ? 'EXISTS' : 'MISSING')

      if (!codeVerifier) {
        throw new Error('Missing PKCE code verifier')
      }

      // Exchange code for tokens
      console.log('🟢 Calling backend /auth/google/callback...')
      const tokens = await authService.exchangeCodeForTokens(code, state, codeVerifier)
      console.log('🟢 Got tokens from backend:', tokens ? 'YES' : 'NO')

      tokenManager.setTokens(tokens.access_token, tokens.refresh_token)
      console.log('🟢 Tokens stored in storage')

      // Clean up
      sessionStorage.removeItem('pkce_code_verifier')

      // Get user info
      console.log('🟢 Calling checkAuth...')
      await checkAuth()
      console.log('🟢 checkAuth completed')

      // Redirect to home
      console.log('🟢 Redirecting to /')
      router.push('/')
    } catch (error) {
      console.error('🔴 OAuth callback failed:', error)
      console.error('🔴 Error message:', error.message)
      throw error
    }
  }

  /**
   * Logout - clear tokens and redirect to login
   */
  const logout = async () => {
    console.log('🔴 logout() CALLED')
    console.trace('🔴 logout() call stack')
    try {
      const refreshToken = tokenManager.getRefreshToken()
      const accessToken = tokenManager.getAccessToken()

      if (refreshToken && accessToken) {
        await authService.logout(refreshToken, accessToken)
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      tokenManager.clearTokens()
      isAuthenticated.value = false
      user.value = null
      stopTokenRefresh()
      console.log('🔴 logout() redirecting to /login')
      router.push('/login')
    }
  }

  /**
   * Refresh access token using refresh token
   */
  const refreshAccessToken = async () => {
    try {
      const refreshToken = tokenManager.getRefreshToken()
      if (!refreshToken) {
        return false
      }

      const tokens = await authService.refreshToken(refreshToken)
      tokenManager.setAccessToken(tokens.access_token)
      return true
    } catch (error) {
      console.error('Token refresh failed:', error)
      return false
    }
  }

  /**
   * Start automatic token refresh (every 10 minutes)
   */
  const startTokenRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }

    // Refresh every 10 minutes (access token expires in 15 min)
    refreshInterval = setInterval(async () => {
      const success = await refreshAccessToken()
      if (!success) {
        console.warn('Auto-refresh failed, logging out')
        logout()
      }
    }, 10 * 60 * 1000) // 10 minutes
  }

  /**
   * Stop automatic token refresh
   */
  const stopTokenRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  return {
    // State
    isAuthenticated: computed(() => isAuthenticated.value),
    user: computed(() => user.value),
    loading: computed(() => loading.value),

    // Methods
    login,
    logout,
    checkAuth,
    handleCallback,
    refreshAccessToken
  }
}

// ==== PKCE Helper Functions ====

/**
 * Generate random code verifier for PKCE
 */
function generateCodeVerifier() {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  return base64UrlEncode(array)
}

/**
 * Generate code challenge from verifier (SHA-256)
 */
async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder()
  const data = encoder.encode(verifier)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return base64UrlEncode(new Uint8Array(hash))
}

/**
 * Base64 URL encode (without padding)
 */
function base64UrlEncode(array) {
  return btoa(String.fromCharCode.apply(null, array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}
