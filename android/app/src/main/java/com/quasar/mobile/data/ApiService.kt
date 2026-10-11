package com.quasar.mobile.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Field

interface QuasarApiService {
    @FormUrlEncoded
    @POST("auth/token")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): AuthResponse

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): UserData

    @GET("auth/me")
    suspend fun getCurrentUser(): UserData

    @GET("backups/providers")
    suspend fun listProviders(): ProviderListResponse

    @GET("backups/sessions")
    suspend fun listBackupSessions(): List<BackupSession>

    @POST("backups/sessions")
    suspend fun createBackupSession(@Body request: CreateBackupSessionRequest): BackupSession

    @GET("backups/sessions/{session_id}")
    suspend fun getBackupSession(@Path("session_id") sessionId: String): BackupSession

    @POST("backups/profile-link")
    suspend fun createProfileLink(): BackupProfileLink

    @GET("backups/profile-link")
    suspend fun getProfileLink(): BackupProfileLink
}

data class RegisterRequest(
    val email: String,
    val password: String,
    val full_name: String?
)

data class CreateBackupSessionRequest(
    val provider: String,
    val device_name: String? = null,
    val encrypted_file_path: String? = null,
    val backup_status: String = "queued"
)
