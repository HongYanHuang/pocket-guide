/**
 * Token Manager
 *
 * Manages access and refresh tokens using browser storage:
 * - Access token: sessionStorage (cleared when tab closes) - 15 min lifetime
 * - Refresh token: localStorage (persists) - 7 day lifetime
 */

export default {
  /**
   * Get access token from sessionStorage
   */
  getAccessToken() {
    return sessionStorage.getItem('access_token')
  },

  /**
   * Store access token in sessionStorage
   */
  setAccessToken(token) {
    sessionStorage.setItem('access_token', token)
  },

  /**
   * Get refresh token from localStorage
   */
  getRefreshToken() {
    return localStorage.getItem('refresh_token')
  },

  /**
   * Store refresh token in localStorage
   */
  setRefreshToken(token) {
    localStorage.setItem('refresh_token', token)
  },

  /**
   * Store both tokens
   */
  setTokens(accessToken, refreshToken) {
    this.setAccessToken(accessToken)
    this.setRefreshToken(refreshToken)
  },

  /**
   * Clear all tokens (logout)
   */
  clearTokens() {
    sessionStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  /**
   * Check if user has tokens
   */
  hasTokens() {
    return !!(this.getAccessToken() || this.getRefreshToken())
  }
}
