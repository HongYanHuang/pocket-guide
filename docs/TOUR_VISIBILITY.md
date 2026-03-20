# Tour Creator Visibility Feature

## Overview

This feature adds creator-based visibility control for tours, allowing the system to differentiate between public tours (visible to everyone) and private tours (visible only to the creator).

## Tour Visibility Rules

### Public Tours
- **Visible to**: Everyone (authenticated and unauthenticated users)
- **Applies to**:
  - All existing tours (before this feature)
  - All tours created from backstage admin panel
  - Tours explicitly marked as public

### Private Tours
- **Visible to**:
  - Tour creator (authenticated user who created it)
  - Backstage admins (can see all tours)
- **Applies to**:
  - Tours created by client-side users (future feature)
  - Tours explicitly marked as private

## API Changes

### Tour Metadata Fields

New fields added to tour metadata:

```json
{
  "tour_id": "rome-tour-20260304-095656-185fb3",
  "city": "Rome",
  "created_at": "2026-03-04T09:56:56.724305",
  "updated_at": "2026-03-04T09:56:56.724305",

  // NEW: Creator information
  "creator_email": "admin@example.com",
  "creator_role": "backstage_admin",
  "created_via": "backstage_ui",
  "visibility": "public"
}
```

**Field Descriptions:**

- `creator_email` (string, optional): Email of the user who created the tour
- `creator_role` (string, optional): Role of creator (backstage_admin, client_user, etc.)
- `created_via` (string, optional): Source of creation ("backstage_ui" or "client_app")
- `visibility` (string, required): Tour visibility - "public" or "private"

### API Endpoints with Visibility Filtering

#### 1. `GET /tours` - List Tours

Returns only tours visible to the current user.

**Authentication**: Optional (returns more tours if authenticated)

**Filtering Logic:**
- Unauthenticated: Only public tours
- Authenticated client user: Public tours + own private tours
- Backstage admin: All tours

**Example Request:**
```bash
# Without auth - see only public tours
curl http://localhost:8000/tours

# With auth - see public + own private tours
curl -H "Authorization: Bearer <token>" http://localhost:8000/tours
```

**Response:**
```json
[
  {
    "tour_id": "rome-tour-20260304-095656-185fb3",
    "city": "Rome",
    "duration_days": 3,
    "total_pois": 12,
    "interests": ["history", "architecture"],
    "created_at": "2026-03-04T09:56:56.724305",
    "optimization_score": 0.58,
    "title_display": "Ancient Rome History · 3 Days",
    "creator_email": "admin@example.com",
    "visibility": "public"
  }
]
```

#### 2. `GET /tours/{tour_id}` - Get Tour Details

Returns tour details if user has permission to view.

**Authentication**: Optional

**Filtering Logic:**
- Public tour: Anyone can access
- Private tour: Only creator or backstage admin can access

**Example Request:**
```bash
# Get public tour (no auth needed)
curl http://localhost:8000/tours/rome-tour-20260304-095656-185fb3?language=en

# Get private tour (requires auth)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/tours/rome-tour-20260304-095656-185fb3?language=en
```

**Error Response (403 Forbidden):**
```json
{
  "detail": "You do not have permission to access this tour"
}
```

#### 3. `POST /tour/generate` - Generate New Tour

Now captures creator information when user is authenticated.

**Authentication**: Optional (anonymous if not provided)

**Behavior:**
- **Backstage admin authenticated**: Creates public tour with creator info
- **Client user authenticated**: Creates private tour with creator info (future)
- **Not authenticated**: Creates public tour without creator info

**Example Request:**
```bash
curl -X POST http://localhost:8000/tour/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "city": "rome",
    "days": 3,
    "interests": ["history", "architecture"],
    "provider": "anthropic",
    "save": true
  }'
```

### Admin Endpoints

#### `POST /admin/migrate-tours-visibility` (Admin Only)

Migrates all existing tours to have proper visibility settings.

**What it does:**
- Sets `visibility: "public"` for all existing tours
- Attempts to infer `creator_email` from version history
- Sets `created_via: "backstage_ui"` for existing tours
- Skips tours that already have visibility field

**Example Request:**
```bash
curl -X POST http://localhost:8000/admin/migrate-tours-visibility \
  -H "Authorization: Bearer <backstage-admin-token>"
```

**Response:**
```json
{
  "success": true,
  "message": "Migration complete",
  "migrated": 15,
  "errors": 0,
  "total_processed": 15
}
```

## Migration Guide

### Step 1: Run Migration (One-Time)

After deploying this feature, run the migration endpoint once to update all existing tours:

```bash
# Get admin token first
curl -X POST http://localhost:8000/auth/backstage/google/login \
  -d '{"redirect_uri": "http://localhost:5173/auth/callback", "code_challenge": "..."}'

# Run migration
curl -X POST http://localhost:8000/admin/migrate-tours-visibility \
  -H "Authorization: Bearer <admin-token>"
```

### Step 2: Verify Migration

Check that tours now have visibility field:

```bash
# List tours (should show creator_email and visibility fields)
curl http://localhost:8000/tours | jq '.[0] | {tour_id, creator_email, visibility}'
```

Expected output:
```json
{
  "tour_id": "rome-tour-20260304-095656-185fb3",
  "creator_email": null,
  "visibility": "public"
}
```

### Step 3: Test Visibility

**Test 1: Unauthenticated access to public tour** (Should work)
```bash
curl http://localhost:8000/tours/rome-tour-20260304-095656-185fb3
```

**Test 2: Create private tour as client user** (Future feature)
```bash
curl -X POST http://localhost:8000/tour/generate \
  -H "Authorization: Bearer <client-user-token>" \
  -d '{"city": "rome", "days": 2, "save": true}'

# Should create tour with visibility: "private"
```

**Test 3: Try to access someone else's private tour** (Should fail with 403)
```bash
curl -H "Authorization: Bearer <different-user-token>" \
  http://localhost:8000/tours/<private-tour-id>
```

## Integration with Client App

### Client-Side Tour Creation (Future)

When client-side users create tours via the mobile/web app:

1. **User must be authenticated** with `client_app` scope
2. **Tour visibility** defaults to "private"
3. **Only creator** can see the tour in their tour list
4. **Backstage admins** can see all tours (for support/moderation)

### Sharing Private Tours (Future Enhancement)

Potential future features:
- Share link: Generate shareable token for private tour
- Make public: Button to change visibility from private to public
- Collaborate: Allow multiple users to co-create a tour

## Backend Implementation Details

### TourManager Changes

The `save_tour()` method now:

1. **Captures creator info** from `user_info` parameter:
   ```python
   if 'creator_email' not in metadata and user_info:
       metadata['creator_email'] = user_info.get('email')
       metadata['creator_role'] = user_info.get('role')
   ```

2. **Sets visibility** based on source and role:
   ```python
   if created_via == 'backstage_ui' or creator_role in ['backstage_admin', 'backstage_editor']:
       metadata['visibility'] = 'public'
   else:
       metadata['visibility'] = 'private'
   ```

3. **Stores creation source**:
   ```python
   metadata['created_via'] = input_parameters.get('generated_via', 'backstage_ui')
   ```

### API Server Changes

1. **Optional auth dependency**: `get_optional_user()` returns user info if authenticated, None otherwise

2. **Visibility filtering** in `list_tours()`:
   ```python
   visibility = metadata.get('visibility', 'public')
   creator_email = metadata.get('creator_email')

   can_view = False
   if visibility == 'public':
       can_view = True
   elif current_user:
       if current_user.get('role') == 'backstage_admin':
           can_view = True
       elif current_user.get('email') == creator_email:
           can_view = True

   if can_view:
       tours.append(...)
   ```

3. **Access control** in `get_tour()`:
   - Same logic as list_tours()
   - Raises `403 Forbidden` if user lacks permission

## Configuration

No configuration changes required. The feature uses existing authentication configuration from `config.yaml`.

## Database Schema (Future)

When migrating to a database, create indexes:

```sql
CREATE INDEX idx_tours_visibility ON tours(visibility);
CREATE INDEX idx_tours_creator_email ON tours(creator_email);
CREATE INDEX idx_tours_visibility_creator ON tours(visibility, creator_email);
```

## Testing Checklist

- [ ] Existing tours default to public visibility
- [ ] Backstage-created tours are public
- [ ] Unauthenticated users see only public tours
- [ ] Authenticated users see public + own private tours
- [ ] Backstage admins see all tours
- [ ] Cannot access other users' private tours (403 error)
- [ ] Migration endpoint works correctly
- [ ] Tour generation captures creator info when authenticated

## Troubleshooting

### Issue: All tours are invisible after feature deploy

**Solution**: Run the migration endpoint to mark existing tours as public:
```bash
curl -X POST http://localhost:8000/admin/migrate-tours-visibility \
  -H "Authorization: Bearer <admin-token>"
```

### Issue: Cannot see own private tours

**Possible causes:**
1. Token expired - refresh access token
2. Wrong user - check `creator_email` in tour metadata
3. Tour visibility incorrectly set - check metadata.json

**Debug:**
```bash
# Check tour metadata
cat tours/rome/<tour-id>/metadata.json | jq '{creator_email, visibility}'

# Check token payload
# Decode JWT at https://jwt.io and verify email matches
```

### Issue: 403 Forbidden when accessing tour

**Causes:**
- Tour is private and you're not the creator
- Not authenticated when accessing private tour
- Token invalid/expired

**Solution:**
1. Verify authentication:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/auth/me
   ```
2. Check if you're the creator:
   ```bash
   cat tours/rome/<tour-id>/metadata.json | grep creator_email
   ```

## Future Enhancements

1. **Tour Sharing**: Generate shareable links for private tours
2. **Visibility Toggle**: Allow creators to change visibility after creation
3. **Collaborative Tours**: Multiple creators for one tour
4. **Tour Groups**: Organize tours into public/private groups
5. **Tour Discovery**: Public tour gallery with search/filter
6. **Tour Templates**: Public tours that can be copied and customized
