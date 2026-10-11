package com.quasar.mobile.archival

import java.io.File
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream
import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream
import org.apache.commons.compress.archivers.tar.TarArchiveEntry
import org.apache.commons.compress.compressors.gzip.GzipCompressorOutputStream
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorOutputStream
import org.apache.commons.compress.compressors.xz.XZCompressorOutputStream
import org.apache.commons.compress.compressors.gzip.GzipCompressorInputStream
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream
import org.apache.commons.compress.compressors.xz.XZCompressorInputStream
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import kotlin.math.roundToInt

/**
 * TAR archive handler supporting gzip, bzip2, and xz compression.
 * Provides high compression ratios and streaming support.
 */
class TarArchiveHandler(
    private val compressionType: CompressionType
) : ArchiveHandler {
    
    enum class CompressionType {
        GZIP,    // Best balance of speed and compression
        BZIP2,   // Better compression than gzip, slower
        XZ       // Best compression, slowest
    }
    
    override val format: ArchiveFormat
        get() = when (compressionType) {
            CompressionType.GZIP -> ArchiveFormat.TAR_GZ
            CompressionType.BZIP2 -> ArchiveFormat.TAR_BZ2
            CompressionType.XZ -> ArchiveFormat.TAR_XZ
        }
    
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
            var processedSize = 0L
            
            FileOutputStream(outputFile).use { fileOut ->
                val bufferedOut = BufferedOutputStream(fileOut, BUFFER_SIZE)
                
                val compressionOut = when (compressionType) {
                    CompressionType.GZIP -> GzipCompressorOutputStream(bufferedOut)
                    CompressionType.BZIP2 -> BZip2CompressorOutputStream(bufferedOut, compressionLevel)
                    CompressionType.XZ -> XZCompressorOutputStream(bufferedOut, compressionLevel)
                }
                
                TarArchiveOutputStream(compressionOut).use { tarOut ->
                    tarOut.setLongFileMode(TarArchiveOutputStream.LONGFILE_POSIX)
                    addFileToTar(inputFile, "", tarOut, onProgress = { processed ->
                        processedSize = processed
                        onProgress(processedSize.toFloat() / totalSize)
                    })
                    tarOut.finish()
                }
                compressionOut.close()
            }
            
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
            ArchiveResult(success = false, error = e.message ?: "TAR archiving failed")
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
            var processedSize = 0L
            var entryCount = 0
            
            outputDirectory.mkdirs()
            
            FileInputStream(archiveFile).use { fileIn ->
                val bufferedIn = BufferedInputStream(fileIn, BUFFER_SIZE)
                
                val compressionIn = when (compressionType) {
                    CompressionType.GZIP -> GzipCompressorInputStream(bufferedIn)
                    CompressionType.BZIP2 -> BZip2CompressorInputStream(bufferedIn)
                    CompressionType.XZ -> XZCompressorInputStream(bufferedIn)
                }
                
                TarArchiveInputStream(compressionIn).use { tarIn ->
                    var entry = tarIn.nextTarEntry
                    while (entry != null) {
                        val outputFile = File(outputDirectory, entry.name)
                        
                        if (entry.isDirectory) {
                            outputFile.mkdirs()
                        } else {
                            outputFile.parentFile?.mkdirs()
                            outputFile.outputStream().use { output ->
                                val buffer = ByteArray(BUFFER_SIZE)
                                var bytesRead: Int
                                while (tarIn.read(buffer).also { bytesRead = it } != -1) {
                                    output.write(buffer, 0, bytesRead)
                                    processedSize += bytesRead
                                    onProgress(processedSize.toFloat() / totalSize)
                                }
                            }
                        }
                        entryCount++
                        entry = tarIn.nextTarEntry
                    }
                }
                compressionIn.close()
            }
            
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
            ArchiveResult(success = false, error = e.message ?: "TAR extraction failed")
        }
    }
    
    override suspend fun verify(archiveFile: File): Boolean {
        return try {
            FileInputStream(archiveFile).use { fileIn ->
                val bufferedIn = BufferedInputStream(fileIn, BUFFER_SIZE)
                
                val compressionIn = when (compressionType) {
                    CompressionType.GZIP -> GzipCompressorInputStream(bufferedIn)
                    CompressionType.BZIP2 -> BZip2CompressorInputStream(bufferedIn)
                    CompressionType.XZ -> XZCompressorInputStream(bufferedIn)
                }
                
                TarArchiveInputStream(compressionIn).use { tarIn ->
                    while (tarIn.nextTarEntry != null) {
                        // Just iterate through all entries to verify integrity
                    }
                }
                compressionIn.close()
            }
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
    
    private fun addFileToTar(
        file: File,
        parentPath: String,
        tarOut: TarArchiveOutputStream,
        onProgress: (Long) -> Unit
    ) {
        val entryName = if (parentPath.isEmpty()) file.name else "$parentPath/${file.name}"
        val entry = TarArchiveEntry(file, entryName)
        
        if (file.isFile) {
            tarOut.putArchiveEntry(entry)
            file.inputStream().use { input ->
                val buffer = ByteArray(BUFFER_SIZE)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    tarOut.write(buffer, 0, bytesRead)
                }
            }
            tarOut.closeArchiveEntry()
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
