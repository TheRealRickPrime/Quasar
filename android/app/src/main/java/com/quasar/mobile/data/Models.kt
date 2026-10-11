package com.quasar.mobile.data

data class AuthResponse(
    val access_token: String,
    val token_type: String,
    val user: UserData
)

data class UserData(
    val id: String,
    val email: String,
    val full_name: String?,
    val created_at: String
)

data class BackupSession(
    val id: String,
    val user_id: String,
    val provider: String,
    val device_name: String?,
    val encrypted_file_path: String?,
    val backup_status: String,
    val upload_progress: Float,
    val created_at: String,
    val updated_at: String
)

data class BackupProfileLink(
    val id: String,
    val user_id: String,
    val profile_slug: String,
    val link_url: String,
    val is_public: Boolean,
    val created_at: String,
    val last_accessed_at: String?
)

data class CloudProvider(
    val name: String,
    val display_name: String,
    val auth_type: String
)

data class ProviderListResponse(
    val providers: List<CloudProvider>
)
