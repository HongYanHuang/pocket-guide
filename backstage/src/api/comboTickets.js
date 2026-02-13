import axios from 'axios'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: '/api/combo-tickets',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('Combo Tickets API Error:', message)
    return Promise.reject(new Error(message))
  }
)

/**
 * Combo Ticket API Methods
 */
export default {
  /**
   * Get all combo tickets for a city
   * @param {string} city - City name (e.g., 'rome', 'paris')
   * @returns {Promise} ComboTicketsResponse
   */
  getComboTickets(city) {
    return apiClient.get(`/cities/${city}`)
  },

  /**
   * Get a specific combo ticket by ID
   * @param {string} city - City name
   * @param {string} ticketId - Combo ticket ID
   * @returns {Promise} ComboTicket
   */
  getComboTicket(city, ticketId) {
    return apiClient.get(`/cities/${city}/${ticketId}`)
  },

  /**
   * Create a new combo ticket
   * @param {string} city - City name
   * @param {Object} ticketData - Combo ticket data
   * @returns {Promise} SuccessResponse
   */
  createComboTicket(city, ticketData) {
    return apiClient.post(`/cities/${city}`, ticketData)
  },

  /**
   * Update an existing combo ticket
   * @param {string} city - City name
   * @param {string} ticketId - Combo ticket ID
   * @param {Object} updateData - Fields to update
   * @returns {Promise} SuccessResponse
   */
  updateComboTicket(city, ticketId, updateData) {
    return apiClient.put(`/cities/${city}/${ticketId}`, updateData)
  },

  /**
   * Delete a combo ticket
   * @param {string} city - City name
   * @param {string} ticketId - Combo ticket ID
   * @returns {Promise} SuccessResponse
   */
  deleteComboTicket(city, ticketId) {
    return apiClient.delete(`/cities/${city}/${ticketId}`)
  },

  /**
   * Validate combo ticket consistency for a city
   * @param {string} city - City name
   * @returns {Promise} ValidationResponse
   */
  validateComboTickets(city) {
    return apiClient.get(`/cities/${city}/validate`)
  },

  /**
   * Get all combo tickets that include a specific POI
   * @param {string} city - City name
   * @param {string} poiName - POI name
   * @returns {Promise} Array of ComboTicket
   */
  getComboTicketsForPOI(city, poiName) {
    return apiClient.get(`/cities/${city}/pois/${poiName}`)
  }
}
