package com.quasar.mobile.licensing

import org.junit.Assert.assertEquals
import org.junit.Test

/** Calls the live Gumroad API with the zero-dollar test purchases. Never increments the use count. */
class GumroadLiveTest {
    private val mgr = LicenseManager(OkHttpPoster(), MemoryStore())

    @Test fun supporterTestKey() {
        val r = mgr.verify("BB83C881-18114DD0-9C65DCA0-CA242234", false)
        assertEquals(Tier.SUPPORTER, (r as VerifyResult.Valid).tier)
    }

    @Test fun proTestKey() {
        val r = mgr.verify("4442E2B0-67C74F10-854E4A55-41AC3FA7", false)
        assertEquals(Tier.PRO, (r as VerifyResult.Valid).tier)
    }

    @Test fun bogusKey() {
        assertEquals(VerifyResult.NotFound, mgr.verify("00000000-00000000-00000000-00000000", false))
    }
}
