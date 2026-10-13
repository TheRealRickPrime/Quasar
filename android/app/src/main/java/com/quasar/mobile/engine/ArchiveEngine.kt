package com.quasar.mobile.engine

import com.github.luben.zstd.ZstdInputStream
import com.github.luben.zstd.ZstdOutputStream
import org.apache.commons.compress.archivers.sevenz.SevenZArchiveEntry
import org.apache.commons.compress.archivers.sevenz.SevenZFile
import org.apache.commons.compress.archivers.sevenz.SevenZMethod
import org.apache.commons.compress.archivers.sevenz.SevenZMethodConfiguration
import org.apache.commons.compress.archivers.sevenz.SevenZOutputFile
import org.apache.commons.compress.archivers.tar.TarArchiveEntry
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream
import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream
import org.apache.commons.compress.archivers.zip.ZipArchiveEntry
import org.apache.commons.compress.archivers.zip.ZipArchiveInputStream
import org.apache.commons.compress.archivers.zip.ZipArchiveOutputStream
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorOutputStream
import org.apache.commons.compress.compressors.gzip.GzipCompressorInputStream
import org.apache.commons.compress.compressors.gzip.GzipCompressorOutputStream
import org.apache.commons.compress.compressors.gzip.GzipParameters
import org.apache.commons.compress.compressors.xz.XZCompressorInputStream
import org.apache.commons.compress.compressors.xz.XZCompressorOutputStream
import org.tukaani.xz.LZMA2Options
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStream
import java.io.OutputStream

enum class Level(val label: String) { FAST("Fast"), BALANCED("Balanced"), MAX("Max") }

enum class ArchiveFormat(val label: String, val ext: String) {
    ZSTD("Zstandard", ".tar.zst"),
    ZSTD_ULTRA("Zstandard Ultra (22)", ".tar.zst"),
    TAR_GZ("TAR + Gzip", ".tar.gz"),
    TAR_BZ2("TAR + Bzip2", ".tar.bz2"),
    TAR_XZ("TAR + XZ", ".tar.xz"),
    ZIP("ZIP (Deflate)", ".zip"),
    SEVEN_Z("7-Zip", ".7z"),
    NONE("None (TAR only)", ".tar"),
}

class SourceEntry(val path: String, val size: Long, val open: () -> InputStream)

object ArchiveEngine {
    private const val BUF = 64 * 1024

    private fun pick(level: Level, fast: Int, balanced: Int, max: Int) =
        when (level) { Level.FAST -> fast; Level.BALANCED -> balanced; Level.MAX -> max }

    fun create(
        entries: List<SourceEntry>,
        format: ArchiveFormat,
        level: Level,
        out: File,
        onProgress: (done: Long, total: Long) -> Unit = { _, _ -> },
    ) {
        val total = entries.sumOf { it.size }.coerceAtLeast(1)
        var done = 0L
        val buf = ByteArray(BUF)
        fun copy(src: InputStream, dst: (ByteArray, Int) -> Unit) {
            src.use { s ->
                while (true) {
                    val n = s.read(buf)
                    if (n < 0) break
                    dst(buf, n)
                    done += n
                    onProgress(done, total)
                }
            }
        }
        when (format) {
            ArchiveFormat.ZIP -> ZipArchiveOutputStream(out).use { zip ->
                zip.setMethod(java.util.zip.ZipEntry.DEFLATED)
                zip.setLevel(pick(level, 1, 6, 9))
                for (e in entries) {
                    zip.putArchiveEntry(ZipArchiveEntry(e.path))
                    copy(e.open()) { b, n -> zip.write(b, 0, n) }
                    zip.closeArchiveEntry()
                }
            }
            ArchiveFormat.SEVEN_Z -> SevenZOutputFile(out).use { sz ->
                sz.setContentMethods(listOf(SevenZMethodConfiguration(SevenZMethod.LZMA2, LZMA2Options(pick(level, 1, 4, 6)))))
                for (e in entries) {
                    val entry = SevenZArchiveEntry().apply { name = e.path; size = e.size; setHasStream(true) }
                    sz.putArchiveEntry(entry)
                    copy(e.open()) { b, n -> sz.write(b, 0, n) }
                    sz.closeArchiveEntry()
                }
            }
            else -> {
                val raw = BufferedOutputStream(FileOutputStream(out), BUF)
                val comp = wrap(format, level, raw)
                TarArchiveOutputStream(comp).use { tar ->
                    tar.setLongFileMode(TarArchiveOutputStream.LONGFILE_POSIX)
                    tar.setBigNumberMode(TarArchiveOutputStream.BIGNUMBER_POSIX)
                    for (e in entries) {
                        val te = TarArchiveEntry(e.path)
                        te.size = e.size
                        tar.putArchiveEntry(te)
                        var written = 0L
                        copy(e.open()) { b, n -> tar.write(b, 0, n); written += n }
                        if (written != e.size) throw java.io.IOException("Size of ${e.path} changed while reading")
                        tar.closeArchiveEntry()
                    }
                }
            }
        }
    }

    private fun wrap(format: ArchiveFormat, level: Level, os: OutputStream): OutputStream = when (format) {
        ArchiveFormat.ZSTD -> ZstdOutputStream(os, pick(level, 3, 12, 19))
        ArchiveFormat.ZSTD_ULTRA -> ZstdOutputStream(os, 22)
        ArchiveFormat.TAR_GZ -> GzipCompressorOutputStream(os, GzipParameters().apply { compressionLevel = pick(level, 1, 6, 9) })
        ArchiveFormat.TAR_BZ2 -> BZip2CompressorOutputStream(os, pick(level, 1, 5, 9))
        ArchiveFormat.TAR_XZ -> XZCompressorOutputStream(os, pick(level, 1, 4, 6))
        else -> os
    }

    fun formatForName(name: String): ArchiveFormat? {
        val n = name.lowercase()
        return when {
            n.endsWith(".tar.zst") -> ArchiveFormat.ZSTD
            n.endsWith(".tar.gz") || n.endsWith(".tgz") -> ArchiveFormat.TAR_GZ
            n.endsWith(".tar.bz2") -> ArchiveFormat.TAR_BZ2
            n.endsWith(".tar.xz") -> ArchiveFormat.TAR_XZ
            n.endsWith(".zip") -> ArchiveFormat.ZIP
            n.endsWith(".7z") -> ArchiveFormat.SEVEN_Z
            n.endsWith(".tar") -> ArchiveFormat.NONE
            else -> null
        }
    }

    /** Extracts [archive]; [sink] returns the stream to write each file entry into. Returns the file count. */
    fun extract(archive: File, format: ArchiveFormat, sink: (path: String) -> OutputStream): Int {
        var count = 0
        val buf = ByteArray(BUF)
        fun write(src: (ByteArray) -> Int, path: String) {
            sink(safePath(path)).use { o ->
                while (true) {
                    val n = src(buf)
                    if (n < 0) break
                    o.write(buf, 0, n)
                }
            }
            count++
        }
        when (format) {
            ArchiveFormat.ZIP -> ZipArchiveInputStream(BufferedInputStream(FileInputStream(archive))).use { zin ->
                while (true) {
                    val e = zin.nextEntry ?: break
                    if (!e.isDirectory) write({ zin.read(it) }, e.name)
                }
            }
            ArchiveFormat.SEVEN_Z -> SevenZFile(archive).use { sz ->
                while (true) {
                    val e = sz.nextEntry ?: break
                    if (!e.isDirectory) write({ sz.read(it) }, e.name)
                }
            }
            else -> {
                val raw = BufferedInputStream(FileInputStream(archive), BUF)
                val dec: InputStream = when (format) {
                    ArchiveFormat.ZSTD, ArchiveFormat.ZSTD_ULTRA -> ZstdInputStream(raw)
                    ArchiveFormat.TAR_GZ -> GzipCompressorInputStream(raw)
                    ArchiveFormat.TAR_BZ2 -> BZip2CompressorInputStream(raw)
                    ArchiveFormat.TAR_XZ -> XZCompressorInputStream(raw)
                    else -> raw
                }
                TarArchiveInputStream(dec).use { tin ->
                    while (true) {
                        val e = tin.nextEntry ?: break
                        if (e.isFile) write({ tin.read(it) }, e.name)
                    }
                }
            }
        }
        return count
    }

    // Drops empty, "." and ".." segments so an archive cannot write outside the chosen folder.
    private fun safePath(p: String) = p.replace('\\', '/').split('/').filter { it.isNotEmpty() && it != "." && it != ".." }
        .joinToString("/").ifEmpty { "file" }
}
