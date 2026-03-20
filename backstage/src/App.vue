<template>
  <div v-if="!isAuthRoute">
    <!-- Authenticated App Layout -->
    <el-container style="height: 100vh">
      <el-aside width="200px" style="background-color: #304156">
        <div style="padding: 20px; color: white; font-size: 18px; font-weight: bold">
          POI Manager
        </div>
        <el-menu
          :default-active="$route.path"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/">
            <span>Cities</span>
          </el-menu-item>
          <el-menu-item index="/tours">
            <span>Tours</span>
          </el-menu-item>
          <el-menu-item index="/tour/generate">
            <span>Generate Tour</span>
          </el-menu-item>
          <el-menu-item index="/combo-tickets">
            <span>Combo Tickets</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header style="background-color: #fff; border-bottom: 1px solid #e6e6e6; display: flex; justify-content: space-between; align-items: center;">
          <h2 style="margin: 0">POI Metadata Manager</h2>
          <UserHeader v-if="isAuthenticated" />
        </el-header>

        <el-main style="background-color: #f0f2f5">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>

  <!-- Auth Routes (Login, Callback) - No Layout -->
  <div v-else>
    <router-view />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from './auth/useAuth'
import UserHeader from './components/UserHeader.vue'

const route = useRoute()
const { isAuthenticated, checkAuth } = useAuth()

// Check if current route is an auth route (login, callback)
const isAuthRoute = computed(() => {
  const result = route.path === '/login' || route.path.startsWith('/auth/')
  console.log('🟠 App.vue isAuthRoute computed:', route.path, '→', result)
  return result
})

// Check authentication on app mount
onMounted(async () => {
  console.log('🟠 App.vue onMounted, route.path:', route.path)
  console.log('🟠 App.vue isAuthRoute.value:', isAuthRoute.value)
  if (!isAuthRoute.value) {
    console.log('🟠 App.vue calling checkAuth()')
    await checkAuth()
  } else {
    console.log('🟠 App.vue SKIPPING checkAuth (auth route)')
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
