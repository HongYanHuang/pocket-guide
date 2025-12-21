import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import POIDetail from '../views/POIDetail.vue'
import TranscriptView from '../views/TranscriptView.vue'
import ResearchView from '../views/ResearchView.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
