package com.quasar.mobile.encryption

import java.io.File
import com.github.luben.zstd.Zstd
import net.lingala.zip4j.ZipFile
import net.lingala.zip4j.model.ZipParameters
import net.lingala.zip4j.model.enums.CompressionLevel
import net.lingala.zip4j.model.enums.CompressionMethod
import java.io.BufferedInputStream
import java.io.BufferedOutputStream

/**
 * Advanced compression using Zstandard (Zstd) and DEFLATE variants.
 * 
 * Zstandard advantages:
 * - 20-30% better compression than DEFLATE
 * - Faster compression/decompression (often 10x faster)
 * - Superior decompression speed
 * - Used by Facebook, Google, Apple, and others
 * - Streaming compression support
 */
class CompressionManager {
    companion object {
        private const val ZSTD_COMPRESSION_LEVEL = 19  // 1-22, higher = better compression, slower
        private const val BUFFER_SIZE = 8192
    }

    enum class CompressionMethod {
        NONE,           // No compression
        ZSTD,          // Zstandard (best compression ratio, fastest)
        ZSTD_HIGH,     // Zstandard with maximum compression
        DEFLATE,       // Standard ZIP compression (DEFLATE)
        DEFLATE_MAX    // ZIP with maximum compression
    }

    /**
     * Compress file using Zstandard (recommended for most cases).
     * Best balance of speed and compression ratio.
     */
    fun compressWithZstd(inputFile: File, outputFile: File): CompressionResult {
        return try {
            val originalSize = inputFile.length()
            val input = inputFile.readBytes()
            val compressed = Zstd.compress(input, ZSTD_COMPRESSION_LEVEL)
            outputFile.writeBytes(compressed)
            
            CompressionResult(
                success = true,
                method = CompressionMethod.ZSTD,
                originalSize = originalSize,
                compressedSize = outputFile.length(),
                compressionRatio = 1.0 - (outputFile.length().toDouble() / originalSize)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            CompressionResult(success = false, error = e.message ?: "Zstd compression failed")
        }
    }

    /**
     * Compress file using maximum Zstandard compression (slowest, best ratio).
     * Use for archival or when time is not critical.
     */
    fun compressWithZstdMax(inputFile: File, outputFile: File): CompressionResult {
        return try {
            val originalSize = inputFile.length()
            val input = inputFile.readBytes()
            // Level 22 is maximum - slower but best compression
            val compressed = Zstd.compress(input, 22)
            outputFile.writeBytes(compressed)
            
            CompressionResult(
                success = true,
                method = CompressionMethod.ZSTD_HIGH,
                originalSize = originalSize,
                compressedSize = outputFile.length(),
                compressionRatio = 1.0 - (outputFile.length().toDouble() / originalSize)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            CompressionResult(success = false, error = e.message ?: "Zstd max compression failed")
        }
    }

    /**
     * Compress to ZIP with DEFLATE (for compatibility).
     * Standard ZIP format - widely compatible but slightly less efficient than Zstd.
     */
    fun compressWithDeflate(inputFile: File, outputFile: File, maxCompression: Boolean = false): CompressionResult {
        return try {
            val originalSize = inputFile.length()
            val zipFile = ZipFile(outputFile)
            val zipParams = ZipParameters().apply {
                compressionMethod = CompressionMethod.DEFLATE
                compressionLevel = if (maxCompression) CompressionLevel.MAXIMUM else CompressionLevel.NORMAL
                isEncryptFiles = false // We handle encryption separately
            }
            zipFile.addFile(inputFile, zipParams)
            zipFile.close()
            
            CompressionResult(
                success = true,
                method = if (maxCompression) CompressionMethod.DEFLATE_MAX else CompressionMethod.DEFLATE,
                originalSize = originalSize,
                compressedSize = outputFile.length(),
                compressionRatio = 1.0 - (outputFile.length().toDouble() / originalSize)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            CompressionResult(success = false, error = e.message ?: "DEFLATE compression failed")
        }
    }

    /**
     * Decompress Zstandard file.
     */
    fun decompressZstd(inputFile: File, outputFile: File): CompressionResult {
        return try {
            val compressedSize = inputFile.length()
            val compressed = inputFile.readBytes()
            val decompressed = Zstd.decompress(compressed)
            outputFile.writeBytes(decompressed)
            
            CompressionResult(
                success = true,
                method = CompressionMethod.ZSTD,
                originalSize = outputFile.length(),
                compressedSize = compressedSize,
                compressionRatio = 1.0 - (compressedSize.toDouble() / outputFile.length())
            )
        } catch (e: Exception) {
            e.printStackTrace()
            CompressionResult(success = false, error = e.message ?: "Zstd decompression failed")
        }
    }

    /**
     * Decompress ZIP file.
     */
    fun decompressDeflate(inputFile: File, outputDir: File): CompressionResult {
        return try {
            val compressedSize = inputFile.length()
            val zipFile = ZipFile(inputFile)
            zipFile.extractAll(outputDir.absolutePath)
            
            val decompressedSize = outputDir.walk().sumOf { it.length() }
            
            CompressionResult(
                success = true,
                method = CompressionMethod.DEFLATE,
                originalSize = decompressedSize,
                compressedSize = compressedSize,
                compressionRatio = 1.0 - (compressedSize.toDouble() / decompressedSize)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            CompressionResult(success = false, error = e.message ?: "DEFLATE decompression failed")
        }
    }

    /**
     * Estimate compression for choosing optimal method.
     * Returns expected compression ratio (0.0 = no compression, 1.0 = impossible to compress).
     */
    fun estimateCompressionRatio(file: File): Double {
        return try {
            // Sample first 1MB to estimate
            val sampleSize = minOf(file.length(), 1024 * 1024).toInt()
            val sample = ByteArray(sampleSize)
            file.inputStream().use { it.read(sample) }
            
            val compressed = Zstd.compress(sample, ZSTD_COMPRESSION_LEVEL)
            val ratio = compressed.size.toDouble() / sample.size
            1.0 - ratio
        } catch (e: Exception) {
            0.5  // Default to 50% estimate
        }
    }
}

data class CompressionResult(
    val success: Boolean,
    val method: CompressionManager.CompressionMethod? = null,
    val originalSize: Long = 0L,
    val compressedSize: Long = 0L,
    val compressionRatio: Double = 0.0,
    val error: String? = null
) {
    val spaceSaved: Long
        get() = originalSize - compressedSize
    
    val percentageReduced: Double
        get() = if (originalSize > 0) (1.0 - (compressedSize.toDouble() / originalSize)) * 100 else 0.0
}
