-- ============================================================================
-- DEMOSTRACIÓN: insertar registros INVÁLIDOS directamente en MySQL.
-- Después de ejecutarlo, la API NO debe mostrarlos (rutas de usuarios, cotizaciones
-- y estadísticas) y las consultas individuales deben dar un error controlado.
-- Requiere haber ejecutado backend/sembrar_datos_prueba.py (cliente1@eventquote.com).
-- Para borrarlos: ejecuta limpiar_registros_invalidos.sql
-- ============================================================================
USE eventquote_db;

-- 1) Usuario con correo inválido y hash falso
INSERT INTO usuarios (nombre, email, password_hash, rol)
VALUES ('PRUEBA INVALIDA', 'correo-invalido', 'hash-falso', 'cliente');

-- 2) Evento con invitados NEGATIVOS y ciudad inexistente + su cotización
INSERT INTO eventos (cliente_id, tipo, invitados, horas, ciudad)
VALUES ((SELECT id FROM usuarios WHERE email = 'cliente1@eventquote.com'), 'boda', -5, 5, 'PRUEBA-INVALIDA');

INSERT INTO cotizaciones (evento_id, costo_estimado, modelo_version)
VALUES ((SELECT id FROM eventos WHERE ciudad = 'PRUEBA-INVALIDA' LIMIT 1), 99999, 'v1');

-- 3) Evento con 99 horas (fuera de rango 1-24) + cotización con costo NEGATIVO
INSERT INTO eventos (cliente_id, tipo, invitados, horas, ciudad)
VALUES ((SELECT id FROM usuarios WHERE email = 'cliente1@eventquote.com'), 'xv', 100, 99.0, 'Queretaro');

INSERT INTO cotizaciones (evento_id, costo_estimado, modelo_version)
VALUES ((SELECT MAX(id) FROM eventos), -500, 'v1');

SELECT 'Registros inválidos insertados. Consulta ahora la API/app: no deben aparecer.' AS mensaje;
