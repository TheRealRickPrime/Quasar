package com.quasar.mobile.update

import com.quasar.mobile.licensing.Edition
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class UpdaterTest {
    private val hash = "a".repeat(64)
    private val legacy = """{"version":"0.3.3","android":{"version":"0.3.2","versionCode":5,
        "url":"https://example.invalid/old.apk","sha256":"$hash"}}"""

    @Test fun legacyUsesPlatformVersionNotGlobalVersion() {
        assertEquals("0.3.2", parseManifest(legacy, 4)!!.version)
        assertNull(parseManifest(legacy, 5))
        assertNull(parseManifest(legacy, 9))
        assertThrows(IOException::class.java) { parseManifest(legacy, 4, Edition.PRO) }
    }

    @Test fun eachEditionKeepsItsOwnPackageAndNeverFallsBack() {
        val editions = Edition.entries.joinToString(",") {
            """"${it.id}":{"version":"0.4.0","versionCode":6,"url":"https://example.invalid/${it.id}.zip",
                "sha256":"$hash","apkFile":"${it.id}.apk","apkSha256":"$hash"}"""
        }
        val json = """{"schemaVersion":2,"version":"9.0.0","android":{"version":"0.3.2",
            "versionCode":5,"editions":{$editions}}}"""
        for (edition in Edition.entries) {
            val info = parseManifest(json, 5, edition)!!
            assertEquals("0.4.0", info.version)
            assertEquals("${edition.id}.apk", info.apkFile)
            assertEquals("https://example.invalid/${edition.id}.zip", info.url)
            assertNull(parseManifest(json, 6, edition))
        }
        assertThrows(IOException::class.java) {
            parseManifest("""{"schemaVersion":2,"android":{"editions":{}}}""", 5, Edition.PRO)
        }
    }

    @Test fun zipExtractionChecksExactMemberAndHash() {
        val zip = File.createTempFile("q-update", ".zip")
        val out = File(zip.parentFile, "${zip.name}.apk")
        try {
            val bytes = "synthetic apk".toByteArray()
            ZipOutputStream(zip.outputStream()).use {
                it.putNextEntry(ZipEntry("Quasar.apk")); it.write(bytes); it.closeEntry()
                it.putNextEntry(ZipEntry("../ignored")); it.write(bytes); it.closeEntry()
            }
            val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            val info = UpdateInfo("0.4.0", 6, "https://example.invalid/q.zip", hash, "Quasar.apk", sha)
            extractApk(zip, info, out)
            assertEquals(bytes.toList(), out.readBytes().toList())
            assertThrows(IOException::class.java) { extractApk(zip, info.copy(apkSha256 = hash), out) }
            assertEquals(false, out.exists())
            assertThrows(IOException::class.java) { extractApk(zip, info.copy(apkFile = "missing.apk"), out) }
        } finally {
            zip.delete(); out.delete()
        }
    }
}
