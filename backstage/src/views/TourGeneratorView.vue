<template>
  <div class="tour-generator-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <h2 style="margin: 0">Generate New Tour</h2>
            <p style="margin: 5px 0 0; color: #909399; font-size: 14px">
              Create an AI-powered walking tour itinerary
            </p>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="180px"
        label-position="left"
        @submit.prevent="handleGenerate"
      >
        <!-- Basic Information -->
        <el-divider content-position="left">
          <el-icon><MapLocation /></el-icon>
          Basic Information
        </el-divider>

        <el-form-item label="City" prop="city" required>
          <el-select
            v-model="formData.city"
            placeholder="Select a city"
            filterable
            style="width: 300px"
          >
            <el-option label="Rome" value="rome" />
            <el-option label="Paris" value="paris" />
            <el-option label="Athens" value="athens" />
            <el-option label="London" value="london" />
          </el-select>
        </el-form-item>

        <el-form-item label="Duration" prop="days" required>
          <el-input-number
            v-model="formData.days"
            :min="1"
            :max="14"
            :step="1"
            placeholder="Number of days"
          />
          <span style="margin-left: 10px; color: #909399">days</span>
        </el-form-item>

        <el-form-item label="Language" prop="language">
          <el-select
            v-model="formData.language"
            placeholder="Select language"
            filterable
            style="width: 300px"
          >
            <el-option label="English" value="en" />
            <el-option label="Chinese (Traditional)" value="zh-tw" />
            <el-option label="Chinese (Simplified)" value="zh-cn" />
            <el-option label="Spanish" value="es" />
            <el-option label="French" value="fr" />
            <el-option label="German" value="de" />
            <el-option label="Italian" value="it" />
            <el-option label="Portuguese (Brazil)" value="pt-br" />
            <el-option label="Japanese" value="ja" />
            <el-option label="Korean" value="ko" />
          </el-select>
        </el-form-item>

        <!-- Preferences -->
        <el-divider content-position="left">
          <el-icon><Star /></el-icon>
          Interests & Preferences
        </el-divider>

        <el-form-item label="Interests" prop="interests">
          <el-select
            v-model="formData.interests"
            multiple
            placeholder="Select interests (optional)"
            style="width: 500px"
          >
            <el-option label="History" value="history" />
            <el-option label="Architecture" value="architecture" />
            <el-option label="Art" value="art" />
            <el-option label="Culture" value="culture" />
            <el-option label="Food" value="food" />
            <el-option label="Shopping" value="shopping" />
            <el-option label="Nature" value="nature" />
            <el-option label="Museums" value="museums" />
            <el-option label="Religion" value="religion" />
            <el-option label="Ancient Sites" value="ancient" />
          </el-select>
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            Select topics that interest you (multiple selections allowed)
          </div>
        </el-form-item>

        <el-form-item label="Must-See POIs" prop="mustSee">
          <el-select
            v-model="formData.mustSee"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="Enter POI names (optional)"
            style="width: 500px"
          >
            <el-option
              v-for="poi in availablePOIs"
              :key="poi"
              :label="poi"
              :value="poi"
            />
          </el-select>
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            POIs that must be included in the itinerary
          </div>
        </el-form-item>

        <el-form-item label="Pace" prop="pace">
          <el-radio-group v-model="formData.pace">
            <el-radio label="relaxed">
              <div style="display: inline-block">
                <div>Relaxed</div>
                <div style="font-size: 12px; color: #909399">Fewer POIs, more time</div>
              </div>
            </el-radio>
            <el-radio label="normal">
              <div style="display: inline-block">
                <div>Normal</div>
                <div style="font-size: 12px; color: #909399">Balanced schedule</div>
              </div>
            </el-radio>
            <el-radio label="packed">
              <div style="display: inline-block">
                <div>Packed</div>
                <div style="font-size: 12px; color: #909399">More POIs, faster pace</div>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Walking Tolerance" prop="walking">
          <el-radio-group v-model="formData.walking">
            <el-radio label="low">
              <div style="display: inline-block">
                <div>Low</div>
                <div style="font-size: 12px; color: #909399">Minimize walking</div>
              </div>
            </el-radio>
            <el-radio label="moderate">
              <div style="display: inline-block">
                <div>Moderate</div>
                <div style="font-size: 12px; color: #909399">Average walking</div>
              </div>
            </el-radio>
            <el-radio label="high">
              <div style="display: inline-block">
                <div>High</div>
                <div style="font-size: 12px; color: #909399">Comfortable with long walks</div>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- Advanced Options -->
        <el-divider content-position="left">
          <el-icon><Setting /></el-icon>
          Advanced Options
        </el-divider>

        <el-form-item label="Optimization Mode" prop="mode">
          <el-radio-group v-model="formData.mode">
            <el-radio label="simple">
              <div style="display: inline-block">
                <div>Simple (Fast)</div>
                <div style="font-size: 12px; color: #909399">Greedy + 2-opt, ~3 seconds</div>
              </div>
            </el-radio>
            <el-radio label="ilp">
              <div style="display: inline-block">
                <div>ILP (Optimal)</div>
                <div style="font-size: 12px; color: #909399">Integer Linear Programming, 5-30 seconds</div>
              </div>
            </el-radio>
          </el-radio-group>
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            ILP mode supports combo tickets, opening hours, and precedence constraints
          </div>
        </el-form-item>

        <el-form-item label="AI Provider" prop="provider">
          <el-select v-model="formData.provider" style="width: 200px">
            <el-option label="Anthropic (Claude)" value="anthropic" />
            <el-option label="OpenAI (GPT)" value="openai" />
            <el-option label="Google (Gemini)" value="google" />
          </el-select>
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            AI provider for POI selection
          </div>
        </el-form-item>

        <el-form-item label="Start Location" prop="startLocation">
          <el-input
            v-model="formData.startLocation"
            placeholder="POI name or coordinates (lat,lng)"
            style="width: 400px"
          />
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            Starting point for the tour (optional, e.g., "Hotel Rome" or "41.8902,12.4922")
          </div>
        </el-form-item>

        <el-form-item label="End Location" prop="endLocation">
          <el-input
            v-model="formData.endLocation"
            placeholder="POI name or coordinates (lat,lng)"
            style="width: 400px"
          />
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            Ending point for the tour (optional)
          </div>
        </el-form-item>

        <el-form-item label="Start Date" prop="startDate">
          <el-date-picker
            v-model="formData.startDate"
            type="date"
            placeholder="Select start date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 200px"
          />
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            Used to check opening hours (optional)
          </div>
        </el-form-item>

        <!-- Actions -->
        <el-divider />

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="generating"
            :disabled="generating"
            @click="handleGenerate"
            :icon="Promotion"
          >
            {{ generating ? 'Generating Tour...' : 'Generate Tour' }}
          </el-button>
          <el-button
            size="large"
            @click="handleReset"
            :disabled="generating"
          >
            Reset
          </el-button>
        </el-form-item>

        <!-- Generation Progress -->
        <el-alert
          v-if="generating"
          type="info"
          :closable="false"
          style="margin-top: 20px"
        >
          <template #title>
            <div style="display: flex; align-items: center; gap: 10px">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>{{ generationStatus }}</span>
            </div>
          </template>
          <div v-if="generationProgress" style="margin-top: 10px">
            <el-progress :percentage="generationProgress" />
          </div>
        </el-alert>

        <!-- Success Message -->
        <el-alert
          v-if="generatedTourId"
          type="success"
          :closable="false"
          style="margin-top: 20px"
        >
          <template #title>
            Tour Generated Successfully!
          </template>
          <div style="margin-top: 10px">
            <el-button type="primary" @click="viewTour" :icon="View">
              View Tour
            </el-button>
            <el-button @click="generateAnother">
              Generate Another
            </el-button>
          </div>
        </el-alert>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  MapLocation, Star, Setting, Promotion, Loading, View
} from '@element-plus/icons-vue'
import tourAPI from '../api/tour'
import metadataAPI from '../api/metadata'

const router = useRouter()

// State
const formRef = ref(null)
const generating = ref(false)
const generationStatus = ref('')
const generationProgress = ref(0)
const generatedTourId = ref(null)
const availablePOIs = ref([])

const formData = ref({
  city: 'rome',
  days: 3,
  interests: [],
  provider: 'anthropic',
  mustSee: [],
  pace: 'normal',
  walking: 'moderate',
  language: 'en',
  mode: 'simple',
  startLocation: '',
  endLocation: '',
  startDate: null
})

// Validation rules
const rules = {
  city: [
    { required: true, message: 'Please select a city', trigger: 'change' }
  ],
  days: [
    { required: true, message: 'Please enter number of days', trigger: 'blur' },
    { type: 'number', min: 1, max: 14, message: 'Duration must be 1-14 days', trigger: 'blur' }
  ]
}

// Methods
const loadAvailablePOIs = async () => {
  if (!formData.value.city) return

  try {
    const response = await metadataAPI.getCityPOIs(formData.value.city)
    if (response.pois && Array.isArray(response.pois)) {
      availablePOIs.value = response.pois.map(poi => poi.poi_name || poi.name || poi)
    }
  } catch (error) {
    console.error('Failed to load POIs:', error)
    availablePOIs.value = []
  }
}

const handleGenerate = async () => {
  try {
    // Validate form
    await formRef.value.validate()

    generating.value = true
    generationStatus.value = 'Initializing tour generation...'
    generationProgress.value = 10

    // Prepare request data
    const requestData = {
      city: formData.value.city,
      days: formData.value.days,
      interests: formData.value.interests,
      provider: formData.value.provider,
      must_see: formData.value.mustSee,
      pace: formData.value.pace,
      walking: formData.value.walking,
      language: formData.value.language,
      mode: formData.value.mode,
      start_location: formData.value.startLocation || null,
      end_location: formData.value.endLocation || null,
      start_date: formData.value.startDate || null,
      save: true
    }

    generationStatus.value = 'Selecting POIs with AI...'
    generationProgress.value = 30

    // Call API to generate tour
    const response = await tourAPI.generateTour(requestData)

    generationStatus.value = 'Tour generated successfully!'
    generationProgress.value = 100

    generatedTourId.value = response.tour_id

    ElMessage.success({
      message: `Tour "${response.tour_id}" generated successfully!`,
      duration: 5000
    })

  } catch (error) {
    console.error('Tour generation error:', error)
    ElMessage.error({
      message: error.message || 'Failed to generate tour',
      duration: 5000
    })
    generationStatus.value = ''
    generationProgress.value = 0
  } finally {
    generating.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
  formData.value = {
    city: 'rome',
    days: 3,
    interests: [],
    provider: 'anthropic',
    mustSee: [],
    pace: 'normal',
    walking: 'moderate',
    language: 'en',
    mode: 'simple',
    startLocation: '',
    endLocation: '',
    startDate: null
  }
  generatedTourId.value = null
  generationStatus.value = ''
  generationProgress.value = 0
}

const viewTour = () => {
  if (generatedTourId.value) {
    router.push(`/tours/${generatedTourId.value}`)
  }
}

const generateAnother = () => {
  generatedTourId.value = null
  generationStatus.value = ''
  generationProgress.value = 0
}

// Watch city changes to reload POIs
watch(() => formData.value.city, () => {
  loadAvailablePOIs()
})

// Lifecycle
onMounted(() => {
  loadAvailablePOIs()
})
</script>

<style scoped>
.tour-generator-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-radio) {
  display: block;
  margin-bottom: 15px;
  height: auto;
  line-height: 1.5;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-divider__text) {
  background-color: #f5f7fa;
  padding: 0 20px;
  font-weight: 600;
  color: #303133;
}
</style>
