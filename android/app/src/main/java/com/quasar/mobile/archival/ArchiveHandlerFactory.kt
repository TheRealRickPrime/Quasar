package com.quasar.mobile.archival

import android.content.Context

/**
 * Factory for creating archive handlers.
 * Supports multiple archive formats for user choice.
 */
object ArchiveHandlerFactory {
    
    fun createHandler(format: ArchiveFormat): ArchiveHandler {
        return when (format) {
            ArchiveFormat.TAR_GZ -> TarArchiveHandler(TarArchiveHandler.CompressionType.GZIP)
            ArchiveFormat.TAR_BZ2 -> TarArchiveHandler(TarArchiveHandler.CompressionType.BZIP2)
            ArchiveFormat.TAR_XZ -> TarArchiveHandler(TarArchiveHandler.CompressionType.XZ)
            ArchiveFormat.ZIP -> ZipArchiveHandler()
            ArchiveFormat.SEVEN_Z -> SevenZipArchiveHandler()
            ArchiveFormat.RAR -> throw UnsupportedOperationException("RAR archiving not supported on Android")
        }
    }
    
    /**
     * Get all supported archive formats.
     */
    fun supportedFormats(): List<ArchiveFormat> {
        return listOf(
            ArchiveFormat.TAR_GZ,
            ArchiveFormat.TAR_BZ2,
            ArchiveFormat.TAR_XZ,
            ArchiveFormat.ZIP,
            ArchiveFormat.SEVEN_Z
        )
    }
    
    /**
     * Recommend best format based on use case.
     */
    fun recommendFormat(useCase: UseCase): ArchiveFormat {
        return when (useCase) {
            UseCase.MAXIMUM_COMPRESSION -> ArchiveFormat.SEVEN_Z
            UseCase.BEST_COMPATIBILITY -> ArchiveFormat.ZIP
            UseCase.FAST_COMPRESSION -> ArchiveFormat.TAR_GZ
            UseCase.BALANCED -> ArchiveFormat.TAR_GZ
        }
    }
    
    enum class UseCase {
        MAXIMUM_COMPRESSION,  // Best ratio (7z > tar.xz > tar.bz2 > tar.gz > zip)
        BEST_COMPATIBILITY,   // Most widely supported (ZIP)
        FAST_COMPRESSION,     // Speed optimized (tar.gz)
        BALANCED              // Speed/compression balance (tar.gz)
    }
}
