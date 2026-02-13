<template>
  <div class="combo-tickets-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <h2 style="margin: 0">Combo Tickets</h2>
            <p style="margin: 5px 0 0; color: #909399; font-size: 14px">
              Manage combo ticket groups for cities
            </p>
          </div>
          <el-button type="primary" @click="showCreateDialog = true" :icon="Plus">
            New Combo Ticket
          </el-button>
        </div>
      </template>

      <!-- City Selector -->
      <el-form :inline="true" style="margin-bottom: 20px">
        <el-form-item label="City">
          <el-select
            v-model="selectedCity"
            placeholder="Select a city"
            @change="loadComboTickets"
            style="width: 200px"
          >
            <el-option
              v-for="city in cities"
              :key="city"
              :label="city.charAt(0).toUpperCase() + city.slice(1)"
              :value="city"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button @click="validateTickets" :icon="Check">
            Validate
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Validation Issues -->
      <el-alert
        v-if="validationIssues.length > 0"
        type="warning"
        title="Validation Issues"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <ul style="margin: 10px 0; padding-left: 20px">
          <li v-for="(issue, index) in validationIssues" :key="index">
            <strong>{{ issue.type.toUpperCase() }}:</strong> {{ issue.message }}
            <span v-if="issue.poi"> (POI: {{ issue.poi }})</span>
            <span v-if="issue.combo_ticket"> (Ticket: {{ issue.combo_ticket }})</span>
          </li>
        </ul>
      </el-alert>

      <!-- Loading State -->
      <div v-if="loading" style="text-align: center; padding: 40px">
        <el-icon :size="40" class="is-loading"><Loading /></el-icon>
        <p style="margin-top: 10px; color: #909399">Loading combo tickets...</p>
      </div>

      <!-- Empty State -->
      <el-empty
        v-else-if="comboTickets.length === 0 && selectedCity"
        description="No combo tickets found for this city"
      >
        <el-button type="primary" @click="showCreateDialog = true">
          Create First Combo Ticket
        </el-button>
      </el-empty>

      <!-- Combo Tickets List -->
      <div v-else class="tickets-list">
        <el-card
          v-for="ticket in comboTickets"
          :key="ticket.id"
          shadow="hover"
          class="ticket-card"
        >
          <div class="ticket-header">
            <div>
              <h3 style="margin: 0; display: flex; align-items: center; gap: 10px">
                📦 {{ ticket.name }}
                <el-tag size="small" type="info">{{ ticket.type }}</el-tag>
              </h3>
              <p v-if="ticket.description" style="margin: 5px 0 0; color: #606266">
                {{ ticket.description }}
              </p>
            </div>
            <div class="ticket-actions">
              <el-button size="small" @click="editTicket(ticket)" :icon="Edit">
                Edit
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="confirmDelete(ticket)"
                :icon="Delete"
              >
                Delete
              </el-button>
            </div>
          </div>

          <el-divider style="margin: 15px 0" />

          <!-- Members -->
          <div class="ticket-section">
            <h4 style="margin: 0 0 10px">Members ({{ ticket.members.length }})</h4>
            <div class="members-flow">
              <el-tag
                v-for="(member, index) in ticket.members"
                :key="member"
                size="large"
                style="margin: 5px"
              >
                {{ member }}
              </el-tag>
              <span v-if="index < ticket.members.length - 1" class="arrow">→</span>
            </div>
          </div>

          <!-- Constraints -->
          <div v-if="ticket.constraints" class="ticket-section">
            <h4 style="margin: 15px 0 10px">Constraints</h4>
            <ul style="margin: 0; padding-left: 20px; color: #606266">
              <li>
                Must visit together:
                <el-tag :type="ticket.constraints.must_visit_together ? 'success' : 'info'" size="small">
                  {{ ticket.constraints.must_visit_together ? 'Yes' : 'No' }}
                </el-tag>
              </li>
              <li v-if="ticket.constraints.max_separation_hours">
                Max separation: {{ ticket.constraints.max_separation_hours }} hours
              </li>
              <li v-if="ticket.constraints.visit_order">
                Visit order: {{ ticket.constraints.visit_order }}
              </li>
            </ul>
          </div>

          <!-- Pricing -->
          <div v-if="ticket.pricing" class="ticket-section">
            <h4 style="margin: 15px 0 10px">Pricing</h4>
            <div style="display: flex; gap: 20px; color: #606266">
              <span v-if="ticket.pricing.adult">
                Adult: <strong>{{ ticket.pricing.currency }} {{ ticket.pricing.adult }}</strong>
              </span>
              <span v-if="ticket.pricing.reduced">
                Reduced: <strong>{{ ticket.pricing.currency }} {{ ticket.pricing.reduced }}</strong>
              </span>
              <span v-if="ticket.pricing.validity_days">
                Valid: <strong>{{ ticket.pricing.validity_days }} day(s)</strong>
              </span>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <combo-ticket-editor
      v-model:visible="showCreateDialog"
      :city="selectedCity"
      :ticket="editingTicket"
      :available-pois="availablePOIs"
      @saved="handleTicketSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Check, Loading } from '@element-plus/icons-vue'
import comboTicketsAPI from '../api/comboTickets'
import metadataAPI from '../api/metadata'
import ComboTicketEditor from '../components/ComboTicketEditor.vue'

// State
const selectedCity = ref('rome')
const cities = ref(['rome', 'paris', 'athens', 'london'])
const comboTickets = ref([])
const availablePOIs = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const editingTicket = ref(null)
const validationIssues = ref([])

// Methods
const loadComboTickets = async () => {
  if (!selectedCity.value) return

  loading.value = true
  try {
    const response = await comboTicketsAPI.getComboTickets(selectedCity.value)
    comboTickets.value = response.combo_tickets || []

    // Load available POIs for this city
    await loadAvailablePOIs()
  } catch (error) {
    ElMessage.error(`Failed to load combo tickets: ${error.message}`)
    comboTickets.value = []
  } finally {
    loading.value = false
  }
}

const loadAvailablePOIs = async () => {
  try {
    const response = await metadataAPI.getCityPOIs(selectedCity.value)
    // Transform POI data to simple array of POI names for easier selection
    if (response.pois && Array.isArray(response.pois)) {
      availablePOIs.value = response.pois.map(poi => ({
        poi_name: poi.poi_name || poi.name || poi,
        poi_id: poi.poi_id || poi.id || poi
      }))
    } else {
      availablePOIs.value = []
    }
  } catch (error) {
    console.error('Failed to load POIs:', error)
    // Fallback: try to get from combo tickets members
    if (comboTickets.value.length > 0) {
      const allMembers = new Set()
      comboTickets.value.forEach(ticket => {
        ticket.members.forEach(member => allMembers.add(member))
      })
      availablePOIs.value = Array.from(allMembers).map(name => ({
        poi_name: name,
        poi_id: name
      }))
    } else {
      availablePOIs.value = []
    }
  }
}

const validateTickets = async () => {
  if (!selectedCity.value) return

  try {
    const response = await comboTicketsAPI.validateComboTickets(selectedCity.value)
    validationIssues.value = response.issues || []

    if (response.valid) {
      ElMessage.success('All combo tickets are valid!')
    } else {
      ElMessage.warning(`Found ${response.count} validation issue(s)`)
    }
  } catch (error) {
    ElMessage.error(`Validation failed: ${error.message}`)
  }
}

const editTicket = (ticket) => {
  editingTicket.value = { ...ticket }
  showCreateDialog.value = true
}

const confirmDelete = (ticket) => {
  ElMessageBox.confirm(
    `Are you sure you want to delete "${ticket.name}"? This will remove the combo ticket and update all POI references.`,
    'Delete Combo Ticket',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    await deleteTicket(ticket)
  }).catch(() => {
    // Cancelled
  })
}

const deleteTicket = async (ticket) => {
  try {
    await comboTicketsAPI.deleteComboTicket(selectedCity.value, ticket.id)
    ElMessage.success(`Combo ticket "${ticket.name}" deleted successfully`)
    await loadComboTickets()
  } catch (error) {
    ElMessage.error(`Failed to delete combo ticket: ${error.message}`)
  }
}

const handleTicketSaved = async () => {
  showCreateDialog.value = false
  editingTicket.value = null
  await loadComboTickets()
}

// Lifecycle
onMounted(() => {
  loadComboTickets()
})
</script>

<style scoped>
.combo-tickets-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tickets-list {
  display: grid;
  gap: 20px;
}

.ticket-card {
  transition: transform 0.2s;
}

.ticket-card:hover {
  transform: translateY(-2px);
}

.ticket-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.ticket-actions {
  display: flex;
  gap: 10px;
}

.ticket-section {
  margin-top: 15px;
}

.ticket-section h4 {
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.members-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}

.arrow {
  font-size: 18px;
  color: #909399;
  margin: 0 5px;
}
</style>
