# API Parameter Handling Guide

## Summary

**FastAPI already ignores undefined parameters by default.** This behavior is guaranteed and built into the framework.

---

## How It Works

### ✅ Undefined Parameters (Ignored)

Extra query parameters that are **not defined** in the endpoint signature are **automatically ignored**.

**Example:**

```python
# Endpoint definition
async def get_progress(tour_id: str, language: str = "en"):
    ...
```

**Request with extra parameters:**
```bash
GET /tours/abc/progress?language=en&foo=bar&random=123
```

**Result:** ✅ Works fine
- `language=en` is used
- `foo=bar` and `random=123` are **silently ignored**
- No error returned

---

### ⚠️ Invalid Parameter Values (Validation Error)

If a **defined** parameter receives an invalid value, FastAPI returns a `422 Unprocessable Entity` error.

**Example:**

```python
# Endpoint expects integer
async def update_progress(poi_id: str, day: int, completed: bool):
    ...
```

**Request with wrong type:**
```bash
POST /tours/abc/progress
Body: {"poi_id": "test", "day": "not-a-number", "completed": true}
```

**Result:** ⚠️ Returns 422 with clear error message
```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "body.day",
      "message": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

---

## Global Exception Handlers (Added)

We've added two global exception handlers to make the API more robust:

### 1. Validation Error Handler

**Purpose:** Provide user-friendly error messages for invalid parameters

**Returns:** 422 with structured error details

**Example Response:**
```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "query.language",
      "message": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 2. General Exception Handler

**Purpose:** Catch unexpected errors and return JSON instead of HTML

**Returns:** 500 with generic error message

**Example Response:**
```json
{
  "detail": "Internal server error",
  "message": "An unexpected error occurred. Please contact support if this persists."
}
```

---

## API Behavior Summary

| Scenario | Behavior | HTTP Status |
|----------|----------|-------------|
| Extra/undefined query params | **Ignored** ✅ | 200 (normal response) |
| Missing required param | Validation error | 422 |
| Wrong param type | Validation error | 422 |
| Invalid enum value | Validation error | 422 |
| Malformed JSON body | Validation error | 422 |
| Resource not found | Not found error | 404 |
| Authentication failure | Auth error | 401/403 |
| Unexpected server error | Generic error | 500 |

---

## Client Guidelines

### ✅ DO

- Send extra parameters if needed (they'll be ignored)
- Use correct data types for defined parameters
- Check response status codes
- Handle 422 validation errors gracefully

### ❌ DON'T

- Rely on undefined parameters (they're ignored)
- Send wrong data types for defined parameters
- Expect 404 for parameter issues (you'll get 422)

---

## Examples

### Example 1: Multiple Undefined Parameters

**Request:**
```bash
GET /tours/rome-tour-123/progress?language=en&debug=true&version=2&timestamp=12345
```

**Result:** ✅ Success
- `language=en` is used
- All other parameters ignored
- Returns normal progress data

### Example 2: Invalid Day Number

**Request:**
```bash
POST /tours/rome-tour-123/progress
{
  "poi_id": "colosseum",
  "day": -5,
  "completed": true
}
```

**Result:** ⚠️ 422 Validation Error
```json
{
  "detail": "Invalid request parameters",
  "errors": [
    {
      "field": "body.day",
      "message": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Example 3: Completely Wrong Endpoint

**Request:**
```bash
GET /tours/rome-tour-123/nonexistent-endpoint
```

**Result:** ❌ 404 Not Found
```json
{
  "detail": "Not Found"
}
```

---

## Technical Details

### How FastAPI Handles Parameters

1. **Path parameters** (`/tours/{tour_id}`): Required, validated
2. **Query parameters** (`?language=en`): Optional by default, can be required
3. **Request body** (JSON): Validated against Pydantic models
4. **Extra parameters**: Ignored at HTTP layer

### Validation Flow

```
Request → CORS → Exception Handlers → Authentication → Validation → Endpoint Logic
            ↓           ↓                    ↓             ↓              ↓
          Allows    Catches errors      Checks JWT    Validates      Business
          origins   gracefully                        params         logic
```

---

## Conclusion

**You don't need to worry about undefined parameters** - FastAPI already handles them correctly by ignoring them. The global exception handlers we added make error messages clearer and ensure consistent JSON responses.

**The 404 error you saw was not from undefined parameters** - it was from the tour file not being found (which is now fixed).

---

**Document Version:** 1.0
**Last Updated:** 2026-03-21
**Author:** Backend Team
