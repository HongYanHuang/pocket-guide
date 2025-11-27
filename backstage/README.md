# Backstage - POI Metadata Manager

Vue.js-based backstage website for managing POI metadata including coordinates, operation hours, and travel distances.

## Features

- 🌍 **City Management** - View all cities with POI counts
- 📝 **POI Editing** - Edit coordinates, visit info, operation hours
- 🗺️ **Interactive Map** - View POIs on Leaflet map with OpenStreetMap
- 📊 **Distance Matrix** - View/recalculate travel times (walking, transit, driving)
- ✅ **Data Validation** - Form validation and error handling
- 🔄 **Real-time Sync** - Direct API integration with FastAPI backend

## Tech Stack

- **Framework**: Vue 3 + Vite
- **UI Library**: Element Plus
- **Maps**: Leaflet.js + vue3-leaflet
- **HTTP Client**: Axios
- **Router**: Vue Router

## Prerequisites

- Node.js 16+ and npm
- FastAPI backend running on `http://localhost:8000`

## Installation

```bash
cd backstage
npm install
```

## Development

1. **Start the FastAPI backend** (in project root):
   ```bash
   python src/api_server.py
   ```
   Backend will run on http://localhost:8000

2. **Start the Vue dev server** (in backstage directory):
   ```bash
   cd backstage
   npm run dev
   ```
   Frontend will run on http://localhost:5173

3. **Open in browser**:
   http://localhost:5173

## Building for Production

```bash
npm run build
```

Build output will be in `backstage/dist/`

To preview the production build:
```bash
npm run preview
```

## Project Structure

```
backstage/
├── src/
│   ├── api/
│   │   └── metadata.js          # API client for FastAPI
│   ├── components/
│   │   ├── POITable.vue         # POI list table
│   │   ├── POIEditor.vue        # Edit form modal
│   │   ├── MapViewer.vue        # Leaflet map
│   │   └── DistanceMatrix.vue   # Distance matrix table
│   ├── views/
│   │   ├── Dashboard.vue        # Main dashboard
│   │   └── POIDetail.vue        # POI detail page
│   ├── router/
│   │   └── index.js             # Vue Router config
│   ├── App.vue                  # Root component
│   └── main.js                  # App entry point
├── index.html
├── vite.config.js               # Vite config with API proxy
└── package.json
```

## Usage Guide

### 1. View Cities

- Homepage shows all cities with POI counts
- Select a city from the dropdown

### 2. Manage POIs

**POIs Tab:**
- View all POIs in a table
- See metadata status (✓ complete, ✗ incomplete)
- Click "Edit" to modify metadata
- Click "Details" for full POI information
- Click "Collect All Metadata" to fetch from Google Maps

**Editing POI Metadata:**
- Update coordinates (latitude/longitude)
- Set indoor/outdoor classification
- Adjust typical visit duration
- Add accessibility info
- Update address, phone, website
- Mark as wheelchair accessible
- Mark as verified

### 3. Map View

**Map Tab:**
- See all POIs plotted on interactive map
- Click markers for POI info popup
- Click "Edit" in popup to modify metadata
- Map automatically centers on city POIs

### 4. Distance Matrix

**Distance Matrix Tab:**
- View travel times between all POI pairs
- Switch between walking/transit/driving modes
- See duration and distance for each pair
- Click "Recalculate" to refresh from Google Maps API

## API Integration

The frontend communicates with the FastAPI backend via these endpoints:

### Cities
- `GET /api/cities` - List all cities
- `GET /api/cities/{city}/pois` - List POIs for a city
- `POST /api/cities/{city}/collect` - Collect all metadata

### POIs
- `GET /api/pois/{city}/{poi_id}` - Get POI details
- `PUT /api/pois/{city}/{poi_id}/metadata` - Update metadata
- `POST /api/pois/{city}/{poi_id}/recollect` - Re-collect from Google Maps

### Distance Matrix
- `GET /api/distances/{city}` - Get distance matrix
- `POST /api/distances/{city}/recalculate` - Recalculate distances

## Configuration

### API Proxy

The `vite.config.js` proxies API calls to the FastAPI backend:

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}
```

For production, update the API base URL in `src/api/metadata.js`:

```javascript
const apiClient = axios.create({
  baseURL: 'https://your-api-domain.com',  // Change this
  // ...
})
```

## Separating Frontend (Future)

This frontend is designed to be easily separated into its own repository:

1. **Extract the backstage folder**:
   ```bash
   git filter-branch --subdirectory-filter backstage
   ```

2. **Update API URL** in `src/api/metadata.js`:
   ```javascript
   baseURL: 'https://api.yourapp.com'
   ```

3. **Deploy independently**:
   - Frontend: Vercel, Netlify, S3
   - Backend: Keep running your FastAPI server

## Troubleshooting

### Port 8000 Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Port 5173 Already in Use

Change port in `vite.config.js`:
```javascript
server: {
  port: 5174  // Use different port
}
```

### Map Not Showing

Make sure Leaflet CSS is imported in `src/main.js`:
```javascript
import 'leaflet/dist/leaflet.css'
```

### API Errors

1. Check FastAPI backend is running on port 8000
2. Check browser console for CORS errors
3. Verify API proxy in `vite.config.js`

## Development Tips

- **Hot Module Replacement**: Changes auto-reload
- **Vue DevTools**: Install browser extension for debugging
- **Element Plus Docs**: https://element-plus.org/
- **Leaflet Docs**: https://leafletjs.com/

## License

Same as parent project
