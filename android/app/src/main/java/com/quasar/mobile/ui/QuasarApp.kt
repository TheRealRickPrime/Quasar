package com.quasar.mobile.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@Composable
fun QuasarApp() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = "onboarding") {
        composable("onboarding") {
            OnboardingScreen(
                onContinue = { navController.navigate("cloud") },
            )
        }
        composable("cloud") {
            CloudSelectionScreen(
                onContinue = { navController.navigate("adb") },
            )
        }
        composable("adb") {
            AdbGuidanceScreen(
                onComplete = { navController.navigate("status") },
            )
        }
        composable("status") {
            UploadStatusScreen()
        }
    }
}
