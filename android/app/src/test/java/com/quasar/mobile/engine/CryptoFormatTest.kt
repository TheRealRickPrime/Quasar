package com.quasar.mobile.engine

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException

/** Host-native format checks in native CI; never launches Android or an emulator. */
class CryptoFormatTest {
    @Test fun existingQsr1VectorAndChunkBoundariesStayCompatible() {
        assumeTrue(System.getProperty("quasar.nativeTests") == "true")
        val plain = "Quasar format compatibility\n".toByteArray()
        val vector = javaClass.getResourceAsStream("/crypto-qsr1.hex")!!.bufferedReader().use { it.readText().trim() }
            .chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        val file = File.createTempFile("qsr-format", ".bin")
        val restored = File.createTempFile("qsr-restored", ".bin")
        try {
            Crypto.decrypt(ByteArrayInputStream(vector), restored, "synthetic-format-test".toCharArray())
            assertArrayEquals(plain, restored.readBytes())
            for (size in listOf(0, 1, 65535, 65536, 65537, 131072)) {
                val data = ByteArray(size) { (it % 251).toByte() }
                file.writeBytes(data)
                val encrypted = ByteArrayOutputStream()
                Crypto.encrypt(file, encrypted, "synthetic-format-test".toCharArray())
                Crypto.decrypt(ByteArrayInputStream(encrypted.toByteArray()), restored,
                    "synthetic-format-test".toCharArray())
                assertArrayEquals(data, restored.readBytes())
            }
            assertThrows(IOException::class.java) {
                Crypto.decrypt(ByteArrayInputStream(vector), restored, "wrong-passphrase".toCharArray())
            }
            assertThrows(IOException::class.java) {
                Crypto.decrypt(ByteArrayInputStream(vector.copyOf(vector.size - 1)), restored,
                    "synthetic-format-test".toCharArray())
            }
            val altered = vector.copyOf().also { it[it.lastIndex] = (it.last().toInt() xor 1).toByte() }
            assertThrows(IOException::class.java) {
                Crypto.decrypt(ByteArrayInputStream(altered), restored, "synthetic-format-test".toCharArray())
            }
        } finally {
            file.delete(); restored.delete()
        }
    }
}
