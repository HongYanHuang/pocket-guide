import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import POIDetail from '../views/POIDetail.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
