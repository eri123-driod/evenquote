# Guion del video (muestra la app, no el código)

Antes de grabar: MySQL y uvicorn encendidos, `python sembrar_datos_prueba.py` ejecutado, app abierta en el teléfono.

| # | Qué mostrar | Qué decir / resultado esperado |
|---|---|---|
| 1 | Login como **cliente** (cliente1@eventquote.com / Cliente123!) | Entra a la pantalla de cliente |
| 2 | Cerrar sesión y probar **contraseña incorrecta** | Mensaje "Correo o contraseña incorrectos" |
| 3 | **Formulario inválido**: invitados 5000 u horas 99 | La app marca el campo en rojo y no envía |
| 4 | **Cotizar** un evento válido | Aparece el costo estimado (ML) y se guarda |
| 5 | Pestaña **Mis Cotizaciones**; cerrar y abrir la app | Historial visible y sesión conservada |
| 6 | Login como **admin** (admin@eventquote.com / Admin123!) | Panel con tabla por cliente y gráfica por tipo |
| 7 | Pestaña **Usuarios**: registrar antes un cliente nuevo y **Hacer Admin** | Mensaje de éxito |
| 8 | Cerrar sesión, entrar con el usuario promovido | Ve el panel administrativo (el cambio persistió) |
| 9 | Pestaña **Cotizaciones** → *Confirmar costo real*; luego **Modelo ML → Reentrenar** | Nueva versión (v2…), MAE y R² visibles |
| 10 | Nueva cotización de cliente | Usa la versión nueva del modelo |
| 11 | En **Swagger** (`/docs`) o Postman: POST /cotizaciones con `invitados: -5` | 422, y el dato no se guarda |
| 12 | En Swagger entrar con token de cliente y probar `/admin/usuarios` | 403 Acceso denegado |
| 13 | En MySQL Workbench ejecutar `pruebas_registros_invalidos.sql` | Registros inválidos insertados |
| 14 | Refrescar el panel admin y *Mis cotizaciones* | Los registros inválidos **no aparecen**; totales coherentes |
| 15 | (Opcional) terminal: `python pruebas/verificar_rubrica.py` | Todas las pruebas en OK |

Al terminar: ejecuta `limpiar_registros_invalidos.sql`.
