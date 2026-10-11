package com.quasar.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.ViewModelProvider
import com.quasar.mobile.data.ApiClient
import com.quasar.mobile.data.TokenManager
import com.quasar.mobile.ui.QuasarApp
import com.quasar.mobile.viewmodel.AuthViewModel
import com.quasar.mobile.viewmodel.BackupViewModel

class MainActivity : ComponentActivity() {
    private lateinit var authViewModel: AuthViewModel
    private lateinit var backupViewModel: BackupViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val apiService = ApiClient.createService(this)
        val tokenManager = TokenManager(this)

        authViewModel = ViewModelProvider.Factory { AuthViewModel(apiService, tokenManager) }.let {
            ViewModelProvider(this, object : ViewModelProvider.Factory {
                override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                    return AuthViewModel(apiService, tokenManager) as T
                }
            }).get(AuthViewModel::class.java)
        }

        backupViewModel = ViewModelProvider.Factory { BackupViewModel(apiService) }.let {
            ViewModelProvider(this, object : ViewModelProvider.Factory {
                override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                    return BackupViewModel(apiService) as T
                }
            }).get(BackupViewModel::class.java)
        }

        setContent {
            QuasarApp(authViewModel, backupViewModel)
        }
    }
}
