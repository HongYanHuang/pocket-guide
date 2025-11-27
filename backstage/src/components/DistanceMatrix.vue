<template>
  <el-card v-loading="loading">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>Distance Matrix - {{ city }}</span>
        <el-button type="primary" size="small" @click="recalculate" :loading="recalculating">
          Recalculate
        </el-button>
      </div>
    </template>

    <div v-if="matrix">
      <el-tabs v-model="activeMode">
        <el-tab-pane label="Walking" name="walking" />
        <el-tab-pane label="Transit" name="transit" />
        <el-tab-pane label="Driving" name="driving" />
      </el-tabs>

      <el-table :data="filteredPairs" style="width: 100%; margin-top: 20px">
        <el-table-column prop="origin_poi_name" label="From" width="200" />
        <el-table-column prop="destination_poi_name" label="To" width="200" />

        <el-table-column label="Duration" width="120">
          <template #default="{ row }">
            {{ row[activeMode]?.duration_text || 'N/A' }}
          </template>
        </el-table-column>

        <el-table-column label="Distance" width="120">
          <template #default="{ row }">
            {{ row[activeMode]?.distance_text || 'N/A' }}
          </template>
        </el-table-column>

        <el-table-column label="Duration (min)" width="130">
          <template #default="{ row }">
            {{ row[activeMode]?.duration_minutes?.toFixed(1) || 'N/A' }}
          </template>
        </el-table-column>

        <el-table-column label="Distance (km)" width="130">
          <template #default="{ row }">
            {{ row[activeMode]?.distance_km?.toFixed(2) || 'N/A' }}
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 20px; color: #909399; font-size: 12px">
        <p>Generated: {{ new Date(matrix.generated_at).toLocaleString() }}</p>
        <p>Total POI Pairs: {{ Object.keys(matrix.poi_pairs).length }}</p>
      </div>
    </div>

    <el-empty v-else description="No distance matrix found. Click 'Recalculate' to generate." />
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, defineProps } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/metadata'

const props = defineProps({
  city: {
    type: String,
    required: true
  }
})

const matrix = ref(null)
const loading = ref(false)
const recalculating = ref(false)
const activeMode = ref('walking')

const filteredPairs = computed(() => {
  if (!matrix.value) return []

  return Object.values(matrix.value.poi_pairs).filter(pair => {
    return pair[activeMode.value] !== undefined
  })
})

const loadMatrix = async () => {
  loading.value = true
  try {
    matrix.value = await api.getDistanceMatrix(props.city)
  } catch (error) {
    console.error('Distance matrix not found:', error.message)
    matrix.value = null
  } finally {
    loading.value = false
  }
}

const recalculate = async () => {
  recalculating.value = true
  try {
    await api.recalculateDistances(props.city)
    ElMessage.success('Distance matrix recalculated successfully')
    await loadMatrix()
  } catch (error) {
    ElMessage.error('Failed to recalculate: ' + error.message)
  } finally {
    recalculating.value = false
  }
}

onMounted(() => {
  loadMatrix()
})
</script>
