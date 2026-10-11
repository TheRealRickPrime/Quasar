package com.quasar.mobile.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.quasar.mobile.cloud.EncryptedCloudProviderFactory
import com.quasar.mobile.cloud.CloudProvider
import com.quasar.mobile.cloud.StorageInfo
import com.quasar.mobile.data.QuasarApiService
import com.quasar.mobile.data.BackupProfileLink
import com.quasar.mobile.data.BackupSession
import com.quasar.mobile.data.ApiCloudProvider
import com.quasar.mobile.data.CreateBackupSessionRequest
import com.quasar.mobile.encryption.DualLayerEncryptionManager
import com.quasar.mobile.compression.CompressionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.io.File

sealed class AdvancedBackupState {
    data object Idle : AdvancedBackupState()
    data object Loading : AdvancedBackupState()
    data class ProviderConnected(val provider: String) : AdvancedBackupState()
    data class Processing(val stage: String, val progress: Float) : AdvancedBackupState()
    data class SessionCreated(val session: BackupSession) : AdvancedBackupState()
    data class ProfileLinkGenerated(val link: BackupProfileLink) : AdvancedBackupState()
    data class StorageInfoFetched(val storage: StorageInfo) : AdvancedBackupState()
    data class BackupComplete(val summary: BackupSummary) : AdvancedBackupState()
    data class Error(val message: String) : AdvancedBackupState()
}

data class BackupSummary(
    val originalSize: Long,
    val finalSize: Long,
    val spaceSaved: Long,
    val percentageReduced: Double,
    val securityLevel: String,
    val encryptionSteps: List<String>,
    val uploadUrl: String?
)

class AdvancedBackupViewModel(
    private val apiService: QuasarApiService,
    private val context: Context
) : ViewModel() {
    private val _backupState = MutableStateFlow<AdvancedBackupState>(AdvancedBackupState.Idle)
    val backupState: StateFlow<AdvancedBackupState> = _backupState

    private val _providers = MutableStateFlow<List<ApiCloudProvider>>(emptyList())
    val providers: StateFlow<List<ApiCloudProvider>> = _providers

    private val _sessions = MutableStateFlow<List<BackupSession>>(emptyList())
    val sessions: StateFlow<List<BackupSession>> = _sessions

    private val dualEncryption = DualLayerEncryptionManager(context, useXChaCha = true)
    private val compressionManager = CompressionManager()
    private var currentProvider: CloudProvider? = null
    private var currentProviderName: String? = null

    fun fetchProviders() {
        viewModelScope.launch {
            try {
                val response = apiService.listProviders()
                _providers.value = response.providers
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Failed to fetch providers")
            }
        }
    }

    fun fetchBackupSessions() {
        viewModelScope.launch {
            try {
                _sessions.value = apiService.listBackupSessions()
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Failed to fetch sessions")
            }
        }
    }

    fun connectToProvider(
        providerName: String,
        authCode: String,
        clientId: String = "",
        appKey: String = ""
    ) {
        _backupState.value = AdvancedBackupState.Loading
        viewModelScope.launch {
            try {
                currentProvider = EncryptedCloudProviderFactory.createEncryptedProvider(
                    context,
                    providerName,
                    clientId = clientId,
                    appKey = appKey
                )
                currentProviderName = providerName

                val authenticated = currentProvider?.authenticate(authCode) ?: false
                if (authenticated) {
                    _backupState.value = AdvancedBackupState.ProviderConnected(providerName)
                    fetchStorageInfo()
                } else {
                    _backupState.value = AdvancedBackupState.Error("Failed to authenticate with $providerName")
                }
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Provider connection failed")
            }
        }
    }

    /**
     * Upload with maximum security and compression.
     */
    fun uploadWithMaximumSecurity(
        file: File,
        compressionMethod: CompressionManager.CompressionMethod = CompressionManager.CompressionMethod.ZSTD_HIGH
    ) {
        _backupState.value = AdvancedBackupState.Processing("Preparing...", 0.0f)
        viewModelScope.launch {
            try {
                val provider = currentProvider ?: throw Exception("No provider connected")
                val providerName = currentProviderName ?: throw Exception("Provider name not set")

                // Encrypt with compression and dual layers
                val encryptedFile = File(file.parentFile, "${file.name}.encrypted")
                val encResult = dualEncryption.encryptFileWithSecurity(
                    inputFile = file,
                    outputFile = encryptedFile,
                    securityLevel = DualLayerEncryptionManager.SecurityLevel.MAXIMUM,
                    compressionMethod = compressionMethod
                ) { stage, progress ->
                    _backupState.value = AdvancedBackupState.Processing(stage, progress)
                }

                if (!encResult.success) {
                    throw Exception(encResult.error ?: "Encryption failed")
                }

                // Upload encrypted file
                var uploadProgress = 0.0f
                val fileId = provider.uploadFile(encryptedFile) { progress ->
                    uploadProgress = progress
                    _backupState.value = AdvancedBackupState.Processing(
                        "Uploading to $providerName...",
                        0.8f + (progress * 0.2f)  // Last 20% for upload
                    )
                }

                // Clean up
                encryptedFile.delete()

                // Create backup session
                val request = CreateBackupSessionRequest(
                    provider = providerName,
                    device_name = "Backup Device",
                    encrypted_file_path = fileId,
                    backup_status = "completed"
                )
                val session = apiService.createBackupSession(request)
                
                val summary = BackupSummary(
                    originalSize = encResult.originalSize,
                    finalSize = encResult.finalSize,
                    spaceSaved = encResult.spaceSaved,
                    percentageReduced = encResult.percentageReduced,
                    securityLevel = "MAXIMUM (Compression + Dual Encryption)",
                    encryptionSteps = encResult.encryptionSteps.map { it.name },
                    uploadUrl = fileId
                )

                _backupState.value = AdvancedBackupState.BackupComplete(summary)
                fetchBackupSessions()
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Backup failed")
            }
        }
    }

    fun fetchStorageInfo() {
        viewModelScope.launch {
            try {
                val provider = currentProvider ?: throw Exception("No provider connected")
                val storageInfo = provider.getStorageInfo()
                _backupState.value = AdvancedBackupState.StorageInfoFetched(storageInfo)
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Failed to fetch storage info")
            }
        }
    }

    fun generateProfileLink() {
        _backupState.value = AdvancedBackupState.Loading
        viewModelScope.launch {
            try {
                val link = apiService.createProfileLink()
                _backupState.value = AdvancedBackupState.ProfileLinkGenerated(link)
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Failed to generate profile link")
            }
        }
    }

    fun disconnectProvider() {
        viewModelScope.launch {
            try {
                currentProvider?.logout()
                currentProvider = null
                currentProviderName = null
                _backupState.value = AdvancedBackupState.Idle
            } catch (e: Exception) {
                _backupState.value = AdvancedBackupState.Error(e.message ?: "Logout failed")
            }
        }
    }
}
