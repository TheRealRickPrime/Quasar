# Quasar API Documentation

## Authentication

All endpoints (except `/health`) require a valid JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Register

**POST** `/api/v1/auth/register`

Request:
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

Response:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Login

**POST** `/api/v1/auth/token`

Request (form-encoded):
```
username=user@example.com
password=secure_password
```

Response:
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

## Backup Sessions

### List all backup sessions

**GET** `/api/v1/backups/sessions`

Response:
```json
[
  {
    "id": "session_id",
    "user_id": "user_id",
    "provider": "google_drive",
    "device_name": "My Phone",
    "backup_status": "queued",
    "upload_progress": 0.0,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
]
```

### Create backup session

**POST** `/api/v1/backups/sessions`

Request:
```json
{
  "provider": "google_drive",
  "device_name": "My Phone",
  "backup_status": "queued"
}
```

### Get backup session

**GET** `/api/v1/backups/sessions/{session_id}`

## Cloud Providers

### List available providers

**GET** `/api/v1/backups/providers`

Response:
```json
{
  "providers": [
    {"name": "google_drive", "display_name": "Google Drive", "auth_type": "oauth"},
    {"name": "dropbox", "display_name": "Dropbox", "auth_type": "oauth"},
    {"name": "onedrive", "display_name": "OneDrive", "auth_type": "oauth"},
    {"name": "aws_s3", "display_name": "AWS S3", "auth_type": "credentials"}
  ]
}
```

## Profile Links

### Create profile link

**POST** `/api/v1/backups/profile-link`

Response:
```json
{
  "id": "link_id",
  "user_id": "user_id",
  "profile_slug": "johndoe-abc123",
  "link_url": "https://quasar.app/u/johndoe-abc123",
  "is_public": false,
  "created_at": "2024-01-01T12:00:00Z",
  "last_accessed_at": null
}
```

### Get profile link

**GET** `/api/v1/backups/profile-link`
