# Native Google Sign-In SDK Integration

## Overview

The mobile app now uses Google's native Sign-In SDK instead of the OAuth browser flow. This provides a better user experience with platform-specific authentication UI.

## Flow

```
1. User taps "Sign in with Google" in app
2. Native Google SDK shows platform-specific sign-in UI
3. SDK returns ID token after successful authentication
4. App sends ID token to backend
5. Backend verifies token with Google
6. Backend returns access_token and refresh_token
7. App uses these tokens for API requests
```

## Backend Endpoint

### POST /auth/client/google/verify-token

**Purpose**: Verify Google ID token from native SDK and return app tokens

**Request**:
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE4MmU0MmMxMz..."
}
```

**Response** (Success - 200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Response** (Error - 400):
```json
{
  "detail": "Invalid ID token: Token expired"
}
```

**Response** (Error - 403):
```json
{
  "detail": "Client app registration is currently disabled. Please contact administrator."
}
```

---

## Client Implementation (Flutter)

### 1. Add Google Sign-In Package

```yaml
# pubspec.yaml
dependencies:
  google_sign_in: ^6.1.5
```

### 2. Configure iOS Client ID

```dart
// lib/config/auth_config.dart
class AuthConfig {
  // iOS OAuth Client ID (from backend team)
  static const String googleClientId =
    '498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com';
}
```

### 3. Implement Sign-In

```dart
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    clientId: AuthConfig.googleClientId,
    scopes: ['email', 'profile', 'openid'],
  );

  Future<Map<String, String>?> signInWithGoogle() async {
    try {
      // 1. Show Google Sign-In UI
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        // User cancelled
        return null;
      }

      // 2. Get authentication tokens
      final GoogleSignInAuthentication auth = await account.authentication;
      final String? idToken = auth.idToken;

      if (idToken == null) {
        throw Exception('Failed to get ID token');
      }

      // 3. Send ID token to backend
      final response = await http.post(
        Uri.parse('https://your-api.com/auth/client/google/verify-token'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'id_token': idToken}),
      );

      if (response.statusCode == 200) {
        // 4. Extract tokens
        final data = jsonDecode(response.body);
        return {
          'access_token': data['access_token'],
          'refresh_token': data['refresh_token'],
        };
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Authentication failed');
      }
    } catch (e) {
      print('Sign-in error: $e');
      return null;
    }
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    // Also clear stored tokens from secure storage
  }
}
```

### 4. Use Tokens for API Calls

```dart
class ApiService {
  final String accessToken;

  ApiService(this.accessToken);

  Future<http.Response> getTours() async {
    return await http.get(
      Uri.parse('https://your-api.com/client/tours'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
    );
  }
}
```

### 5. Handle Token Refresh

```dart
Future<String?> refreshAccessToken(String refreshToken) async {
  final response = await http.post(
    Uri.parse('https://your-api.com/auth/refresh'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'refresh_token': refreshToken}),
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    return data['access_token'];
  }
  return null;
}
```

---

## iOS Configuration

### 1. Add URL Scheme (Info.plist)

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.googleusercontent.apps.498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5</string>
    </array>
  </dict>
</array>
```

### 2. Update GoogleService-Info.plist

Download from Firebase Console and add to Xcode project.

---

## Testing

### 1. Test with Cloudflare Tunnel

```bash
# Start backend server
./scripts/start_api_server.sh

# In another terminal, start tunnel
./start-mobile-test-tmux.sh
# Or manually:
cloudflared tunnel --url http://localhost:8000
```

Use the tunnel URL in your app (e.g., `https://xyz.trycloudflare.com`).

### 2. Test Sign-In Flow

1. Tap "Sign in with Google"
2. Select Google account
3. Verify token is sent to backend
4. Check backend logs: `INFO:api_auth:ID token verified for user@example.com`
5. Confirm access_token and refresh_token are returned
6. Test API call with access_token

### 3. Test Error Cases

- Invalid token: Send expired/malformed ID token → expect 400 error
- Unverified email: Use account with unverified email → expect 403 error
- Public signup disabled: Set `allow_public_signup: false` → expect 403 error

---

## Backend Configuration

### Environment Variables

```bash
# .env file
GOOGLE_IOS_CLIENT_ID=498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com
```

### Config File

```yaml
# config.yaml
authentication:
  enabled: true
  allow_public_signup: true  # Set to false to disable new registrations
  default_role: client_user
  default_scopes:
    - client_app
    - read_tours
    - user_data

  google_oauth:
    clients:
      ios:
        client_id: "${GOOGLE_IOS_CLIENT_ID}"
```

---

## Differences from OAuth Browser Flow

| Feature | OAuth Browser Flow | Native SDK Flow |
|---------|-------------------|-----------------|
| User Experience | Opens browser/WebView | Native platform UI |
| Redirect URI | Custom URL scheme | Not needed |
| PKCE Required | Yes | No (handled by SDK) |
| Backend Endpoint | `/auth/client/google/callback` | `/auth/client/google/verify-token` |
| Client Secret | Not needed | Not needed |
| Token Verification | Exchange auth code | Verify ID token |

---

## Security Notes

1. **ID Token Verification**: Backend verifies token with Google's tokeninfo endpoint
2. **Client ID Validation**: Backend checks token's `aud` field matches iOS client ID
3. **Email Verification**: Backend requires email to be verified by Google
4. **Token Expiration**: ID tokens are short-lived (typically 1 hour)
5. **HTTPS Required**: All API calls must use HTTPS in production

---

## Troubleshooting

### "Invalid ID token: Token expired"
- ID tokens are short-lived
- Get a fresh token from SDK before sending to backend

### "Invalid client_id"
- Ensure iOS client ID matches in both:
  - Flutter app: `AuthConfig.googleClientId`
  - Backend: `.env` file `GOOGLE_IOS_CLIENT_ID`

### "Email not verified by Google"
- User must verify their email with Google first
- Ask user to check their Gmail and click verification link

### "Client app registration is currently disabled"
- Backend admin has disabled public signup
- Set `allow_public_signup: true` in `config.yaml`

---

## Next Steps

1. ✅ Backend endpoint implemented
2. ⬜ Implement Flutter sign-in flow
3. ⬜ Test with Cloudflare Tunnel
4. ⬜ Add token storage (secure storage)
5. ⬜ Implement token refresh logic
6. ⬜ Add error handling and retry logic
7. ⬜ Test on physical iOS device
