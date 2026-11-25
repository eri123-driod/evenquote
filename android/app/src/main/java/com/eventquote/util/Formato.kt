package com.eventquote.util

import com.google.gson.JsonParser
import retrofit2.HttpException
import java.io.IOException
import java.util.Locale

/** Formato de dinero consistente sin importar el idioma del telefono: $12,345.67 */
fun formatoMoneda(valor: Double): String = String.format(Locale.US, "\$%,.2f", valor)

/** "2026-11-19T18:30:00" -> "2026-11-19 18:30" */
fun fechaCorta(fecha: String): String = fecha.replace("T", " ").take(16)

/** Lee el mensaje {"detail": "..."} que manda el backend (ya viene en español). */
private fun detalleDelServidor(e: HttpException): String? {
    try {
        val cuerpo = e.response()?.errorBody()?.string()
        if (cuerpo.isNullOrBlank()) return null
        val elemento = JsonParser.parseString(cuerpo)
        if (!elemento.isJsonObject) return null
        val detail = elemento.asJsonObject.get("detail") ?: return null
        return if (detail.isJsonPrimitive) detail.asString else null
    } catch (_: Exception) {
        return null
    }
}

/** Convierte excepciones de Retrofit/red en mensajes entendibles para el usuario. */
fun mensajeDeError(e: Throwable, porDefecto: String): String = when (e) {
    is HttpException -> detalleDelServidor(e) ?: when (e.code()) {
        400, 409 -> "$porDefecto (datos duplicados o inválidos)"
        401 -> "Credenciales inválidas o sesión expirada. Inicia sesión de nuevo."
        403 -> "No tienes permisos para realizar esta acción."
        404 -> "Servicio no encontrado en el servidor (404). Revisa la versión del backend."
        422 -> "Los datos enviados no son válidos. Revisa el formulario."
        in 500..599 -> "Error interno del servidor (${e.code()}). Revisa la terminal de uvicorn."
        else -> "$porDefecto (HTTP ${e.code()})"
    }
    is IOException ->
        "No se pudo conectar al servidor. Verifica que uvicorn esté encendido y la URL en ApiService.kt."
    else -> porDefecto
}
