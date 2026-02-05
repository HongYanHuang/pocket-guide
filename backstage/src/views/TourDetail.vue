<template>
  <div>
    <el-page-header @back="$router.push('/tours')">
      <template #content>
        <div style="display: flex; align-items: center; gap: 12px">
          <span style="font-size: 18px; font-weight: 600">
            {{ tour?.metadata?.city }} Tour
          </span>
          <el-tag v-if="tour" size="small">
            {{ tour.itinerary.length }} days
          </el-tag>
        </div>
      </template>
    </el-page-header>

    <div style="margin-top: 20px">
      <!-- Loading State -->
      <div v-if="loading" style="text-align: center; padding: 40px">
        <el-icon class="is-loading" :size="30">
          <loading />
        </el-icon>
        <p style="margin-top: 10px">Loading tour...</p>
      </div>

      <!-- Error State -->
      <el-alert
        v-else-if="error"
        title="Error Loading Tour"
        type="error"
        :description="error"
        show-icon
        :closable="false"
      />

      <!-- Tour Details -->
      <div v-else-if="tour">
        <!-- Tour Info Card -->
        <el-card style="margin-bottom: 20px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 600">Tour Information</span>
              <el-tag :type="getScoreType(tour.optimization_scores.overall_score)">
                Score: {{ (tour.optimization_scores.overall_score * 100).toFixed(0) }}%
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="Created">
              {{ formatDate(tour.metadata.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="Tour ID">
              <el-text type="info" size="small">{{ tour.metadata.tour_id }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="Duration">
              {{ tour.itinerary.length }} days
            </el-descriptions-item>
            <el-descriptions-item label="Total POIs">
              {{ totalPOIs }}
            </el-descriptions-item>
            <el-descriptions-item label="Total Walking">
              {{ tour.optimization_scores.total_distance_km.toFixed(1) }} km
            </el-descriptions-item>
            <el-descriptions-item label="Optimization">
              Distance: {{ (tour.optimization_scores.distance_score * 100).toFixed(0) }}% |
              Coherence: {{ (tour.optimization_scores.coherence_score * 100).toFixed(0) }}%
            </el-descriptions-item>
            <el-descriptions-item label="Interests" :span="2">
              <el-tag
                v-for="interest in tour.input_parameters.interests"
                :key="interest"
                size="small"
                style="margin-right: 5px"
              >
                {{ interest }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Pace">
              {{ tour.input_parameters.preferences.pace }}
            </el-descriptions-item>
            <el-descriptions-item label="Walking Tolerance">
              {{ tour.input_parameters.preferences.walking_tolerance }}
            </el-descriptions-item>
            <el-descriptions-item label="Language" v-if="tour.input_parameters.language">
              {{ tour.input_parameters.language }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- Constraint Violations -->
          <div v-if="tour.constraints_violated.length > 0" style="margin-top: 15px">
            <el-alert
              title="Constraint Violations"
              type="warning"
              :closable="false"
            >
              <ul style="margin: 5px 0; padding-left: 20px">
                <li v-for="(violation, idx) in tour.constraints_violated" :key="idx">
                  {{ violation }}
                </li>
              </ul>
            </el-alert>
          </div>
        </el-card>

        <!-- Itinerary Timeline -->
        <el-card style="margin-bottom: 20px">
          <template #header>
            <span style="font-weight: 600">Daily Itinerary</span>
          </template>

          <el-timeline>
            <el-timeline-item
              v-for="day in tour.itinerary"
              :key="day.day"
              :timestamp="`Day ${day.day}`"
              placement="top"
            >
              <el-card>
                <template #header>
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span style="font-weight: 600">Day {{ day.day }}</span>
                    <div>
                      <el-tag size="small" style="margin-right: 5px">
                        {{ day.total_hours.toFixed(1) }}h total
                      </el-tag>
                      <el-tag size="small" type="warning">
                        {{ day.total_walking_km.toFixed(1) }}km walking
                      </el-tag>
                    </div>
                  </div>
                </template>

                <!-- POIs for this day -->
                <div v-for="(poi, index) in day.pois" :key="index">
                  <el-card
                    shadow="hover"
                    :body-style="{ padding: '15px' }"
                    style="margin-bottom: 15px"
                  >
                    <div style="display: flex; justify-content: space-between; align-items: start">
                      <div style="flex: 1">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
                          <span style="
                            background: #409EFF;
                            color: white;
                            width: 24px;
                            height: 24px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 12px;
                            font-weight: 600;
                          ">
                            {{ index + 1 }}
                          </span>
                          <span style="font-weight: 600; font-size: 15px">{{ poi.poi }}</span>
                          <el-tag size="small" :type="getPriorityType(poi.priority)">
                            {{ poi.priority }}
                          </el-tag>
                        </div>

                        <div style="color: #606266; font-size: 13px; margin-bottom: 10px; padding-left: 34px">
                          {{ poi.reason }}
                        </div>

                        <div style="padding-left: 34px">
                          <el-tag size="small" effect="plain" style="margin-right: 5px">
                            {{ poi.estimated_hours.toFixed(1) }}h visit
                          </el-tag>
                          <el-tag v-if="poi.period" size="small" type="info" effect="plain">
                            {{ poi.period }}
                          </el-tag>
                        </div>

                        <!-- Transcript Toggle -->
                        <div style="margin-top: 12px; padding-left: 34px">
                          <el-button
                            size="small"
                            @click="toggleTranscript(poi.poi)"
                            :loading="transcriptLoading[poi.poi]"
                          >
                            {{
                              expandedTranscripts[poi.poi]
                                ? 'Hide Transcript'
                                : 'View Transcript'
                            }}
                          </el-button>

                          <!-- Expanded Transcript -->
                          <el-collapse-transition>
                            <div v-if="expandedTranscripts[poi.poi]" style="margin-top: 10px">
                              <el-card :body-style="{ padding: '15px', background: '#f5f7fa' }">
                                <div
                                  v-if="transcripts[poi.poi]"
                                  style="white-space: pre-wrap; font-size: 13px; line-height: 1.6"
                                >
                                  {{ transcripts[poi.poi] }}
                                </div>
                                <div v-else style="color: #909399; font-style: italic">
                                  Transcript not available
                                </div>
                              </el-card>
                            </div>
                          </el-collapse-transition>
                        </div>

                        <!-- Backup POIs -->
                        <div
                          v-if="tour.backup_pois[poi.poi] && tour.backup_pois[poi.poi].length > 0"
                          style="margin-top: 12px; padding-left: 34px"
                        >
                          <el-collapse>
                            <el-collapse-item title="View Backup Options" name="1">
                              <div
                                v-for="backup in tour.backup_pois[poi.poi]"
                                :key="backup.poi"
                                style="padding: 10px; background: #f0f9ff; border-radius: 4px; margin-bottom: 8px"
                              >
                                <div style="font-weight: 600; margin-bottom: 4px">
                                  {{ backup.poi }}
                                  <el-tag size="small" style="margin-left: 8px">
                                    {{ (backup.similarity_score * 100).toFixed(0) }}% similar
                                  </el-tag>
                                </div>
                                <div style="font-size: 12px; color: #606266; margin-bottom: 4px">
                                  {{ backup.reason }}
                                </div>
                                <div style="font-size: 11px; color: #909399; font-style: italic">
                                  {{ backup.substitute_scenario }}
                                </div>
                              </div>
                            </el-collapse-item>
                          </el-collapse>
                        </div>
                      </div>
                    </div>
                  </el-card>

                  <!-- Walking transition to next POI -->
                  <div
                    v-if="index < day.pois.length - 1"
                    style="text-align: center; margin-bottom: 15px"
                  >
                    <el-icon :size="16" color="#909399">
                      <arrow-down />
                    </el-icon>
                    <div style="color: #909399; font-size: 12px">
                      {{ poi.walking_time_to_next || 'Walking to next POI' }}
                      <span v-if="poi.distance_to_next_km">
                        ({{ poi.distance_to_next_km.toFixed(1) }}km)
                      </span>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- Rejected POIs -->
        <el-card v-if="tour.rejected_pois.length > 0">
          <template #header>
            <span style="font-weight: 600">Rejected POIs</span>
            <el-text type="info" size="small" style="margin-left: 10px">
              ({{ tour.rejected_pois.length }} POIs not selected)
            </el-text>
          </template>

          <el-table :data="tour.rejected_pois" stripe>
            <el-table-column prop="poi" label="POI" width="200" />
            <el-table-column prop="reason" label="Rejection Reason" />
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Loading, ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'

const route = useRoute()
const loading = ref(true)
const error = ref(null)
const tour = ref(null)
const expandedTranscripts = ref({})
const transcripts = ref({})
const transcriptLoading = ref({})

// Computed total POIs
const totalPOIs = computed(() => {
  if (!tour.value) return 0
  return tour.value.itinerary.reduce((sum, day) => sum + day.pois.length, 0)
})

// Load tour details
const loadTour = async () => {
  try {
    loading.value = true
    error.value = null

    const tourId = route.params.tourId
    const response = await axios.get(`http://localhost:8000/tours/${tourId}`)
    tour.value = response.data

  } catch (err) {
    console.error('Error loading tour:', err)
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

// Toggle transcript visibility
const toggleTranscript = async (poiName) => {
  if (expandedTranscripts.value[poiName]) {
    // Collapse
    expandedTranscripts.value[poiName] = false
    return
  }

  // Expand and load if needed
  if (!transcripts.value[poiName]) {
    await loadTranscript(poiName)
  }

  expandedTranscripts.value[poiName] = true
}

// Load POI transcript
const loadTranscript = async (poiName) => {
  try {
    transcriptLoading.value[poiName] = true

    const city = tour.value.metadata.city
    const poiId = poiName.toLowerCase().replace(/ /g, '-').replace(/[()]/g, '')

    // Use the tour's language if specified, otherwise default to 'en'
    const language = tour.value.input_parameters?.language || 'en'

    const response = await axios.get(`http://localhost:8000/pois/${city}/${poiId}/transcript`, {
      params: { language }
    })
    transcripts.value[poiName] = response.data.transcript

  } catch (err) {
    console.error(`Error loading transcript for ${poiName}:`, err)
    transcripts.value[poiName] = null
  } finally {
    transcriptLoading.value[poiName] = false
  }
}

// Format date
const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Get score color type
const getScoreType = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
}

// Get priority color type
const getPriorityType = (priority) => {
  if (priority === 'high') return 'danger'
  if (priority === 'medium') return 'warning'
  return 'info'
}

onMounted(() => {
  loadTour()
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
