package com.quasar.mobile.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@Composable
fun QuasarApp() {
    QuasarTheme {
        val navController = rememberNavController()

        NavHost(navController = navController, startDestination = "onboarding") {
            composable("onboarding") {
                OnboardingScreen(onContinue = { navController.navigate("auth_choice") })
            }
            composable("auth_choice") {
                Column(
                    modifier = androidx.compose.foundation.layout.Modifier
                        .fillMaxSize()
                        .background(QuasarColors.midnight)
                        .padding(24.dp),
                    verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
                ) {
                    Button(
                        onClick = { navController.navigate("sign_up") },
                        modifier = androidx.compose.foundation.layout.Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
                    ) {
                        Text("Create account")
                    }
                    Spacer(modifier = androidx.compose.foundation.layout.Modifier.height(12.dp))
                    OutlinedButton(
                        onClick = { navController.navigate("sign_in") },
                        modifier = androidx.compose.foundation.layout.Modifier.fillMaxWidth(),
                    ) {
                        Text("Sign in")
                    }
                }
            }
            composable("sign_up") {
                SignUpScreen(onContinue = { navController.navigate("cloud") })
            }
            composable("sign_in") {
                SignInScreen(onContinue = { navController.navigate("cloud") })
            }
            composable("cloud") {
                CloudSelectionScreen(onContinue = { navController.navigate("adb") })
            }
            composable("adb") {
                AdbGuidanceScreen(onComplete = { navController.navigate("status") })
            }
            composable("status") {
                UploadStatusScreen()
            }
        }
    }
}

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
