/**
 * Authentication Service
 *
 * Handles API calls to backend auth endpoints
 */

import axios from 'axios'

const authApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000
})

export default {
  /**
   * Get Google OAuth authorization URL
   * @param {string} redirectUri - Frontend redirect URI (e.g., http://localhost:5173/auth/callback)
   * @param {string} codeChallenge - PKCE code challenge
   * @returns {Promise<{auth_url: string, state: string}>}
   */
  async getGoogleAuthUrl(redirectUri, codeChallenge) {
    const { data } = await authApi.get('/auth/google/login', {
      params: {
        redirect_uri: redirectUri,
        code_challenge: codeChallenge
      }
    })
    return data
  },

  /**
   * Exchange authorization code for tokens
   * @param {string} code - Authorization code from Google
   * @param {string} state - State parameter from OAuth flow
   * @param {string} codeVerifier - PKCE code verifier
   * @returns {Promise<{access_token: string, refresh_token: string, token_type: string, expires_in: number}>}
   */
  async exchangeCodeForTokens(code, state, codeVerifier) {
    const { data } = await authApi.get('/auth/google/callback', {
      params: {
        code,
        state,
        code_verifier: codeVerifier
      }
    })
    return data
  },

  /**
   * Refresh access token using refresh token
   * @param {string} refreshToken - Refresh token
   * @returns {Promise<{access_token: string, refresh_token: string}>}
   */
  async refreshToken(refreshToken) {
    const { data } = await authApi.post('/auth/refresh', {
      refresh_token: refreshToken
    })
    return data
  },

  /**
   * Logout - invalidate refresh token
   * @param {string} refreshToken - Refresh token to invalidate
   * @param {string} accessToken - Current access token for authorization
   */
  async logout(refreshToken, accessToken) {
    await authApi.post('/auth/logout',
      { refresh_token: refreshToken },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    )
  },

  /**
   * Get current user info
   * @param {string} accessToken - Access token
   * @returns {Promise<{email: string, name: string, picture: string, role: string}>}
   */
  async getCurrentUser(accessToken) {
    const { data } = await authApi.get('/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` }
    })
    return data
  },

  /**
   * Get active sessions (admin only)
   * @param {string} accessToken - Access token
   * @returns {Promise<{total_sessions: number, sessions: Array}>}
   */
  async getActiveSessions(accessToken) {
    const { data } = await authApi.get('/admin/sessions', {
      headers: { Authorization: `Bearer ${accessToken}` }
    })
    return data
  }
}
