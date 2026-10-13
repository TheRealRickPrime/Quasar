package com.quasar.mobile.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class UpdaterTest {
    private val json = """{"version":"0.4.0","windows":{"url":"w","sha256":"x"},
        "android":{"versionCode":5,"url":"http://a/q.apk","sha256":"abc"}}"""

    @Test fun newerCodeIsOffered() {
        val info = parseManifest(json, 4)!!
        assertEquals("0.4.0", info.version)
        assertEquals("http://a/q.apk", info.url)
    }

    @Test fun sameOrOlderIsNot() {
        assertNull(parseManifest(json, 5))
        assertNull(parseManifest(json, 9))
    }
}
