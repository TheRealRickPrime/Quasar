package com.quasar.mobile.licensing

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.io.IOException
import java.time.Instant
import java.time.ZoneId
import java.time.YearMonth

private const val GB = 1024L * 1024L * 1024L

enum class Tier(val label: String, val price: String, val backupsPerMonth: Int?, val uploadBytesPerMonth: Long?) {
    FREE("Free", "$0", 6, 2 * GB),
    SUPPORTER("Supporter", "$10", 15, 30 * GB),
    PRO("Pro", "$25 one-time", null, null),
}

interface HttpPoster {
    @Throws(IOException::class)
    fun postForm(url: String, fields: Map<String, String>): String
}

interface KeyValueStore {
    fun get(key: String): String?
    fun put(key: String, value: String?)
}

class MemoryStore : KeyValueStore {
    private val map = HashMap<String, String>()
    override fun get(key: String) = map[key]
    override fun put(key: String, value: String?) {
        if (value == null) map.remove(key) else map[key] = value
    }
}

data class LicenseInfo(val key: String, val tier: Tier, val email: String, val checkedAt: Long)

sealed class VerifyResult {
    data class Valid(val key: String, val tier: Tier, val email: String) : VerifyResult()
    data class Rejected(val message: String) : VerifyResult()
    object NotFound : VerifyResult()
    object NetworkError : VerifyResult()
}

data class Check(val allowed: Boolean, val message: String = "")

class LicenseManager(
    private val http: HttpPoster,
    private val store: KeyValueStore,
    private val clock: () -> Long = { System.currentTimeMillis() },
    private val zone: ZoneId = ZoneId.systemDefault(),
) {
    companion object {
        const val VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
        val PERMALINKS = linkedMapOf("qygwf" to Tier.SUPPORTER, "qwjtj" to Tier.PRO)
        const val RECHECK_MS = 3L * 24 * 3600 * 1000
        const val OFFLINE_GRACE_MS = 30L * 24 * 3600 * 1000
        const val MSG_NOT_FOUND = "That license key wasn't found. Check it and try again."
        const val MSG_NETWORK = "Couldn't reach the license server. Check your internet connection and try again."
        private val PRODUCT_ID_HINT = Regex("'product_id' to '([^']+)'")
    }

    // ---- Gumroad verification ----

    fun verify(key: String, increment: Boolean): VerifyResult {
        val licenseKey = key.trim()
        if (licenseKey.isEmpty()) return VerifyResult.NotFound
        try {
            for (permalink in PERMALINKS.keys) {
                var json = post(mapOf("product_permalink" to permalink), licenseKey, increment)
                if (!json.success()) {
                    val hint = PRODUCT_ID_HINT.find(json.str("message") ?: "")?.groupValues?.get(1)
                    if (hint != null) json = post(mapOf("product_id" to hint), licenseKey, increment)
                }
                if (!json.success()) continue
                val purchase = json.getAsJsonObject("purchase") ?: continue
                val tier = PERMALINKS[purchase.str("short_product_id")] ?: PERMALINKS[purchase.str("permalink")] ?: continue
                rejection(purchase)?.let { return VerifyResult.Rejected(it) }
                return VerifyResult.Valid(licenseKey, tier, purchase.str("email") ?: "")
            }
        } catch (e: IOException) {
            return VerifyResult.NetworkError
        } catch (e: RuntimeException) {
            return VerifyResult.NetworkError
        }
        return VerifyResult.NotFound
    }

    private fun post(idField: Map<String, String>, key: String, increment: Boolean): JsonObject {
        val fields = idField + mapOf("license_key" to key, "increment_uses_count" to increment.toString())
        val body = http.postForm(VERIFY_URL, fields)
        return JsonParser.parseString(body).asJsonObject
    }

    private fun JsonObject.success() = get("success")?.let { !it.isJsonNull && it.asBoolean } ?: false
    private fun JsonObject.str(name: String): String? = get(name)?.takeIf { !it.isJsonNull }?.asString
    private fun JsonObject.flag(name: String) = get(name)?.takeIf { !it.isJsonNull }?.let { e: JsonElement -> e.asBoolean } ?: false
    private fun JsonObject.present(name: String) = get(name)?.let { !it.isJsonNull && it.asString.isNotEmpty() } ?: false

    private fun rejection(p: JsonObject): String? = when {
        p.flag("refunded") -> "This purchase was refunded, so the license is no longer valid."
        p.flag("chargebacked") || p.flag("disputed") -> "This purchase is disputed, so the license is not valid."
        p.present("subscription_cancelled_at") || p.present("subscription_failed_at") ->
            "This subscription is no longer active."
        else -> null
    }

    // ---- Activation / cache ----

    fun activate(key: String): String? {
        return when (val r = verify(key, true)) {
            is VerifyResult.Valid -> {
                saveLicense(LicenseInfo(r.key, r.tier, r.email, clock()))
                null
            }
            is VerifyResult.Rejected -> r.message
            VerifyResult.NotFound -> MSG_NOT_FOUND
            VerifyResult.NetworkError -> MSG_NETWORK
        }
    }

    fun deactivate() {
        for (k in listOf("lic_key", "lic_tier", "lic_email", "lic_checked")) store.put(k, null)
    }

    fun cachedLicense(): LicenseInfo? {
        val key = store.get("lic_key") ?: return null
        val tier = store.get("lic_tier")?.let { runCatching { Tier.valueOf(it) }.getOrNull() } ?: return null
        return LicenseInfo(key, tier, store.get("lic_email") ?: "", store.get("lic_checked")?.toLongOrNull() ?: 0L)
    }

    private fun saveLicense(l: LicenseInfo) {
        store.put("lic_key", l.key)
        store.put("lic_tier", l.tier.name)
        store.put("lic_email", l.email)
        store.put("lic_checked", l.checkedAt.toString())
    }

    /** Effective tier: cached license unless it has not been verified for 30 days. */
    fun currentTier(): Tier {
        val l = cachedLicense() ?: return Tier.FREE
        return if (clock() - l.checkedAt > OFFLINE_GRACE_MS) Tier.FREE else l.tier
    }

    /** Re-verifies online when the cached check is 3+ days old. Call off the main thread. */
    fun refreshIfDue() {
        val l = cachedLicense() ?: return
        if (clock() - l.checkedAt < RECHECK_MS) return
        when (val r = verify(l.key, false)) {
            is VerifyResult.Valid -> saveLicense(LicenseInfo(r.key, r.tier, r.email, clock()))
            is VerifyResult.Rejected, VerifyResult.NotFound -> deactivate()
            VerifyResult.NetworkError -> Unit
        }
    }

    // ---- Monthly usage ----

    private fun monthKey(): String = YearMonth.from(Instant.ofEpochMilli(clock()).atZone(zone)).toString()

    private fun rollMonth() {
        val m = monthKey()
        if (store.get("usage_month") != m) {
            store.put("usage_month", m)
            store.put("usage_backups", "0")
            store.put("usage_upload", "0")
        }
    }

    fun backupsUsed(): Int { rollMonth(); return store.get("usage_backups")?.toIntOrNull() ?: 0 }
    fun uploadUsedBytes(): Long { rollMonth(); return store.get("usage_upload")?.toLongOrNull() ?: 0L }

    fun canStartBackup(): Check {
        val tier = currentTier()
        val limit = tier.backupsPerMonth ?: return Check(true)
        return if (backupsUsed() >= limit) {
            Check(false, "${tier.label} plan limit reached: $limit backups this month. Upgrade on the License page.")
        } else Check(true)
    }

    fun recordBackup() {
        val n = backupsUsed() + 1
        store.put("usage_backups", n.toString())
    }

    fun canUpload(bytes: Long): Check {
        val tier = currentTier()
        val limit = tier.uploadBytesPerMonth ?: return Check(true)
        return if (uploadUsedBytes() + bytes > limit) {
            Check(false, "${tier.label} plan limit reached: ${limit / GB} GB of cloud upload this month. Upgrade on the License page.")
        } else Check(true)
    }

    fun recordUpload(bytes: Long) {
        store.put("usage_upload", (uploadUsedBytes() + bytes).toString())
    }
}
