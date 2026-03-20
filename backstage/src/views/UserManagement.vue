<template>
  <div class="user-management">
    <div class="header">
      <h2>User Management</h2>
      <el-button @click="loadUsers" :loading="loading" :icon="Refresh">
        Refresh
      </el-button>
    </div>

    <el-card>
      <el-tabs v-model="activeTab">
        <!-- Backstage Users Tab -->
        <el-tab-pane label="Backstage Users" name="backstage">
          <template #label>
            <span>
              Backstage Users
              <el-tag size="small" style="margin-left: 8px">
                {{ backstageUsers.length }}
              </el-tag>
            </span>
          </template>

          <el-table
            :data="backstageUsers"
            style="width: 100%"
            v-loading="loading"
            empty-text="No backstage users online"
          >
            <el-table-column prop="picture" label="Avatar" width="80">
              <template #default="{ row }">
                <el-avatar :src="row.picture" :size="40">
                  {{ row.name.charAt(0) }}
                </el-avatar>
              </template>
            </el-table-column>

            <el-table-column prop="name" label="Name" min-width="150" />

            <el-table-column prop="email" label="Email" min-width="200" />

            <el-table-column prop="role" label="Role" width="150">
              <template #default="{ row }">
                <el-tag
                  :type="getRoleTagType(row.role)"
                  effect="plain"
                >
                  {{ formatRole(row.role) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="scopes" label="Scopes" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="scope in row.scopes"
                  :key="scope"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ scope }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="last_accessed" label="Last Active" width="180">
              <template #default="{ row }">
                {{ formatTime(row.last_accessed) }}
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="Login Time" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Client App Users Tab -->
        <el-tab-pane label="Client Users" name="client">
          <template #label>
            <span>
              Client Users
              <el-tag size="small" style="margin-left: 8px">
                {{ clientUsers.length }}
              </el-tag>
            </span>
          </template>

          <el-table
            :data="clientUsers"
            style="width: 100%"
            v-loading="loading"
            empty-text="No client users online"
          >
            <el-table-column prop="picture" label="Avatar" width="80">
              <template #default="{ row }">
                <el-avatar :src="row.picture" :size="40">
                  {{ row.name.charAt(0) }}
                </el-avatar>
              </template>
            </el-table-column>

            <el-table-column prop="name" label="Name" min-width="150" />

            <el-table-column prop="email" label="Email" min-width="200" />

            <el-table-column prop="role" label="Role" width="150">
              <template #default="{ row }">
                <el-tag type="info" effect="plain">
                  {{ formatRole(row.role) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="scopes" label="Scopes" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="scope in row.scopes"
                  :key="scope"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ scope }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="last_accessed" label="Last Active" width="180">
              <template #default="{ row }">
                {{ formatTime(row.last_accessed) }}
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="Login Time" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="true"
      @close="error = ''"
      style="margin-top: 16px"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import adminApi from '../api/admin'

const activeTab = ref('backstage')
const loading = ref(false)
const error = ref('')
const backstageUsers = ref([])
const clientUsers = ref([])

const loadUsers = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await adminApi.listUsers()
    backstageUsers.value = data.backstage.users
    clientUsers.value = data.client.users

    ElMessage.success(`Loaded ${data.total} active users`)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load users'
    ElMessage.error('Failed to load users')
  } finally {
    loading.value = false
  }
}

const getRoleTagType = (role) => {
  const roleTypes = {
    'backstage_admin': 'danger',
    'backstage_editor': 'warning',
    'backstage_viewer': 'success',
    'client_user': 'info'
  }
  return roleTypes[role] || 'info'
}

const formatRole = (role) => {
  const roleNames = {
    'backstage_admin': 'Admin',
    'backstage_editor': 'Editor',
    'backstage_viewer': 'Viewer',
    'client_user': 'User'
  }
  return roleNames[role] || role
}

const formatTime = (isoString) => {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-table) {
  margin-top: 16px;
}

:deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}
</style>
