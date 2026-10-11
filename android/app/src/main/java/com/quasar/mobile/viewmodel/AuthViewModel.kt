package com.quasar.mobile.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.quasar.mobile.data.QuasarApiService
import com.quasar.mobile.data.RegisterRequest
import com.quasar.mobile.data.TokenManager
import com.quasar.mobile.data.UserData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class AuthState {
    data object Loading : AuthState()
    data class Authenticated(val user: UserData) : AuthState()
    data class Error(val message: String) : AuthState()
    data object Unauthenticated : AuthState()
}

class AuthViewModel(
    private val apiService: QuasarApiService,
    private val tokenManager: TokenManager
) : ViewModel() {
    private val _authState = MutableStateFlow<AuthState>(AuthState.Unauthenticated)
    val authState: StateFlow<AuthState> = _authState

    fun login(email: String, password: String) {
        _authState.value = AuthState.Loading
        viewModelScope.launch {
            try {
                val response = apiService.login(email, password)
                tokenManager.saveTokens(response.access_token, response.user.id, response.user.email)
                _authState.value = AuthState.Authenticated(response.user)
            } catch (e: Exception) {
                _authState.value = AuthState.Error(e.message ?: "Login failed")
            }
        }
    }

    fun register(email: String, password: String, fullName: String?) {
        _authState.value = AuthState.Loading
        viewModelScope.launch {
            try {
                val request = RegisterRequest(email, password, fullName)
                val user = apiService.register(request)
                _authState.value = AuthState.Authenticated(user)
            } catch (e: Exception) {
                _authState.value = AuthState.Error(e.message ?: "Registration failed")
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            tokenManager.clearTokens()
            _authState.value = AuthState.Unauthenticated
        }
    }
}
