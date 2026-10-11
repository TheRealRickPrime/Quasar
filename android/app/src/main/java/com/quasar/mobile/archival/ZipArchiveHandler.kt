package com.quasar.mobile.archival

import java.io.File
import net.lingala.zip4j.ZipFile
import net.lingala.zip4j.model.ZipParameters
import net.lingala.zip4j.model.enums.CompressionLevel
import net.lingala.zip4j.model.enums.CompressionMethod as Zip4jCompressionMethod
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.security.MessageDigest

/**
 * ZIP archive handler using Zip4j.
 * Compatible with standard ZIP tools, good compression ratio.
 */
class ZipArchiveHandler : ArchiveHandler {
    override val format: ArchiveFormat = ArchiveFormat.ZIP
    
    companion object {
        private const val BUFFER_SIZE = 65536
    }
    
    override suspend fun archive(
        inputFile: File,
        outputFile: File,
        compressionLevel: Int,
        onProgress: (Float) -> Unit
    ): ArchiveResult {
        val startTime = System.currentTimeMillis()
        return try {
            val totalSize = inputFile.length()
            val zipFile = ZipFile(outputFile)
            
            val zipParams = ZipParameters().apply {
                compressionMethod = Zip4jCompressionMethod.DEFLATE
                compressionLevel = when {
                    compressionLevel < 5 -> CompressionLevel.FASTER
                    compressionLevel < 15 -> CompressionLevel.NORMAL
                    else -> CompressionLevel.MAXIMUM
                }
            }
            
            zipFile.addFile(inputFile, zipParams)
            zipFile.close()
            
            // Update progress
            onProgress(1.0f)
            
            val elapsedMillis = System.currentTimeMillis() - startTime
            
            ArchiveResult(
                success = true,
                format = format,
                inputFile = inputFile,
                outputFile = outputFile,
                originalSize = totalSize,
                compressedSize = outputFile.length(),
                compressionRatio = outputFile.length().toDouble() / totalSize,
                elapsedMillis = elapsedMillis,
                entriesCount = 1,
                checksum = calculateChecksum(outputFile)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            ArchiveResult(success = false, error = e.message ?: "ZIP archiving failed")
        }
    }
    
    override suspend fun extract(
        archiveFile: File,
        outputDirectory: File,
        onProgress: (Float) -> Unit
    ): ArchiveResult {
        val startTime = System.currentTimeMillis()
        return try {
            val totalSize = archiveFile.length()
            val zipFile = ZipFile(archiveFile)
            
            zipFile.extractAll(outputDirectory.absolutePath)
            val entryCount = zipFile.fileHeaders.size
            zipFile.close()
            
            onProgress(1.0f)
            
            val elapsedMillis = System.currentTimeMillis() - startTime
            
            ArchiveResult(
                success = true,
                format = format,
                outputFile = outputDirectory,
                originalSize = calculateDirectorySize(outputDirectory),
                compressedSize = totalSize,
                elapsedMillis = elapsedMillis,
                entriesCount = entryCount
            )
        } catch (e: Exception) {
            e.printStackTrace()
            ArchiveResult(success = false, error = e.message ?: "ZIP extraction failed")
        }
    }
    
    override suspend fun verify(archiveFile: File): Boolean {
        return try {
            val zipFile = ZipFile(archiveFile)
            val isValid = zipFile.isValidZipFile
            zipFile.close()
            isValid
        } catch (e: Exception) {
            false
        }
    }
    
    private fun calculateChecksum(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            var bytesRead: Int
            while (input.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        return android.util.Base64.encodeToString(digest.digest(), android.util.Base64.DEFAULT)
    }
    
    private fun calculateDirectorySize(directory: File): Long {
        return directory.walk().sumOf { it.length() }
    }
}
