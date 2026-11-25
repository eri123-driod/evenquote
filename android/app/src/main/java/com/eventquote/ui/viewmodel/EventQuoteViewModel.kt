package com.eventquote.ui.viewmodel

import android.app.Application
import android.util.Patterns
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.eventquote.data.local.SessionManager
import com.eventquote.data.model.*
import com.eventquote.data.remote.RetrofitClient
import com.eventquote.util.formatoMoneda
import com.eventquote.util.mensajeDeError
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class UiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val erroresCampo: Map<String, String> = emptyMap(),
    val mensajeExito: String? = null,
    val token: String? = null,
    val currentUser: UserDto? = null,
    val estimacionActual: PrediccionResponse? = null,
    val historialCliente: List<CotizacionItem> = emptyList(),
    val estadisticasAdmin: EstadisticasResponse? = null,
    val cotizacionesAdmin: List<AdminCotizacionItem> = emptyList(),
    val usuariosAdmin: List<AdminUsuarioItem> = emptyList(),
    val mlInfo: MlInfoResponse? = null
)

/**
 * VistaModelo (MVVM): mantiene el estado de las pantallas y aplica las validaciones de entrada
 * ANTES de llamar al backend (el backend vuelve a validar todo por su cuenta).
 */
class EventQuoteViewModel(application: Application) : AndroidViewModel(application) {
    private val sessionManager = SessionManager(application)
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var restaurando = false

    // ------------------------------------------------------------------ validaciones
    private fun correoValido(email: String) = Patterns.EMAIL_ADDRESS.matcher(email.trim()).matches()

    private fun passwordFuerte(p: String) = p.length >= 8 && p.any { it.isLetter() } && p.any { it.isDigit() }

    private fun conErrores(errores: Map<String, String>) {
        _state.value = _state.value.copy(erroresCampo = errores, error = null, mensajeExito = null)
    }

    fun limpiarMensajes() {
        _state.value = _state.value.copy(error = null, mensajeExito = null, erroresCampo = emptyMap())
    }

    // ------------------------------------------------------------------ sesión
    /**
     * Restaura la sesion guardada. Solo borra el token si el servidor lo rechaza (401/403);
     * si el servidor esta apagado o no hay red, conserva la sesion para el siguiente intento.
     */
    fun restaurarSesion(onRestored: (String) -> Unit) {
        if (restaurando || _state.value.token != null) return
        restaurando = true
        viewModelScope.launch {
            try {
                val savedToken = sessionManager.tokenFlow.first()
                if (!savedToken.isNullOrBlank()) {
                    try {
                        val user = RetrofitClient.api.getMe("Bearer $savedToken")
                        _state.value = _state.value.copy(token = "Bearer $savedToken", currentUser = user)
                        onRestored(user.rol)
                    } catch (e: HttpException) {
                        if (e.code() == 401 || e.code() == 403) sessionManager.clearSession()
                    } catch (_: Exception) {
                        // Sin conexion: se queda en el login, la sesion se conserva.
                    }
                }
            } finally {
                restaurando = false
            }
        }
    }

    fun login(email: String, password: String, onSuccess: (String) -> Unit) {
        val errores = mutableMapOf<String, String>()
        if (email.isBlank()) errores["email"] = "Ingresa tu correo"
        else if (!correoValido(email)) errores["email"] = "Correo no válido (ejemplo: nombre@correo.com)"
        if (password.isBlank()) errores["password"] = "Ingresa tu contraseña"
        if (errores.isNotEmpty()) {
            conErrores(errores)
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, mensajeExito = null, erroresCampo = emptyMap())
            try {
                val res = RetrofitClient.api.login(LoginRequest(email.trim(), password))
                sessionManager.saveSession(res.access_token, res.user.rol, res.user.nombre)
                _state.value = _state.value.copy(
                    isLoading = false,
                    token = "Bearer ${res.access_token}",
                    currentUser = res.user
                )
                onSuccess(res.user.rol)
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = mensajeDeError(e, "No se pudo iniciar sesión")
                )
            }
        }
    }

    fun register(nombre: String, email: String, password: String, onRegistered: () -> Unit) {
        val errores = mutableMapOf<String, String>()
        if (nombre.trim().length < 2 || nombre.none { it.isLetter() }) {
            errores["nombre"] = "Escribe tu nombre (mínimo 2 letras)"
        }
        if (!correoValido(email)) errores["email"] = "Correo no válido (ejemplo: nombre@correo.com)"
        if (!passwordFuerte(password)) errores["password"] = "Mínimo 8 caracteres, con letras y números"
        if (errores.isNotEmpty()) {
            conErrores(errores)
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, erroresCampo = emptyMap())
            try {
                RetrofitClient.api.register(RegisterRequest(nombre.trim(), email.trim(), password))
                _state.value = _state.value.copy(isLoading = false, mensajeExito = "Cuenta creada. Inicia sesión.")
                onRegistered()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = mensajeDeError(e, "No se pudo registrar")
                )
            }
        }
    }

    // ------------------------------------------------------------------ cliente
    fun cotizarYGuardar(
        tipo: String,
        invitadosStr: String,
        horasStr: String,
        ciudad: String,
        servicios: List<String>
    ) {
        val invitados = invitadosStr.trim().toIntOrNull()
        val horas = horasStr.trim().replace(',', '.').toFloatOrNull()

        val errores = mutableMapOf<String, String>()
        if (invitados == null || invitados !in 1..2000) errores["invitados"] = "Debe ser un número entero entre 1 y 2000"
        if (horas == null || horas !in 1f..24f) errores["horas"] = "Debe ser un número entre 1 y 24"
        if (errores.isNotEmpty() || invitados == null || horas == null) {
            conErrores(errores)
            return
        }

        val token = _state.value.token ?: run {
            _state.value = _state.value.copy(error = "Tu sesión no es válida. Inicia sesión de nuevo.")
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, mensajeExito = null, erroresCampo = emptyMap())
            try {
                val req = CotizacionRequest(tipo, invitados, horas, ciudad, servicios)
                val pred = RetrofitClient.api.predecir(token, req)
                RetrofitClient.api.guardarCotizacion(token, req)
                _state.value = _state.value.copy(
                    isLoading = false,
                    estimacionActual = pred,
                    mensajeExito = "Cotización guardada en tu historial"
                )
                cargarHistorialCliente()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = mensajeDeError(e, "Error al calcular la cotización")
                )
            }
        }
    }

    fun cargarHistorialCliente() {
        val token = _state.value.token ?: return
        viewModelScope.launch {
            try {
                val lista = RetrofitClient.api.misCotizaciones(token)
                _state.value = _state.value.copy(historialCliente = lista)
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = mensajeDeError(e, "No se pudo cargar tu historial"))
            }
        }
    }

    // ------------------------------------------------------------------ administrador
    fun cargarPanelAdmin() {
        val token = _state.value.token ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val stats = RetrofitClient.api.getEstadisticas(token)
                val cots = RetrofitClient.api.getAllCotizaciones(token)
                val users = RetrofitClient.api.getUsuarios(token)
                _state.value = _state.value.copy(
                    isLoading = false,
                    estadisticasAdmin = stats,
                    cotizacionesAdmin = cots,
                    usuariosAdmin = users
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = mensajeDeError(e, "Error cargando datos de administrador")
                )
            }
        }
    }

    fun promoverUsuario(userId: Int) {
        val token = _state.value.token ?: return
        viewModelScope.launch {
            try {
                val res = RetrofitClient.api.promoverUsuario(token, userId)
                _state.value = _state.value.copy(mensajeExito = res["mensaje"] ?: "Usuario promovido", error = null)
                cargarPanelAdmin()
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = mensajeDeError(e, "Error al promover usuario"))
            }
        }
    }

    fun confirmarCostoReal(eventoId: Int, costoStr: String, fuente: String) {
        val token = _state.value.token ?: return
        val costo = costoStr.trim().replace(",", ".").toDoubleOrNull()
        if (costo == null || costo <= 0.0 || costo > 10_000_000.0) {
            _state.value = _state.value.copy(error = "El costo real debe ser un número entre 1 y 10,000,000", mensajeExito = null)
            return
        }
        if (fuente.trim().length < 3) {
            _state.value = _state.value.copy(error = "Indica la fuente del costo (mínimo 3 caracteres)", mensajeExito = null)
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, mensajeExito = null)
            try {
                val res = RetrofitClient.api.confirmarCostoReal(token, CostoRealRequest(eventoId, costo, fuente.trim()))
                _state.value = _state.value.copy(isLoading = false, mensajeExito = res["mensaje"] ?: "Costo real confirmado")
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = mensajeDeError(e, "No se pudo guardar el costo real"))
            }
        }
    }

    fun cargarMlInfo() {
        val token = _state.value.token ?: return
        viewModelScope.launch {
            try {
                val info = RetrofitClient.api.getMlInfo(token)
                _state.value = _state.value.copy(mlInfo = info)
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = mensajeDeError(e, "No se pudo cargar la información del modelo"))
            }
        }
    }

    fun reentrenarModelo() {
        val token = _state.value.token ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, mensajeExito = null)
            try {
                val info = RetrofitClient.api.reentrenarModelo(token)
                _state.value = _state.value.copy(
                    isLoading = false,
                    mlInfo = info,
                    mensajeExito = "Modelo reentrenado: ${info.version} (error medio ${formatoMoneda(info.mae_cv)} MXN)"
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = mensajeDeError(e, "No se pudo reentrenar el modelo"))
            }
        }
    }

    fun logout(onLoggedOut: () -> Unit) {
        viewModelScope.launch {
            sessionManager.clearSession()
            _state.value = UiState()
            onLoggedOut()
        }
    }
}
