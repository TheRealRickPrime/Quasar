package com.quasar.mobile.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "quasar_prefs")

class TokenManager(private val context: Context) {
    private val accessTokenKey = stringPreferencesKey("access_token")
    private val userIdKey = stringPreferencesKey("user_id")
    private val userEmailKey = stringPreferencesKey("user_email")

    val accessToken: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[accessTokenKey]
    }

    val userId: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[userIdKey]
    }

    val userEmail: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[userEmailKey]
    }

    suspend fun saveTokens(token: String, userId: String, email: String) {
        context.dataStore.edit { preferences ->
            preferences[accessTokenKey] = token
            preferences[userIdKey] = userId
            preferences[userEmailKey] = email
        }
    }

    suspend fun clearTokens() {
        context.dataStore.edit { preferences ->
            preferences.remove(accessTokenKey)
            preferences.remove(userIdKey)
            preferences.remove(userEmailKey)
        }
    }
}
