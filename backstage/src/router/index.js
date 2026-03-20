import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../auth/useAuth'
import Dashboard from '../views/Dashboard.vue'
import POIDetail from '../views/POIDetail.vue'
import TranscriptView from '../views/TranscriptView.vue'
import ResearchView from '../views/ResearchView.vue'
import ToursView from '../views/ToursView.vue'
import TourDetail from '../views/TourDetail.vue'
import TourGeneratorView from '../views/TourGeneratorView.vue'
import ComboTicketsView from '../views/ComboTicketsView.vue'
import Login from '../views/Login.vue'
import AuthCallback from '../views/AuthCallback.vue'

const routes = [
  // Auth routes (no authentication required)
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: AuthCallback,
    meta: { requiresAuth: false }
  },

  // Protected routes (authentication required)
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/poi/:city/:poiId',
    name: 'POIDetail',
    component: POIDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/poi/:city/:poiId/transcript',
    name: 'TranscriptView',
    component: TranscriptView,
    meta: { requiresAuth: true }
  },
  {
    path: '/poi/:city/:poiId/research',
    name: 'ResearchView',
    component: ResearchView,
    meta: { requiresAuth: true }
  },
  {
    path: '/tours',
    name: 'ToursView',
    component: ToursView,
    meta: { requiresAuth: true }
  },
  {
    path: '/tours/:tourId',
    name: 'TourDetail',
    component: TourDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/tour/generate',
    name: 'TourGenerator',
    component: TourGeneratorView,
    meta: { requiresAuth: true }
  },
  {
    path: '/combo-tickets',
    name: 'ComboTickets',
    component: ComboTicketsView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  console.log('🔷 Router guard triggered')
  console.log('🔷 Navigating to:', to.path, 'name:', to.name)
  console.log('🔷 requiresAuth:', to.meta.requiresAuth)

  const { isAuthenticated, checkAuth, loading } = useAuth()
  console.log('🔷 isAuthenticated:', isAuthenticated.value)

  // Public routes
  if (!to.meta.requiresAuth) {
    console.log('🔷 Public route, no auth required')
    // If already authenticated and trying to access login, redirect to home
    if (to.name === 'Login' && isAuthenticated.value) {
      console.log('🔷 Already authenticated, redirecting to /')
      next('/')
    } else {
      console.log('🔷 Allowing navigation to:', to.path)
      next()
    }
    return
  }

  // Protected routes - check authentication
  console.log('🔷 Protected route, checking auth...')
  if (!isAuthenticated.value && !loading.value) {
    console.log('🔷 Calling checkAuth...')
    await checkAuth()
  }

  if (isAuthenticated.value) {
    console.log('🔷 Authenticated, allowing access')
    next()
  } else {
    console.log('🔷 Not authenticated, redirecting to login')
    // Redirect to login with return URL
    next({
      name: 'Login',
      query: { redirect: to.fullPath }
    })
  }
})

export default router
