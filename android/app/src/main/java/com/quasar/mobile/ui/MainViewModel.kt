package com.quasar.mobile.ui

import android.app.Application
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.quasar.mobile.engine.ArchiveEngine
import com.quasar.mobile.engine.ArchiveFormat
import com.quasar.mobile.engine.Crypto
import com.quasar.mobile.engine.Level
import com.quasar.mobile.engine.PickedSource
import com.quasar.mobile.engine.SourceEntry
import com.quasar.mobile.engine.Sources
import com.quasar.mobile.engine.TreeWriter
import com.quasar.mobile.licensing.LicenseManager
import com.quasar.mobile.licensing.OkHttpPoster
import com.quasar.mobile.licensing.PrefsStore
import com.quasar.mobile.licensing.Tier
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class LabRow(val format: ArchiveFormat, val sizeBytes: Long?, val millis: Long, val error: String? = null)

fun formatBytes(b: Long): String {
    if (b < 1024) return "$b B"
    val units = arrayOf("KB", "MB", "GB", "TB")
    var v = b.toDouble(); var i = -1
    while (v >= 1024 && i < units.size - 1) { v /= 1024; i++ }
    return String.format(Locale.US, "%.2f %s", v, units[i])
}

class MainViewModel(private val app: Application) : AndroidViewModel(app) {
    val licenses = LicenseManager(OkHttpPoster(), PrefsStore(app))

    // License state (snapshot so Compose recomposes)
    var tier by mutableStateOf(licenses.currentTier()); private set
    var backupsUsed by mutableStateOf(licenses.backupsUsed()); private set
    var licenseEmail by mutableStateOf(licenses.cachedLicense()?.email ?: ""); private set
    var licenseBusy by mutableStateOf(false); private set
    var licenseMessage by mutableStateOf<String?>(null)

    // Backup state
    val sources = mutableStateListOf<PickedSource>()
    var format by mutableStateOf(ArchiveFormat.ZSTD)
    var level by mutableStateOf(Level.BALANCED)
    var passphrase by mutableStateOf("")
    var outputFolder by mutableStateOf<Uri?>(null)
    var busy by mutableStateOf(false); private set
    var progress by mutableStateOf(0f); private set
    var status by mutableStateOf<String?>(null); private set
    var result by mutableStateOf<String?>(null); private set

    // Restore state
    var restoreArchive by mutableStateOf<Pair<Uri, String>?>(null)
    var restoreFolder by mutableStateOf<Uri?>(null)
    var restorePassphrase by mutableStateOf("")

    // Lab state
    var labFile by mutableStateOf<Pair<Uri, String>?>(null)
    var labRows by mutableStateOf<List<LabRow>>(emptyList()); private set

    init {
        viewModelScope.launch(Dispatchers.IO) {
            licenses.refreshIfDue()
            refreshLicense()
        }
    }

    fun refreshLicense() {
        tier = licenses.currentTier()
        backupsUsed = licenses.backupsUsed()
        licenseEmail = licenses.cachedLicense()?.email ?: ""
    }

    fun activate(key: String) {
        if (licenseBusy) return
        licenseBusy = true
        licenseMessage = null
        viewModelScope.launch {
            val err = withContext(Dispatchers.IO) { licenses.activate(key) }
            licenseBusy = false
            refreshLicense()
            licenseMessage = err ?: "License activated: ${tier.label} plan."
        }
    }

    fun deactivate() {
        licenses.deactivate()
        refreshLicense()
        licenseMessage = "License removed. You're on the Free plan."
    }

    fun addSource(uri: Uri, folder: Boolean) {
        if (sources.none { it.uri == uri }) sources += Sources.describe(app, uri, folder)
    }

    fun displayName(uri: Uri): String =
        app.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
            if (it.moveToFirst()) it.getString(0) else null
        } ?: "file"

    private fun cacheFile(name: String) = File(app.cacheDir, name).also { it.parentFile?.mkdirs() }

    fun runBackup() {
        if (busy) return
        result = null
        val check = licenses.canStartBackup()
        if (!check.allowed) { result = check.message; return }
        val out = outputFolder
        if (sources.isEmpty()) { result = "Add at least one file or folder."; return }
        if (out == null) { result = "Choose an output folder."; return }
        val pass = passphrase
        val fmt = format; val lvl = level
        busy = true; progress = 0f; status = "Scanning files..."
        viewModelScope.launch {
            val msg = withContext(Dispatchers.IO) {
                val tmp = cacheFile("backup.tmp")
                try {
                    val t0 = System.currentTimeMillis()
                    val entries = Sources.collect(app, sources.toList())
                    val original = entries.sumOf { it.size }
                    withContext(Dispatchers.Main) { status = "Compressing ${entries.size} files..." }
                    ArchiveEngine.create(entries, fmt, lvl, tmp) { d, t -> progress = d.toFloat() / t }
                    val archived = tmp.length()
                    val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
                    val encrypt = pass.isNotEmpty()
                    val name = "quasar-backup-$stamp${fmt.ext}${if (encrypt) ".qenc" else ""}"
                    withContext(Dispatchers.Main) { status = if (encrypt) "Encrypting..." else "Saving..." }
                    TreeWriter(app, out).open(name).use { os ->
                        if (encrypt) Crypto.encrypt(tmp, os, pass.toCharArray())
                        else tmp.inputStream().use { it.copyTo(os) }
                    }
                    licenses.recordBackup()
                    val secs = (System.currentTimeMillis() - t0) / 1000.0
                    "Saved $name\nOriginal: ${formatBytes(original)}\nArchive: ${formatBytes(archived)}" +
                        (if (encrypt) "\nEncrypted file: XChaCha20-Poly1305 (Argon2id key)" else "") +
                        "\nTime: ${String.format(Locale.US, "%.1f", secs)} s"
                } catch (e: Throwable) {
                    "Backup failed: ${e.message ?: e.javaClass.simpleName}"
                } finally { tmp.delete() }
            }
            busy = false; status = null; result = msg
            refreshLicense()
        }
    }

    fun runRestore() {
        if (busy) return
        result = null
        val arch = restoreArchive; val dest = restoreFolder
        if (arch == null) { result = "Choose an archive."; return }
        if (dest == null) { result = "Choose a destination folder."; return }
        val pass = restorePassphrase
        busy = true; status = "Restoring..."
        viewModelScope.launch {
            val msg = withContext(Dispatchers.IO) {
                val tmpEnc = cacheFile("restore.dec")
                val tmpArc = cacheFile("restore.in")
                try {
                    val encrypted = arch.second.lowercase().endsWith(".qenc")
                    val baseName = arch.second.removeSuffix(".qenc").removeSuffix(".QENC")
                    val fmt = ArchiveEngine.formatForName(baseName) ?: error("Unrecognised archive type: ${arch.second}")
                    val input = app.contentResolver.openInputStream(arch.first) ?: error("Cannot open the archive")
                    input.use {
                        if (encrypted) {
                            if (pass.isEmpty()) error("This archive is encrypted: enter the passphrase.")
                            Crypto.decrypt(it, tmpEnc, pass.toCharArray())
                        } else tmpEnc.outputStream().use { o -> it.copyTo(o) }
                    }
                    val writer = TreeWriter(app, dest)
                    val n = ArchiveEngine.extract(tmpEnc, fmt) { writer.open(it) }
                    "Restored $n files."
                } catch (e: Throwable) {
                    "Restore failed: ${e.message ?: e.javaClass.simpleName}"
                } finally { tmpEnc.delete(); tmpArc.delete() }
            }
            busy = false; status = null; result = msg
        }
    }

    fun runLab() {
        val f = labFile ?: return
        if (busy) return
        busy = true; labRows = emptyList(); progress = 0f
        val lvl = level
        viewModelScope.launch {
            val rows = ArrayList<LabRow>()
            for ((i, fmt) in ArchiveFormat.values().withIndex()) {
                status = "Testing ${fmt.label}..."
                val row = withContext(Dispatchers.IO) {
                    val tmp = cacheFile("lab.tmp")
                    val t0 = System.currentTimeMillis()
                    try {
                        val size = app.contentResolver.openAssetFileDescriptor(f.first, "r")?.use { it.length } ?: -1L
                        val entry = SourceEntry(f.second, size) { app.contentResolver.openInputStream(f.first)!! }
                        ArchiveEngine.create(listOf(entry), fmt, lvl, tmp)
                        LabRow(fmt, tmp.length(), System.currentTimeMillis() - t0)
                    } catch (e: Throwable) {
                        LabRow(fmt, null, System.currentTimeMillis() - t0, e.message ?: e.javaClass.simpleName)
                    } finally { tmp.delete() }
                }
                rows += row
                labRows = rows.toList()
                progress = (i + 1f) / ArchiveFormat.values().size
            }
            busy = false; status = null
        }
    }
}
