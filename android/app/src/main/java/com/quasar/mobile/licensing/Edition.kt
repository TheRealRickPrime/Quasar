package com.quasar.mobile.licensing

enum class Edition(val id: String, val label: String) {
    FREE("free", "Free"),
    FREE_ADS("free-ads", "Free with Ads"),
    SUPPORTER("supporter", "Supporter"),
    PRO("pro", "Pro");

    val baseTier: Tier get() = if (this == FREE_ADS) Tier.FREE_ADS else Tier.FREE
    fun showsAffiliates(tier: Tier) = this == FREE_ADS && tier == Tier.FREE_ADS

    companion object {
        fun fromId(id: String): Edition = entries.first { it.id == id }
    }
}
