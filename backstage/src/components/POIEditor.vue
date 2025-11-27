<template>
  <el-dialog
    v-model="dialogVisible"
    title="Edit POI Metadata"
    width="600px"
    @close="onClose"
  >
    <el-form :model="formData" label-width="150px">
      <el-divider content-position="left">Coordinates</el-divider>

      <el-form-item label="Latitude">
        <el-input-number
          v-model="formData.coordinates.latitude"
          :min="-90"
          :max="90"
          :precision="6"
          :step="0.000001"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="Longitude">
        <el-input-number
          v-model="formData.coordinates.longitude"
          :min="-180"
          :max="180"
          :precision="6"
          :step="0.000001"
          style="width: 100%"
        />
      </el-form-item>

      <el-divider content-position="left">Visit Information</el-divider>

      <el-form-item label="Indoor/Outdoor">
        <el-select v-model="formData.visit_info.indoor_outdoor" style="width: 100%">
          <el-option label="Indoor" value="indoor" />
          <el-option label="Outdoor" value="outdoor" />
          <el-option label="Mixed" value="mixed" />
          <el-option label="Unknown" value="unknown" />
        </el-select>
      </el-form-item>

      <el-form-item label="Duration (minutes)">
        <el-input-number
          v-model="formData.visit_info.typical_duration_minutes"
          :min="1"
          :max="480"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="Accessibility">
        <el-input v-model="formData.visit_info.accessibility" />
      </el-form-item>

      <el-divider content-position="left">Additional Info</el-divider>

      <el-form-item label="Address">
        <el-input v-model="formData.address" type="textarea" :rows="2" />
      </el-form-item>

      <el-form-item label="Phone">
        <el-input v-model="formData.phone" />
      </el-form-item>

      <el-form-item label="Website">
        <el-input v-model="formData.website" />
      </el-form-item>

      <el-form-item label="Wheelchair">
        <el-checkbox v-model="formData.wheelchair_accessible">
          Wheelchair Accessible
        </el-checkbox>
      </el-form-item>

      <el-form-item label="Verified">
        <el-checkbox v-model="formData.verified">
          Metadata Verified
        </el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">Cancel</el-button>
      <el-button type="primary" @click="save" :loading="saving">Save</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/metadata'

const props = defineProps({
  visible: Boolean,
  city: String,
  poiId: String,
  initialData: Object
})

const emit = defineEmits(['update:visible', 'saved'])

const dialogVisible = ref(props.visible)
const saving = ref(false)
const formData = ref({
  coordinates: {
    latitude: 0,
    longitude: 0
  },
  visit_info: {
    indoor_outdoor: 'unknown',
    typical_duration_minutes: 30,
    accessibility: ''
  },
  address: '',
  phone: '',
  website: '',
  wheelchair_accessible: false,
  verified: false
})

watch(() => props.visible, (val) => {
  dialogVisible.value = val
  if (val && props.initialData) {
    loadInitialData()
  }
})

watch(dialogVisible, (val) => {
  emit('update:visible', val)
})

const loadInitialData = () => {
  if (props.initialData?.coordinates) {
    formData.value.coordinates = {
      latitude: props.initialData.coordinates.latitude || 0,
      longitude: props.initialData.coordinates.longitude || 0
    }
  }

  if (props.initialData?.visit_info) {
    formData.value.visit_info = {
      indoor_outdoor: props.initialData.visit_info.indoor_outdoor || 'unknown',
      typical_duration_minutes: props.initialData.visit_info.typical_duration_minutes || 30,
      accessibility: props.initialData.visit_info.accessibility || ''
    }
  }

  formData.value.address = props.initialData?.address || ''
  formData.value.phone = props.initialData?.phone || ''
  formData.value.website = props.initialData?.website || ''
  formData.value.wheelchair_accessible = props.initialData?.wheelchair_accessible || false
  formData.value.verified = props.initialData?.verified || false
}

const save = async () => {
  if (!props.city || !props.poiId) {
    ElMessage.error('Missing city or POI ID')
    return
  }

  saving.value = true
  try {
    await api.updatePOI(props.city, props.poiId, formData.value)
    ElMessage.success('POI metadata updated successfully')
    emit('saved')
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error('Failed to update POI: ' + error.message)
  } finally {
    saving.value = false
  }
}

const onClose = () => {
  emit('update:visible', false)
}
</script>
