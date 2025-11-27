<template>
  <div>
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>City Selection</span>
          <el-button type="primary" size="small" @click="loadCities" :loading="loading">
            Refresh
          </el-button>
        </div>
      </template>

      <el-select
        v-model="selectedCity"
        placeholder="Select a city"
        style="width: 300px"
        @change="onCityChange"
      >
        <el-option
          v-for="city in cities"
          :key="city.name"
          :label="`${city.name} (${city.poi_count} POIs)`"
          :value="city.name"
        />
      </el-select>
    </el-card>

    <el-tabs v-if="selectedCity" v-model="activeTab">
      <el-tab-pane label="POIs" name="pois">
        <POITable :city="selectedCity" :key="selectedCity" />
      </el-tab-pane>

      <el-tab-pane label="Map View" name="map">
        <MapViewer :city="selectedCity" :key="selectedCity" />
      </el-tab-pane>

      <el-tab-pane label="Distance Matrix" name="distances">
        <DistanceMatrix :city="selectedCity" :key="selectedCity" />
      </el-tab-pane>
    </el-tabs>

    <el-empty v-else description="Please select a city to view POIs" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/metadata'
import POITable from '../components/POITable.vue'
import MapViewer from '../components/MapViewer.vue'
import DistanceMatrix from '../components/DistanceMatrix.vue'

const cities = ref([])
const selectedCity = ref('')
const activeTab = ref('pois')
const loading = ref(false)

const loadCities = async () => {
  loading.value = true
  try {
    cities.value = await api.getCities()
  } catch (error) {
    ElMessage.error('Failed to load cities: ' + error.message)
  } finally {
    loading.value = false
  }
}

const onCityChange = () => {
  activeTab.value = 'pois'
}

onMounted(() => {
  loadCities()
})
</script>
