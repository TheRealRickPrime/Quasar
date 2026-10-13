package com.quasar.mobile.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.lifecycle.viewmodel.compose.viewModel
import com.quasar.mobile.engine.ArchiveFormat
import com.quasar.mobile.engine.Level
import com.quasar.mobile.licensing.Tier

@Composable
fun QuasarApp() {
    val nav = rememberNavController()
    val vm: MainViewModel = viewModel()
    val back = { nav.popBackStack(); Unit }
    NavHost(nav, startDestination = "home") {
        composable("home") { HomeScreen(vm) { nav.navigate(it) } }
        composable("backup") { Page("Backup", back) { BackupScreen(vm) } }
        composable("restore") { Page("Restore", back) { RestoreScreen(vm) } }
        composable("lab") { Page("Compression Lab", back) { LabScreen(vm) } }
        composable("license") { Page("License", back) { LicenseScreen(vm) } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Page(title: String, onBack: () -> Unit, content: @Composable () -> Unit) {
    Scaffold(topBar = {
        TopAppBar(title = { Text(title) }, navigationIcon = {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
        })
    }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) { content() }
    }
}

@Composable
private fun Section(title: String, body: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            body()
        }
    }
}

@Composable
private fun HomeScreen(vm: MainViewModel, go: (String) -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Spacer(Modifier.height(24.dp))
        Text("Quasar", style = MaterialTheme.typography.displaySmall, color = QuasarColors.accent)
        Text("Compress and encrypt your files. No account needed.", color = QuasarColors.steel)
        val limit = vm.tier.backupsPerMonth?.toString() ?: "unlimited"
        Section("${vm.tier.label} plan") {
            Text("Backups this month: ${vm.backupsUsed} of $limit")
        }
        Button(onClick = { go("backup") }, Modifier.fillMaxWidth()) { Text("New backup") }
        OutlinedButton(onClick = { go("restore") }, Modifier.fillMaxWidth()) { Text("Restore an archive") }
        OutlinedButton(onClick = { go("lab") }, Modifier.fillMaxWidth()) { Text("Compression Lab") }
        OutlinedButton(onClick = { go("license") }, Modifier.fillMaxWidth()) { Text("Settings / License") }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FormatPicker(vm: MainViewModel, showFormat: Boolean = false) {
    if (showFormat) {
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ArchiveFormat.values().forEach { f ->
                FilterChip(vm.format == f, { vm.format = f }, { Text(f.label) })
            }
        }
    }
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Level.values().forEach { l -> FilterChip(vm.level == l, { vm.level = l }, { Text(l.label) }) }
    }
}

@Composable
private fun StatusBlock(vm: MainViewModel) {
    if (vm.busy) {
        vm.status?.let { Text(it) }
        LinearProgressIndicator(progress = { vm.progress }, modifier = Modifier.fillMaxWidth())
    }
    vm.result?.let { Section("Result") { Text(it) } }
}

@Composable
private fun BackupScreen(vm: MainViewModel) {
    val files = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { l ->
        l.forEach { vm.addSource(it, false) }
    }
    val folder = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { u ->
        if (u != null) vm.addSource(u, true)
    }
    val out = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { u ->
        if (u != null) vm.outputFolder = u
    }
    Section("1. Sources") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { files.launch(arrayOf("*/*")) }) { Text("Add files") }
            OutlinedButton(onClick = { folder.launch(null) }) { Text("Add folder") }
            if (vm.sources.isNotEmpty()) OutlinedButton(onClick = { vm.sources.clear() }) { Text("Clear") }
        }
        if (vm.sources.isEmpty()) Text("Nothing selected yet.", color = QuasarColors.softGray)
        vm.sources.forEach { Text((if (it.isFolder) "[folder] " else "") + it.name) }
    }
    Section("2. Format and level") { FormatPicker(vm, showFormat = true) }
    Section("3. Passphrase (optional)") {
        OutlinedTextField(vm.passphrase, { vm.passphrase = it }, Modifier.fillMaxWidth(),
            label = { Text("Leave empty for no encryption") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation())
        Text("Encrypted with XChaCha20-Poly1305; the key is derived with Argon2id. There is no way to recover a lost passphrase.",
            style = MaterialTheme.typography.bodySmall, color = QuasarColors.softGray)
    }
    Section("4. Save to") {
        OutlinedButton(onClick = { out.launch(null) }) { Text(if (vm.outputFolder == null) "Choose output folder" else "Folder chosen (tap to change)") }
    }
    Button(onClick = { vm.runBackup() }, Modifier.fillMaxWidth(), enabled = !vm.busy) { Text("Start backup") }
    StatusBlock(vm)
}

@Composable
private fun RestoreScreen(vm: MainViewModel) {
    val arch = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        if (u != null) vm.restoreArchive = u to vm.displayName(u)
    }
    val dest = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { u ->
        if (u != null) vm.restoreFolder = u
    }
    Section("Archive") {
        OutlinedButton(onClick = { arch.launch(arrayOf("*/*")) }) { Text("Choose archive") }
        Text(vm.restoreArchive?.second ?: "None selected", color = QuasarColors.softGray)
        OutlinedTextField(vm.restorePassphrase, { vm.restorePassphrase = it }, Modifier.fillMaxWidth(),
            label = { Text("Passphrase (if encrypted)") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation())
    }
    Section("Restore into") {
        OutlinedButton(onClick = { dest.launch(null) }) { Text(if (vm.restoreFolder == null) "Choose folder" else "Folder chosen (tap to change)") }
    }
    Button(onClick = { vm.runRestore() }, Modifier.fillMaxWidth(), enabled = !vm.busy) { Text("Restore") }
    StatusBlock(vm)
}

@Composable
private fun LabScreen(vm: MainViewModel) {
    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        if (u != null) vm.labFile = u to vm.displayName(u)
    }
    Text("Runs every format on one file and compares size and time. Nothing is saved.", color = QuasarColors.steel)
    Section("File") {
        OutlinedButton(onClick = { pick.launch(arrayOf("*/*")) }) { Text("Choose file") }
        Text(vm.labFile?.second ?: "None selected", color = QuasarColors.softGray)
        FormatPicker(vm)
    }
    Button(onClick = { vm.runLab() }, Modifier.fillMaxWidth(), enabled = !vm.busy && vm.labFile != null) { Text("Run comparison") }
    if (vm.busy) {
        vm.status?.let { Text(it) }
        LinearProgressIndicator(progress = { vm.progress }, modifier = Modifier.fillMaxWidth())
    }
    if (vm.labRows.isNotEmpty()) Section("Results") {
        vm.labRows.forEach { r ->
            val line = if (r.sizeBytes != null) "${formatBytes(r.sizeBytes)}  -  ${r.millis} ms" else "failed: ${r.error}"
            Text("${r.format.label}: $line")
        }
    }
}

@Composable
private fun LicenseScreen(vm: MainViewModel) {
    val ctx = LocalContext.current
    var key by remember { mutableStateOf("") }
    fun open(url: String) = ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    Section("Current plan: ${vm.tier.label}") {
        val limit = vm.tier.backupsPerMonth?.toString() ?: "unlimited"
        Text("Backups this month: ${vm.backupsUsed} of $limit")
        Text(vm.tier.uploadBytesPerMonth?.let { "Cloud upload: ${it / (1024L * 1024 * 1024)} GB per month" } ?: "Cloud upload: unlimited")
        if (vm.licenseEmail.isNotEmpty()) Text("Licensed to ${vm.licenseEmail}", color = QuasarColors.softGray)
    }
    Section("Activate a license") {
        OutlinedTextField(key, { key = it }, Modifier.fillMaxWidth(), label = { Text("License key") }, singleLine = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { vm.activate(key) }, enabled = !vm.licenseBusy && key.isNotBlank()) {
                Text(if (vm.licenseBusy) "Checking..." else "Activate")
            }
            OutlinedButton(onClick = { vm.deactivate() }, enabled = vm.tier != Tier.FREE || vm.licenseEmail.isNotEmpty()) { Text("Deactivate") }
        }
        vm.licenseMessage?.let { Text(it) }
    }
    Section("Plans") {
        Text("Free ($0): 6 backups and 2 GB cloud upload per month")
        Text("Supporter ($10): 15 backups and 30 GB cloud upload per month")
        Text("Pro ($25 one-time): unlimited backups and upload")
        Button(onClick = { open("https://quasarlabs3.gumroad.com/l/qygwf") }, Modifier.fillMaxWidth()) { Text("Buy Supporter - $10") }
        Button(onClick = { open("https://quasarlabs3.gumroad.com/l/qwjtj") }, Modifier.fillMaxWidth()) { Text("Buy Pro - $25") }
    }
    Section("Updates") {
        Text(vm.updateMessage)
        Button(onClick = { vm.checkOrInstallUpdate() }, enabled = !vm.updateBusy, modifier = Modifier.fillMaxWidth()) {
            Text("Check for updates")
        }
    }
    Text("Support: quasarlabs-inc@outlook.com", color = QuasarColors.steel)
    Text("Copyright (c) 2026 Quasar Labs. All rights reserved.", color = QuasarColors.softGray,
        style = MaterialTheme.typography.bodySmall)
}
