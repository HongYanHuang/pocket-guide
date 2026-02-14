import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import POIDetail from '../views/POIDetail.vue'
import TranscriptView from '../views/TranscriptView.vue'
import ResearchView from '../views/ResearchView.vue'
import ToursView from '../views/ToursView.vue'
import TourDetail from '../views/TourDetail.vue'
import TourGeneratorView from '../views/TourGeneratorView.vue'
import ComboTicketsView from '../views/ComboTicketsView.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/poi/:city/:poiId',
    name: 'POIDetail',
    component: POIDetail
  },
  {
    path: '/poi/:city/:poiId/transcript',
    name: 'TranscriptView',
    component: TranscriptView
  },
  {
    path: '/poi/:city/:poiId/research',
    name: 'ResearchView',
    component: ResearchView
  },
  {
    path: '/tours',
    name: 'ToursView',
    component: ToursView
  },
  {
    path: '/tours/:tourId',
    name: 'TourDetail',
    component: TourDetail
  },
  {
    path: '/tour/generate',
    name: 'TourGenerator',
    component: TourGeneratorView
  },
  {
    path: '/combo-tickets',
    name: 'ComboTickets',
    component: ComboTicketsView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
