CREATE DATABASE IF NOT EXISTS eventquote_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE eventquote_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('cliente', 'admin') NOT NULL DEFAULT 'cliente',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS servicios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL
);

INSERT IGNORE INTO servicios (codigo, nombre) VALUES
('banquete', 'Banquete y Catering'),
('dj', 'Música y DJ'),
('decoracion', 'Decoración y Ambientación'),
('fotografia', 'Fotografía y Video');

CREATE TABLE IF NOT EXISTS eventos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    tipo ENUM('boda', 'xv', 'cumpleanos', 'corporativo') NOT NULL,
    invitados INT NOT NULL,
    horas DECIMAL(4,1) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    fecha DATE NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evento_servicios (
    evento_id INT NOT NULL,
    servicio_id INT NOT NULL,
    PRIMARY KEY (evento_id, servicio_id),
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
    FOREIGN KEY (servicio_id) REFERENCES servicios(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evento_id INT NOT NULL,
    costo_estimado DECIMAL(12,2) NOT NULL,
    modelo_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS costos_confirmados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evento_id INT NOT NULL UNIQUE,
    costo_real DECIMAL(12,2) NOT NULL,
    fuente VARCHAR(150) NOT NULL,
    validado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
);
