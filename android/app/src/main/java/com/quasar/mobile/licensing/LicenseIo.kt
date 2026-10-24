package com.quasar.mobile.licensing

import android.content.Context
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

class OkHttpPoster(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build(),
) : HttpPoster {
    // Gumroad answers failures with 4xx plus a JSON body, so the body is returned regardless of status.
    override fun postForm(url: String, fields: Map<String, String>): String {
        val body = FormBody.Builder().also { b -> fields.forEach { (k, v) -> b.add(k, v) } }.build()
        client.newCall(Request.Builder().url(url).post(body).build()).execute().use { r ->
            if (r.code >= 500 || r.code == 429) throw IOException("License service temporarily unavailable")
            return r.body?.string() ?: throw IOException("Empty response")
        }
    }
}

class PrefsStore(context: Context) : KeyValueStore {
    private val prefs = context.getSharedPreferences("quasar_license", Context.MODE_PRIVATE)
    override fun get(key: String): String? = prefs.getString(key, null)
    override fun put(key: String, value: String?) {
        prefs.edit().apply { if (value == null) remove(key) else putString(key, value) }.apply()
    }
}
