<template>
  <div>
    <el-page-header @back="$router.push('/')">
      <template #content>
        <div style="display: flex; align-items: center; gap: 12px">
          <span style="font-size: 18px; font-weight: 600">Tours & Itineraries</span>
        </div>
      </template>
    </el-page-header>

    <div style="margin-top: 20px">
      <!-- Loading State -->
      <div v-if="loading" style="text-align: center; padding: 40px">
        <el-icon class="is-loading" :size="30">
          <loading />
        </el-icon>
        <p style="margin-top: 10px">Loading tours...</p>
      </div>

      <!-- Error State -->
      <el-alert
        v-else-if="error"
        title="Error Loading Tours"
        type="error"
        :description="error"
        show-icon
        :closable="false"
      />

      <!-- Empty State -->
      <el-empty
        v-else-if="groupedTours.length === 0"
        description="No tours found"
      >
        <el-button type="primary">Create First Tour</el-button>
      </el-empty>

      <!-- Tours List (Grouped by City) -->
      <div v-else>
        <div v-for="group in groupedTours" :key="group.city" style="margin-bottom: 30px">
          <el-divider content-position="left">
            <span style="font-size: 16px; font-weight: 600">{{ group.city }}</span>
            <el-tag size="small" style="margin-left: 10px">{{ group.tours.length }} tours</el-tag>
          </el-divider>

          <el-row :gutter="20">
            <el-col
              v-for="tour in group.tours"
              :key="tour.tour_id"
              :xs="24"
              :sm="12"
              :md="8"
              :lg="6"
              style="margin-bottom: 20px"
            >
              <el-card
                shadow="hover"
                :body-style="{ padding: '0px' }"
                style="cursor: pointer"
                @click="viewTour(tour.tour_id)"
              >
                <div style="padding: 20px">
                  <div style="display: flex; justify-content: space-between; align-items: start">
                    <div style="flex: 1">
                      <div style="font-weight: 600; font-size: 14px; margin-bottom: 8px">
                        {{ formatDate(tour.created_at) }}
                      </div>
                      <div style="color: #909399; font-size: 12px; margin-bottom: 12px">
                        {{ tour.tour_id.substring(tour.tour_id.length - 6) }}
                      </div>
                    </div>
                    <el-tag
                      v-if="tour.optimization_score"
                      :type="getScoreType(tour.optimization_score)"
                      size="small"
                    >
                      {{ (tour.optimization_score * 100).toFixed(0) }}%
                    </el-tag>
                  </div>

                  <div style="margin-bottom: 12px">
                    <el-tag size="small" effect="plain" style="margin-right: 5px">
                      {{ tour.duration_days }} days
                    </el-tag>
                    <el-tag size="small" effect="plain">
                      {{ tour.total_pois }} POIs
                    </el-tag>
                  </div>

                  <div v-if="tour.interests.length > 0" style="margin-top: 10px">
                    <el-tag
                      v-for="interest in tour.interests.slice(0, 3)"
                      :key="interest"
                      size="small"
                      type="info"
                      effect="plain"
                      style="margin-right: 5px; margin-bottom: 5px"
                    >
                      {{ interest }}
                    </el-tag>
                    <span
                      v-if="tour.interests.length > 3"
                      style="font-size: 12px; color: #909399"
                    >
                      +{{ tour.interests.length - 3 }} more
                    </span>
                  </div>
                </div>

                <div
                  style="
                    padding: 12px 20px;
                    background-color: #f5f7fa;
                    border-top: 1px solid #ebeef5;
                    font-size: 12px;
                    color: #606266;
                  "
                >
                  Click to view itinerary →
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const loading = ref(true)
const error = ref(null)
const tours = ref([])

// Group tours by city
const groupedTours = computed(() => {
  const groups = {}

  tours.value.forEach(tour => {
    if (!groups[tour.city]) {
      groups[tour.city] = {
        city: tour.city,
        tours: []
      }
    }
    groups[tour.city].tours.push(tour)
  })

  return Object.values(groups)
})

// Load tours from API
const loadTours = async () => {
  try {
    loading.value = true
    error.value = null

    const response = await axios.get('http://localhost:8000/tours')
    tours.value = response.data

  } catch (err) {
    console.error('Error loading tours:', err)
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

// Navigate to tour detail
const viewTour = (tourId) => {
  router.push(`/tours/${tourId}`)
}

// Format date
const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Get score type for tag color
const getScoreType = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
}

onMounted(() => {
  loadTours()
})
</script>

<style scoped>
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
