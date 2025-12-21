<template>
  <div class="research-structured">
    <!-- Basic Info -->
    <el-card v-if="data.basic_info" class="section-card">
      <template #header>
        <h3>Basic Information</h3>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item v-if="data.basic_info.period" label="Period">
          {{ data.basic_info.period }}
        </el-descriptions-item>
        <el-descriptions-item v-if="data.basic_info.date_built" label="Date Built">
          {{ data.basic_info.date_built }}
        </el-descriptions-item>
        <el-descriptions-item v-if="data.basic_info.date_relative" label="Age">
          {{ data.basic_info.date_relative }}
        </el-descriptions-item>
        <el-descriptions-item v-if="data.basic_info.current_state" label="Current State">
          {{ data.basic_info.current_state }}
        </el-descriptions-item>
        <el-descriptions-item v-if="data.basic_info.description" label="Description" :span="2">
          {{ data.basic_info.description }}
        </el-descriptions-item>
        <el-descriptions-item v-if="data.basic_info.labels && data.basic_info.labels.length" label="Labels">
          <el-tag v-for="label in data.basic_info.labels" :key="label" size="small" style="margin-right: 5px">
            {{ label }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Core Features -->
    <el-card v-if="data.core_features && data.core_features.length" class="section-card">
      <template #header>
        <h3>Core Features</h3>
      </template>
      <ul class="feature-list">
        <li v-for="(feature, index) in data.core_features" :key="index">
          {{ feature }}
        </li>
      </ul>
    </el-card>

    <!-- People -->
    <el-card v-if="data.people && data.people.length" class="section-card">
      <template #header>
        <h3>People ({{ data.people.length }})</h3>
      </template>
      <el-collapse>
        <el-collapse-item
          v-for="(person, index) in data.people"
          :key="index"
          :title="person.name"
          :name="index"
        >
          <el-descriptions :column="1" border>
            <el-descriptions-item v-if="person.role" label="Role">
              {{ person.role }}
            </el-descriptions-item>
            <el-descriptions-item v-if="person.personality" label="Personality">
              {{ person.personality }}
            </el-descriptions-item>
            <el-descriptions-item v-if="person.origin" label="Origin">
              {{ person.origin }}
            </el-descriptions-item>
            <el-descriptions-item v-if="person.relationship_type" label="Relationship">
              {{ person.relationship_type }}
            </el-descriptions-item>
            <el-descriptions-item v-if="person.labels && person.labels.length" label="Labels">
              <el-tag v-for="label in person.labels" :key="label" size="small" style="margin-right: 5px">
                {{ label }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- Events -->
    <el-card v-if="data.events && data.events.length" class="section-card">
      <template #header>
        <h3>Events ({{ data.events.length }})</h3>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(event, index) in data.events"
          :key="index"
          :timestamp="event.date || 'Unknown date'"
          placement="top"
        >
          <el-card>
            <h4>{{ event.name }}</h4>
            <p v-if="event.significance">{{ event.significance }}</p>
            <div v-if="event.labels && event.labels.length" style="margin-top: 10px">
              <el-tag v-for="label in event.labels" :key="label" size="small" style="margin-right: 5px">
                {{ label }}
              </el-tag>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- Locations -->
    <el-card v-if="data.locations && data.locations.length" class="section-card">
      <template #header>
        <h3>Locations ({{ data.locations.length }})</h3>
      </template>
      <el-row :gutter="20">
        <el-col
          v-for="(location, index) in data.locations"
          :key="index"
          :xs="24"
          :sm="12"
          :md="8"
        >
          <el-card class="location-card" shadow="hover">
            <h4>{{ location.name }}</h4>
            <p v-if="location.description">{{ location.description }}</p>
            <div v-if="location.labels && location.labels.length" style="margin-top: 10px">
              <el-tag v-for="label in location.labels" :key="label" size="small" style="margin-right: 5px">
                {{ label }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- Concepts -->
    <el-card v-if="data.concepts && data.concepts.length" class="section-card">
      <template #header>
        <h3>Concepts ({{ data.concepts.length }})</h3>
      </template>
      <el-row :gutter="20">
        <el-col
          v-for="(concept, index) in data.concepts"
          :key="index"
          :xs="24"
          :sm="12"
        >
          <el-card class="concept-card" shadow="hover">
            <h4>{{ concept.name }}</h4>
            <p v-if="concept.explanation">{{ concept.explanation }}</p>
            <div v-if="concept.labels && concept.labels.length" style="margin-top: 10px">
              <el-tag v-for="label in concept.labels" :key="label" size="small" style="margin-right: 5px">
                {{ label }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  data: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.research-structured {
  padding: 20px;
}

.section-card {
  margin-bottom: 20px;
}

.section-card h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.feature-list {
  margin: 0;
  padding-left: 20px;
}

.feature-list li {
  margin-bottom: 10px;
  line-height: 1.6;
}

.location-card,
.concept-card {
  margin-bottom: 20px;
  height: 100%;
}

.location-card h4,
.concept-card h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

.location-card p,
.concept-card p {
  margin: 0;
  color: #606266;
  line-height: 1.6;
}

:deep(.el-timeline-item__timestamp) {
  color: #909399;
  font-weight: 500;
}

:deep(.el-collapse-item__header) {
  font-weight: 500;
  font-size: 15px;
}
</style>
