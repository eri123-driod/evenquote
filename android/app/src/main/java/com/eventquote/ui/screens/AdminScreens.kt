package com.eventquote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.eventquote.data.model.AdminCotizacionItem
import com.eventquote.data.model.TipoEstadistica
import com.eventquote.ui.viewmodel.EventQuoteViewModel
import com.eventquote.util.fechaCorta
import com.eventquote.util.formatoMoneda

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminHomeScreen(
    vm: EventQuoteViewModel,
    onLogout: () -> Unit
) {
    val state by vm.state.collectAsState()
    var tabIndex by remember { mutableIntStateOf(0) }

    LaunchedEffect(Unit) { vm.cargarPanelAdmin() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Panel Administrador") },
                actions = {
                    TextButton(onClick = { vm.logout(onLogout) }) { Text("Salir") }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            ScrollableTabRow(selectedTabIndex = tabIndex, edgePadding = 8.dp) {
                Tab(selected = tabIndex == 0, onClick = { tabIndex = 0; vm.limpiarMensajes(); vm.cargarPanelAdmin() }, text = { Text("Estadísticas") })
                Tab(selected = tabIndex == 1, onClick = { tabIndex = 1; vm.limpiarMensajes() }, text = { Text("Cotizaciones") })
                Tab(selected = tabIndex == 2, onClick = { tabIndex = 2; vm.limpiarMensajes() }, text = { Text("Usuarios") })
                Tab(selected = tabIndex == 3, onClick = { tabIndex = 3; vm.limpiarMensajes() }, text = { Text("Modelo ML") })
            }

            if (state.isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
            state.error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(8.dp))
            }
            state.mensajeExito?.let {
                Text(it, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(8.dp))
            }

            when (tabIndex) {
                0 -> AdminEstadisticasTab(vm)
                1 -> AdminCotizacionesTab(vm)
                2 -> AdminUsuariosTab(vm)
                3 -> AdminModeloTab(vm)
            }
        }
    }
}

@Composable
fun AdminEstadisticasTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()
    val stats = state.estadisticasAdmin

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Resumen General (Registros Válidos)", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(6.dp))
                    Text("Total de cotizaciones: ${stats?.total_eventos ?: 0}")
                    Text("Volumen estimado: ${formatoMoneda(stats?.volumen_cotizado ?: 0.0)} MXN")
                }
            }
        }

        item {
            Text("Costo Promedio por Tipo de Evento", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            BarrasPromedioChart(stats?.resumen_por_tipo ?: emptyList())
        }

        item {
            Text("Registros por Cliente", style = MaterialTheme.typography.titleMedium)
        }

        items(stats?.resumen_por_cliente ?: emptyList()) { fila ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.padding(12.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(fila.cliente, style = MaterialTheme.typography.titleSmall)
                        Text(fila.email, style = MaterialTheme.typography.bodySmall)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("${fila.total_cotizaciones} cotiz.")
                        Text(formatoMoneda(fila.volumen), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }

        item {
            Text("Resumen por Tipo de Evento", style = MaterialTheme.typography.titleMedium)
        }

        items(stats?.resumen_por_tipo ?: emptyList()) { fila ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.padding(12.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("${fila.tipo.uppercase()} (${fila.total_cotizaciones} eventos)")
                    Text("Prom: ${formatoMoneda(fila.costo_promedio)}")
                }
            }
        }
    }
}

@Composable
fun BarrasPromedioChart(datos: List<TipoEstadistica>) {
    if (datos.isEmpty()) {
        Text("No hay datos suficientes para graficar.")
        return
    }
    val maxVal = datos.maxOf { it.costo_promedio }.coerceAtLeast(1.0)
    val colores = listOf(Color(0xFF3F51B5), Color(0xFF009688), Color(0xFFFF9800), Color(0xFFE91E63))

    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().height(240.dp).padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            datos.forEachIndexed { i, d ->
                val fraccion = (d.costo_promedio / maxVal).toFloat().coerceIn(0.03f, 1f)
                Column(
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        formatoMoneda(d.costo_promedio),
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(Modifier.height(4.dp))
                    Box(
                        modifier = Modifier.weight(1f).fillMaxWidth(0.6f),
                        contentAlignment = Alignment.BottomCenter
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .fillMaxHeight(fraccion)
                                .background(colores[i % colores.size])
                        )
                    }
                    Spacer(Modifier.height(4.dp))
                    Text(
                        d.tipo.uppercase(),
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
fun AdminCotizacionesTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()
    var seleccionada by remember { mutableStateOf<AdminCotizacionItem?>(null) }

    seleccionada?.let { cot ->
        ConfirmarCostoDialog(
            cot = cot,
            onDismiss = { seleccionada = null },
            onConfirm = { costo, fuente ->
                vm.confirmarCostoReal(cot.evento_id, costo, fuente)
                seleccionada = null
            }
        )
    }

    if (state.cotizacionesAdmin.isEmpty() && !state.isLoading) {
        Box(modifier = Modifier.fillMaxSize().padding(24.dp)) {
            Text("Todavía no hay cotizaciones registradas.")
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(state.cotizacionesAdmin) { c ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("#${c.id} ${c.cliente}", style = MaterialTheme.typography.titleSmall)
                        Text(formatoMoneda(c.costo_estimado), style = MaterialTheme.typography.titleSmall)
                    }
                    Text("${c.tipo.uppercase()} | ${c.ciudad} | ${c.invitados} inv. | ${c.horas} hrs")
                    Text("Correo: ${c.email} | Fecha: ${fechaCorta(c.fecha)}", style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = { seleccionada = c }) {
                        Text("Confirmar costo real (para entrenar el modelo)")
                    }
                }
            }
        }
    }
}

@Composable
fun ConfirmarCostoDialog(
    cot: AdminCotizacionItem,
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit
) {
    var costo by remember { mutableStateOf("") }
    var fuente by remember { mutableStateOf("Cotización final del proveedor") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Confirmar costo real") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Evento #${cot.evento_id} (${cot.tipo.uppercase()}, ${cot.ciudad}). Estimado: ${formatoMoneda(cot.costo_estimado)}")
                OutlinedTextField(
                    value = costo,
                    onValueChange = { costo = it },
                    label = { Text("Costo real en MXN") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
                )
                OutlinedTextField(
                    value = fuente,
                    onValueChange = { fuente = it },
                    label = { Text("Fuente del dato") },
                    singleLine = true
                )
            }
        },
        confirmButton = { TextButton(onClick = { onConfirm(costo, fuente) }) { Text("Guardar") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancelar") } }
    )
}

@Composable
fun AdminModeloTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()
    val info = state.mlInfo

    LaunchedEffect(Unit) { vm.cargarMlInfo() }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Modelo de Machine Learning", style = MaterialTheme.typography.titleMedium)
                    if (info == null) {
                        Text("Cargando información del modelo...")
                    } else {
                        Text("Versión activa: ${info.version}")
                        Text("Algoritmo: ${info.modelo}")
                        Text("Entrenado: ${info.entrenado_en}")
                        Text("Datos: ${info.muestras_total} (${info.muestras_base} base + ${info.muestras_reales} reales de clientes)")
                        Text("Registros inválidos descartados: ${info.descartados_invalidos}")
                        Spacer(Modifier.height(4.dp))
                        Text("Desempeño (${info.metodo_evaluacion})", style = MaterialTheme.typography.titleSmall)
                        Text("Error medio absoluto (MAE): ${formatoMoneda(info.mae_cv)} MXN")
                        Text("R²: ${"%.3f".format(info.r2_cv)}")
                        Spacer(Modifier.height(4.dp))
                        Text("Variables: ${info.variables.joinToString(", ")}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Aprender de los datos de los clientes", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "1) Ve a la pestaña Cotizaciones y confirma el costo real de un evento.\n" +
                            "2) Pulsa Reentrenar: el modelo se vuelve a entrenar con esos datos guardados en MySQL.",
                        style = MaterialTheme.typography.bodySmall
                    )
                    if (info != null) {
                        Text("Costos reales disponibles en la base de datos: ${info.reales_disponibles}")
                    }
                    Button(
                        onClick = { vm.reentrenarModelo() },
                        enabled = !state.isLoading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (state.isLoading) "Entrenando..." else "Reentrenar modelo")
                    }
                }
            }
        }
    }
}

@Composable
fun AdminUsuariosTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(state.usuariosAdmin) { u ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.padding(12.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(u.nombre, style = MaterialTheme.typography.titleSmall)
                        Text(u.email, style = MaterialTheme.typography.bodySmall)
                        Text("Rol actual: ${u.rol.uppercase()}", style = MaterialTheme.typography.labelMedium)
                    }
                    if (u.rol == "cliente") {
                        Button(onClick = { vm.promoverUsuario(u.id) }) {
                            Text("Hacer Admin")
                        }
                    }
                }
            }
        }
    }
}
