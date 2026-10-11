package com.quasar.mobile.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.quasar.mobile.data.BackupProfileLink
import com.quasar.mobile.data.BackupSession
import com.quasar.mobile.data.CloudProvider
import com.quasar.mobile.data.CreateBackupSessionRequest
import com.quasar.mobile.data.QuasarApiService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class BackupState {
    data object Idle : BackupState()
    data object Loading : BackupState()
    data class SessionCreated(val session: BackupSession) : BackupState()
    data class ProfileLinkGenerated(val link: BackupProfileLink) : BackupState()
    data class Error(val message: String) : BackupState()
}

class BackupViewModel(private val apiService: QuasarApiService) : ViewModel() {
    private val _backupState = MutableStateFlow<BackupState>(BackupState.Idle)
    val backupState: StateFlow<BackupState> = _backupState

    private val _providers = MutableStateFlow<List<CloudProvider>>(emptyList())
    val providers: StateFlow<List<CloudProvider>> = _providers

    private val _sessions = MutableStateFlow<List<BackupSession>>(emptyList())
    val sessions: StateFlow<List<BackupSession>> = _sessions

    fun fetchProviders() {
        viewModelScope.launch {
            try {
                val response = apiService.listProviders()
                _providers.value = response.providers
            } catch (e: Exception) {
                _backupState.value = BackupState.Error(e.message ?: "Failed to fetch providers")
            }
        }
    }

    fun fetchBackupSessions() {
        viewModelScope.launch {
            try {
                _sessions.value = apiService.listBackupSessions()
            } catch (e: Exception) {
                _backupState.value = BackupState.Error(e.message ?: "Failed to fetch sessions")
            }
        }
    }

    fun createBackupSession(provider: String, deviceName: String?) {
        _backupState.value = BackupState.Loading
        viewModelScope.launch {
            try {
                val request = CreateBackupSessionRequest(
                    provider = provider,
                    device_name = deviceName,
                    backup_status = "queued"
                )
                val session = apiService.createBackupSession(request)
                _backupState.value = BackupState.SessionCreated(session)
                fetchBackupSessions()
            } catch (e: Exception) {
                _backupState.value = BackupState.Error(e.message ?: "Failed to create session")
            }
        }
    }

    fun generateProfileLink() {
        _backupState.value = BackupState.Loading
        viewModelScope.launch {
            try {
                val link = apiService.createProfileLink()
                _backupState.value = BackupState.ProfileLinkGenerated(link)
            } catch (e: Exception) {
                _backupState.value = BackupState.Error(e.message ?: "Failed to generate profile link")
            }
        }
    }
}
