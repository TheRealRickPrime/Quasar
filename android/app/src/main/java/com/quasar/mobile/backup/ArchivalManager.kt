package com.quasar.mobile.backup

import com.quasar.mobile.archival.ArchiveFormat
import com.quasar.mobile.archival.ArchiveHandler
import com.quasar.mobile.archival.ArchiveHandlerFactory
import com.quasar.mobile.archival.ArchiveResult
import java.io.File

/**
 * Manages archival options and compression format selection.
 */
class ArchivalManager {
    
    data class ArchivalOption(
        val format: ArchiveFormat,
        val title: String,
        val description: String,
        val compression: CompressionProfile,
        val speed: Speed,
        val compatibility: Compatibility,
        val estimatedRatio: Double,
        val use: String
    )
    
    enum class Speed {
        VERY_FAST,  // < 1 sec per GB
        FAST,       // 1-2 sec per GB
        MODERATE,   // 2-5 sec per GB
        SLOW,       // 5+ sec per GB
        VERY_SLOW   // 10+ sec per GB
    }
    
    enum class Compatibility {
        UNIVERSAL,      // Works everywhere
        WIDELY_SUPPORTED, // Most systems
        COMMON,         // Common systems
        LINUX_FOCUSED,  // Primarily Linux/Mac
        SPECIALIZED     // Specific use cases
    }
    
    enum class CompressionProfile {
        ULTRA,      // Maximum compression (7z)
        HIGH,       // High compression (xz, bz2)
        BALANCED,   // Speed/compression balance (gzip)
        FAST        // Speed optimized (deflate)
    }
    
    /**
     * All available archival options with detailed comparisons.
     */
    fun getArchivalOptions(): List<ArchivalOption> {
        return listOf(
            ArchivalOption(
                format = ArchiveFormat.TAR_GZ,
                title = "TAR.GZ",
                description = "Best Balance (Recommended)",
                compression = CompressionProfile.BALANCED,
                speed = Speed.FAST,
                compatibility = Compatibility.UNIVERSAL,
                estimatedRatio = 0.40,
                use = "• Fast & reliable\n• 40-45% compression\n• Works everywhere\n• ~1.5 sec/GB"
            ),
            ArchivalOption(
                format = ArchiveFormat.TAR_BZ2,
                title = "TAR.BZ2",
                description = "High Compression",
                compression = CompressionProfile.HIGH,
                speed = Speed.MODERATE,
                compatibility = Compatibility.WIDELY_SUPPORTED,
                estimatedRatio = 0.35,
                use = "• 35-40% compression\n• Slower than gzip\n• Good for archival\n• ~3-4 sec/GB"
            ),
            ArchivalOption(
                format = ArchiveFormat.TAR_XZ,
                title = "TAR.XZ",
                description = "Maximum Compression (Slow)",
                compression = CompressionProfile.ULTRA,
                speed = Speed.SLOW,
                compatibility = Compatibility.LINUX_FOCUSED,
                estimatedRatio = 0.30,
                use = "• 30-35% compression\n• Very slow (5-8 sec/GB)\n• Best for long-term archival\n• Linux/Mac native support"
            ),
            ArchivalOption(
                format = ArchiveFormat.ZIP,
                title = "ZIP",
                description = "Maximum Compatibility",
                compression = CompressionProfile.BALANCED,
                speed = Speed.FAST,
                compatibility = Compatibility.UNIVERSAL,
                estimatedRatio = 0.42,
                use = "• Works on all systems\n• ~42-45% compression\n• Fast processing\n• Windows/Mac/Linux native"
            ),
            ArchivalOption(
                format = ArchiveFormat.SEVEN_Z,
                title = "7Z",
                description = "Best Compression (Slowest)",
                compression = CompressionProfile.ULTRA,
                speed = Speed.VERY_SLOW,
                compatibility = Compatibility.COMMON,
                estimatedRatio = 0.25,
                use = "• 25-30% compression\n• Slowest option (15+ sec/GB)\n• For maximum archival\n• Needs 7z software"
            )
        )
    }
    
    /**
     * Get recommended format based on user priorities.
     */
    fun recommendFormat(priority: Priority): ArchiveFormat {
        return when (priority) {
            Priority.SPEED -> ArchiveFormat.TAR_GZ
            Priority.COMPRESSION -> ArchiveFormat.SEVEN_Z
            Priority.COMPATIBILITY -> ArchiveFormat.ZIP
            Priority.BALANCE -> ArchiveFormat.TAR_GZ
        }
    }
    
    enum class Priority {
        SPEED,
        COMPRESSION,
        COMPATIBILITY,
        BALANCE
    }
    
    /**
     * Compare formats side-by-side.
     */
    fun compareFormats(): ComparisonMatrix {
        return ComparisonMatrix(
            formats = listOf(
                "TAR.GZ" to "1.5 sec/GB | 40% | Universal",
                "TAR.BZ2" to "3.5 sec/GB | 37% | Widely supported",
                "TAR.XZ" to "6 sec/GB | 32% | Linux-focused",
                "ZIP" to "1.5 sec/GB | 42% | Universal",
                "7Z" to "18 sec/GB | 27% | Common"
            )
        )
    }
    
    data class ComparisonMatrix(
        val formats: List<Pair<String, String>>
    )
}
