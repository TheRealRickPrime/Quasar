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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.quasar.mobile.viewmodel.BackupState
import com.quasar.mobile.viewmodel.BackupViewModel

@Composable
fun CloudSelectionScreen(backupViewModel: BackupViewModel, onContinue: () -> Unit) {
    val selectedProvider = remember { mutableStateOf("") }
    val providers = backupViewModel.providers.collectAsState()

    LaunchedEffect(Unit) {
        backupViewModel.fetchProviders()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
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

        providers.value.forEach { provider ->
            Button(
                onClick = {
                    selectedProvider.value = provider.name
                    backupViewModel.createBackupSession(provider.name, "My Device")
                    onContinue()
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (selectedProvider.value == provider.name) QuasarColors.accent else QuasarColors.navy,
                ),
            ) {
                Text(provider.display_name)
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
fun UploadStatusScreen(backupViewModel: BackupViewModel) {
    val sessions = backupViewModel.sessions.collectAsState()
    val backupState = backupViewModel.backupState.collectAsState()

    LaunchedEffect(Unit) {
        backupViewModel.fetchBackupSessions()
    }

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

        when (backupState.value) {
            BackupState.Loading -> {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                    color = QuasarColors.accent,
                )
            }
            is BackupState.Error -> {
                Text(
                    text = (backupState.value as BackupState.Error).message,
                    color = QuasarColors.accent,
                )
            }
            is BackupState.ProfileLinkGenerated -> {
                val link = (backupState.value as BackupState.ProfileLinkGenerated).link
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(QuasarColors.navy)
                        .padding(16.dp),
                ) {
                    Text(
                        text = "Your profile",
                        color = QuasarColors.paper,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = link.link_url,
                        color = QuasarColors.accent,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Use this link to check your backup status and access downloads.",
                        color = QuasarColors.steel,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
            else -> {}
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Active sessions
        Text(
            text = "Active backups",
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(12.dp))

        sessions.value.forEach { session ->
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
                            text = session.device_name ?: "Unnamed Device",
                            color = QuasarColors.paper,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = session.provider.uppercase(),
                            color = QuasarColors.steel,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    Text(
                        text = "${(session.upload_progress * 100).toInt()}%",
                        color = QuasarColors.accent,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                LinearProgressIndicator(
                    progress = { session.upload_progress },
                    modifier = Modifier.fillMaxWidth(),
                    color = QuasarColors.accent,
                    trackColor = QuasarColors.midnight,
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        Button(
            onClick = { backupViewModel.generateProfileLink() },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Generate profile link")
        }
    }
}
