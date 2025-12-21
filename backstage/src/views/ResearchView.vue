<template>
  <div class="research-view">
    <el-page-header @back="goBack" :content="`Research: ${poiName}`" />

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <el-alert
      v-else-if="error"
      type="error"
      :title="error"
      show-icon
      :closable="false"
    />

    <div v-else class="content-container">
      <!-- View Toggle -->
      <el-card class="toggle-card">
        <el-radio-group v-model="viewMode" size="default">
          <el-radio-button label="structured">Structured View</el-radio-button>
          <el-radio-button label="raw">Raw YAML</el-radio-button>
        </el-radio-group>
      </el-card>

      <!-- Structured View -->
      <ResearchStructured v-if="viewMode === 'structured'" :data="data" />

      <!-- Raw YAML View -->
      <ResearchRaw v-else-if="viewMode === 'raw'" :raw-yaml="data.raw_yaml" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import metadataAPI from '../api/metadata'
import ResearchStructured from '../components/ResearchStructured.vue'
import ResearchRaw from '../components/ResearchRaw.vue'

const route = useRoute()
const router = useRouter()

const city = computed(() => route.params.city)
const poiId = computed(() => route.params.poiId)
const poiName = computed(() => poiId.value.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))

const loading = ref(true)
const error = ref(null)
const data = ref({
  poi_id: '',
  name: '',
  city: '',
  basic_info: null,
  core_features: [],
  people: null,
  events: null,
  locations: null,
  concepts: null,
  raw_yaml: ''
})

const viewMode = ref('structured')

const fetchResearch = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await metadataAPI.getResearch(city.value, poiId.value)
    data.value = response
  } catch (err) {
    error.value = err.message || 'Failed to load research data'
    console.error('Error fetching research:', err)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchResearch()
})
</script>

<style scoped>
.research-view {
  padding: 20px;
}

.loading-container {
  margin-top: 20px;
}

.content-container {
  margin-top: 20px;
}

.toggle-card {
  margin-bottom: 20px;
  text-align: center;
}
</style>
