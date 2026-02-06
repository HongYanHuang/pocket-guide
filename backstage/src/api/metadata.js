import axios from 'axios'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// API methods
export default {
  // Cities
  getCities() {
    return apiClient.get('/cities')
  },

  getCityPOIs(city) {
    return apiClient.get(`/cities/${city}/pois`)
  },

  verifyCity(city) {
    return apiClient.get(`/cities/${city}/verify`)
  },

  collectCityMetadata(city) {
    return apiClient.post(`/cities/${city}/collect`)
  },

  // POIs
  getPOI(city, poiId) {
    return apiClient.get(`/pois/${city}/${poiId}`)
  },

  updatePOI(city, poiId, metadata) {
    return apiClient.put(`/pois/${city}/${poiId}/metadata`, metadata)
  },

  recollectPOI(city, poiId) {
    return apiClient.post(`/pois/${city}/${poiId}/recollect`)
  },

  // Transcript
  getTranscript(city, poiId) {
    return apiClient.get(`/pois/${city}/${poiId}/transcript`)
  },

  updateTranscript(city, poiId, transcript) {
    return apiClient.put(`/pois/${city}/${poiId}/transcript`, { transcript })
  },

  // Research
  getResearch(city, poiId) {
    return apiClient.get(`/pois/${city}/${poiId}/research`)
  },

  // Distance Matrix
  getDistanceMatrix(city) {
    return apiClient.get(`/distances/${city}`)
  },

  recalculateDistances(city) {
    return apiClient.post(`/distances/${city}/recalculate`)
  },

  // Tours
  getTours() {
    return apiClient.get('/tours')
  },

  getTour(tourId, language = 'en') {
    return apiClient.get(`/tours/${tourId}`, {
      params: { language }
    })
  },

  getTourTranscriptLinks(tourId, language = 'en') {
    return apiClient.get(`/tours/${tourId}/transcript-links`, {
      params: { language }
    })
  },

  replacePOIInTour(tourId, originalPoi, replacementPoi, mode, language, day) {
    return apiClient.post(`/tours/${tourId}/replace-poi`, {
      original_poi: originalPoi,
      replacement_poi: replacementPoi,
      mode: mode,
      language: language,
      day: day
    })
  }
}
