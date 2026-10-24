package com.quasar.mobile.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.content.pm.PackageManager
import android.provider.Settings
import androidx.core.content.FileProvider
import com.google.gson.JsonParser
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import java.util.zip.ZipFile
import java.net.URI
import com.quasar.mobile.BuildConfig
import com.quasar.mobile.licensing.Edition

const val MANIFEST_URL = "https://quasarli.github.io/latest.json"

data class UpdateInfo(
    val version: String, val versionCode: Long, val url: String, val sha256: String,
    val apkFile: String? = null, val apkSha256: String? = null,
)

/** Returns the Android entry from the manifest if its versionCode is newer than [currentCode]. */
fun parseManifest(json: String, currentCode: Long, edition: Edition = Edition.FREE): UpdateInfo? {
    val root = JsonParser.parseString(json).asJsonObject
    val platform = root.getAsJsonObject("android")
    val editions = platform.getAsJsonObject("editions")
    val a = if (editions != null) {
        editions.getAsJsonObject(edition.id) ?: throw IOException("No update is published for this distribution yet.")
    } else {
        if ((root.get("schemaVersion")?.asInt ?: 1) != 1 || edition != Edition.FREE) {
            throw IOException("No update is published for this distribution yet.")
        }
        platform
    }
    val version = a.get("version")?.asString ?: platform.get("version")?.asString
        ?: root.get("version").asString
    val info = UpdateInfo(
        version, a.get("versionCode").asLong,
        a.get("url").asString, a.get("sha256").asString,
        a.get("apkFile")?.asString, a.get("apkSha256")?.asString,
    )
    val uri = URI(info.url)
    require(uri.scheme == "https" && !uri.host.isNullOrEmpty() && uri.userInfo == null) { "Invalid update URL" }
    require(info.sha256.matches(Regex("[a-fA-F0-9]{64}"))) { "Invalid update SHA256" }
    if (editions != null) {
        require(info.apkFile?.matches(Regex("[A-Za-z0-9._-]+\\.apk")) == true) { "Invalid APK filename" }
        require(info.apkSha256?.matches(Regex("[a-fA-F0-9]{64}")) == true) { "Invalid APK SHA256" }
    }
    return if (info.versionCode > currentCode) info else null
}

fun extractApk(zip: File, info: UpdateInfo, out: File) {
    val name = info.apkFile ?: throw IOException("Missing APK filename")
    val sha = MessageDigest.getInstance("SHA-256")
    try {
        ZipFile(zip).use { archive ->
            val entries = archive.entries().asSequence().filter { it.name == name }.toList()
            val entry = entries.singleOrNull() ?: throw IOException("The ZIP must contain exactly one matching APK.")
            if (entry.size <= 0 || entry.size > 512L * 1024 * 1024) throw IOException("Invalid APK size")
            archive.getInputStream(entry).use { input ->
                out.outputStream().use { output ->
                    val buf = ByteArray(65536)
                    var done = 0L
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        done += n
                        if (done > 512L * 1024 * 1024) throw IOException("APK exceeds size limit")
                        output.write(buf, 0, n); sha.update(buf, 0, n)
                    }
                }
            }
        }
        val hash = sha.digest().joinToString("") { "%02x".format(it) }
        if (!hash.equals(info.apkSha256, ignoreCase = true)) throw IOException("APK integrity check failed")
    } catch (e: IOException) {
        out.delete()
        throw e
    }
}

class Updater(
    private val context: Context,
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS).readTimeout(60, TimeUnit.SECONDS).build(),
) {
    @Suppress("DEPRECATION")
    fun currentCode(): Long {
        val pi = context.packageManager.getPackageInfo(context.packageName, 0)
        return if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else pi.versionCode.toLong()
    }

    fun check(): UpdateInfo? {
        client.newCall(Request.Builder().url(MANIFEST_URL).build()).execute().use { r ->
            if (!r.isSuccessful) throw IOException("Update server returned ${r.code}")
            return parseManifest(r.body!!.string(), currentCode(), Edition.fromId(BuildConfig.EDITION))
        }
    }

    fun download(info: UpdateInfo, onProgress: (Float) -> Unit): File {
        val dir = File(context.cacheDir, "updates").apply { deleteRecursively(); mkdirs() }
        val out = File(dir, if (info.apkFile != null) "download.zip" else "Quasar-update.apk")
        val sha = MessageDigest.getInstance("SHA-256")
        client.newCall(Request.Builder().url(info.url).build()).execute().use { r ->
            if (!r.isSuccessful) throw IOException("Download failed (${r.code})")
            val body = r.body!!
            val total = body.contentLength().toFloat()
            var done = 0L
            body.byteStream().use { input ->
                out.outputStream().use { os ->
                    val buf = ByteArray(1 shl 16)
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        os.write(buf, 0, n); sha.update(buf, 0, n); done += n
                        if (total > 0) onProgress(done / total)
                    }
                }
            }
        }
        val hex = sha.digest().joinToString("") { "%02x".format(it) }
        if (!hex.equals(info.sha256, ignoreCase = true)) {
            out.delete()
            throw IOException("The downloaded update failed its integrity check, so it was not installed.")
        }
        val apk = if (info.apkFile != null) {
            File(dir, info.apkFile).also { extractApk(out, info, it); out.delete() }
        } else out
        try {
            verifyPackage(apk, info.versionCode)
        } catch (e: IOException) {
            apk.delete()
            throw e
        }
        return apk
    }

    @Suppress("DEPRECATION")
    private fun verifyPackage(apk: File, expectedCode: Long) {
        val flags = if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES
            else PackageManager.GET_SIGNATURES
        val pm = context.packageManager
        val candidate = pm.getPackageArchiveInfo(apk.absolutePath, flags)
            ?: throw IOException("The downloaded file is not an installable APK.")
        val installed = pm.getPackageInfo(context.packageName, flags)
        val code = if (Build.VERSION.SDK_INT >= 28) candidate.longVersionCode else candidate.versionCode.toLong()
        fun certificates(p: android.content.pm.PackageInfo): Set<String> {
            val signatures = if (Build.VERSION.SDK_INT >= 28) p.signingInfo?.apkContentsSigners else p.signatures
            return signatures?.map {
                MessageDigest.getInstance("SHA-256").digest(it.toByteArray()).joinToString("") { b -> "%02x".format(b) }
            }?.toSet() ?: emptySet()
        }
        val actual = certificates(candidate)
        if (candidate.packageName != context.packageName || code != expectedCode ||
            actual.isEmpty() || actual != certificates(installed)) {
            throw IOException("Update package, version or signing certificate does not match this app.")
        }
    }

    /** Opens the system installer. Returns false if the user still has to allow installs from Quasar. */
    fun install(apk: File): Boolean {
        if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls()) {
            context.startActivity(
                Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
            return false
        }
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", apk)
        context.startActivity(
            Intent(Intent.ACTION_VIEW).setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK),
        )
        return true
    }
}
