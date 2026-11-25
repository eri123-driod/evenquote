package com.eventquote.data.remote

import com.eventquote.data.model.*
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body req: LoginRequest): LoginResponse

    @POST("auth/register")
    suspend fun register(@Body req: RegisterRequest): Map<String, String>

    @GET("auth/me")
    suspend fun getMe(@Header("Authorization") token: String): UserDto

    @POST("cotizaciones/predecir")
    suspend fun predecir(
        @Header("Authorization") token: String,
        @Body req: CotizacionRequest
    ): PrediccionResponse

    @POST("cotizaciones")
    suspend fun guardarCotizacion(
        @Header("Authorization") token: String,
        @Body req: CotizacionRequest
    ): GuardarCotizacionResponse

    @GET("cotizaciones/mias")
    suspend fun misCotizaciones(@Header("Authorization") token: String): List<CotizacionItem>

    @GET("admin/estadisticas")
    suspend fun getEstadisticas(@Header("Authorization") token: String): EstadisticasResponse

    @GET("admin/cotizaciones")
    suspend fun getAllCotizaciones(@Header("Authorization") token: String): List<AdminCotizacionItem>

    @GET("admin/usuarios")
    suspend fun getUsuarios(@Header("Authorization") token: String): List<AdminUsuarioItem>

    @GET("admin/ml/info")
    suspend fun getMlInfo(@Header("Authorization") token: String): MlInfoResponse

    @POST("admin/ml/reentrenar")
    suspend fun reentrenarModelo(@Header("Authorization") token: String): MlInfoResponse

    @POST("admin/costos-confirmados")
    suspend fun confirmarCostoReal(
        @Header("Authorization") token: String,
        @Body req: CostoRealRequest
    ): Map<String, String>

    @PATCH("admin/usuarios/{id}/promover")
    suspend fun promoverUsuario(
        @Header("Authorization") token: String,
        @Path("id") userId: Int
    ): Map<String, String>
}

object RetrofitClient {
    // Emulador de Android Studio: 10.0.2.2 apunta al localhost de tu PC.
    // Telefono fisico: cambia por la IPv4 de tu PC, ej. "http://192.168.1.75:8000/"
    const val BASE_URL = "http://127.0.0.1:8000/"

    private val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(httpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
