<template>
  <el-card v-loading="loading">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>{{ poi?.poi_name || 'POI Details' }}</span>
        <el-button @click="$router.back()">Back</el-button>
      </div>
    </template>

    <div v-if="poi">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="POI ID">{{ poi.poi_id }}</el-descriptions-item>
        <el-descriptions-item label="City">{{ poi.city }}</el-descriptions-item>

        <el-descriptions-item label="Latitude" v-if="poi.metadata?.coordinates">
          {{ poi.metadata.coordinates.latitude }}
        </el-descriptions-item>
        <el-descriptions-item label="Longitude" v-if="poi.metadata?.coordinates">
          {{ poi.metadata.coordinates.longitude }}
        </el-descriptions-item>

        <el-descriptions-item label="Indoor/Outdoor" v-if="poi.metadata?.visit_info">
          {{ poi.metadata.visit_info.indoor_outdoor }}
        </el-descriptions-item>
        <el-descriptions-item label="Duration" v-if="poi.metadata?.visit_info">
          {{ poi.metadata.visit_info.typical_duration_minutes }} minutes
        </el-descriptions-item>

        <el-descriptions-item label="Address" :span="2" v-if="poi.metadata?.address">
          {{ poi.metadata.address }}
        </el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 20px">
        <el-button type="primary" @click="showEditDialog = true">Edit</el-button>
        <el-button @click="recollect" :loading="recollecting">Recollect from Google Maps</el-button>
      </div>
    </div>

    <POIEditor
      v-if="poi"
      v-model:visible="showEditDialog"
      :city="poi.city"
      :poi-id="poi.poi_id"
      :initial-data="poi.metadata"
      @saved="loadPOI"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api/metadata'
import POIEditor from '../components/POIEditor.vue'

const route = useRoute()
const poi = ref(null)
const loading = ref(false)
const recollecting = ref(false)
const showEditDialog = ref(false)

const loadPOI = async () => {
  loading.value = true
  try {
    poi.value = await api.getPOI(route.params.city, route.params.poiId)
  } catch (error) {
    ElMessage.error('Failed to load POI: ' + error.message)
  } finally {
    loading.value = false
  }
}

const recollect = async () => {
  recollecting.value = true
  try {
    await api.recollectPOI(route.params.city, route.params.poiId)
    ElMessage.success('Metadata recollected successfully')
    await loadPOI()
  } catch (error) {
    ElMessage.error('Failed to recollect: ' + error.message)
  } finally {
    recollecting.value = false
  }
}

onMounted(() => {
  loadPOI()
})
</script>
