-- Borra los registros inválidos creados por pruebas_registros_invalidos.sql
USE eventquote_db;
SET SQL_SAFE_UPDATES = 0;

DELETE FROM usuarios WHERE nombre = 'PRUEBA INVALIDA';
DELETE FROM eventos WHERE ciudad = 'PRUEBA-INVALIDA' OR horas > 24 OR invitados < 1;
DELETE FROM cotizaciones WHERE costo_estimado <= 0;

SET SQL_SAFE_UPDATES = 1;
SELECT 'Registros inválidos eliminados.' AS mensaje;
