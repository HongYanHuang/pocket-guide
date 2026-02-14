import axios from 'axios'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes for tour generation
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('Tour API Error:', message)
    return Promise.reject(new Error(message))
  }
)

/**
 * Tour Generation API Methods
 */
export default {
  /**
   * Generate a new tour
   *
   * @param {Object} params - Tour generation parameters
   * @param {string} params.city - City name (required)
   * @param {number} params.days - Number of days (required)
   * @param {Array<string>} params.interests - List of interests
   * @param {string} params.provider - AI provider (anthropic, openai, google)
   * @param {Array<string>} params.must_see - POIs that must be included
   * @param {string} params.pace - Trip pace (relaxed, normal, packed)
   * @param {string} params.walking - Walking tolerance (low, moderate, high)
   * @param {string} params.language - Language code (ISO 639-1)
   * @param {string} params.mode - Optimization mode (simple, ilp)
   * @param {string} params.start_location - Start location
   * @param {string} params.end_location - End location
   * @param {string} params.start_date - Start date (YYYY-MM-DD)
   * @param {boolean} params.save - Whether to save the tour
   * @returns {Promise<Object>} Generated tour data
   */
  generateTour(params) {
    return apiClient.post('/tour/generate', params)
  }
}
