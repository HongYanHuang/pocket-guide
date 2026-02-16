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
          <Loading />
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
        <!-- Route Overview Card -->
        <el-card
          v-if="tour.input_parameters.start_location || tour.input_parameters.end_location"
          style="margin-bottom: 20px; background: linear-gradient(to right, #f0f9ff, #e0f2fe)"
        >
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon :size="18"><Guide /></el-icon>
              <span style="font-weight: 600">Journey Route</span>
            </div>
          </template>

          <div style="display: flex; align-items: center; justify-content: center; gap: 20px; padding: 20px 0">
            <!-- Start Location -->
            <div v-if="tour.input_parameters.start_location" class="route-point">
              <div class="route-icon start-icon">
                <el-icon :size="24"><LocationInformation /></el-icon>
              </div>
              <div style="margin-top: 10px; text-align: center">
                <div style="font-size: 12px; color: #67c23a; font-weight: 600; margin-bottom: 5px">
                  START POINT
                </div>
                <div style="font-size: 14px; font-weight: 500">
                  {{ tour.input_parameters.start_location }}
                </div>
              </div>
            </div>

            <!-- Arrow / Days -->
            <div v-if="tour.input_parameters.start_location || tour.input_parameters.end_location" style="display: flex; flex-direction: column; align-items: center; margin: 0 20px">
              <el-icon :size="30" style="color: #409eff"><Right /></el-icon>
              <el-tag size="small" style="margin-top: 10px" type="info">
                {{ tour.itinerary.length }} day{{ tour.itinerary.length > 1 ? 's' : '' }} · {{ totalPOIs }} POIs
              </el-tag>
            </div>

            <!-- End Location -->
            <div v-if="tour.input_parameters.end_location" class="route-point">
              <div class="route-icon end-icon">
                <el-icon :size="24"><Location /></el-icon>
              </div>
              <div style="margin-top: 10px; text-align: center">
                <div style="font-size: 12px; color: #e6a23c; font-weight: 600; margin-bottom: 5px">
                  END POINT
                </div>
                <div style="font-size: 14px; font-weight: 500">
                  {{ tour.input_parameters.end_location }}
                </div>
              </div>
            </div>

            <!-- Message when neither is set -->
            <div v-if="!tour.input_parameters.start_location && !tour.input_parameters.end_location" style="color: #909399; text-align: center">
              <el-icon :size="24"><Guide /></el-icon>
              <div style="margin-top: 10px">No specific start or end location set</div>
            </div>
          </div>
        </el-card>

        <!-- Tour Map -->
        <el-card style="margin-bottom: 20px">
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon :size="18"><Location /></el-icon>
              <span style="font-weight: 600">Interactive Map</span>
            </div>
          </template>
          <TourMap :tour="tour" />
        </el-card>

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
            <el-descriptions-item label="Start Location" :span="2" v-if="tour.input_parameters.start_location">
              <el-tag type="success" size="small">
                <el-icon style="margin-right: 5px"><LocationInformation /></el-icon>
                {{ tour.input_parameters.start_location }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="End Location" :span="2" v-if="tour.input_parameters.end_location">
              <el-tag type="warning" size="small">
                <el-icon style="margin-right: 5px"><Location /></el-icon>
                {{ tour.input_parameters.end_location }}
              </el-tag>
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
                    <div style="display: flex; align-items: center; gap: 10px">
                      <span style="font-weight: 600">Day {{ day.day }}</span>
                      <!-- Start location indicator for Day 1 -->
                      <el-tag
                        v-if="day.day === 1 && tour.input_parameters.start_location"
                        size="small"
                        type="success"
                      >
                        <el-icon style="margin-right: 3px"><LocationInformation /></el-icon>
                        Starts from: {{ tour.input_parameters.start_location }}
                      </el-tag>
                      <!-- End location indicator for last day -->
                      <el-tag
                        v-if="day.day === tour.itinerary.length && tour.input_parameters.end_location"
                        size="small"
                        type="warning"
                      >
                        <el-icon style="margin-right: 3px"><Location /></el-icon>
                        Ends at: {{ tour.input_parameters.end_location }}
                      </el-tag>
                    </div>
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

                <!-- Start Location Card (Day 1 only) -->
                <el-card
                  v-if="day.day === 1 && tour.input_parameters.start_location"
                  shadow="hover"
                  :body-style="{ padding: '15px' }"
                  style="margin-bottom: 15px; border-left: 3px solid #67c23a"
                >
                  <div style="display: flex; justify-content: space-between; align-items: start">
                    <div style="flex: 1">
                      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
                        <span style="
                          background: linear-gradient(135deg, #67c23a, #85ce61);
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
                          <el-icon :size="14"><LocationInformation /></el-icon>
                        </span>
                        <span style="font-weight: 600; font-size: 15px">
                          {{ tour.input_parameters.start_location }}
                        </span>
                        <el-tag size="small" type="success">
                          Start Point
                        </el-tag>
                      </div>

                      <div style="color: #606266; font-size: 13px; margin-bottom: 10px; padding-left: 34px">
                        Your journey begins here
                      </div>
                    </div>
                  </div>
                </el-card>

                <!-- Walking transition from start location to first POI -->
                <div
                  v-if="day.day === 1 && tour.input_parameters.start_location && day.pois.length > 0"
                  style="text-align: center; margin-bottom: 15px"
                >
                  <el-icon :size="16" color="#909399">
                    <ArrowDown />
                  </el-icon>
                  <div style="color: #909399; font-size: 12px">
                    Walking to first POI
                  </div>
                </div>

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
                          <span style="font-weight: 600; font-size: 15px">
                            <span :style="{ textDecoration: hasPendingReplacement(poi.poi) ? 'line-through' : 'none', opacity: hasPendingReplacement(poi.poi) ? 0.5 : 1 }">
                              {{ poi.poi }}
                            </span>
                            <span v-if="hasPendingReplacement(poi.poi)" style="color: #67C23A; font-weight: 600">
                              → {{ getPendingReplacement(poi.poi).replacement_poi }}
                            </span>
                          </span>
                          <el-tag size="small" :type="getPriorityType(poi.priority)">
                            {{ poi.priority }}
                          </el-tag>
                          <el-tag v-if="hasPendingReplacement(poi.poi)" size="small" type="success">
                            Pending
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
                          v-if="getEffectiveBackupPOIs(poi.poi).length > 0"
                          style="margin-top: 12px; padding-left: 34px"
                        >
                          <!-- Pending Replacement Notice -->
                          <el-alert
                            v-if="hasPendingReplacement(poi.poi)"
                            type="success"
                            :closable="false"
                            style="margin-bottom: 10px"
                          >
                            <div style="display: flex; justify-content: space-between; align-items: center">
                              <span>
                                Queued: {{ poi.poi }} → {{ getPendingReplacement(poi.poi).replacement_poi }}
                              </span>
                              <el-button
                                size="small"
                                @click="removePendingReplacement(poi.poi)"
                              >
                                Undo
                              </el-button>
                            </div>
                          </el-alert>

                          <el-collapse>
                            <el-collapse-item title="View Backup Options" name="1">
                              <div
                                v-for="backup in getEffectiveBackupPOIs(poi.poi)"
                                :key="backup.poi"
                                style="padding: 10px; background: #f0f9ff; border-radius: 4px; margin-bottom: 8px"
                                :style="{ opacity: isBackupPOIAvailable(backup.poi) ? 1 : 0.5 }"
                              >
                                <div style="display: flex; justify-content: space-between; align-items: start">
                                  <div style="flex: 1">
                                    <div style="font-weight: 600; margin-bottom: 4px">
                                      {{ backup.poi }}
                                      <el-tag size="small" style="margin-left: 8px">
                                        {{ (backup.similarity_score * 100).toFixed(0) }}% similar
                                      </el-tag>
                                      <el-tag
                                        v-if="!isBackupPOIAvailable(backup.poi)"
                                        size="small"
                                        type="info"
                                        style="margin-left: 8px"
                                      >
                                        Already selected
                                      </el-tag>
                                    </div>
                                    <div style="font-size: 12px; color: #606266; margin-bottom: 4px">
                                      {{ backup.reason }}
                                    </div>
                                    <div style="font-size: 11px; color: #909399; font-style: italic">
                                      {{ backup.substitute_scenario }}
                                    </div>
                                  </div>

                                  <!-- Replace Button -->
                                  <el-button
                                    type="primary"
                                    size="small"
                                    @click="addPendingReplacement(poi.poi, backup, day.day)"
                                    :disabled="!isBackupPOIAvailable(backup.poi)"
                                  >
                                    Replace
                                  </el-button>
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
                      <ArrowDown />
                    </el-icon>
                    <div style="color: #909399; font-size: 12px">
                      {{ poi.walking_time_to_next || 'Walking to next POI' }}
                      <span v-if="poi.distance_to_next_km">
                        ({{ poi.distance_to_next_km.toFixed(1) }}km)
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Walking transition from last POI to end location -->
                <div
                  v-if="day.day === tour.itinerary.length && tour.input_parameters.end_location && day.pois.length > 0"
                  style="text-align: center; margin-bottom: 15px"
                >
                  <el-icon :size="16" color="#909399">
                    <ArrowDown />
                  </el-icon>
                  <div style="color: #909399; font-size: 12px">
                    Walking to end point
                  </div>
                </div>

                <!-- End Location Card (Last day only) -->
                <el-card
                  v-if="day.day === tour.itinerary.length && tour.input_parameters.end_location"
                  shadow="hover"
                  :body-style="{ padding: '15px' }"
                  style="border-left: 3px solid #e6a23c"
                >
                  <div style="display: flex; justify-content: space-between; align-items: start">
                    <div style="flex: 1">
                      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
                        <span style="
                          background: linear-gradient(135deg, #e6a23c, #f0c78a);
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
                          <el-icon :size="14"><Location /></el-icon>
                        </span>
                        <span style="font-weight: 600; font-size: 15px">
                          {{ tour.input_parameters.end_location }}
                        </span>
                        <el-tag size="small" type="warning">
                          End Point
                        </el-tag>
                      </div>

                      <div style="color: #606266; font-size: 13px; margin-bottom: 10px; padding-left: 34px">
                        Your journey ends here
                      </div>
                    </div>
                  </div>
                </el-card>
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

    <!-- Floating Action Bar for Pending Replacements -->
    <transition name="el-fade-in">
      <div
        v-if="pendingReplacementsCount > 0"
        style="
          position: fixed;
          bottom: 30px;
          left: 50%;
          transform: translateX(-50%);
          background: white;
          padding: 20px 30px;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          z-index: 1000;
          min-width: 600px;
        "
      >
        <div style="display: flex; align-items: center; gap: 20px">
          <!-- Count -->
          <div style="display: flex; align-items: center; gap: 10px">
            <el-tag type="warning" size="large">
              {{ pendingReplacementsCount }} Pending Replacement{{ pendingReplacementsCount > 1 ? 's' : '' }}
            </el-tag>
          </div>

          <!-- Info -->
          <div style="font-size: 12px; color: #909399">
            Keep current order and timing
          </div>

          <!-- Actions -->
          <div style="display: flex; gap: 10px; margin-left: auto">
            <el-button @click="discardAllReplacements" :disabled="savingReplacements">
              Discard All
            </el-button>
            <el-button
              type="primary"
              @click="saveAllReplacements"
              :loading="savingReplacements"
            >
              Save Changes
            </el-button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Loading, ArrowDown, LocationInformation, Location, Guide, Right } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import TourMap from '../components/TourMap.vue'

const route = useRoute()
const loading = ref(true)
const error = ref(null)
const tour = ref(null)
const expandedTranscripts = ref({})
const transcripts = ref({})
const transcriptLoading = ref({})

// POI Replacement state
const pendingReplacements = ref({}) // Map: original_poi -> { replacement_poi, day }
const savingReplacements = ref(false)

// Computed total POIs
const totalPOIs = computed(() => {
  if (!tour.value) return 0
  return tour.value.itinerary.reduce((sum, day) => sum + day.pois.length, 0)
})

// Get all currently selected POIs (including pending replacements)
const currentSelectedPOIs = computed(() => {
  if (!tour.value) return new Set()

  const pois = new Set()

  for (const day of tour.value.itinerary) {
    for (const poi of day.pois) {
      const originalPoi = poi.poi

      // If this POI has a pending replacement, use the replacement instead
      if (pendingReplacements.value[originalPoi]) {
        pois.add(pendingReplacements.value[originalPoi].replacement_poi)
      } else {
        pois.add(originalPoi)
      }
    }
  }

  return pois
})

// Get backup POIs for a POI - simple, just return what's in tour.backup_pois
const getEffectiveBackupPOIs = (originalPoiName) => {
  if (!tour.value) return []

  // Simply return the backup POIs from tour data
  return tour.value.backup_pois[originalPoiName] || []
}

// Check if a backup POI is available (not already selected)
const isBackupPOIAvailable = (backupPoiName) => {
  // Just check if this POI is not already in the current selection
  return !currentSelectedPOIs.value.has(backupPoiName)
}

// Check if a POI has pending replacement
const hasPendingReplacement = (poiName) => {
  return !!pendingReplacements.value[poiName]
}

// Get pending replacement for a POI
const getPendingReplacement = (poiName) => {
  return pendingReplacements.value[poiName]
}

// Count of pending replacements
const pendingReplacementsCount = computed(() => {
  return Object.keys(pendingReplacements.value).length
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
      params: {
        language,
        tour_id: tour.value.metadata.tour_id  // Include tour context for linked transcripts
      }
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

// Add a pending replacement
const addPendingReplacement = (originalPoi, backupPoi, dayNum) => {
  pendingReplacements.value[originalPoi] = {
    replacement_poi: backupPoi.poi,
    day: dayNum
  }

  ElMessage.info({
    message: `Queued replacement: ${originalPoi} → ${backupPoi.poi}`,
    duration: 2000
  })
}

// Remove a pending replacement
const removePendingReplacement = (originalPoi) => {
  delete pendingReplacements.value[originalPoi]
  ElMessage.info({
    message: 'Replacement removed from queue',
    duration: 2000
  })
}

// Discard all pending replacements
const discardAllReplacements = () => {
  pendingReplacements.value = {}
  ElMessage.info({
    message: 'All pending replacements discarded',
    duration: 2000
  })
}

// Save all pending replacements
const saveAllReplacements = async () => {
  const replacementsList = Object.keys(pendingReplacements.value)

  if (replacementsList.length === 0) {
    ElMessage.warning({
      message: 'No pending replacements to save',
      duration: 2000
    })
    return
  }

  try {
    savingReplacements.value = true

    const tourId = route.params.tourId
    const language = tour.value.input_parameters?.language || 'en'

    // Build replacements array for API
    const replacements = replacementsList.map(originalPoi => ({
      original_poi: originalPoi,
      replacement_poi: pendingReplacements.value[originalPoi].replacement_poi,
      day: pendingReplacements.value[originalPoi].day
    }))

    const response = await axios.post(
      `http://localhost:8000/tours/${tourId}/replace-pois-batch`,
      {
        replacements: replacements,
        mode: 'simple',
        language: language
      }
    )

    // Success - show message and reload tour
    ElMessage.success({
      message: response.data.message || `Successfully replaced ${replacementsList.length} POI(s)`,
      duration: 3000
    })

    // Clear pending replacements
    pendingReplacements.value = {}

    // Reload tour to show updated data
    await loadTour()

  } catch (err) {
    console.error('Error replacing POIs:', err)
    ElMessage.error({
      message: err.response?.data?.detail || 'Failed to replace POIs',
      duration: 5000
    })
  } finally {
    savingReplacements.value = false
  }
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

/* Route display styles */
.route-point {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.route-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.route-icon:hover {
  transform: scale(1.1);
}

.start-icon {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.end-icon {
  background: linear-gradient(135deg, #e6a23c, #f0c78a);
}
</style>
