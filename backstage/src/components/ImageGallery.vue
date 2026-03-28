<template>
  <div v-loading="loading">
    <!-- No images state -->
    <el-empty v-if="!loading && images.length === 0" description="No images uploaded yet" :image-size="80" />

    <!-- Tour Images (Cover + Gallery) -->
    <div v-else-if="uploadType === 'tour' && !loading">
      <!-- Cover Image -->
      <div v-if="coverImage" style="margin-bottom: 30px">
        <div style="font-weight: 600; margin-bottom: 12px; color: #303133">
          <el-icon><Star /></el-icon>
          Cover Image
        </div>
        <el-card :body-style="{ padding: '0' }" shadow="hover">
          <img
            :src="coverImage.url"
            :alt="coverImage.caption || 'Cover'"
            style="width: 100%; height: 300px; object-fit: cover; cursor: pointer"
            @click="previewImage(coverImage.url)"
          />
          <div style="padding: 15px">
            <div style="font-weight: 500; margin-bottom: 8px">
              {{ coverImage.caption || 'No caption' }}
            </div>
            <div style="font-size: 12px; color: #909399; margin-bottom: 10px">
              Uploaded {{ formatDate(coverImage.uploaded_at) }} by {{ coverImage.uploaded_by }}
            </div>
            <el-button
              type="danger"
              size="small"
              :loading="deleting === coverImage.filename"
              @click="handleDelete(coverImage.filename)"
            >
              <el-icon><Delete /></el-icon>
              Delete
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- Gallery Images -->
      <div v-if="galleryImages.length > 0">
        <div style="font-weight: 600; margin-bottom: 12px; color: #303133">
          <el-icon><PictureFilled /></el-icon>
          Gallery ({{ galleryImages.length }})
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px">
          <el-card
            v-for="img in galleryImages"
            :key="img.filename"
            :body-style="{ padding: '0' }"
            shadow="hover"
          >
            <img
              :src="img.url"
              :alt="img.caption || 'Gallery'"
              style="width: 100%; height: 200px; object-fit: cover; cursor: pointer"
              @click="previewImage(img.url)"
            />
            <div style="padding: 12px">
              <div style="font-weight: 500; margin-bottom: 6px; font-size: 14px">
                {{ img.caption || 'No caption' }}
              </div>
              <div style="font-size: 11px; color: #909399; margin-bottom: 8px">
                Order: {{ img.order }} • {{ formatDate(img.uploaded_at) }}
              </div>
              <el-button
                type="danger"
                size="small"
                :loading="deleting === img.filename"
                @click="handleDelete(img.filename)"
              >
                <el-icon><Delete /></el-icon>
                Delete
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- POI Images -->
    <div v-else-if="uploadType === 'poi' && !loading && images.length > 0">
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px">
        <el-card
          v-for="img in images"
          :key="img.filename"
          :body-style="{ padding: '0' }"
          shadow="hover"
        >
          <el-tag
            v-if="img.is_cover"
            type="warning"
            size="small"
            style="position: absolute; top: 10px; left: 10px; z-index: 1"
          >
            <el-icon><Star /></el-icon>
            Cover
          </el-tag>
          <img
            :src="img.url"
            :alt="img.caption || 'POI'"
            style="width: 100%; height: 200px; object-fit: cover; cursor: pointer"
            @click="previewImage(img.url)"
          />
          <div style="padding: 12px">
            <div style="font-weight: 500; margin-bottom: 6px; font-size: 14px">
              {{ img.caption || 'No caption' }}
            </div>
            <div style="font-size: 11px; color: #909399; margin-bottom: 8px">
              Order: {{ img.order }} • {{ formatDate(img.uploaded_at) }}
            </div>
            <el-button
              type="danger"
              size="small"
              :loading="deleting === img.filename"
              @click="handleDelete(img.filename)"
            >
              <el-icon><Delete /></el-icon>
              Delete
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Image Preview Dialog -->
    <el-image-viewer
      v-if="previewUrl"
      :url-list="[previewUrl]"
      @close="previewUrl = null"
      teleported
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, Delete, PictureFilled } from '@element-plus/icons-vue'
import apiClient from '../api/client'

const props = defineProps({
  uploadType: {
    type: String,
    required: true
  },
  identifier: {
    type: String,
    required: true
  },
  city: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['refresh'])

const loading = ref(false)
const images = ref([])
const deleting = ref(null)
const previewUrl = ref(null)

const coverImage = computed(() => {
  if (props.uploadType === 'tour' && images.value.cover) {
    return images.value.cover
  }
  return null
})

const galleryImages = computed(() => {
  if (props.uploadType === 'tour' && images.value.gallery) {
    return images.value.gallery.sort((a, b) => a.order - b.order)
  }
  return []
})

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString()
}

const previewImage = (url) => {
  previewUrl.value = url
}

const loadImages = async () => {
  loading.value = true
  try {
    let url
    if (props.uploadType === 'poi') {
      url = `/pois/${props.city}/${props.identifier}/images`
    } else if (props.uploadType === 'tour') {
      url = `/tours/${props.identifier}/images`
    }

    const response = await apiClient.get(url)

    if (props.uploadType === 'poi') {
      images.value = response.images || []
    } else if (props.uploadType === 'tour') {
      images.value = response
    }
  } catch (error) {
    if (error.message && !error.message.includes('404')) {
      console.error('Failed to load images:', error)
    }
    images.value = props.uploadType === 'tour' ? { cover: null, gallery: [] } : []
  } finally {
    loading.value = false
  }
}

const handleDelete = async (filename) => {
  try {
    await ElMessageBox.confirm(
      `Delete ${filename}?`,
      'Warning',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )

    deleting.value = filename

    let url
    if (props.uploadType === 'poi') {
      url = `/pois/${props.city}/${props.identifier}/images/${filename}`
    } else if (props.uploadType === 'tour') {
      url = `/tours/${props.identifier}/images/${filename}`
    }

    await apiClient.delete(url)

    ElMessage.success('Image deleted successfully')
    await loadImages()
    emit('refresh')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
      ElMessage.error(error.message || 'Failed to delete image')
    }
  } finally {
    deleting.value = null
  }
}

onMounted(() => {
  loadImages()
})

// Expose loadImages for parent components
defineExpose({ loadImages })
</script>
