<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>POIs in {{ city }}</span>
        <div>
          <el-button size="small" @click="loadPOIs" :loading="loading">Refresh</el-button>
          <el-button type="primary" size="small" @click="collectMetadata" :loading="collecting">
            Collect All Metadata
          </el-button>
        </div>
      </div>
    </template>

    <el-table :data="pois" v-loading="loading" style="width: 100%">
      <el-table-column label="POI Name">
        <template #default="{ row }">
          {{ getDisplayName(row) }}
          <el-tag v-if="row.name?.names && Object.keys(row.name.names).length > 1"
                  size="small" type="info" style="margin-left: 6px">
            {{ Object.keys(row.name.names).length }} langs
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="Has Metadata" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_metadata ? 'success' : 'warning'" size="small">
            {{ row.has_metadata ? '✓' : '✗' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="Has Coordinates" width="140" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_coordinates ? 'success' : 'warning'" size="small">
            {{ row.has_coordinates ? '✓' : '✗' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="last_updated" label="Last Updated" width="200">
        <template #default="{ row }">
          {{ row.last_updated ? formatDate(row.last_updated) : 'N/A' }}
        </template>
      </el-table-column>

      <el-table-column label="Actions" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="editPOI(row)">Edit</el-button>
          <el-button size="small" @click="viewDetails(row)">Details</el-button>
        </template>
      </el-table-column>
    </el-table>

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
import { ref, onMounted, defineProps } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api/metadata'
import POIEditor from './POIEditor.vue'

const props = defineProps({
  city: {
    type: String,
    required: true
  }
})

const router = useRouter()
const pois = ref([])
const loading = ref(false)
const collecting = ref(false)
const showEditDialog = ref(false)
const selectedPOI = ref(null)

const loadPOIs = async () => {
  loading.value = true
  try {
    pois.value = await api.getCityPOIs(props.city)
  } catch (error) {
    ElMessage.error('Failed to load POIs: ' + error.message)
  } finally {
    loading.value = false
  }
}

const collectMetadata = async () => {
  collecting.value = true
  try {
    await api.collectCityMetadata(props.city)
    ElMessage.success('Metadata collection started')
    await loadPOIs()
  } catch (error) {
    ElMessage.error('Failed to collect metadata: ' + error.message)
  } finally {
    collecting.value = false
  }
}

const editPOI = async (poi) => {
  try {
    const fullPOI = await api.getPOI(props.city, poi.poi_id)
    selectedPOI.value = fullPOI
    showEditDialog.value = true
  } catch (error) {
    ElMessage.error('Failed to load POI details: ' + error.message)
  }
}

const viewDetails = (poi) => {
  router.push(`/poi/${props.city}/${poi.poi_id}`)
}

const onPOISaved = () => {
  loadPOIs()
}

const getDisplayName = (poi) => {
  if (poi.name?.names) {
    // Use browser locale to pick localized name
    const lang = navigator.language?.split('-')[0]
    if (lang && poi.name.names[lang]) return poi.name.names[lang]
  }
  return poi.name?.default || poi.poi_name || 'Unknown'
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  loadPOIs()
})
</script>
