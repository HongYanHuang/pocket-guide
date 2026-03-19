<template>
  <div class="user-header">
    <el-dropdown @command="handleCommand" trigger="click">
      <div class="user-info">
        <el-avatar :src="user?.picture" :size="36">
          {{ userInitial }}
        </el-avatar>
        <div class="user-details">
          <span class="user-name">{{ user?.name }}</span>
          <span class="user-role">{{ roleLabel }}</span>
        </div>
        <el-icon class="dropdown-icon">
          <ArrowDown />
        </el-icon>
      </div>

      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item disabled class="user-email-item">
            <el-icon><User /></el-icon>
            {{ user?.email }}
          </el-dropdown-item>

          <el-dropdown-item disabled class="user-role-item">
            <el-icon><Setting /></el-icon>
            Role: {{ user?.role || 'N/A' }}
          </el-dropdown-item>

          <el-dropdown-item
            v-if="isAdmin"
            command="sessions"
            divided
          >
            <el-icon><View /></el-icon>
            View Active Sessions
          </el-dropdown-item>

          <el-dropdown-item command="logout" divided>
            <el-icon><SwitchButton /></el-icon>
            Logout
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- Sessions Dialog -->
    <el-dialog
      v-model="sessionsDialogVisible"
      title="Active Sessions"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="loadingSessions" class="loading-container">
        <el-icon :size="32" class="is-loading">
          <Loading />
        </el-icon>
        <p>Loading sessions...</p>
      </div>

      <div v-else-if="sessionsError" class="error-container">
        <el-alert type="error" :closable="false" show-icon>
          {{ sessionsError }}
        </el-alert>
      </div>

      <div v-else>
        <el-table :data="sessions" stripe style="width: 100%">
          <el-table-column prop="email" label="Email" min-width="200" />
          <el-table-column prop="name" label="Name" min-width="150" />
          <el-table-column prop="role" label="Role" width="140">
            <template #default="scope">
              <el-tag :type="getRoleTagType(scope.row.role)">
                {{ scope.row.role }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="client_type" label="Client" width="120" />
          <el-table-column prop="last_accessed" label="Last Active" width="180">
            <template #default="scope">
              {{ formatTimestamp(scope.row.last_accessed) }}
            </template>
          </el-table-column>
          <el-table-column prop="expires_at" label="Expires" width="180">
            <template #default="scope">
              {{ formatTimestamp(scope.row.expires_at) }}
            </template>
          </el-table-column>
        </el-table>

        <div class="sessions-summary">
          <el-statistic title="Total Active Sessions" :value="totalSessions" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '../auth/useAuth'
import authService from '../auth/authService'
import tokenManager from '../auth/tokenManager'
import { ElMessage } from 'element-plus'
import {
  ArrowDown, User, Setting, SwitchButton, View, Loading
} from '@element-plus/icons-vue'

const { user, logout } = useAuth()

const sessionsDialogVisible = ref(false)
const sessions = ref([])
const totalSessions = ref(0)
const loadingSessions = ref(false)
const sessionsError = ref('')

const userInitial = computed(() => {
  return user.value?.name?.charAt(0).toUpperCase() || 'U'
})

const roleLabel = computed(() => {
  const role = user.value?.role
  if (!role) return ''

  const labels = {
    backstage_admin: 'Admin',
    backstage_editor: 'Editor',
    backstage_viewer: 'Viewer',
    client_user: 'User'
  }

  return labels[role] || role
})

const isAdmin = computed(() => {
  return user.value?.role === 'backstage_admin'
})

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await logout()
      ElMessage.success('Logged out successfully')
    } catch (error) {
      console.error('Logout error:', error)
      ElMessage.error('Logout failed')
    }
  } else if (command === 'sessions') {
    await loadSessions()
  }
}

const loadSessions = async () => {
  sessionsDialogVisible.value = true
  loadingSessions.value = true
  sessionsError.value = ''

  try {
    const accessToken = tokenManager.getAccessToken()
    const data = await authService.getActiveSessions(accessToken)

    sessions.value = data.sessions || []
    totalSessions.value = data.total_sessions || 0
  } catch (error) {
    console.error('Failed to load sessions:', error)
    sessionsError.value = error.message || 'Failed to load sessions'
  } finally {
    loadingSessions.value = false
  }
}

const getRoleTagType = (role) => {
  const types = {
    backstage_admin: 'danger',
    backstage_editor: 'warning',
    backstage_viewer: 'info',
    client_user: 'success'
  }
  return types[role] || ''
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}
</script>

<style scoped>
.user-header {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.user-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  line-height: 1.2;
}

.user-role {
  font-size: 12px;
  color: #888;
  line-height: 1.2;
}

.dropdown-icon {
  font-size: 14px;
  color: #666;
  transition: transform 0.3s;
}

.user-email-item,
.user-role-item {
  font-size: 13px;
  color: #666;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 16px;
}

.loading-container p {
  color: #666;
  margin: 0;
}

.sessions-summary {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

@media (max-width: 768px) {
  .user-details {
    display: none;
  }

  .user-info {
    padding: 6px;
  }
}
</style>
