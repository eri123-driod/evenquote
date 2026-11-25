# EventQuote — Cotizador Inteligente de Eventos

Aplicación móvil (Kotlin + Jetpack Compose) con backend FastAPI, base de datos MySQL y
**Machine Learning** que estima el costo de un evento. Proyecto del 3er parcial de Aplicaciones Móviles.

## Arquitectura

| Capa | Tecnología | Patrón | Dónde |
|---|---|---|---|
| Frontend móvil | Kotlin + Jetpack Compose + Retrofit + DataStore | **MVVM** | `android/` |
| Backend | FastAPI (Python) | **MC** (Modelo–Controlador) | `backend/app/` |
| Base de datos | MySQL | — | `database/schema.sql` |
| Funcionalidad integradora | **Machine Learning** (scikit-learn) | — | `backend/app/services/ml_service.py` |

**MVVM (Android):** `data/model` y `data/remote` + `data/local` = **Modelo** (datos y su acceso);
`ui/screens` = **Vista**; `ui/viewmodel` = **VistaModelo** (estado y validaciones de entrada).

**MC (Backend):** `app/models/schemas.py` = **Modelos** (estructura y reglas de validación);
`app/controllers/` = **Controladores** (rutas, permisos y respuestas); `app/core/` = configuración, BD y seguridad.

## Roles y seguridad
- **Cliente:** inicia sesión, cotiza eventos, consulta **solo** sus cotizaciones.
- **Administrador:** estadísticas (tablas + gráfica), cotizaciones y usuarios, promover clientes a admin,
  confirmar costos reales y reentrenar el modelo.
- Contraseñas con **Argon2id** (passlib); las respuestas nunca incluyen contraseñas ni hashes.
- JWT; el **rol se lee siempre de la BD** en cada petición. El registro rechaza cualquier campo `rol` (422).
- Toda entrada se valida con modelos Pydantic (también si viene de Postman/curl). Las ciudades, tipos y servicios son listas cerradas.
- **Datos leídos de MySQL también se validan** antes de responder: un registro inválido se **excluye** de listas,
  estadísticas y modelo ML; en una consulta individual devuelve un error controlado (409).
- Acceso a registros: un cliente no puede ver cotizaciones ajenas cambiando el id (404).
- Primer administrador: `python crear_admin.py` (usa las mismas reglas y el mismo hash que el resto del sistema).

## Machine Learning (Opción A)
- **Qué predice:** el costo estimado (MXN) de un evento.
- **Variables:** tipo de evento, ciudad, invitados, log(invitados), horas y 4 banderas de servicios (banquete, DJ, decoración, fotografía).
- **Datos:** dataset base documentado (25 eventos) **+ costos reales confirmados por el admin sobre eventos capturados por los clientes** (tabla `costos_confirmados`). Los registros inválidos se descartan.
- **Evaluación:** validación cruzada de 5 pliegues (MAE y R²). Se comparan varios modelos (Ridge sobre log-costo con distintos `alpha` y Random Forest) y se guarda el de menor MAE. Con el dataset base: **MAE ≈ $2,800 MXN y R² ≈ 0.99**.
- **Flujo completo:** cliente captura el evento → backend predice → se guarda en MySQL → admin confirma el costo real → admin pulsa **Reentrenar** (pestaña *Modelo ML*) → nueva versión (v2, v3…) con métricas visibles en la app.

## Puesta en marcha
### 1) MySQL
Abre MySQL Workbench (o XAMPP) y ejecuta `database/schema.sql`.

### 2) Backend (VS Code, carpeta `backend/`)
```bash
cd backend
copy .env.example .env        # y escribe tu contraseña de MySQL en DATABASE_URL
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python crear_admin.py                 # primer administrador (Enter x3 = admin@eventquote.com / Admin123!)
python sembrar_datos_prueba.py        # cuentas y datos de prueba
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Comprueba `http://localhost:8000/docs`. El modelo ML se entrena solo la primera vez que arranca el servidor.

### 3) App (Android Studio)
Abre la carpeta `android/` (la que contiene `settings.gradle.kts`), espera la sincronización y ejecuta.
- Emulador: `BASE_URL = "http://10.0.2.2:8000/"` (valor por defecto).
- Teléfono físico: cambia `BASE_URL` en `data/remote/ApiService.kt` por la IPv4 de tu PC (ej. `http://192.168.1.75:8000/`), mismo Wi-Fi, y permite el puerto 8000 en el firewall de Windows.

## Cuentas de prueba
| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@eventquote.com | Admin123! |
| Cliente | cliente1@eventquote.com | Cliente123! |
| Cliente | cliente2@eventquote.com | Cliente123! |

## Pruebas de la rúbrica
**Automáticas** (con el servidor encendido): `python pruebas/verificar_rubrica.py` — comprueba login, contraseña incorrecta,
permisos por rol, validación directa a la API, acceso a registros ajenos, promoción persistente, registros inválidos
insertados en MySQL, panel coherente y flujo ML.

**Manuales** (para el video): ver `GUION_VIDEO.md`. Registros inválidos en MySQL:
`database/pruebas_registros_invalidos.sql` (insertar) y `database/limpiar_registros_invalidos.sql` (borrar).
> La base de datos NO tiene restricciones CHECK a propósito: así se pueden insertar registros inválidos para demostrar que la API los excluye.

## Endpoints principales
`POST /auth/register` · `POST /auth/login` · `GET /auth/me` · `POST /cotizaciones/predecir` · `POST /cotizaciones` ·
`GET /cotizaciones/mias` · `GET /cotizaciones/{id}` · `GET /admin/estadisticas` · `GET /admin/cotizaciones` ·
`GET /admin/usuarios` · `GET /admin/usuarios/{id}` · `PATCH /admin/usuarios/{id}/promover` ·
`POST /admin/costos-confirmados` · `GET /admin/ml/info` · `POST /admin/ml/reentrenar`
