# MongoDB Schema

## Collections

### users

```javascript
{
  _id: ObjectId,
  email: String (unique, indexed),
  hashed_password: String,
  full_name: String,
  is_active: Boolean,
  created_at: Date,
  updated_at: Date
}
```

### backup_sessions

```javascript
{
  _id: ObjectId,
  user_id: String (indexed),
  provider: String,
  device_name: String,
  encrypted_file_path: String,
  backup_status: String, // "queued", "in_progress", "completed", "failed"
  upload_progress: Float, // 0.0 - 1.0
  created_at: Date,
  updated_at: Date
}
```

### backup_profiles

```javascript
{
  _id: ObjectId,
  user_id: String (unique, indexed),
  profile_slug: String (unique, indexed),
  link_url: String,
  is_public: Boolean,
  created_at: Date,
  last_accessed_at: Date
}
```

### provider_connections

```javascript
{
  _id: ObjectId,
  user_id: String (indexed),
  provider: String,
  external_account_id: String,
  is_connected: Boolean,
  created_at: Date,
  updated_at: Date
}
```

## Indexes

```javascript
db.users.createIndex({ email: 1 }, { unique: true })
db.backup_sessions.createIndex({ user_id: 1 })
db.backup_sessions.createIndex({ created_at: -1 })
db.backup_profiles.createIndex({ user_id: 1 }, { unique: true })
db.backup_profiles.createIndex({ profile_slug: 1 }, { unique: true })
db.provider_connections.createIndex({ user_id: 1 })
db.provider_connections.createIndex({ user_id: 1, provider: 1 }, { unique: true })
```
