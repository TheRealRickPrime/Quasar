package com.quasar.mobile.encryption

import javax.crypto.Cipher
import javax.crypto.CipherInputStream
import javax.crypto.CipherOutputStream
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec
import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.goterl.lazysodium.LazySodiumAndroid
import com.goterl.lazysodium.exceptions.SodiumException
import com.goterl.lazysodium.utils.Key
import com.goterl.lazysodium.utils.LibSodium
import java.io.File
import kotlin.random.Random

/**
 * XChaCha20-Poly1305 encryption using libsodium.
 * Stronger than AES-GCM for certain threat models:
 * - Extended nonce (192 bits vs 96 bits) prevents nonce reuse vulnerability
 * - Better performance on devices without AES-NI
 * - Used by Signal, WireGuard, and other privacy tools
 */
class XChaCha20Poly1305Manager(private val context: Context) {
    private val lazySodium: LazySodiumAndroid by lazy { LazySodiumAndroid() }
    private val masterKey by lazy {
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
    }
    private val encryptedPrefs by lazy {
        EncryptedSharedPreferences.create(
            context,
            "quasar_xchacha_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    companion object {
        private const val XCHACHA_NONCE_BYTES = 24  // 192 bits
        private const val POLY1305_ABYTES = 17      // 16 byte tag + 1 byte for padding
        private const val BUFFER_SIZE = 8192
    }

    /**
     * Generate or retrieve XChaCha20 key.
     */
    fun getOrCreateKey(): Key {
        val savedKeyString = encryptedPrefs.getString("xchacha_key", null)
        
        return if (savedKeyString != null) {
            Key.fromHex(savedKeyString)
        } else {
            try {
                val key = lazySodium.keygen(LibSodium.XCHACHA20POLY1305_IETF)
                val encodedKey = key.hexString
                encryptedPrefs.edit().putString("xchacha_key", encodedKey).apply()
                key
            } catch (e: SodiumException) {
                e.printStackTrace()
                throw Exception("Failed to generate XChaCha20 key: ${e.message}")
            }
        }
    }

    /**
     * Encrypt file with XChaCha20-Poly1305.
     */
    fun encryptFile(inputFile: File, outputFile: File): EncryptionResult {
        val key = getOrCreateKey()
        val nonce = ByteArray(XCHACHA_NONCE_BYTES)
        Random.nextBytes(nonce)
        
        return try {
            inputFile.inputStream().use { input ->
                outputFile.outputStream().use { output ->
                    // Write nonce first (not secret, needed for decryption)
                    output.write(nonce)
                    
                    val buffer = ByteArray(BUFFER_SIZE)
                    var bytesRead: Int
                    var totalRead = 0L
                    
                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        try {
                            val encrypted = lazySodium.encryptDetached(
                                buffer.copyOf(bytesRead),
                                null,
                                nonce,
                                key
                            )
                            // Write tag first, then ciphertext
                            output.write(encrypted.tag)
                            output.write(encrypted.ciphertext)
                            totalRead += bytesRead
                        } catch (e: SodiumException) {
                            throw Exception("Encryption failed: ${e.message}")
                        }
                    }
                }
            }
            
            // Store nonce for decryption
            val encodedNonce = android.util.Base64.encodeToString(nonce, android.util.Base64.DEFAULT)
            encryptedPrefs.edit().putString(
                "xchacha_nonce_${outputFile.name}",
                encodedNonce
            ).apply()
            
            EncryptionResult(
                success = true,
                encryptedFile = outputFile,
                iv = nonce,
                originalSize = inputFile.length(),
                encryptedSize = outputFile.length(),
                checksumOriginal = calculateChecksum(inputFile),
                checksumEncrypted = calculateChecksum(outputFile)
            )
        } catch (e: Exception) {
            e.printStackTrace()
            EncryptionResult(success = false, error = e.message ?: "XChaCha20 encryption failed")
        }
    }

    /**
     * Decrypt file encrypted with XChaCha20-Poly1305.
     */
    fun decryptFile(encryptedFile: File, outputFile: File): EncryptionResult {
        val key = getOrCreateKey()
        
        return try {
            encryptedFile.inputStream().use { input ->
                // Read nonce from beginning of file
                val nonce = ByteArray(XCHACHA_NONCE_BYTES)
                if (input.read(nonce) != XCHACHA_NONCE_BYTES) {
                    throw Exception("Invalid encrypted file: nonce not found")
                }
                
                outputFile.outputStream().use { output ->
                    val buffer = ByteArray(BUFFER_SIZE + POLY1305_ABYTES)
                    var bytesRead: Int
                    
                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        if (bytesRead < POLY1305_ABYTES) {
                            throw Exception("Invalid encrypted data: insufficient bytes")
                        }
                        
                        try {
                            // Tag is first 16 bytes, ciphertext is remainder
                            val tag = buffer.copyOfRange(0, 16)
                            val ciphertext = buffer.copyOfRange(16, bytesRead)
                            
                            val decrypted = lazySodium.decryptDetached(
                                ciphertext,
                                null,
                                tag,
                                nonce,
                                key
                            )
                            output.write(decrypted)
                        } catch (e: SodiumException) {
                            throw Exception("Decryption failed or file corrupted: ${e.message}")
                        }
                    }
                }
            }
            
            EncryptionResult(
                success = true,
                encryptedFile = outputFile,
                originalSize = outputFile.length(),
                encryptedSize = encryptedFile.length()
            )
        } catch (e: Exception) {
            e.printStackTrace()
            EncryptionResult(success = false, error = e.message ?: "XChaCha20 decryption failed")
        }
    }

    /**
     * Calculate SHA-256 checksum of a file.
     */
    private fun calculateChecksum(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            var bytesRead: Int
            while (input.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        return android.util.Base64.encodeToString(digest.digest(), android.util.Base64.DEFAULT)
    }

    /**
     * Clear stored keys and nonces.
     */
    fun clearKeys() {
        encryptedPrefs.edit().clear().apply()
    }
}
