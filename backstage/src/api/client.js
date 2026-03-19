/**
 * Centralized API Client with Authentication
 *
 * Provides a configured axios instance with:
 * - Automatic Authorization header injection
 * - Token refresh on 401 errors
 * - Response/error interceptors
 */

import axios from 'axios'
import tokenManager from '../auth/tokenManager'
import authService from '../auth/authService'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Track token refresh state
let isRefreshing = false
let refreshSubscribers = []

/**
 * Subscribe to token refresh completion
 */
function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback)
}

/**
 * Notify all subscribers when token is refreshed
 */
function onTokenRefreshed(token) {
  refreshSubscribers.forEach(callback => callback(token))
  refreshSubscribers = []
}

// Request interceptor - Add Authorization header
apiClient.interceptors.request.use(
  config => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle token refresh on 401
apiClient.interceptors.response.use(
  response => response.data,
  async error => {
    const originalRequest = error.config

    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Token refresh already in progress, queue this request
        return new Promise(resolve => {
          subscribeTokenRefresh(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(apiClient(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = tokenManager.getRefreshToken()
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        // Refresh the access token
        const tokens = await authService.refreshToken(refreshToken)
        tokenManager.setAccessToken(tokens.access_token)

        // Update Authorization header and retry original request
        originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`

        // Notify all queued requests
        onTokenRefreshed(tokens.access_token)

        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed - clear tokens and redirect to login
        console.error('Token refresh failed:', refreshError)
        tokenManager.clearTokens()
        window.location.href = '/login'
        throw refreshError
      } finally {
        isRefreshing = false
      }
    }

    // Extract error message
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export default apiClient
