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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import androidx.compose.foundation.BorderStroke
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.DisposableEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
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
    val owner = LocalLifecycleOwner.current
    DisposableEffect(owner, vm) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) vm.recheckLicense()
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    val back = { nav.popBackStack(); Unit }
    NavHost(nav, startDestination = "home") {
        composable("home") { HomeScreen(vm) { nav.navigate(it) } }
        composable("backup") { Page("Backup", back) { BackupScreen(vm) } }
        composable("restore") { Page("Restore", back) { RestoreScreen(vm) } }
        composable("lab") { Page("Compression Lab", back) { LabScreen(vm) } }
        composable("license") { Page("License", back) { LicenseScreen(vm) } }
        composable("privacy") { Page("Privacy & data", back) { PrivacyScreen(vm) } }
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
        Column(Modifier.padding(pad).fillMaxSize().spaceTexture().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) { content() }
    }
}

@Composable
private fun Section(title: String, body: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(),
        border = BorderStroke(1.dp, QuasarColors.steel.copy(alpha = 0.18f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            body()
        }
    }
}

@Composable
private fun HomeScreen(vm: MainViewModel, go: (String) -> Unit) {
    Column(Modifier.fillMaxSize().spaceTexture().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
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
        OutlinedButton(onClick = { go("privacy") }, Modifier.fillMaxWidth()) { Text("Privacy & data") }
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
    var confirm by remember { mutableStateOf(false) }
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
    Text("Restoring replaces files with matching names in the selected folder. Choose a new empty " +
        "folder to avoid data loss.", style = MaterialTheme.typography.bodySmall, color = QuasarColors.steel)
    Button(onClick = { confirm = true }, Modifier.fillMaxWidth(),
        enabled = !vm.busy && vm.restoreArchive != null && vm.restoreFolder != null) { Text("Restore") }
    if (confirm) AlertDialog(
        onDismissRequest = { confirm = false },
        title = { Text("Restore and replace matching files?") },
        text = { Column(Modifier.verticalScroll(rememberScrollState())) {
            Text("Archive: ${vm.restoreArchive?.second}\nDestination: ${vm.restoreFolder}\n\n" +
                "Existing files with matching names will be deleted and recreated. " +
                "A failed restore can leave partial files. Use a new empty folder if possible.\n\n" +
                DataSafety.DELETE + "\n\n" + DataSafety.LEGAL)
        } },
        confirmButton = { TextButton(onClick = { confirm = false; vm.runRestore() }) { Text("Restore") } },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text("Cancel") } },
    )
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
    var confirmRemove by remember { mutableStateOf(false) }
    fun open(url: String) = ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    Section("Current plan: ${vm.tier.label}") {
        Text("Distribution: ${vm.edition.label}. A paid package alone does not activate a paid plan.")
        val limit = vm.tier.backupsPerMonth?.toString() ?: "unlimited"
        Text("Backups this month: ${vm.backupsUsed} of $limit")
        Text(vm.tier.uploadBytesPerMonth?.let { "Upload allowance: ${it / (1024L * 1024 * 1024)} GB per month" } ?: "Upload allowance: unlimited")
        Text("No hosted storage is included. This Android app saves to your chosen document folder; " +
            "a direct cloud-upload workflow is not implemented.", style = MaterialTheme.typography.bodySmall)
        if (vm.licenseEmail.isNotEmpty()) Text("Licensed to ${vm.licenseEmail}", color = QuasarColors.softGray)
    }
    Section("Activate a license") {
        OutlinedTextField(key, { key = it }, Modifier.fillMaxWidth(), label = { Text("Gumroad license key") },
            singleLine = true, visualTransformation = PasswordVisualTransformation())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { vm.activate(key) }, enabled = !vm.licenseBusy && key.isNotBlank()) {
                Text(if (vm.licenseBusy) "Checking..." else "Activate")
            }
            OutlinedButton(onClick = { confirmRemove = true },
                enabled = vm.licenses.cachedLicense() != null && !vm.licenseBusy) { Text("Deactivate") }
        }
        vm.licenseMessage?.let { Text(it) }
    }
    Section("Plans") {
        Text("Free ($0): 6 backups and 2 GB cloud upload per month")
        Text("Free with Ads ($0): 10 backups and 2 GB upload allowance per month; optional affiliate recommendations")
        Text("Supporter ($10): 15 backups and 30 GB cloud upload per month")
        Text("Pro ($25 one-time): unlimited backups and upload")
        Button(onClick = { open("https://quasarlabs3.gumroad.com/l/qygwf") }, Modifier.fillMaxWidth()) { Text("Buy Supporter - $10") }
        Button(onClick = { open("https://quasarlabs3.gumroad.com/l/qwjtj") }, Modifier.fillMaxWidth()) { Text("Buy Pro - $25") }
    }
    if (confirmRemove) AlertDialog(
        onDismissRequest = { confirmRemove = false },
        title = { Text("Remove local activation?") },
        text = { Text("This forgets the key on this device, not your Gumroad purchase, backups, " +
            "cloud copies or monthly usage. Keep your receipt key to activate again.") },
        confirmButton = { TextButton(onClick = { confirmRemove = false; vm.deactivate() }) { Text("Deactivate") } },
        dismissButton = { TextButton(onClick = { confirmRemove = false }) { Text("Cancel") } },
    )
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

@Composable
private fun PrivacyScreen(vm: MainViewModel) {
    val ctx = LocalContext.current
    Section("Local app data") {
        Text("Settings, usage and activation stay in this app's private storage across updates and " +
            "edition changes. Deactivate on the License page removes this device's key only. Android " +
            "Settings > Apps > Quasar > Storage > Clear storage (or uninstalling) removes local app data " +
            "and activation. Keep your receipt key. The app asks Android not to back up its private data; " +
            "device migration behavior may vary. Clearing Sources only clears the selection, not files.")
    }
    Section("Backups and cloud copies") {
        Text("Manage saved archives and restored files using your Android Files app or the document " +
            "provider you selected. Clearing app storage does not remove these saved files. Temporary " +
            "working files in Quasar's cache are normally deleted after operations; Android Settings " +
            "can clear remaining cache. Original selected source files are not deleted by backup. " +
            "Restore deletes/replaces matching names in the chosen folder. There is no secure-wipe " +
            "or cloud-delete feature. Manage cloud trash, versions, synced copies and retention through " +
            "the relevant provider. No hosted storage is included.")
    }
    Section("Permissions and connections") {
        Text("The system document picker grants access to files/folders you select; no all-files " +
            "permission is requested. Internet is used for Gumroad activation/rechecks and requested " +
            "update checks/downloads. Install-package permission is requested only for a user-approved " +
            "update, not automatic installation. Gumroad rechecks are due every 3 days with up to " +
            "30 days offline. There is no ad SDK, remote ad image, or affiliate tracking request from " +
            "these cards. A deliberate link tap opens your external browser, where that provider's " +
            "privacy/cookie policies apply.")
    }
    Section("Before deleting or overwriting") {
        Text(DataSafety.DELETE)
        Text(DataSafety.LEGAL)
    }
    if (vm.showAffiliates) Section("Affiliate recommendations - optional") {
        Text("Quasar Labs may earn a commission if you purchase through these links. No purchase or " +
            "click is required; recommendations never change your backup allowance. Independent " +
            "third-party services, not Quasar features.")
        Text("AdGuard - our primary recommendation. Optional ad blocking for browsers and devices.")
        OutlinedButton(onClick = { ctx.startActivity(Intent(Intent.ACTION_VIEW,
            Uri.parse("https://adguard.com/?aid=138471"))) }, Modifier.fillMaxWidth()) {
            Text("Explore AdGuard in browser")
        }
        Text("Optional alternatives for different needs:")
        OutlinedButton(onClick = { ctx.startActivity(Intent(Intent.ACTION_VIEW,
            Uri.parse("https://adguard-vpn.com/?aid=138471"))) }, Modifier.fillMaxWidth()) {
            Text("Explore AdGuard VPN in browser")
        }
        OutlinedButton(onClick = { ctx.startActivity(Intent(Intent.ACTION_VIEW,
            Uri.parse("https://adguard-dns.io/?aid=138471"))) }, Modifier.fillMaxWidth()) {
            Text("Explore AdGuard DNS in browser")
        }
    }
}
