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
    private fun mgr(http: HttpPoster, store: KeyValueStore = MemoryStore(), edition: Edition = Edition.FREE) =
        LicenseManager(http, store, { now }, ZoneOffset.UTC, edition)

    @Test fun tierLimits() {
        assertEquals(6, Tier.FREE.backupsPerMonth)
        assertEquals(2L * 1024 * 1024 * 1024, Tier.FREE.uploadBytesPerMonth)
        assertEquals(10, Tier.FREE_ADS.backupsPerMonth)
        assertEquals(Tier.FREE.uploadBytesPerMonth, Tier.FREE_ADS.uploadBytesPerMonth)
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
        val m = mgr(FakeHttp { f -> if (f["product_id"] == "7sQ_4QWbmr1Miy5LYzh-Bw==") ok("qygwf") else FAIL })
        assertNull(m.activate("KEY"))
        assertEquals(Tier.SUPPORTER, m.currentTier())
        repeat(15) { m.recordBackup() }
        assertFalse(m.canStartBackup().allowed)

        val pro = mgr(FakeHttp { f -> if (f["product_id"] == "9R_AkG7S8By0ZotuYyM1Lg==") ok("qwjtj") else FAIL })
        assertNull(pro.activate("KEY"))
        repeat(100) { pro.recordBackup() }
        assertTrue(pro.canStartBackup().allowed)
    }

    @Test fun usesExactProductIdsAndMapsVerifiedIdentity() {
        val http = FakeHttp { f ->
            when {
                f["product_id"] == "9R_AkG7S8By0ZotuYyM1Lg==" -> ok("qwjtj")
                else -> FAIL
            }
        }
        val r = mgr(http).verify("KEY", false)
        assertEquals(VerifyResult.Valid("KEY", Tier.PRO, "a@b.c"), r)
        assertEquals("false", http.calls.last()["increment_uses_count"])
        assertEquals("KEY", http.calls.last()["license_key"])
        assertEquals(LicenseManager.PRODUCT_IDS.keys.toList(), http.calls.map { it["product_id"] })
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

    @Test fun switchingDistributionsKeepsLicenseAndUsageAndCannotUnlockPaid() {
        val store = MemoryStore()
        val http = FakeHttp { ok("qygwf") }
        val free = mgr(http, store)
        repeat(6) { free.recordBackup() }
        free.recordUpload(1024L)
        assertFalse(free.canStartBackup().allowed)
        val ads = mgr(http, store, Edition.FREE_ADS)
        assertEquals(6, ads.backupsUsed())
        assertTrue(ads.canStartBackup().allowed)
        repeat(4) { ads.recordBackup() }
        assertFalse(ads.canStartBackup().allowed)
        assertTrue(Edition.FREE_ADS.showsAffiliates(ads.currentTier()))
        for (edition in listOf(Edition.SUPPORTER, Edition.PRO)) {
            assertEquals(Tier.FREE, mgr(http, store, edition).currentTier())
        }
        assertNull(ads.activate("SYNTHETIC-TEST-ONLY"))
        assertFalse(Edition.FREE_ADS.showsAffiliates(ads.currentTier()))
        val paid = mgr(http, store, Edition.PRO)
        assertEquals(Tier.SUPPORTER, paid.currentTier())
        assertEquals(10, paid.backupsUsed())
        paid.deactivate()
        assertEquals(10, mgr(http, store).backupsUsed())
        assertEquals(1024L, mgr(http, store).uploadUsedBytes())
    }

    @Test fun refundRevokesAndOfflineExpiryFallsBackToBundledFreeExperience() {
        var body = ok("qygwf")
        val store = MemoryStore()
        val http = FakeHttp { body }
        val ads = mgr(http, store, Edition.FREE_ADS)
        ads.activate("SYNTHETIC-TEST-ONLY")
        now += 31L * 24 * 3600 * 1000
        assertEquals(Tier.FREE_ADS, ads.currentTier())
        body = """{"success":true,"purchase":{"short_product_id":"qygwf","refunded":true}}"""
        ads.refreshIfDue()
        assertNull(ads.cachedLicense())
        assertTrue(ads.edition.showsAffiliates(ads.currentTier()))
    }

    @Test fun conflictingProductIdentityIsRejected() {
        val http = FakeHttp {
            """{"success":true,"purchase":{"product_id":"unrelated","short_product_id":"qwjtj"}}"""
        }
        assertEquals(VerifyResult.NotFound, mgr(http).verify("SYNTHETIC-TEST-ONLY", false))
    }
}
