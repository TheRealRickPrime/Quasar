package com.quasar.mobile.engine

import com.goterl.lazysodium.SodiumAndroid
import java.io.DataInputStream
import java.io.EOFException
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.security.SecureRandom

/**
 * File format: "QSR1" | salt(16) | noncePrefix(16) | repeated [len(4, BE) | ciphertext].
 * Each chunk is XChaCha20-Poly1305 (IETF) with nonce = noncePrefix | chunkIndex(8, BE) and a one-byte
 * AAD marking the final chunk, so reordering and truncation are detected. Key = Argon2id(passphrase, salt).
 */
object Crypto {
    private val MAGIC = "QSR1".toByteArray()
    private const val CHUNK = 64 * 1024
    private const val TAG = 16
    private const val OPS = 2L
    private const val MEM = 64L * 1024 * 1024
    private const val ALG_ARGON2ID13 = 2

    private val sodium by lazy { SodiumAndroid().also { it.sodium_init() } }

    private fun deriveKey(pass: CharArray, salt: ByteArray): ByteArray {
        val pw = String(pass).toByteArray(Charsets.UTF_8)
        val key = ByteArray(32)
        val rc = sodium.crypto_pwhash(key, key.size.toLong(), pw, pw.size.toLong(), salt, OPS, com.sun.jna.NativeLong(MEM), ALG_ARGON2ID13)
        pw.fill(0)
        if (rc != 0) throw IOException("Key derivation failed (not enough memory?)")
        return key
    }

    private fun nonce(prefix: ByteArray, index: Long): ByteArray =
        ByteBuffer.allocate(24).put(prefix).putLong(index).array()

    private fun readFully(i: InputStream, b: ByteArray): Int {
        var n = 0
        while (n < b.size) {
            val r = i.read(b, n, b.size - n)
            if (r < 0) break
            n += r
        }
        return n
    }

    fun encrypt(input: File, output: OutputStream, pass: CharArray) {
        val rnd = SecureRandom()
        val salt = ByteArray(16).also(rnd::nextBytes)
        val prefix = ByteArray(16).also(rnd::nextBytes)
        val key = deriveKey(pass, salt)
        output.write(MAGIC); output.write(salt); output.write(prefix)
        FileInputStream(input).buffered(CHUNK).use { inp ->
            var cur = ByteArray(CHUNK)
            var curLen = readFully(inp, cur)
            var next = ByteArray(CHUNK)
            var index = 0L
            while (true) {
                val nextLen = if (curLen == CHUNK) readFully(inp, next) else 0
                val last = nextLen == 0
                val ct = ByteArray(curLen + TAG)
                val ctLen = LongArray(1)
                val ad = byteArrayOf(if (last) 1 else 0)
                val rc = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
                    ct, ctLen, cur, curLen.toLong(), ad, 1L, null, nonce(prefix, index), key)
                if (rc != 0) throw IOException("Encryption failed")
                output.write(ByteBuffer.allocate(4).putInt(ct.size).array())
                output.write(ct)
                if (last) break
                val t = cur; cur = next; next = t
                curLen = nextLen
                index++
            }
        }
        key.fill(0)
    }

    fun decrypt(input: InputStream, output: File, pass: CharArray) {
        val din = DataInputStream(input.buffered(CHUNK))
        val magic = ByteArray(4)
        val salt = ByteArray(16)
        val prefix = ByteArray(16)
        try {
            din.readFully(magic); din.readFully(salt); din.readFully(prefix)
        } catch (e: EOFException) { throw IOException("Not a Quasar encrypted file") }
        if (!magic.contentEquals(MAGIC)) throw IOException("Not a Quasar encrypted file")
        val key = deriveKey(pass, salt)
        FileOutputStream(output).buffered(CHUNK).use { out ->
            var index = 0L
            var len = readLen(din)
            if (len < 0) throw IOException("Encrypted file is truncated")
            while (true) {
                if (len < TAG || len > CHUNK + TAG) throw IOException("Encrypted file is corrupted")
                val ct = ByteArray(len)
                try { din.readFully(ct) } catch (e: EOFException) { throw IOException("Encrypted file is truncated") }
                val nextLen = readLen(din)
                val last = nextLen < 0
                val pt = ByteArray(len - TAG)
                val ptLen = LongArray(1)
                val rc = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(
                    pt, ptLen, null, ct, len.toLong(), byteArrayOf(if (last) 1 else 0), 1L, nonce(prefix, index), key)
                if (rc != 0) throw IOException("Wrong passphrase, or the file is corrupted or truncated")
                out.write(pt)
                if (last) break
                len = nextLen
                index++
            }
        }
        key.fill(0)
    }

    private fun readLen(d: DataInputStream): Int {
        val b = ByteArray(4)
        val n = readFully(d, b)
        if (n == 0) return -1
        if (n < 4) throw IOException("Encrypted file is truncated")
        return ByteBuffer.wrap(b).int
    }
}
