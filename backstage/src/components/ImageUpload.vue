<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div style="display: flex; align-items: center; gap: 8px">
          <el-icon :size="18"><Picture /></el-icon>
          <span style="font-weight: 600">{{ title }}</span>
        </div>
        <el-button v-if="!showUpload" type="primary" size="small" @click="showUpload = true">
          <el-icon><Plus /></el-icon>
          Upload Image
        </el-button>
      </div>
    </template>

    <!-- Upload Form -->
    <el-collapse-transition>
      <div v-if="showUpload" style="margin-bottom: 20px; padding: 20px; background: #f5f7fa; border-radius: 8px">
        <el-form :model="uploadForm" label-width="120px" size="default">
          <el-form-item v-if="uploadType === 'tour'" label="Image Type">
            <el-radio-group v-model="uploadForm.imageType">
              <el-radio value="cover">Cover Image</el-radio>
              <el-radio value="gallery">Gallery Image</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="Image File">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              accept="image/jpeg,image/png,image/webp"
              :on-change="handleFileChange"
              :file-list="uploadForm.fileList"
            >
              <template #trigger>
                <el-button type="primary"><el-icon><Upload /></el-icon> Select Image</el-button>
              </template>
              <template #tip>
                <div style="font-size: 12px; color: #909399; margin-top: 8px">
                  Max 5MB • JPEG, PNG, WebP • Auto-compressed
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <el-form-item label="Caption">
            <el-input v-model="uploadForm.caption" placeholder="Optional image description" />
          </el-form-item>

          <el-form-item v-if="uploadType === 'poi'" label="Set as Cover">
            <el-switch v-model="uploadForm.isCover" />
          </el-form-item>

          <el-form-item v-if="uploadType === 'tour' && uploadForm.imageType === 'gallery'" label="Display Order">
            <el-input-number v-model="uploadForm.order" :min="0" />
          </el-form-item>

          <el-form-item v-if="uploadType === 'poi'" label="Display Order">
            <el-input-number v-model="uploadForm.order" :min="0" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleUpload" :loading="uploading">
              <el-icon v-if="!uploading"><Upload /></el-icon>
              {{ uploading ? 'Uploading...' : 'Upload' }}
            </el-button>
            <el-button @click="cancelUpload">Cancel</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-collapse-transition>

    <!-- Image Gallery -->
    <ImageGallery
      :upload-type="uploadType"
      :identifier="identifier"
      :city="city"
      @refresh="$emit('uploaded')"
    />
  </el-card>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Plus, Upload } from '@element-plus/icons-vue'
import axios from 'axios'
import ImageGallery from './ImageGallery.vue'

const props = defineProps({
  uploadType: {
    type: String,
    required: true,
    validator: (value) => ['poi', 'tour'].includes(value)
  },
  identifier: {
    type: String,
    required: true
  },
  city: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: 'Images'
  }
})

const emit = defineEmits(['uploaded'])

const showUpload = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)

const uploadForm = reactive({
  imageType: 'cover', // for tours
  caption: '',
  isCover: false, // for POIs
  order: 0,
  fileList: []
})

const handleFileChange = (file, fileList) => {
  uploadForm.fileList = fileList
}

const cancelUpload = () => {
  showUpload.value = false
  uploadForm.fileList = []
  uploadForm.caption = ''
  uploadForm.isCover = false
  uploadForm.order = 0
  uploadForm.imageType = 'cover'
}

const handleUpload = async () => {
  if (uploadForm.fileList.length === 0) {
    ElMessage.warning('Please select an image file')
    return
  }

  const file = uploadForm.fileList[0].raw
  
  // Validate file size (5MB)
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('File size must be less than 5MB')
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('image', file)
    
    if (uploadForm.caption) {
      formData.append('caption', uploadForm.caption)
    }

    let url
    if (props.uploadType === 'poi') {
      url = `/pois/${props.city}/${props.identifier}/images`
      formData.append('is_cover', uploadForm.isCover)
      formData.append('order', uploadForm.order)
    } else if (props.uploadType === 'tour') {
      url = `/tours/${props.identifier}/images`
      formData.append('image_type', uploadForm.imageType)
      if (uploadForm.imageType === 'gallery') {
        formData.append('order', uploadForm.order)
      }
    }

    const response = await axios.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    ElMessage.success(response.data.message || 'Image uploaded successfully')
    cancelUpload()
    emit('uploaded')
  } catch (error) {
    console.error('Upload failed:', error)
    ElMessage.error(error.response?.data?.detail || 'Failed to upload image')
  } finally {
    uploading.value = false
  }
}
</script>
