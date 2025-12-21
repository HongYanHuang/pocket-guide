<template>
  <div class="research-raw">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Raw YAML</span>
          <el-button
            type="primary"
            size="small"
            @click="copyToClipboard"
            :icon="DocumentCopy"
          >
            Copy to Clipboard
          </el-button>
        </div>
      </template>

      <pre class="yaml-content">{{ rawYaml }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'

const props = defineProps({
  rawYaml: {
    type: String,
    required: true
  }
})

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.rawYaml)
    ElMessage.success('Copied to clipboard!')
  } catch (err) {
    ElMessage.error('Failed to copy to clipboard')
    console.error('Copy failed:', err)
  }
}
</script>

<style scoped>
.research-raw {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.yaml-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 13px;
  line-height: 1.5;
  background-color: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  max-height: 600px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}
</style>
