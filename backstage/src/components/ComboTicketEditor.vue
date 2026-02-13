<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEditing ? 'Edit Combo Ticket' : 'Create Combo Ticket'"
    width="700px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="180px"
      label-position="left"
    >
      <!-- Basic Info -->
      <el-divider content-position="left">Basic Information</el-divider>

      <el-form-item label="Ticket ID" prop="id">
        <el-input
          v-model="formData.id"
          placeholder="archaeological_pass_rome"
          :disabled="isEditing"
        >
          <template #append>
            <el-tooltip content="Lowercase letters, numbers, and underscores only">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="Name" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="Rome Archaeological Pass"
        />
      </el-form-item>

      <el-form-item label="Description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="2"
          placeholder="Combined ticket for ancient Rome sites"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="Type" prop="type">
        <el-select v-model="formData.type" placeholder="Select type" style="width: 100%">
          <el-option label="Same Day - Consecutive" value="same_day_consecutive" />
          <el-option label="Same Day - Any Order" value="same_day_any_order" />
          <el-option label="Same Day - Clustered" value="same_day_clustered" />
          <el-option label="Multi-Day" value="multi_day" />
        </el-select>
      </el-form-item>

      <!-- Members -->
      <el-divider content-position="left">Members</el-divider>

      <el-form-item label="POIs" prop="members">
        <div style="width: 100%">
          <el-select
            v-model="formData.members"
            multiple
            filterable
            placeholder="Select POIs to include"
            style="width: 100%; margin-bottom: 10px"
          >
            <el-option
              v-for="poi in availablePOIs"
              :key="poi.poi_name"
              :label="poi.poi_name"
              :value="poi.poi_name"
            />
          </el-select>

          <!-- Draggable Member List -->
          <div v-if="formData.members.length > 0" class="members-list">
            <div
              v-for="(member, index) in formData.members"
              :key="member"
              class="member-item"
            >
              <el-icon class="drag-handle"><Rank /></el-icon>
              <span>{{ index + 1 }}. {{ member }}</span>
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                circle
                @click="removeMember(index)"
              />
            </div>
          </div>

          <el-alert
            v-if="formData.members.length < 2"
            type="warning"
            :closable="false"
            show-icon
            style="margin-top: 10px"
          >
            A combo ticket must have at least 2 members
          </el-alert>
        </div>
      </el-form-item>

      <!-- Constraints -->
      <el-divider content-position="left">Constraints</el-divider>

      <el-form-item label="Must Visit Together">
        <el-switch v-model="formData.constraints.must_visit_together" />
      </el-form-item>

      <el-form-item label="Max Separation (hours)">
        <el-input-number
          v-model="formData.constraints.max_separation_hours"
          :min="0"
          :max="24"
          :step="0.5"
        />
      </el-form-item>

      <el-form-item label="Visit Order">
        <el-select v-model="formData.constraints.visit_order" style="width: 200px">
          <el-option label="Flexible" value="flexible" />
          <el-option label="Fixed" value="fixed" />
          <el-option label="Chronological" value="chronological" />
        </el-select>
      </el-form-item>

      <el-form-item label="Same Day Required">
        <el-switch v-model="formData.constraints.same_day_required" />
      </el-form-item>

      <!-- Pricing -->
      <el-divider content-position="left">Pricing (Optional)</el-divider>

      <el-form-item label="Adult Price">
        <el-input-number
          v-model="formData.pricing.adult"
          :min="0"
          :precision="2"
          :step="1"
        />
      </el-form-item>

      <el-form-item label="Reduced Price">
        <el-input-number
          v-model="formData.pricing.reduced"
          :min="0"
          :precision="2"
          :step="1"
        />
      </el-form-item>

      <el-form-item label="Currency">
        <el-input
          v-model="formData.pricing.currency"
          placeholder="EUR"
          style="width: 100px"
          maxlength="3"
        />
      </el-form-item>

      <el-form-item label="Validity (days)">
        <el-input-number
          v-model="formData.pricing.validity_days"
          :min="1"
          :max="30"
        />
      </el-form-item>

      <!-- Booking Info -->
      <el-divider content-position="left">Booking Information (Optional)</el-divider>

      <el-form-item label="Booking Required">
        <el-switch v-model="formData.booking_info.required" />
      </el-form-item>

      <el-form-item label="Booking URL">
        <el-input
          v-model="formData.booking_info.url"
          placeholder="https://example.com/book"
        />
      </el-form-item>

      <el-form-item label="Advance Booking (days)">
        <el-input-number
          v-model="formData.booking_info.advance_booking_days"
          :min="0"
          :max="365"
        />
      </el-form-item>

      <el-form-item label="Notes">
        <el-input
          v-model="formData.booking_info.notes"
          type="textarea"
          :rows="2"
          placeholder="Additional booking notes"
          maxlength="300"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">Cancel</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled, Delete, Rank } from '@element-plus/icons-vue'
import comboTicketsAPI from '../api/comboTickets'

// Props
const props = defineProps({
  visible: Boolean,
  city: String,
  ticket: Object, // For editing
  availablePOIs: Array
})

// Emits
const emit = defineEmits(['update:visible', 'saved'])

// State
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const formRef = ref(null)
const saving = ref(false)

const defaultFormData = () => ({
  id: '',
  name: '',
  description: '',
  type: 'same_day_consecutive',
  members: [],
  constraints: {
    must_visit_together: true,
    max_separation_hours: 4,
    visit_order: 'flexible',
    same_day_required: true
  },
  pricing: {
    adult: null,
    reduced: null,
    currency: 'EUR',
    validity_days: 1
  },
  booking_info: {
    required: false,
    recommended: false,
    advance_booking_days: null,
    url: '',
    notes: ''
  }
})

const formData = ref(defaultFormData())

const isEditing = computed(() => !!props.ticket)

// Validation rules
const rules = {
  id: [
    { required: true, message: 'Please enter a ticket ID', trigger: 'blur' },
    {
      pattern: /^[a-z0-9_]+$/,
      message: 'ID must contain only lowercase letters, numbers, and underscores',
      trigger: 'blur'
    }
  ],
  name: [
    { required: true, message: 'Please enter a name', trigger: 'blur' },
    { min: 3, max: 100, message: 'Name must be 3-100 characters', trigger: 'blur' }
  ],
  type: [
    { required: true, message: 'Please select a type', trigger: 'change' }
  ],
  members: [
    {
      type: 'array',
      required: true,
      min: 2,
      message: 'Please select at least 2 POIs',
      trigger: 'change'
    }
  ]
}

// Methods
const removeMember = (index) => {
  formData.value.members.splice(index, 1)
}

const handleClose = () => {
  formRef.value?.resetFields()
  formData.value = defaultFormData()
  dialogVisible.value = false
}

const handleSave = async () => {
  try {
    // Validate form
    await formRef.value.validate()

    // Prepare data (remove null/empty optional fields)
    const data = {
      id: formData.value.id,
      name: formData.value.name,
      type: formData.value.type,
      members: formData.value.members,
      constraints: formData.value.constraints
    }

    if (formData.value.description) {
      data.description = formData.value.description
    }

    // Add pricing if any field is filled
    if (formData.value.pricing.adult || formData.value.pricing.reduced) {
      data.pricing = {}
      if (formData.value.pricing.adult) data.pricing.adult = formData.value.pricing.adult
      if (formData.value.pricing.reduced) data.pricing.reduced = formData.value.pricing.reduced
      data.pricing.currency = formData.value.pricing.currency
      data.pricing.validity_days = formData.value.pricing.validity_days
    }

    // Add booking info if required or URL provided
    if (formData.value.booking_info.required || formData.value.booking_info.url) {
      data.booking_info = {}
      if (formData.value.booking_info.required) {
        data.booking_info.required = true
      }
      if (formData.value.booking_info.url) {
        data.booking_info.url = formData.value.booking_info.url
      }
      if (formData.value.booking_info.advance_booking_days) {
        data.booking_info.advance_booking_days = formData.value.booking_info.advance_booking_days
      }
      if (formData.value.booking_info.notes) {
        data.booking_info.notes = formData.value.booking_info.notes
      }
    }

    saving.value = true

    if (isEditing.value) {
      // Update existing ticket
      await comboTicketsAPI.updateComboTicket(props.city, formData.value.id, data)
      ElMessage.success('Combo ticket updated successfully')
    } else {
      // Create new ticket
      await comboTicketsAPI.createComboTicket(props.city, data)
      ElMessage.success('Combo ticket created successfully')
    }

    emit('saved')
    handleClose()
  } catch (error) {
    ElMessage.error(error.message || 'Failed to save combo ticket')
  } finally {
    saving.value = false
  }
}

// Watch for ticket prop changes (for editing)
watch(() => props.ticket, (newTicket) => {
  if (newTicket) {
    formData.value = {
      ...defaultFormData(),
      ...newTicket,
      constraints: {
        ...defaultFormData().constraints,
        ...(newTicket.constraints || {})
      },
      pricing: {
        ...defaultFormData().pricing,
        ...(newTicket.pricing || {})
      },
      booking_info: {
        ...defaultFormData().booking_info,
        ...(newTicket.booking_info || {})
      }
    }
  }
}, { immediate: true })
</script>

<style scoped>
.members-list {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background-color: #f5f7fa;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background-color: white;
  border-radius: 4px;
  margin-bottom: 8px;
}

.member-item:last-child {
  margin-bottom: 0;
}

.drag-handle {
  cursor: move;
  color: #909399;
}

.member-item span {
  flex: 1;
}
</style>
