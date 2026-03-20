import apiClient from './client'

export default {
  /**
   * Get all active user sessions (admin only)
   */
  async listUsers() {
    return await apiClient.get('/admin/users')
  }
}
