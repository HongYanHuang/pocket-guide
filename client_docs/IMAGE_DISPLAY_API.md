# POI and Tour Image Display API - Client Implementation Guide

## Overview

This guide shows how to display POI and tour images in your Flutter/mobile client app. Images are uploaded via the backstage admin panel and served through public API endpoints.

---

## Features

✅ **Optional Images** - Backward compatible, images are optional
✅ **Multiple Images** - POIs support up to 5 images, tours support 1 cover + 10 gallery
✅ **Cover Images** - Dedicated cover image for highlighting
✅ **Captions** - Each image can have a descriptive caption
✅ **Automatic Compression** - All images are compressed to JPEG (85% quality)
✅ **Public Access** - No authentication required to view images

---

## API Endpoints

### Get POI Images

```http
GET /pois/{city}/{poi_id}/images
```

**Example:**
```http
GET /pois/rome/colosseum/images
```

**Response:**
```json
{
  "poi_id": "colosseum",
  "city": "rome",
  "images": [
    {
      "filename": "image_001.jpg",
      "url": "/pois/rome/colosseum/images/image_001.jpg",
      "caption": "Front view of the Colosseum",
      "is_cover": true,
      "order": 0,
      "uploaded_at": "2026-03-28T10:00:00.000000"
    },
    {
      "filename": "image_002.jpg",
      "url": "/pois/rome/colosseum/images/image_002.jpg",
      "caption": "Interior view",
      "is_cover": false,
      "order": 1,
      "uploaded_at": "2026-03-28T11:00:00.000000"
    }
  ]
}
```

**If No Images:**
```json
{
  "poi_id": "colosseum",
  "city": "rome",
  "images": []
}
```

---

### Get POI Image File

```http
GET /pois/{city}/{poi_id}/images/{filename}
```

**Example:**
```http
GET /pois/rome/colosseum/images/image_001.jpg
```

**Response:** JPEG image file (binary)

---

### Get Tour Images

```http
GET /tours/{tour_id}/images
```

**Example:**
```http
GET /tours/rome-tour-20260304-095656-185fb3/images
```

**Response:**
```json
{
  "tour_id": "rome-tour-20260304-095656-185fb3",
  "cover": {
    "filename": "cover.jpg",
    "url": "/tours/rome-tour-20260304-095656-185fb3/images/cover.jpg",
    "caption": "Ancient Rome Tour Highlights",
    "uploaded_at": "2026-03-28T10:00:00.000000",
    "uploaded_by": "admin@example.com",
    "order": 0,
    "is_cover": true
  },
  "gallery": [
    {
      "filename": "gallery_001.jpg",
      "url": "/tours/rome-tour-20260304-095656-185fb3/images/gallery_001.jpg",
      "caption": "Day 1 Route Overview",
      "uploaded_at": "2026-03-28T11:00:00.000000",
      "uploaded_by": "admin@example.com",
      "order": 0,
      "is_cover": false
    }
  ]
}
```

**If No Images:**
```json
{
  "tour_id": "rome-tour-20260304-095656-185fb3",
  "cover": null,
  "gallery": []
}
```

---

### Get Tour Image File

```http
GET /tours/{tour_id}/images/{filename}
```

**Example:**
```http
GET /tours/rome-tour-20260304-095656-185fb3/images/cover.jpg
```

**Response:** JPEG image file (binary)

---

## Flutter Implementation

### 1. Data Models

```dart
// POI Image Model
class POIImage {
  final String filename;
  final String url;
  final String? caption;
  final bool isCover;
  final int order;
  final DateTime uploadedAt;

  POIImage({
    required this.filename,
    required this.url,
    this.caption,
    required this.isCover,
    required this.order,
    required this.uploadedAt,
  });

  factory POIImage.fromJson(Map<String, dynamic> json) {
    return POIImage(
      filename: json['filename'],
      url: json['url'],
      caption: json['caption'],
      isCover: json['is_cover'] ?? false,
      order: json['order'] ?? 0,
      uploadedAt: DateTime.parse(json['uploaded_at']),
    );
  }
}

// POI Images Response
class POIImagesResponse {
  final String poiId;
  final String city;
  final List<POIImage> images;

  POIImagesResponse({
    required this.poiId,
    required this.city,
    required this.images,
  });

  factory POIImagesResponse.fromJson(Map<String, dynamic> json) {
    return POIImagesResponse(
      poiId: json['poi_id'],
      city: json['city'],
      images: (json['images'] as List? ?? [])
          .map((img) => POIImage.fromJson(img))
          .toList(),
    );
  }

  // Get cover image
  POIImage? get coverImage =>
      images.firstWhere((img) => img.isCover, orElse: () => images.isNotEmpty ? images.first : null);

  // Get gallery images (sorted by order)
  List<POIImage> get galleryImages {
    final sorted = List<POIImage>.from(images);
    sorted.sort((a, b) => a.order.compareTo(b.order));
    return sorted;
  }
}

// Tour Image Model
class TourImage {
  final String filename;
  final String url;
  final String? caption;
  final DateTime uploadedAt;
  final String uploadedBy;
  final int order;
  final bool isCover;

  TourImage({
    required this.filename,
    required this.url,
    this.caption,
    required this.uploadedAt,
    required this.uploadedBy,
    required this.order,
    required this.isCover,
  });

  factory TourImage.fromJson(Map<String, dynamic> json) {
    return TourImage(
      filename: json['filename'],
      url: json['url'],
      caption: json['caption'],
      uploadedAt: DateTime.parse(json['uploaded_at']),
      uploadedBy: json['uploaded_by'],
      order: json['order'] ?? 0,
      isCover: json['is_cover'] ?? false,
    );
  }
}

// Tour Images Response
class TourImagesResponse {
  final String tourId;
  final TourImage? cover;
  final List<TourImage> gallery;

  TourImagesResponse({
    required this.tourId,
    this.cover,
    required this.gallery,
  });

  factory TourImagesResponse.fromJson(Map<String, dynamic> json) {
    return TourImagesResponse(
      tourId: json['tour_id'],
      cover: json['cover'] != null ? TourImage.fromJson(json['cover']) : null,
      gallery: (json['gallery'] as List? ?? [])
          .map((img) => TourImage.fromJson(img))
          .toList(),
    );
  }
}
```

---

### 2. API Service

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ImageApiService {
  final String baseUrl;

  ImageApiService({required this.baseUrl});

  // Get POI images
  Future<POIImagesResponse> getPOIImages(String city, String poiId) async {
    final url = Uri.parse('$baseUrl/pois/$city/$poiId/images');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return POIImagesResponse.fromJson(json.decode(response.body));
    } else if (response.statusCode == 404) {
      // No images found, return empty
      return POIImagesResponse(poiId: poiId, city: city, images: []);
    } else {
      throw Exception('Failed to load POI images: ${response.statusCode}');
    }
  }

  // Get tour images
  Future<TourImagesResponse> getTourImages(String tourId) async {
    final url = Uri.parse('$baseUrl/tours/$tourId/images');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return TourImagesResponse.fromJson(json.decode(response.body));
    } else if (response.statusCode == 404) {
      // No images found, return empty
      return TourImagesResponse(tourId: tourId, cover: null, gallery: []);
    } else {
      throw Exception('Failed to load tour images: ${response.statusCode}');
    }
  }

  // Build full image URL
  String getImageUrl(String relativeUrl) {
    return '$baseUrl$relativeUrl';
  }
}
```

---

### 3. UI Widgets

#### POI Image Gallery

```dart
class POIImageGallery extends StatelessWidget {
  final POIImagesResponse images;
  final String baseUrl;

  const POIImageGallery({
    Key? key,
    required this.images,
    required this.baseUrl,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (images.images.isEmpty) {
      return SizedBox.shrink(); // No images, hide widget
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Cover Image (if available)
        if (images.coverImage != null) ...[
          Text('Gallery', style: Theme.of(context).textTheme.titleLarge),
          SizedBox(height: 8),
          GestureDetector(
            onTap: () => _showFullscreenImage(context, images.coverImage!),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network(
                '$baseUrl${images.coverImage!.url}',
                height: 200,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) {
                  return Container(
                    height: 200,
                    color: Colors.grey[300],
                    child: Icon(Icons.broken_image, size: 50),
                  );
                },
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Container(
                    height: 200,
                    color: Colors.grey[200],
                    child: Center(child: CircularProgressIndicator()),
                  );
                },
              ),
            ),
          ),
          if (images.coverImage!.caption != null) ...[
            SizedBox(height: 4),
            Text(
              images.coverImage!.caption!,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          SizedBox(height: 16),
        ],

        // Gallery Grid
        if (images.images.length > 1) ...[
          Text('More Photos', style: Theme.of(context).textTheme.titleMedium),
          SizedBox(height: 8),
          GridView.builder(
            shrinkWrap: true,
            physics: NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: 1,
            ),
            itemCount: images.galleryImages.length,
            itemBuilder: (context, index) {
              final image = images.galleryImages[index];
              return GestureDetector(
                onTap: () => _showFullscreenImage(context, image),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    '$baseUrl${image.url}',
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        color: Colors.grey[300],
                        child: Icon(Icons.broken_image, size: 30),
                      );
                    },
                  ),
                ),
              );
            },
          ),
        ],
      ],
    );
  }

  void _showFullscreenImage(BuildContext context, POIImage image) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            title: Text(image.caption ?? ''),
          ),
          body: Center(
            child: InteractiveViewer(
              child: Image.network('$baseUrl${image.url}'),
            ),
          ),
        ),
      ),
    );
  }
}
```

#### Tour Cover Image

```dart
class TourCoverImage extends StatelessWidget {
  final TourImage? coverImage;
  final String baseUrl;

  const TourCoverImage({
    Key? key,
    this.coverImage,
    required this.baseUrl,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (coverImage == null) {
      return SizedBox.shrink(); // No cover image
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Image.network(
            '$baseUrl${coverImage!.url}',
            height: 250,
            width: double.infinity,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return Container(
                height: 250,
                color: Colors.grey[300],
                child: Icon(Icons.broken_image, size: 60),
              );
            },
          ),
        ),
        if (coverImage!.caption != null) ...[
          SizedBox(height: 8),
          Text(
            coverImage!.caption!,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ],
    );
  }
}
```

---

### 4. Usage Examples

#### POI Detail Screen

```dart
class POIDetailScreen extends StatefulWidget {
  final String city;
  final String poiId;

  @override
  _POIDetailScreenState createState() => _POIDetailScreenState();
}

class _POIDetailScreenState extends State<POIDetailScreen> {
  final imageService = ImageApiService(baseUrl: 'http://your-api-server:8000');
  POIImagesResponse? images;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _loadImages();
  }

  Future<void> _loadImages() async {
    try {
      final result = await imageService.getPOIImages(widget.city, widget.poiId);
      setState(() {
        images = result;
        loading = false;
      });
    } catch (e) {
      print('Failed to load images: $e');
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('POI Details')),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // POI basic info...

            SizedBox(height: 24),

            // Image Gallery
            if (!loading && images != null && images!.images.isNotEmpty)
              POIImageGallery(
                images: images!,
                baseUrl: imageService.baseUrl,
              ),

            // Rest of POI details...
          ],
        ),
      ),
    );
  }
}
```

#### Tour Detail Screen

```dart
class TourDetailScreen extends StatefulWidget {
  final String tourId;

  @override
  _TourDetailScreenState createState() => _TourDetailScreenState();
}

class _TourDetailScreenState extends State<TourDetailScreen> {
  final imageService = ImageApiService(baseUrl: 'http://your-api-server:8000');
  TourImagesResponse? images;

  @override
  void initState() {
    super.initState();
    _loadImages();
  }

  Future<void> _loadImages() async {
    try {
      final result = await imageService.getTourImages(widget.tourId);
      setState(() => images = result);
    } catch (e) {
      print('Failed to load images: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Tour Details')),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Tour Cover Image
            if (images?.cover != null)
              TourCoverImage(
                coverImage: images!.cover,
                baseUrl: imageService.baseUrl,
              ),

            SizedBox(height: 24),

            // Tour basic info...

            // Tour gallery images (if needed)
            if (images?.gallery.isNotEmpty ?? false) ...[
              SizedBox(height: 24),
              Text('Gallery', style: Theme.of(context).textTheme.titleLarge),
              SizedBox(height: 8),
              GridView.builder(
                shrinkWrap: true,
                physics: NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                ),
                itemCount: images!.gallery.length,
                itemBuilder: (context, index) {
                  final img = images!.gallery[index];
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      '${imageService.baseUrl}${img.url}',
                      fit: BoxFit.cover,
                    ),
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

---

## Error Handling

### Handle Missing Images Gracefully

```dart
Future<POIImagesResponse> getPOIImagesSafe(String city, String poiId) async {
  try {
    return await imageService.getPOIImages(city, poiId);
  } catch (e) {
    // Return empty response if API fails
    return POIImagesResponse(poiId: poiId, city: city, images: []);
  }
}
```

### Network Image with Fallback

```dart
Widget buildImageWithFallback(String imageUrl) {
  return Image.network(
    imageUrl,
    fit: BoxFit.cover,
    errorBuilder: (context, error, stackTrace) {
      // Show placeholder when image fails to load
      return Container(
        color: Colors.grey[300],
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.image_not_supported, size: 40, color: Colors.grey[600]),
            SizedBox(height: 8),
            Text('Image unavailable', style: TextStyle(color: Colors.grey[600])),
          ],
        ),
      );
    },
    loadingBuilder: (context, child, loadingProgress) {
      if (loadingProgress == null) return child;
      return Center(
        child: CircularProgressIndicator(
          value: loadingProgress.expectedTotalBytes != null
              ? loadingProgress.cumulativeBytesLoaded /
                loadingProgress.expectedTotalBytes!
              : null,
        ),
      );
    },
  );
}
```

---

## Best Practices

### 1. Caching

Use `cached_network_image` package for better performance:

```yaml
dependencies:
  cached_network_image: ^3.3.0
```

```dart
import 'package:cached_network_image/cached_network_image.dart';

CachedNetworkImage(
  imageUrl: '$baseUrl${image.url}',
  placeholder: (context, url) => CircularProgressIndicator(),
  errorWidget: (context, url, error) => Icon(Icons.error),
  fit: BoxFit.cover,
)
```

### 2. Lazy Loading

Load images only when needed:

```dart
class POIDetailScreen extends StatefulWidget {
  @override
  _POIDetailScreenState createState() => _POIDetailScreenState();
}

class _POIDetailScreenState extends State<POIDetailScreen> {
  POIImagesResponse? images;

  @override
  void initState() {
    super.initState();
    // Don't load images immediately
  }

  void _loadImagesWhenNeeded() async {
    if (images == null) {
      final result = await imageService.getPOIImages(widget.city, widget.poiId);
      setState(() => images = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        children: [
          // POI basic info...

          // Load images when user scrolls to this section
          VisibilityDetector(
            key: Key('images-section'),
            onVisibilityChanged: (info) {
              if (info.visibleFraction > 0.5) {
                _loadImagesWhenNeeded();
              }
            },
            child: images != null
                ? POIImageGallery(images: images!, baseUrl: baseUrl)
                : CircularProgressIndicator(),
          ),
        ],
      ),
    );
  }
}
```

### 3. Offline Support

Cache image metadata for offline viewing:

```dart
import 'package:shared_preferences/shared_preferences.dart';

Future<void> cacheImageMetadata(String poiId, POIImagesResponse images) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('poi_images_$poiId', json.encode(images.toJson()));
}

Future<POIImagesResponse?> getCachedImageMetadata(String poiId) async {
  final prefs = await SharedPreferences.getInstance();
  final cached = prefs.getString('poi_images_$poiId');
  if (cached != null) {
    return POIImagesResponse.fromJson(json.decode(cached));
  }
  return null;
}
```

---

## Testing

### Manual Testing Checklist

- [ ] POI with images displays correctly
- [ ] POI without images (empty response) handles gracefully
- [ ] Tour with cover image displays
- [ ] Tour with gallery images displays
- [ ] Tour without images handles gracefully
- [ ] Image tap opens fullscreen preview
- [ ] Network error shows placeholder
- [ ] Slow network shows loading indicator
- [ ] Images are cached after first load

### Test URLs

```dart
// Test with Colosseum (should have images)
final images = await imageService.getPOIImages('rome', 'colosseum');

// Test with POI that has no images
final empty = await imageService.getPOIImages('rome', 'unknown-poi');

// Test tour images
final tourImages = await imageService.getTourImages('rome-tour-20260304-095656-185fb3');
```

---

## FAQ

**Q: Are images required?**
A: No, images are completely optional. Your app should handle POIs/tours without images gracefully.

**Q: What image formats are supported?**
A: All images are automatically converted to JPEG format by the backend.

**Q: What's the maximum image size?**
A: Backend limits uploads to 5MB and compresses to ~85% quality JPEG.

**Q: Do I need authentication to view images?**
A: No, image viewing is public. Only upload/delete require admin authentication.

**Q: Can images change after I cache them?**
A: Yes, admins can upload/delete images anytime. Consider implementing cache invalidation or periodic refresh.

**Q: What if an image URL is broken?**
A: Always use `errorBuilder` in `Image.network()` to show a placeholder.

---

## Support

If you encounter issues:
1. Check API server is running at correct URL
2. Verify image URLs are accessible (test in browser)
3. Check network connectivity
4. Review error logs for API response errors
5. Ensure base URL doesn't have trailing slash

For backend issues, see `docs/IMAGE_UPLOAD_DESIGN.md`
