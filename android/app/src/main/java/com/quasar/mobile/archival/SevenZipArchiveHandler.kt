package com.quasar.mobile.archival

import java.io.File
import net.sf.sevenzipjbinding.IInArchive
import net.sf.sevenzipjbinding.SevenZip
import net.sf.sevenzipjbinding.impl.RandomAccessFileInStream
import net.sf.sevenzipjbinding.inStream.FileInStream
import org.apache.commons.compress.archivers.sevenz.SevenZArchiveEntry
import org.apache.commons.compress.archivers.sevenz.SevenZOutputFile
import java.io.BufferedInputStream
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest

/**
 * 7z archive handler using Apache Commons Compress.
 * Best compression ratio but slower processing.
 */
class SevenZipArchiveHandler : ArchiveHandler {
    override val format: ArchiveFormat = ArchiveFormat.SEVEN_Z
    
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
            
            SevenZOutputFile(outputFile).use { sevenZOut ->
                addFileToSevenZ(inputFile, "", sevenZOut)
            }
            
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
            ArchiveResult(success = false, error = e.message ?: "7z archiving failed")
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
            
            SevenZip.openInArchive(null, RandomAccessFileInStream(archiveFile)).use { archive ->
                for (i in 0 until archive.numberOfItems) {
                    val item = archive.getSimpleInterface().archiveItems[i]
                    val outputFile = File(outputDirectory, item.path)
                    
                    if (!item.isFolder) {
                        outputFile.parentFile?.mkdirs()
                        val content = archive.getSimpleInterface().getArchiveItem(i).content
                        outputFile.writeBytes(content)
                        processedSize += content.size
                        entryCount++
                    }
                    
                    onProgress((i + 1).toFloat() / archive.numberOfItems)
                }
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
            ArchiveResult(success = false, error = e.message ?: "7z extraction failed")
        }
    }
    
    override suspend fun verify(archiveFile: File): Boolean {
        return try {
            SevenZip.openInArchive(null, RandomAccessFileInStream(archiveFile)).use { archive ->
                archive.numberOfItems > 0
            }
        } catch (e: Exception) {
            false
        }
    }
    
    private fun addFileToSevenZ(
        file: File,
        parentPath: String,
        sevenZOut: SevenZOutputFile
    ) {
        if (file.isFile) {
            val entry = SevenZArchiveEntry().apply {
                name = if (parentPath.isEmpty()) file.name else "$parentPath/${file.name}"
                size = file.length()
            }
            sevenZOut.putArchiveEntry(entry)
            file.inputStream().use { input ->
                input.copyTo(sevenZOut, BUFFER_SIZE)
            }
            sevenZOut.closeArchiveEntry()
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
