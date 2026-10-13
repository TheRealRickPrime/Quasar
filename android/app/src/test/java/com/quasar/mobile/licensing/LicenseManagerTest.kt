package com.quasar.mobile.licensing

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException
import java.time.ZoneOffset

private class FakeHttp(val handler: (Map<String, String>) -> String) : HttpPoster {
    val calls = ArrayList<Map<String, String>>()
    override fun postForm(url: String, fields: Map<String, String>): String {
        calls += fields
        return handler(fields)
    }
}

private fun ok(short: String) =
    """{"success":true,"purchase":{"short_product_id":"$short","email":"a@b.c","refunded":false}}"""

private const val FAIL = """{"success":false,"message":"That license does not exist for the provided product."}"""

class LicenseManagerTest {
    private var now = 1_760_000_000_000L
    private fun mgr(http: HttpPoster, store: KeyValueStore = MemoryStore()) =
        LicenseManager(http, store, { now }, ZoneOffset.UTC)

    @Test fun tierLimits() {
        assertEquals(6, Tier.FREE.backupsPerMonth)
        assertEquals(2L * 1024 * 1024 * 1024, Tier.FREE.uploadBytesPerMonth)
        assertEquals(15, Tier.SUPPORTER.backupsPerMonth)
        assertEquals(30L * 1024 * 1024 * 1024, Tier.SUPPORTER.uploadBytesPerMonth)
        assertNull(Tier.PRO.backupsPerMonth)
        assertNull(Tier.PRO.uploadBytesPerMonth)
    }

    @Test fun freeBlocksAfterSixBackups() {
        val m = mgr(FakeHttp { FAIL })
        repeat(6) { assertTrue(m.canStartBackup().allowed); m.recordBackup() }
        val c = m.canStartBackup()
        assertFalse(c.allowed)
        assertEquals("Free plan limit reached: 6 backups this month. Upgrade on the License page.", c.message)
    }

    @Test fun usageResetsNextMonth() {
        val m = mgr(FakeHttp { FAIL })
        repeat(6) { m.recordBackup() }
        assertFalse(m.canStartBackup().allowed)
        now += 32L * 24 * 3600 * 1000
        assertTrue(m.canStartBackup().allowed)
        assertEquals(0, m.backupsUsed())
    }

    @Test fun uploadQuota() {
        val m = mgr(FakeHttp { FAIL })
        val gb = 1024L * 1024 * 1024
        assertTrue(m.canUpload(2 * gb).allowed)
        m.recordUpload(gb)
        assertFalse(m.canUpload(2 * gb).allowed)
    }

    @Test fun activatesSupporterAndProIsUnlimited() {
        val m = mgr(FakeHttp { f -> if (f["product_permalink"] == "qygwf") ok("qygwf") else FAIL })
        assertNull(m.activate("KEY"))
        assertEquals(Tier.SUPPORTER, m.currentTier())
        repeat(15) { m.recordBackup() }
        assertFalse(m.canStartBackup().allowed)

        val pro = mgr(FakeHttp { f -> if (f["product_permalink"] == "qwjtj") ok("qwjtj") else FAIL })
        assertNull(pro.activate("KEY"))
        repeat(100) { pro.recordBackup() }
        assertTrue(pro.canStartBackup().allowed)
    }

    @Test fun retriesWithProductIdHintAndMapsByShortId() {
        val http = FakeHttp { f ->
            when {
                f.containsKey("product_permalink") ->
                    """{"success":false,"message":"The 'product_id' parameter is required. Please set 'product_id' to 'ABC123==' in the request."}"""
                f["product_id"] == "ABC123==" -> ok("qwjtj")
                else -> FAIL
            }
        }
        val r = mgr(http).verify("KEY", false)
        assertEquals(VerifyResult.Valid("KEY", Tier.PRO, "a@b.c"), r)
        assertEquals("false", http.calls.last()["increment_uses_count"])
        assertEquals("KEY", http.calls.last()["license_key"])
    }

    @Test fun rejectsBadPurchases() {
        val flags = listOf(""""refunded":true""", """"chargebacked":true""", """"disputed":true""",
            """"subscription_cancelled_at":"2026-01-01"""", """"subscription_failed_at":"2026-01-01"""")
        for (flag in flags) {
            val body = """{"success":true,"purchase":{"short_product_id":"qygwf",$flag}}"""
            assertTrue(flag, mgr(FakeHttp { body }).verify("K", false) is VerifyResult.Rejected)
        }
    }

    @Test fun notFoundAndNetworkMessages() {
        assertEquals(LicenseManager.MSG_NOT_FOUND, mgr(FakeHttp { FAIL }).activate("nope"))
        val down = object : HttpPoster {
            override fun postForm(url: String, fields: Map<String, String>): String = throw IOException("x")
        }
        assertEquals(LicenseManager.MSG_NETWORK, mgr(down).activate("k"))
    }

    @Test fun recheckAndOfflineGrace() {
        var online = true
        val http = FakeHttp { if (online) ok("qygwf") else throw IOException("offline") }
        val m = mgr(http)
        assertNull(m.activate("K"))
        val before = http.calls.size
        now += 2L * 24 * 3600 * 1000
        m.refreshIfDue()
        assertEquals(before, http.calls.size)
        online = false
        now += 8L * 24 * 3600 * 1000
        m.refreshIfDue()
        assertEquals(Tier.SUPPORTER, m.currentTier())
        now += 25L * 24 * 3600 * 1000
        assertEquals(Tier.FREE, m.currentTier())
    }

    @Test fun deactivateReverts() {
        val m = mgr(FakeHttp { ok("qygwf") })
        m.activate("K")
        m.deactivate()
        assertEquals(Tier.FREE, m.currentTier())
    }
}
