<template>
  <div class="transcript-view">
    <el-page-header @back="goBack" :content="`Transcript: ${poiName}`" />

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

    <el-alert
      v-else-if="!data.has_transcript && !data.has_summary"
      type="warning"
      title="No transcript or summary found for this POI"
      show-icon
      :closable="false"
    />

    <div v-else class="content-container">
      <el-row :gutter="20">
        <!-- Transcript Column -->
        <el-col :xs="24" :md="16">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>Transcript</span>
                <div>
                  <el-button
                    v-if="!isEditing && data.has_transcript"
                    type="primary"
                    size="small"
                    @click="startEditing"
                  >
                    Edit
                  </el-button>
                  <template v-if="isEditing">
                    <el-button
                      size="small"
                      @click="cancelEditing"
                    >
                      Cancel
                    </el-button>
                    <el-button
                      type="primary"
                      size="small"
                      @click="saveTranscript"
                      :loading="saving"
                    >
                      Save
                    </el-button>
                  </template>
                </div>
              </div>
            </template>

            <div v-if="!data.has_transcript">
              <el-empty description="No transcript available" />
            </div>
            <div v-else-if="!isEditing" class="transcript-content">
              {{ data.transcript }}
            </div>
            <el-input
              v-else
              v-model="editedTranscript"
              type="textarea"
              :rows="20"
              placeholder="Enter transcript content..."
              class="transcript-editor"
            />
          </el-card>
        </el-col>

        <!-- Summary Column -->
        <el-col :xs="24" :md="8">
          <el-card class="summary-card sticky">
            <template #header>
              <h3>Summary Points</h3>
            </template>

            <div v-if="!data.has_summary">
              <el-empty description="No summary available" :image-size="60" />
            </div>
            <ul v-else-if="data.summary && data.summary.length" class="summary-list">
              <li v-for="(point, index) in data.summary" :key="index">
                {{ point }}
              </li>
            </ul>
            <el-empty v-else description="Summary file exists but is empty" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import metadataAPI from '../api/metadata'

const route = useRoute()
const router = useRouter()

const city = computed(() => route.params.city)
const poiId = computed(() => route.params.poiId)
const poiName = computed(() => poiId.value.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))

const loading = ref(true)
const error = ref(null)
const data = ref({
  transcript: null,
  summary: null,
  has_transcript: false,
  has_summary: false
})

const isEditing = ref(false)
const editedTranscript = ref('')
const originalTranscript = ref('')
const saving = ref(false)

const fetchTranscript = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await metadataAPI.getTranscript(city.value, poiId.value)
    data.value = response
    originalTranscript.value = response.transcript || ''
  } catch (err) {
    error.value = err.message || 'Failed to load transcript'
    console.error('Error fetching transcript:', err)
  } finally {
    loading.value = false
  }
}

const startEditing = () => {
  editedTranscript.value = data.value.transcript || ''
  isEditing.value = true
}

const cancelEditing = async () => {
  if (editedTranscript.value !== originalTranscript.value) {
    try {
      await ElMessageBox.confirm(
        'You have unsaved changes. Are you sure you want to cancel?',
        'Confirm Cancel',
        {
          confirmButtonText: 'Yes, cancel',
          cancelButtonText: 'No, keep editing',
          type: 'warning'
        }
      )
      isEditing.value = false
      editedTranscript.value = ''
    } catch {
      // User clicked "No, keep editing"
    }
  } else {
    isEditing.value = false
    editedTranscript.value = ''
  }
}

const saveTranscript = async () => {
  if (!editedTranscript.value.trim()) {
    ElMessage.warning('Transcript cannot be empty')
    return
  }

  try {
    await ElMessageBox.confirm(
      'This will create a backup of the current transcript and save your changes. Continue?',
      'Confirm Save',
      {
        confirmButtonText: 'Save',
        cancelButtonText: 'Cancel',
        type: 'info'
      }
    )

    saving.value = true

    const response = await metadataAPI.updateTranscript(
      city.value,
      poiId.value,
      editedTranscript.value
    )

    data.value.transcript = editedTranscript.value
    originalTranscript.value = editedTranscript.value
    isEditing.value = false

    const backupFile = response.data?.backup_file
    if (backupFile) {
      ElMessage.success({
        message: `Transcript saved successfully! Backup created: ${backupFile}`,
        duration: 5000
      })
    } else {
      ElMessage.success('Transcript saved successfully!')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.message || 'Failed to save transcript')
      console.error('Error saving transcript:', err)
    }
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchTranscript()
})
</script>

<style scoped>
.transcript-view {
  padding: 20px;
}

.loading-container {
  margin-top: 20px;
}

.content-container {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.transcript-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 15px;
  color: #303133;
  max-height: 600px;
  overflow-y: auto;
}

.transcript-editor {
  font-family: inherit;
}

:deep(.transcript-editor textarea) {
  line-height: 1.8;
  font-size: 15px;
}

.summary-card {
  height: fit-content;
}

.summary-card.sticky {
  position: sticky;
  top: 20px;
}

.summary-card h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.summary-list {
  margin: 0;
  padding-left: 20px;
  list-style-type: disc;
}

.summary-list li {
  margin-bottom: 12px;
  line-height: 1.6;
  color: #606266;
}
</style>
