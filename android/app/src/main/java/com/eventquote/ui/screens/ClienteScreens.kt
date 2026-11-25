package com.eventquote.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.eventquote.ui.viewmodel.EventQuoteViewModel
import com.eventquote.util.fechaCorta
import com.eventquote.util.formatoMoneda

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClienteHomeScreen(
    vm: EventQuoteViewModel,
    onLogout: () -> Unit
) {
    val state by vm.state.collectAsState()
    var tabIndex by remember { mutableIntStateOf(0) }

    LaunchedEffect(Unit) { vm.cargarHistorialCliente() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Hola, ${state.currentUser?.nombre ?: "Cliente"}") },
                actions = {
                    TextButton(onClick = { vm.logout(onLogout) }) { Text("Salir") }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            TabRow(selectedTabIndex = tabIndex) {
                Tab(
                    selected = tabIndex == 0,
                    onClick = { tabIndex = 0; vm.limpiarMensajes() },
                    text = { Text("Cotizar Evento") }
                )
                Tab(
                    selected = tabIndex == 1,
                    onClick = { tabIndex = 1; vm.limpiarMensajes(); vm.cargarHistorialCliente() },
                    text = { Text("Mis Cotizaciones") }
                )
            }

            if (tabIndex == 0) {
                FormularioCotizacionTab(vm)
            } else {
                HistorialClienteTab(vm)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun FormularioCotizacionTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()
    var tipo by remember { mutableStateOf("boda") }
    var invitados by remember { mutableStateOf("120") }
    var horas by remember { mutableStateOf("5") }
    var ciudad by remember { mutableStateOf("Queretaro") }
    val servicios = remember { mutableStateListOf("banquete") }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Tipo de Evento", style = MaterialTheme.typography.titleSmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("boda", "xv", "cumpleanos", "corporativo").forEach { opcion ->
                    FilterChip(
                        selected = tipo == opcion,
                        onClick = { tipo = opcion },
                        label = { Text(opcion.uppercase()) }
                    )
                }
            }
        }

        item {
            OutlinedTextField(
                value = invitados,
                onValueChange = { invitados = it; vm.limpiarMensajes() },
                label = { Text("Número de Invitados (1 - 2000)") },
                singleLine = true,
                isError = state.erroresCampo["invitados"] != null,
                supportingText = { state.erroresCampo["invitados"]?.let { Text(it) } },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )
        }

        item {
            OutlinedTextField(
                value = horas,
                onValueChange = { horas = it; vm.limpiarMensajes() },
                label = { Text("Duración en Horas (1 - 24)") },
                singleLine = true,
                isError = state.erroresCampo["horas"] != null,
                supportingText = { state.erroresCampo["horas"]?.let { Text(it) } },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth()
            )
        }

        item {
            Text("Ciudad", style = MaterialTheme.typography.titleSmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Queretaro", "San Juan del Rio", "CDMX", "Guadalajara", "Monterrey").forEach { c ->
                    FilterChip(selected = ciudad == c, onClick = { ciudad = c }, label = { Text(c) })
                }
            }
        }

        item {
            Text("Servicios Incluidos", style = MaterialTheme.typography.titleSmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("banquete", "dj", "decoracion", "fotografia").forEach { srv ->
                    val active = servicios.contains(srv)
                    FilterChip(
                        selected = active,
                        onClick = { if (active) servicios.remove(srv) else servicios.add(srv) },
                        label = { Text(srv) }
                    )
                }
            }
        }

        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                state.mensajeExito?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
                Button(
                    onClick = { vm.cotizarYGuardar(tipo, invitados, horas, ciudad, servicios.toList()) },
                    enabled = !state.isLoading,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (state.isLoading) "Calculando con ML..." else "Obtener Cotización Estimada")
                }
            }
        }

        item {
            state.estimacionActual?.let { est ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Costo Estimado (${est.modelo_version})", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "${formatoMoneda(est.costo_estimado)} ${est.moneda}",
                            style = MaterialTheme.typography.headlineMedium
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "Nota: Presupuesto orientativo generado mediante regresión estadística.",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun HistorialClienteTab(vm: EventQuoteViewModel) {
    val state by vm.state.collectAsState()

    if (state.historialCliente.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize().padding(24.dp)) {
            Text(state.error ?: "Aún no tienes cotizaciones registradas.")
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        items(state.historialCliente) { cot ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${cot.tipo.uppercase()} - ${cot.ciudad}", style = MaterialTheme.typography.titleMedium)
                        Text(formatoMoneda(cot.costo_estimado), style = MaterialTheme.typography.titleMedium)
                    }
                    Text("${cot.invitados} invitados | ${cot.horas} hrs")
                    Text("Fecha: ${fechaCorta(cot.fecha)}", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
