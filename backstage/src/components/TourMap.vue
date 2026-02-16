<template>
  <div class="tour-map-container">
    <div id="tour-map" style="height: 500px; border-radius: 8px"></div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  tour: {
    type: Object,
    required: true
  }
})

let map = null
const markers = []
const polylines = []

// Day colors for differentiation
const dayColors = [
  '#409EFF', // Blue (Day 1)
  '#67C23A', // Green (Day 2)
  '#E6A23C', // Orange (Day 3)
  '#F56C6C', // Red (Day 4)
  '#9C27B0', // Purple (Day 5)
  '#00BCD4', // Cyan (Day 6)
  '#FF9800', // Deep Orange (Day 7)
]

const initMap = () => {
  // Clear existing map if any
  if (map) {
    map.remove()
    map = null
  }
  markers.length = 0
  polylines.length = 0

  // Initialize map
  map = L.map('tour-map').setView([41.9028, 12.4964], 13) // Default Rome center

  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map)

  // Fix for default marker icon issue with Webpack/Vite
  delete L.Icon.Default.prototype._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  })

  renderTourOnMap()
}

const createNumberedIcon = (number, color) => {
  return L.divIcon({
    className: 'numbered-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">
        ${number}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  })
}

const createLocationIcon = (type) => {
  const color = type === 'start' ? '#67c23a' : '#e6a23c'
  const icon = type === 'start' ? '▶' : '⬛'

  return L.divIcon({
    className: 'location-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 16px;
        border: 3px solid white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.4);
      ">
        ${icon}
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  })
}

// Parse location string to coordinates
// Can be either "lat,lng" or a place name (for place names, return null)
const parseLocationCoordinates = (locationStr) => {
  if (!locationStr) return null

  // Check if it's a coordinate pair (format: "lat,lng")
  const coordMatch = locationStr.match(/^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$/)
  if (coordMatch) {
    const lat = parseFloat(coordMatch[1])
    const lng = parseFloat(coordMatch[2])

    // Validate coordinates
    if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
      return [lat, lng]
    }
  }

  // If not valid coordinates, it's a place name - return null
  return null
}

const renderTourOnMap = () => {
  if (!map || !props.tour) return

  const allCoordinates = []
  let poiCounter = 0

  // Add start location if exists
  if (props.tour.input_parameters?.start_location) {
    const startCoords = parseLocationCoordinates(props.tour.input_parameters.start_location)

    if (startCoords) {
      // Use parsed coordinates
      const marker = L.marker(startCoords, {
        icon: createLocationIcon('start')
      }).addTo(map)

      marker.bindPopup(`
        <div style="font-weight: 600; margin-bottom: 4px">Start Point</div>
        <div>${props.tour.input_parameters.start_location}</div>
      `)

      markers.push(marker)
      allCoordinates.push(startCoords)
    } else {
      // Fallback: Place name or invalid coords - use first POI location
      const firstPOI = props.tour.itinerary[0]?.pois[0]
      if (firstPOI?.coordinates) {
        const marker = L.marker(
          [firstPOI.coordinates.latitude, firstPOI.coordinates.longitude],
          { icon: createLocationIcon('start') }
        ).addTo(map)

        marker.bindPopup(`
          <div style="font-weight: 600; margin-bottom: 4px">Start Point</div>
          <div>${props.tour.input_parameters.start_location}</div>
          <div style="font-size: 11px; color: #909399; margin-top: 4px">
            (Approximate location - based on first POI)
          </div>
        `)

        markers.push(marker)
        allCoordinates.push([firstPOI.coordinates.latitude, firstPOI.coordinates.longitude])
      }
    }
  }

  // Render each day
  props.tour.itinerary.forEach((day, dayIndex) => {
    const dayColor = dayColors[dayIndex % dayColors.length]
    const dayCoordinates = []

    // Add markers for each POI
    day.pois.forEach((poi, poiIndex) => {
      if (!poi.coordinates?.latitude || !poi.coordinates?.longitude) {
        return
      }

      poiCounter++
      const coords = [poi.coordinates.latitude, poi.coordinates.longitude]
      dayCoordinates.push(coords)
      allCoordinates.push(coords)

      // Create marker
      const marker = L.marker(coords, {
        icon: createNumberedIcon(poiCounter, dayColor)
      }).addTo(map)

      // Create popup
      const popupContent = `
        <div style="min-width: 200px">
          <div style="font-weight: 600; font-size: 15px; margin-bottom: 4px; color: ${dayColor}">
            ${poi.poi}
          </div>
          <div style="font-size: 12px; color: #606266; margin-bottom: 8px">
            ${poi.reason || ''}
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap">
            <span style="background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 11px">
              Day ${day.day}
            </span>
            <span style="background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 11px">
              ${poi.estimated_hours}h
            </span>
            <span style="background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 11px">
              ${poi.priority}
            </span>
          </div>
        </div>
      `
      marker.bindPopup(popupContent)

      markers.push(marker)
    })

    // Draw polyline connecting POIs of this day
    if (dayCoordinates.length > 1) {
      const polyline = L.polyline(dayCoordinates, {
        color: dayColor,
        weight: 3,
        opacity: 0.7,
        dashArray: '10, 5'
      }).addTo(map)

      polylines.push(polyline)
    }
  })

  // Add end location if exists
  if (props.tour.input_parameters?.end_location) {
    const endCoords = parseLocationCoordinates(props.tour.input_parameters.end_location)

    if (endCoords) {
      // Use parsed coordinates
      const marker = L.marker(endCoords, {
        icon: createLocationIcon('end')
      }).addTo(map)

      marker.bindPopup(`
        <div style="font-weight: 600; margin-bottom: 4px">End Point</div>
        <div>${props.tour.input_parameters.end_location}</div>
      `)

      markers.push(marker)
      allCoordinates.push(endCoords)
    } else {
      // Fallback: Place name or invalid coords - use last POI location
      const lastDay = props.tour.itinerary[props.tour.itinerary.length - 1]
      const lastPOI = lastDay?.pois[lastDay.pois.length - 1]

      if (lastPOI?.coordinates) {
        const marker = L.marker(
          [lastPOI.coordinates.latitude, lastPOI.coordinates.longitude],
          { icon: createLocationIcon('end') }
        ).addTo(map)

        marker.bindPopup(`
          <div style="font-weight: 600; margin-bottom: 4px">End Point</div>
          <div>${props.tour.input_parameters.end_location}</div>
          <div style="font-size: 11px; color: #909399; margin-top: 4px">
            (Approximate location - based on last POI)
          </div>
        `)

        markers.push(marker)
        allCoordinates.push([lastPOI.coordinates.latitude, lastPOI.coordinates.longitude])
      }
    }
  }

  // Fit map bounds to show all markers
  if (allCoordinates.length > 0) {
    const bounds = L.latLngBounds(allCoordinates)
    map.fitBounds(bounds, { padding: [50, 50] })
  }
}

onMounted(() => {
  initMap()
})

// Watch for tour changes
watch(() => props.tour, () => {
  if (map) {
    renderTourOnMap()
  }
}, { deep: true })
</script>

<style scoped>
.tour-map-container {
  width: 100%;
}

/* Override Leaflet default styles */
:deep(.leaflet-popup-content-wrapper) {
  border-radius: 8px;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.2);
}

:deep(.leaflet-popup-content) {
  margin: 12px;
}

:deep(.numbered-marker) {
  background: transparent;
  border: none;
}

:deep(.location-marker) {
  background: transparent;
  border: none;
}
</style>
