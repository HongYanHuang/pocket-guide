<template>
  <el-card v-loading="loading">
    <template #header>
      <span>Map View - {{ city }}</span>
    </template>

    <div v-if="pois.length > 0" style="height: 600px">
      <l-map
        ref="map"
        :zoom="zoom"
        :center="center"
        @ready="onMapReady"
      >
        <l-tile-layer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <l-marker
          v-for="poi in poisWithCoords"
          :key="poi.poi_id"
          :lat-lng="[poi.metadata.coordinates.latitude, poi.metadata.coordinates.longitude]"
        >
          <l-popup>
            <div style="min-width: 200px">
              <h3 style="margin: 0 0 10px 0">{{ poi.poi_name }}</h3>
              <p style="margin: 5px 0; font-size: 12px">
                <strong>Lat:</strong> {{ poi.metadata.coordinates.latitude.toFixed(6) }}<br>
                <strong>Lng:</strong> {{ poi.metadata.coordinates.longitude.toFixed(6) }}
              </p>
              <p v-if="poi.metadata.visit_info" style="margin: 5px 0; font-size: 12px">
                <strong>Type:</strong> {{ poi.metadata.visit_info.indoor_outdoor }}<br>
                <strong>Duration:</strong> {{ poi.metadata.visit_info.typical_duration_minutes }} min
              </p>
              <el-button size="small" type="primary" @click="editPOI(poi)" style="margin-top: 10px">
                Edit
              </el-button>
            </div>
          </l-popup>
        </l-marker>
      </l-map>
    </div>

    <el-empty v-else description="No POIs with coordinates found" />

    <POIEditor
      v-model:visible="showEditDialog"
      :city="city"
      :poi-id="selectedPOI?.poi_id"
      :initial-data="selectedPOI?.metadata"
      @saved="onPOISaved"
    />
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, defineProps } from 'vue'
import { ElMessage } from 'element-plus'
import { LMap, LTileLayer, LMarker, LPopup } from '@vue-leaflet/vue-leaflet'
import api from '../api/metadata'
import POIEditor from './POIEditor.vue'

const props = defineProps({
  city: {
    type: String,
    required: true
  }
})

const pois = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const selectedPOI = ref(null)
const zoom = ref(13)
const center = ref([37.9838, 23.7275]) // Default: Athens

const poisWithCoords = computed(() => {
  return pois.value.filter(poi =>
    poi.metadata?.coordinates?.latitude && poi.metadata?.coordinates?.longitude
  )
})

const loadPOIs = async () => {
  loading.value = true
  try {
    const poiList = await api.getCityPOIs(props.city)

    // Load full details for each POI to get coordinates
    const detailPromises = poiList.map(poi => api.getPOI(props.city, poi.poi_id))
    const detailedPOIs = await Promise.all(detailPromises)

    pois.value = detailedPOIs

    // Calculate center from POIs
    if (poisWithCoords.value.length > 0) {
      const avgLat = poisWithCoords.value.reduce((sum, poi) =>
        sum + poi.metadata.coordinates.latitude, 0) / poisWithCoords.value.length
      const avgLng = poisWithCoords.value.reduce((sum, poi) =>
        sum + poi.metadata.coordinates.longitude, 0) / poisWithCoords.value.length
      center.value = [avgLat, avgLng]
    }
  } catch (error) {
    ElMessage.error('Failed to load POIs: ' + error.message)
  } finally {
    loading.value = false
  }
}

const editPOI = async (poi) => {
  selectedPOI.value = poi
  showEditDialog.value = true
}

const onPOISaved = () => {
  loadPOIs()
}

const onMapReady = () => {
  // Map is ready
}

onMounted(() => {
  loadPOIs()
})
</script>

<style scoped>
:deep(.leaflet-container) {
  height: 100%;
  width: 100%;
}
</style>
