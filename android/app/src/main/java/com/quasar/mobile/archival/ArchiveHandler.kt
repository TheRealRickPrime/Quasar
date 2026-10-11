package com.quasar.mobile.archival

import java.io.File

/**
 * Unified interface for archive format support.
 * Each archive handler manages compression, encryption, and extraction.
 */
interface ArchiveHandler {
    val format: ArchiveFormat
    
    suspend fun archive(
        inputFile: File,
        outputFile: File,
        compressionLevel: Int = 19,
        onProgress: (Float) -> Unit = {}
    ): ArchiveResult
    
    suspend fun extract(
        archiveFile: File,
        outputDirectory: File,
        onProgress: (Float) -> Unit = {}
    ): ArchiveResult
    
    suspend fun verify(archiveFile: File): Boolean
}

enum class ArchiveFormat(val extension: String, val mimeType: String) {
    TAR_GZ(".tar.gz", "application/gzip"),
    TAR_BZ2(".tar.bz2", "application/x-bzip2"),
    TAR_XZ(".tar.xz", "application/x-xz"),
    ZIP(".zip", "application/zip"),
    SEVEN_Z(".7z", "application/x-7z-compressed"),
    RAR(".rar", "application/x-rar-compressed")
}

data class ArchiveResult(
    val success: Boolean,
    val format: ArchiveFormat? = null,
    val inputFile: File? = null,
    val outputFile: File? = null,
    val originalSize: Long = 0L,
    val compressedSize: Long = 0L,
    val compressionRatio: Double = 0.0,
    val elapsedMillis: Long = 0L,
    val entriesCount: Int = 0,
    val checksum: String = "",
    val error: String? = null
) {
    val spaceSaved: Long
        get() = originalSize - compressedSize
    
    val percentageReduced: Double
        get() = if (originalSize > 0) (1.0 - (compressedSize.toDouble() / originalSize)) * 100 else 0.0
    
    val throughputMbps: Double
        get() = if (elapsedMillis > 0) (originalSize.toDouble() / (1024 * 1024)) / (elapsedMillis / 1000.0) else 0.0
}
