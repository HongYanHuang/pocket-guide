# POI and Tour Image Upload Feature Design

## Overview

This feature allows backstage admins to upload images for POIs and tours, which are then accessible to both backstage and client apps.

---

## Requirements

### 1. POI Images
- Upload multiple images per POI in backstage
- Images accessible from both backstage and client side
- Optional parameter (backward compatible)
- Images stored per city and POI

### 2. Tour Images
- Upload images for specific tours in backstage
- Cover image + gallery images support
- Images accessible from both backstage and client side
- Optional parameter (backward compatible)

---

## Storage Structure

### POI Images

```
poi_images/
└── {city}/
    └── {poi_id}/
        ├── metadata.json
        ├── image_001.jpg
        ├── image_002.jpg
        └── image_003.jpg
```

**metadata.json**:
```json
{
  "poi_id": "colosseum",
  "city": "rome",
  "created_at": "2026-03-28T10:00:00Z",
  "updated_at": "2026-03-28T11:30:00Z",
  "images": [
    {
      "filename": "image_001.jpg",
      "uploaded_at": "2026-03-28T10:00:00Z",
      "uploaded_by": "admin@example.com",
      "caption": "Front view of Colosseum",
      "is_cover": true,
      "order": 0
    },
    {
      "filename": "image_002.jpg",
      "uploaded_at": "2026-03-28T10:15:00Z",
      "uploaded_by": "admin@example.com",
      "caption": "Interior view",
      "is_cover": false,
      "order": 1
    }
  ]
}
```

### Tour Images

```
tours/
└── {city}/
    └── {tour_id}/
        ├── images/
        │   ├── cover.jpg
        │   ├── gallery_001.jpg
        │   └── gallery_002.jpg
        └── metadata.json (updated with images field)
```

**metadata.json** (extended):
```json
{
  "tour_id": "rome-tour-123",
  "city": "rome",
  // ... existing fields ...
  "images": {
    "cover": {
      "filename": "cover.jpg",
      "uploaded_at": "2026-03-28T10:00:00Z",
      "uploaded_by": "admin@example.com",
      "caption": "Ancient Rome tour highlights"
    },
    "gallery": [
      {
        "filename": "gallery_001.jpg",
        "uploaded_at": "2026-03-28T10:15:00Z",
        "uploaded_by": "admin@example.com",
        "caption": "Day 1 route overview",
        "order": 0
      }
    ]
  }
}
```

---

## API Endpoints

### POI Image Management (Backstage)

#### 1. Upload POI Image

```
POST /backstage/pois/{city}/{poi_id}/images
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Fields:
- image: File (required) - Image file (JPEG, PNG, WebP)
- caption: String (optional) - Image description
- is_cover: Boolean (optional, default: false) - Set as cover image
- order: Integer (optional) - Display order
```

**Response**:
```json
{
  "success": true,
  "filename": "image_001.jpg",
  "url": "/pois/rome/colosseum/images/image_001.jpg",
  "message": "Image uploaded successfully"
}
```

#### 2. Get POI Images List

```
GET /pois/{city}/{poi_id}/images
```

**Response**:
```json
{
  "poi_id": "colosseum",
  "city": "rome",
  "images": [
    {
      "filename": "image_001.jpg",
      "url": "/pois/rome/colosseum/images/image_001.jpg",
      "caption": "Front view",
      "is_cover": true,
      "order": 0,
      "uploaded_at": "2026-03-28T10:00:00Z"
    }
  ]
}
```

#### 3. Serve POI Image

```
GET /pois/{city}/{poi_id}/images/{filename}
```

Returns the image file directly (Content-Type: image/jpeg, etc.)

#### 4. Delete POI Image

```
DELETE /backstage/pois/{city}/{poi_id}/images/{filename}
Authorization: Bearer {admin_token}
```

**Response**:
```json
{
  "success": true,
  "message": "Image deleted successfully"
}
```

#### 5. Update POI Image Metadata

```
PATCH /backstage/pois/{city}/{poi_id}/images/{filename}
Authorization: Bearer {admin_token}
Content-Type: application/json

Body:
{
  "caption": "Updated caption",
  "is_cover": true,
  "order": 0
}
```

---

### Tour Image Management (Backstage)

#### 1. Upload Tour Image

```
POST /backstage/tours/{tour_id}/images
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Fields:
- image: File (required)
- image_type: String (required) - "cover" or "gallery"
- caption: String (optional)
- order: Integer (optional, for gallery images)
```

**Response**:
```json
{
  "success": true,
  "filename": "cover.jpg",
  "url": "/tours/rome-tour-123/images/cover.jpg",
  "image_type": "cover",
  "message": "Tour image uploaded successfully"
}
```

#### 2. Get Tour Images

```
GET /tours/{tour_id}/images
```

**Response**:
```json
{
  "tour_id": "rome-tour-123",
  "cover": {
    "filename": "cover.jpg",
    "url": "/tours/rome-tour-123/images/cover.jpg",
    "caption": "Ancient Rome tour",
    "uploaded_at": "2026-03-28T10:00:00Z"
  },
  "gallery": [
    {
      "filename": "gallery_001.jpg",
      "url": "/tours/rome-tour-123/images/gallery_001.jpg",
      "caption": "Day 1 overview",
      "order": 0,
      "uploaded_at": "2026-03-28T10:15:00Z"
    }
  ]
}
```

#### 3. Serve Tour Image

```
GET /tours/{tour_id}/images/{filename}
```

Returns the image file directly.

#### 4. Delete Tour Image

```
DELETE /backstage/tours/{tour_id}/images/{filename}
Authorization: Bearer {admin_token}
```

---

## Integration with Existing APIs

### POI Metadata API

Add optional `images` field to POI responses:

```json
{
  "poi_id": "colosseum",
  "poi_name": "Colosseum",
  "city": "rome",
  "metadata": {
    // ... existing fields ...
  },
  "images": {
    "cover": {
      "url": "/pois/rome/colosseum/images/image_001.jpg",
      "caption": "Front view"
    },
    "gallery": [
      {
        "url": "/pois/rome/colosseum/images/image_002.jpg",
        "caption": "Interior view"
      }
    ]
  }
}
```

### Tour API

Add optional `images` field to tour responses:

```json
{
  "metadata": {
    "tour_id": "rome-tour-123",
    // ... existing fields ...
    "cover_image": "/tours/rome-tour-123/images/cover.jpg"
  },
  "images": {
    "cover": {
      "url": "/tours/rome-tour-123/images/cover.jpg",
      "caption": "Ancient Rome tour"
    },
    "gallery": [...]
  },
  "itinerary": [...]
}
```

---

## Backward Compatibility

### If No Images

```json
{
  "poi_id": "colosseum",
  "metadata": {...},
  // images field omitted or null
}
```

### If Images Not Supported by Client

Clients can simply ignore the `images` field. All existing functionality continues to work.

---

## File Upload Constraints

- **Max file size**: 10 MB per image
- **Allowed formats**: JPEG, PNG, WebP
- **Max images per POI**: 20 images
- **Max gallery images per tour**: 10 images
- **Image naming**: Sequential (image_001.jpg, image_002.jpg, etc.)

---

## Security

- **Upload**: Requires backstage admin authentication
- **View/Download**: Public access (no authentication)
- **Delete**: Requires backstage admin authentication
- **File validation**: Check MIME type and file extension
- **Sanitization**: Remove EXIF data for privacy

---

## Implementation Plan

### Phase 1: POI Images (Priority)
1. Create POI image storage structure
2. Add POI image upload endpoint (backstage)
3. Add POI image serve endpoint (public)
4. Add POI image list endpoint (public)
5. Add POI image delete endpoint (backstage)
6. Update POI API responses to include images

### Phase 2: Tour Images
1. Create tour image storage structure
2. Add tour image upload endpoint (backstage)
3. Add tour image serve endpoint (public)
4. Add tour image list endpoint (public)
5. Add tour image delete endpoint (backstage)
6. Update tour API responses to include images

### Phase 3: Image Management
1. Add image metadata update endpoint
2. Add image reordering capability
3. Add bulk upload support
4. Add image optimization (resize, compress)

---

## Testing Checklist

### POI Images
- [ ] Upload single image
- [ ] Upload multiple images
- [ ] Set cover image
- [ ] View images list
- [ ] Serve image file
- [ ] Delete image
- [ ] Update image metadata
- [ ] Backward compatibility (POIs without images)

### Tour Images
- [ ] Upload cover image
- [ ] Upload gallery images
- [ ] Replace cover image
- [ ] View images list
- [ ] Serve image file
- [ ] Delete images
- [ ] Backward compatibility (tours without images)

### Security
- [ ] Upload requires admin auth
- [ ] Non-admin cannot upload
- [ ] Non-admin cannot delete
- [ ] Public can view images
- [ ] File type validation
- [ ] File size validation

---

## Example Usage

### Backstage Upload POI Image

```javascript
const formData = new FormData();
formData.append('image', imageFile);
formData.append('caption', 'Front view of Colosseum');
formData.append('is_cover', 'true');

const response = await fetch('/backstage/pois/rome/colosseum/images', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
  },
  body: formData,
});
```

### Client Display POI Images

```dart
// Fetch POI with images
final poi = await apiService.getPOI('rome', 'colosseum');

if (poi.images != null && poi.images!.cover != null) {
  // Display cover image
  Image.network(poi.images!.cover!.url);
}

// Display gallery
if (poi.images?.gallery != null) {
  for (var img in poi.images!.gallery!) {
    Image.network(img.url);
  }
}
```

---

## Notes

- Images are stored locally in the backend filesystem
- Consider adding CDN support in the future
- Consider adding image optimization (thumbnails, WebP conversion)
- Consider adding image moderation/approval workflow
