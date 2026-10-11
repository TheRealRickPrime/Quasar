package com.quasar.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun OnboardingScreen(onContinue: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                        MaterialTheme.colorScheme.background,
                    )
                )
            )
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Quasar",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = "Secure your device image. Protect your data. Keep access in your hands.",
            modifier = Modifier.padding(top = 16.dp, bottom = 32.dp),
            style = MaterialTheme.typography.bodyLarge,
        )

        Button(
            onClick = onContinue,
            shape = RoundedCornerShape(12.dp),
        ) {
            Text("Start backup setup")
        }
    }
}

@Composable
fun CloudSelectionScreen(onContinue: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Choose your cloud provider", style = MaterialTheme.typography.headlineMedium)
        Text("Google Drive, Dropbox, OneDrive, S3-compatible storage", modifier = Modifier.padding(top = 8.dp, bottom = 24.dp))
        Button(onClick = onContinue) {
            Text("Continue")
        }
    }
}

@Composable
fun AdbGuidanceScreen(onComplete: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Android Backup Setup", style = MaterialTheme.typography.headlineMedium)
        Text("1. Enable Developer options\n2. Turn on USB debugging\n3. Connect device to a computer\n4. Use ADB to create the encrypted backup\n5. Upload the archive to your preferred cloud provider", modifier = Modifier.padding(top = 16.dp, bottom = 24.dp))
        Button(onClick = onComplete) {
            Text("Complete setup")
        }
    }
}

@Composable
fun UploadStatusScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Upload status", style = MaterialTheme.typography.headlineMedium)
        Text("Queued", modifier = Modifier.padding(top = 12.dp))
        Text("Your cloud session and profile link will appear here.")
    }
}
