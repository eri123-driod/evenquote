package com.eventquote.data.model

data class LoginRequest(val email: String, val password: String)
data class RegisterRequest(val nombre: String, val email: String, val password: String)

data class UserDto(
    val id: Int,
    val nombre: String,
    val email: String,
    val rol: String
)

data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val user: UserDto
)

data class CotizacionRequest(
    val tipo: String,
    val invitados: Int,
    val duracion_horas: Float,
    val ciudad: String,
    val servicios: List<String>,
    val fecha: String? = null
)

data class PrediccionResponse(
    val costo_estimado: Double,
    val moneda: String,
    val modelo_version: String
)

data class GuardarCotizacionResponse(
    val cotizacion_id: Int,
    val evento_id: Int,
    val costo_estimado: Double,
    val moneda: String,
    val modelo_version: String
)

data class CotizacionItem(
    val id: Int,
    val tipo: String,
    val ciudad: String,
    val invitados: Int,
    val horas: Float,
    val costo_estimado: Double,
    val modelo_version: String,
    val fecha: String
)

data class TipoEstadistica(
    val tipo: String,
    val total_cotizaciones: Int,
    val costo_promedio: Double
)

data class ClienteEstadistica(
    val cliente: String,
    val email: String,
    val total_cotizaciones: Int,
    val volumen: Double
)

data class EstadisticasResponse(
    val total_eventos: Int,
    val volumen_cotizado: Double,
    val resumen_por_tipo: List<TipoEstadistica>,
    val resumen_por_cliente: List<ClienteEstadistica>? = null
)

data class AdminCotizacionItem(
    val id: Int,
    val evento_id: Int,
    val cliente: String,
    val email: String,
    val tipo: String,
    val ciudad: String,
    val invitados: Int,
    val horas: Float,
    val costo_estimado: Double,
    val fecha: String
)

data class AdminUsuarioItem(
    val id: Int,
    val nombre: String,
    val email: String,
    val rol: String,
    val creado_en: String
)

data class CostoRealRequest(
    val evento_id: Int,
    val costo_real: Double,
    val fuente: String
)

data class MlInfoResponse(
    val version: String,
    val modelo: String,
    val entrenado_en: String,
    val muestras_base: Int,
    val muestras_reales: Int,
    val muestras_total: Int,
    val descartados_invalidos: Int,
    val mae_cv: Double,
    val r2_cv: Double,
    val metodo_evaluacion: String,
    val variables: List<String>,
    val reales_disponibles: Int
)
