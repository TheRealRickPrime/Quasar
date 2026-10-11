package com.quasar.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun OnboardingScreen(onContinue: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        QuasarColors.navy.copy(alpha = 0.95f),
                        QuasarColors.midnight,
                    )
                )
            )
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "QUASAR",
            style = MaterialTheme.typography.displaySmall,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "Your encrypted phone image backup, ready when you are.",
            style = MaterialTheme.typography.bodyLarge,
            color = QuasarColors.paper.copy(alpha = 0.82f),
        )
        Spacer(modifier = Modifier.height(28.dp))
        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Start secure backup")
        }
    }
}

@Composable
fun SignUpScreen(onContinue: () -> Unit) {
    val email = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }
    val fullName = remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Create account",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(24.dp))

        TextField(
            value = fullName.value,
            onValueChange = { fullName.value = it },
            label = { Text("Full name") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = email.value,
            onValueChange = { email.value = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = password.value,
            onValueChange = { password.value = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Create account")
        }
    }
}

@Composable
fun SignInScreen(onContinue: () -> Unit) {
    val email = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Sign in",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(24.dp))

        TextField(
            value = email.value,
            onValueChange = { email.value = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = password.value,
            onValueChange = { password.value = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Sign in")
        }
    }
}

@Composable
fun CloudSelectionScreen(onContinue: () -> Unit) {
    val selectedProvider = remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Choose your storage",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "Google Drive • Dropbox • OneDrive • AWS S3",
            color = QuasarColors.paper.copy(alpha = 0.75f),
        )
        Spacer(modifier = Modifier.height(24.dp))

        listOf(
            "Google Drive" to "google_drive",
            "Dropbox" to "dropbox",
            "OneDrive" to "onedrive",
            "AWS S3" to "aws_s3",
        ).forEach { (name, value) ->
            Button(
                onClick = {
                    selectedProvider.value = value
                    onContinue()
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (selectedProvider.value == value) QuasarColors.accent else QuasarColors.navy,
                ),
            ) {
                Text(name)
            }
            Spacer(modifier = Modifier.height(12.dp))
        }
    }
}

@Composable
fun AdbGuidanceScreen(onComplete: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Text(
            text = "ADB backup setup",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(20.dp))
        Text(
            text = "Follow these steps to create an encrypted backup of your phone:\n\n" +
                    "1. Enable Developer options\n" +
                    "   Settings → About device → Tap Build number 7 times\n\n" +
                    "2. Turn on USB debugging\n" +
                    "   Settings → Developer options → USB debugging\n\n" +
                    "3. Connect your phone to a computer via USB\n\n" +
                    "4. Open a terminal and run:\n" +
                    "   adb backup -all -f quasar_backup.ab\n\n" +
                    "5. Your phone will ask to confirm — approve it\n\n" +
                    "6. Upload the encrypted archive to your chosen provider",
            color = QuasarColors.paper.copy(alpha = 0.85f),
            style = MaterialTheme.typography.bodyMedium,
        )
        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = onComplete,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Backup ready")
        }
    }
}

@Composable
fun UploadStatusScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Text(
            text = "Upload status",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(20.dp))

        // Status card
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(QuasarColors.navy)
                .padding(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        text = "Session: Queued",
                        color = QuasarColors.paper,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "Secure connection active",
                        color = QuasarColors.steel,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(
                    text = "0%",
                    color = QuasarColors.accent,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            LinearProgressIndicator(
                progress = { 0f },
                modifier = Modifier.fillMaxWidth(),
                color = QuasarColors.accent,
                trackColor = QuasarColors.midnight,
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Profile link section
        Text(
            text = "Your profile",
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "quasar.app/u/your-profile",
            color = QuasarColors.accent,
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(
            text = "Use this link to check your backup status and access downloads from any device.",
            color = QuasarColors.steel,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
