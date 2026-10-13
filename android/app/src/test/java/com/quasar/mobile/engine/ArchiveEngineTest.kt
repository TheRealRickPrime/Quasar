package com.quasar.mobile.engine

import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File

/** Round trips every pure-Java format (Zstandard needs Android native libs, so it is not covered here). */
class ArchiveEngineTest {
    @Test fun roundTrips() {
        val data = mapOf("a.txt" to "hello ".repeat(5000).toByteArray(), "dir/b.bin" to ByteArray(300_000) { (it % 251).toByte() })
        val entries = data.map { (p, b) -> SourceEntry(p, b.size.toLong()) { ByteArrayInputStream(b) } }
        val formats = listOf(ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ,
            ArchiveFormat.ZIP, ArchiveFormat.SEVEN_Z, ArchiveFormat.NONE)
        for (f in formats) for (l in Level.values()) {
            val file = File.createTempFile("qtest", f.ext)
            try {
                ArchiveEngine.create(entries, f, l, file)
                val got = HashMap<String, ByteArray>()
                ArchiveEngine.extract(file, f) { p ->
                    object : ByteArrayOutputStream() {
                        override fun close() { got[p] = toByteArray() }
                    }
                }
                assertEquals("$f $l", data.keys, got.keys)
                data.forEach { (p, b) -> assertEquals("$f $l $p", b.toList(), got[p]!!.toList()) }
            } finally { file.delete() }
        }
    }
}
