package com.eventquote.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "eventquote_session")

class SessionManager(private val context: Context) {
    companion object {
        val TOKEN_KEY = stringPreferencesKey("jwt_token")
        val ROL_KEY = stringPreferencesKey("user_rol")
        val NOMBRE_KEY = stringPreferencesKey("user_nombre")
    }

    val tokenFlow: Flow<String?> = context.dataStore.data.map { it[TOKEN_KEY] }
    val rolFlow: Flow<String?> = context.dataStore.data.map { it[ROL_KEY] }

    suspend fun saveSession(token: String, rol: String, nombre: String) {
        context.dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[ROL_KEY] = rol
            prefs[NOMBRE_KEY] = nombre
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { it.clear() }
    }
}
