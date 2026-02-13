<template>
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
        <el-menu-item index="/combo-tickets">
          <span>Combo Tickets</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background-color: #fff; border-bottom: 1px solid #e6e6e6">
        <h2 style="margin: 0; line-height: 60px">POI Metadata Manager</h2>
      </el-header>

      <el-main style="background-color: #f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
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
