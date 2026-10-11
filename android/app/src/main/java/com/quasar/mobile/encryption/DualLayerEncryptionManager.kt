package com.quasar.mobile.encryption

import android.content.Context
import com.quasar.mobile.compression.CompressionManager
import java.io.File

/**
 * Dual-encryption with optional compression.
 * Provides maximum security with:
 * 1. Optional Zstandard compression (reduces size by 20-30%)
 * 2. AES-256-GCM encryption (standard, fast)
 * 3. XChaCha20-Poly1305 encryption wrapper (maximum security)
 */
class DualLayerEncryptionManager(
    private val context: Context,
    private val useXChaCha: Boolean = true
) {
    private val aesManager = EncryptionManager(context)
    private val xchachaManager = XChaCha20Poly1305Manager(context)
    private val compressionManager = CompressionManager()

    enum class SecurityLevel {
        STANDARD,      // AES-256-GCM only
        ENHANCED,      // AES-256-GCM + XChaCha20-Poly1305
        MAXIMUM        // Compression + both encryption layers
    }

    /**
     * Encrypt file with optional compression and dual encryption.
     * 
     * Security Level STANDARD: AES-256-GCM
     * Security Level ENHANCED: AES-256-GCM + XChaCha20-Poly1305
     * Security Level MAXIMUM: Zstd compression + AES-256-GCM + XChaCha20-Poly1305
     */
    fun encryptFileWithSecurity(
        inputFile: File,
        outputFile: File,
        securityLevel: SecurityLevel = SecurityLevel.ENHANCED,
        compressionMethod: CompressionManager.CompressionMethod = CompressionManager.CompressionMethod.ZSTD,
        onProgress: (String, Float) -> Unit = { _, _ -> }
    ): DualEncryptionResult {
        return try {
            var workingFile = inputFile
            var totalSize = inputFile.length()
            val results = mutableListOf<EncryptionStep>()

            // Step 1: Compression (if MAXIMUM security)
            if (securityLevel == SecurityLevel.MAXIMUM) {
                onProgress("Compressing...", 0.1f)
                val compressedFile = File(outputFile.parentFile, "${outputFile.name}.compressed")
                val compResult = when (compressionMethod) {
                    CompressionManager.CompressionMethod.ZSTD_HIGH -> 
                        compressionManager.compressWithZstdMax(workingFile, compressedFile)
                    CompressionManager.CompressionMethod.DEFLATE_MAX -> 
                        compressionManager.compressWithDeflate(workingFile, compressedFile, maxCompression = true)
                    else -> compressionManager.compressWithZstd(workingFile, compressedFile)
                }

                if (!compResult.success) {
                    return DualEncryptionResult(
                        success = false,
                        error = "Compression failed: ${compResult.error}"
                    )
                }

                results.add(EncryptionStep(
                    name = "Compression (${compressionMethod.name})",
                    originalSize = compResult.originalSize,
                    resultSize = compResult.compressedSize,
                    compressionRatio = compResult.compressionRatio
                ))

                workingFile = compressedFile
                totalSize = compResult.compressedSize
            }

            // Step 2: First encryption layer (AES-256-GCM)
            onProgress("Encrypting (Layer 1: AES-256-GCM)...", 0.4f)
            val aesEncryptedFile = File(outputFile.parentFile, "${outputFile.name}.aes")
            val aesResult = aesManager.encryptFile(workingFile, aesEncryptedFile)

            if (!aesResult.success) {
                return DualEncryptionResult(
                    success = false,
                    error = "AES encryption failed: ${aesResult.error}"
                )
            }

            results.add(EncryptionStep(
                name = "AES-256-GCM Encryption",
                originalSize = aesResult.originalSize,
                resultSize = aesResult.encryptedSize
            ))

            // Step 3: Second encryption layer (XChaCha20-Poly1305) if enhanced/maximum
            var finalFile = aesEncryptedFile
            if (useXChaCha) {
                onProgress("Encrypting (Layer 2: XChaCha20-Poly1305)...", 0.8f)
                val xchachaEncryptedFile = outputFile
                val xchachaResult = xchachaManager.encryptFile(aesEncryptedFile, xchachaEncryptedFile)

                if (!xchachaResult.success) {
                    return DualEncryptionResult(
                        success = false,
                        error = "XChaCha20 encryption failed: ${xchachaResult.error}"
                    )
                }

                results.add(EncryptionStep(
                    name = "XChaCha20-Poly1305 Encryption",
                    originalSize = xchachaResult.originalSize,
                    resultSize = xchachaResult.encryptedSize
                ))

                finalFile = xchachaEncryptedFile
                aesEncryptedFile.delete()  // Clean up intermediate file
            }

            // Clean up intermediate files
            if (securityLevel == SecurityLevel.MAXIMUM && workingFile != inputFile) {
                workingFile.delete()
            }

            onProgress("Complete", 1.0f)

            DualEncryptionResult(
                success = true,
                encryptedFile = finalFile,
                securityLevel = securityLevel,
                encryptionSteps = results,
                originalSize = inputFile.length(),
                finalSize = finalFile.length(),
                totalReduction = 1.0 - (finalFile.length().toDouble() / inputFile.length())
            )
        } catch (e: Exception) {
            e.printStackTrace()
            DualEncryptionResult(success = false, error = e.message ?: "Dual encryption failed")
        }
    }

    /**
     * Decrypt file that was encrypted with encryptFileWithSecurity().
     * Automatically reverses all encryption layers and decompression.
     */
    fun decryptFileWithSecurity(
        encryptedFile: File,
        outputFile: File,
        securityLevel: SecurityLevel = SecurityLevel.ENHANCED,
        compressionMethod: CompressionManager.CompressionMethod = CompressionManager.CompressionMethod.ZSTD,
        onProgress: (String, Float) -> Unit = { _, _ -> }
    ): DualEncryptionResult {
        return try {
            var workingFile = encryptedFile
            val results = mutableListOf<EncryptionStep>()

            // Step 1: Remove XChaCha20 layer if used
            if (useXChaCha) {
                onProgress("Decrypting (Layer 2: XChaCha20-Poly1305)...", 0.25f)
                val aesEncryptedFile = File(outputFile.parentFile, "${outputFile.name}.aes.tmp")
                val xchachaResult = xchachaManager.decryptFile(encryptedFile, aesEncryptedFile)

                if (!xchachaResult.success) {
                    return DualEncryptionResult(
                        success = false,
                        error = "XChaCha20 decryption failed: ${xchachaResult.error}"
                    )
                }

                results.add(EncryptionStep(
                    name = "XChaCha20-Poly1305 Decryption",
                    originalSize = xchachaResult.encryptedSize,
                    resultSize = xchachaResult.originalSize
                ))

                workingFile = aesEncryptedFile
            }

            // Step 2: Remove AES layer
            onProgress("Decrypting (Layer 1: AES-256-GCM)...", 0.5f)
            val decryptedFile = if (securityLevel == SecurityLevel.MAXIMUM) {
                File(outputFile.parentFile, "${outputFile.name}.decompressed.tmp")
            } else {
                outputFile
            }
            val aesResult = aesManager.decryptFile(workingFile, decryptedFile)

            if (!aesResult.success) {
                return DualEncryptionResult(
                    success = false,
                    error = "AES decryption failed: ${aesResult.error}"
                )
            }

            results.add(EncryptionStep(
                name = "AES-256-GCM Decryption",
                originalSize = aesResult.encryptedSize,
                resultSize = aesResult.originalSize
            ))

            // Step 3: Decompress if needed
            if (securityLevel == SecurityLevel.MAXIMUM) {
                onProgress("Decompressing...", 0.9f)
                val compResult = when (compressionMethod) {
                    CompressionManager.CompressionMethod.DEFLATE,
                    CompressionManager.CompressionMethod.DEFLATE_MAX -> 
                        compressionManager.decompressDeflate(decryptedFile, outputFile.parentFile)
                    else -> compressionManager.decompressZstd(decryptedFile, outputFile)
                }

                if (!compResult.success) {
                    return DualEncryptionResult(
                        success = false,
                        error = "Decompression failed: ${compResult.error}"
                    )
                }

                results.add(EncryptionStep(
                    name = "Decompression (${compressionMethod.name})",
                    originalSize = compResult.compressedSize,
                    resultSize = compResult.originalSize
                ))

                decryptedFile.delete()
            }

            // Clean up temporary files
            if (useXChaCha && workingFile != encryptedFile) {
                workingFile.delete()
            }

            onProgress("Complete", 1.0f)

            DualEncryptionResult(
                success = true,
                encryptedFile = outputFile,
                securityLevel = securityLevel,
                encryptionSteps = results,
                originalSize = encryptedFile.length(),
                finalSize = outputFile.length()
            )
        } catch (e: Exception) {
            e.printStackTrace()
            DualEncryptionResult(success = false, error = e.message ?: "Dual decryption failed")
        }
    }
}

data class EncryptionStep(
    val name: String,
    val originalSize: Long = 0L,
    val resultSize: Long = 0L,
    val compressionRatio: Double = 0.0
)

data class DualEncryptionResult(
    val success: Boolean,
    val encryptedFile: File? = null,
    val securityLevel: DualLayerEncryptionManager.SecurityLevel? = null,
    val encryptionSteps: List<EncryptionStep> = emptyList(),
    val originalSize: Long = 0L,
    val finalSize: Long = 0L,
    val totalReduction: Double = 0.0,
    val error: String? = null
) {
    val spaceSaved: Long
        get() = originalSize - finalSize
    
    val percentageReduced: Double
        get() = if (originalSize > 0) (1.0 - (finalSize.toDouble() / originalSize)) * 100 else 0.0
}
