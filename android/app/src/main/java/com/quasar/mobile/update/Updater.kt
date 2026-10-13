package com.quasar.mobile.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import com.google.gson.JsonParser
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

const val MANIFEST_URL = "https://quasarli.github.io/latest.json"

data class UpdateInfo(val version: String, val versionCode: Long, val url: String, val sha256: String)

/** Returns the Android entry from the manifest if its versionCode is newer than [currentCode]. */
fun parseManifest(json: String, currentCode: Long): UpdateInfo? {
    val root = JsonParser.parseString(json).asJsonObject
    val a = root.getAsJsonObject("android")
    val info = UpdateInfo(
        root.get("version").asString, a.get("versionCode").asLong,
        a.get("url").asString, a.get("sha256").asString,
    )
    return if (info.versionCode > currentCode) info else null
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
            return parseManifest(r.body!!.string(), currentCode())
        }
    }

    fun download(info: UpdateInfo, onProgress: (Float) -> Unit): File {
        val dir = File(context.cacheDir, "updates").apply { deleteRecursively(); mkdirs() }
        val out = File(dir, "Quasar-${info.version}.apk")
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
        return out
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
