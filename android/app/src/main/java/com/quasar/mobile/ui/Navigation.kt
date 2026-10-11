package com.quasar.mobile.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.quasar.mobile.viewmodel.AuthViewModel
import com.quasar.mobile.viewmodel.BackupViewModel

@Composable
fun QuasarApp(authViewModel: AuthViewModel, backupViewModel: BackupViewModel) {
    QuasarTheme {
        val navController = rememberNavController()

        NavHost(navController = navController, startDestination = "onboarding") {
            composable("onboarding") {
                OnboardingScreen(onContinue = { navController.navigate("auth_choice") })
            }
            composable("auth_choice") {
                AuthChoiceScreen(
                    onSignUp = { navController.navigate("sign_up") },
                    onSignIn = { navController.navigate("sign_in") },
                )
            }
            composable("sign_up") {
                SignUpScreen(
                    authViewModel = authViewModel,
                    onContinue = { navController.navigate("cloud") }
                )
            }
            composable("sign_in") {
                SignInScreen(
                    authViewModel = authViewModel,
                    onContinue = { navController.navigate("cloud") }
                )
            }
            composable("cloud") {
                CloudSelectionScreen(
                    backupViewModel = backupViewModel,
                    onContinue = { navController.navigate("adb") }
                )
            }
            composable("adb") {
                AdbGuidanceScreen(onComplete = { navController.navigate("status") })
            }
            composable("status") {
                UploadStatusScreen(backupViewModel)
            }
        }
    }
}

@Composable
fun AuthChoiceScreen(onSignUp: () -> Unit, onSignIn: () -> Unit) {
    androidx.compose.foundation.layout.Column(
        modifier = androidx.compose.foundation.layout.Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .padding(24.dp),
        verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
    ) {
        androidx.compose.material3.Button(
            onClick = onSignUp,
            modifier = androidx.compose.foundation.layout.Modifier.fillMaxWidth(),
            colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            androidx.compose.material3.Text("Create account")
        }
        androidx.compose.foundation.layout.Spacer(modifier = androidx.compose.foundation.layout.Modifier.height(12.dp))
        androidx.compose.material3.OutlinedButton(
            onClick = onSignIn,
            modifier = androidx.compose.foundation.layout.Modifier.fillMaxWidth(),
        ) {
            androidx.compose.material3.Text("Sign in")
        }
    }
}

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
