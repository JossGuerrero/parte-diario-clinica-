#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 1: CREATE DATABASE FROM ZERO
Elimina todo y crea estructura profesional limpia
"""

import psycopg2
from datetime import datetime

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

def log(msg, end="\n"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", end=end)

print("\n" + "="*80)
print("🚀 PASO 1: CREAR BD DESDE CERO")
print("="*80 + "\n")

try:
    pc = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, 
                         user=PG_USER, password=PG_PASS)
    cur = pc.cursor()
    
    # DROP TODO
    log("🗑️  Eliminando tablas existentes...")
    cur.execute("""
        DROP TABLE IF EXISTS atencion CASCADE;
        DROP TABLE IF EXISTS medico CASCADE;
        DROP TABLE IF EXISTS paciente CASCADE;
        DROP TABLE IF EXISTS institucion CASCADE;
        DROP TABLE IF EXISTS tipo_consulta CASCADE;
        DROP TABLE IF EXISTS cie10 CASCADE;
    """)
    pc.commit()
    log("✓ Limpizado\n")
    
    # CREAR TABLAS
    log("🏗️  Creando estructura...\n")
    
    # 1. INSTITUCION
    log("   📍 institucion...", end=" ")
    cur.execute("""
        CREATE TABLE institucion (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL UNIQUE,
            codigo VARCHAR(50),
            activo BOOLEAN DEFAULT true,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_institucion_nombre ON institucion(nombre);
    """)
    pc.commit()
    log("✓")
    
    # 2. MEDICO
    log("   👨‍⚕️  medico...", end=" ")
    cur.execute("""
        CREATE TABLE medico (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL UNIQUE,
            especialidad VARCHAR(100),
            cedula VARCHAR(20),
            activo BOOLEAN DEFAULT true,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_medico_nombre ON medico(nombre);
    """)
    pc.commit()
    log("✓")
    
    # 3. PACIENTE
    log("   👥 paciente...", end=" ")
    cur.execute("""
        CREATE TABLE paciente (
            id SERIAL PRIMARY KEY,
            cedula VARCHAR(20) NOT NULL UNIQUE,
            nombre VARCHAR(150) NOT NULL,
            fecha_nacimiento DATE,
            genero VARCHAR(10),
            activo BOOLEAN DEFAULT true,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_paciente_cedula ON paciente(cedula);
        CREATE INDEX idx_paciente_nombre ON paciente(nombre);
    """)
    pc.commit()
    log("✓")
    
    # 4. TIPO_CONSULTA
    log("   📋 tipo_consulta...", end=" ")
    cur.execute("""
        CREATE TABLE tipo_consulta (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL UNIQUE,
            valor_base NUMERIC(10,2) DEFAULT 0,
            activo BOOLEAN DEFAULT true
        );
        CREATE INDEX idx_tipo_consulta_nombre ON tipo_consulta(nombre);
    """)
    pc.commit()
    log("✓")
    
    # 5. CIE10
    log("   🔬 cie10...", end=" ")
    cur.execute("""
        CREATE TABLE cie10 (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(10) NOT NULL UNIQUE,
            descripcion VARCHAR(255),
            activo BOOLEAN DEFAULT true
        );
        CREATE INDEX idx_cie10_codigo ON cie10(codigo);
    """)
    pc.commit()
    log("✓")
    
    # 6. ATENCION (PRINCIPAL)
    log("   🏥 atencion...", end=" ")
    cur.execute("""
        CREATE TABLE atencion (
            id SERIAL PRIMARY KEY,
            idts_access VARCHAR(50) NOT NULL UNIQUE,
            fecha_atencion DATE NOT NULL,
            paciente_id INTEGER REFERENCES paciente(id) ON DELETE SET NULL,
            medico_id INTEGER REFERENCES medico(id) ON DELETE SET NULL,
            cie10_id INTEGER REFERENCES cie10(id) ON DELETE SET NULL,
            tipo_consulta_id INTEGER REFERENCES tipo_consulta(id) ON DELETE SET NULL,
            institucion_id INTEGER REFERENCES institucion(id) ON DELETE SET NULL,
            numero_factura VARCHAR(50),
            valor_consulta NUMERIC(10,2) DEFAULT 0,
            edad INTEGER,
            genero VARCHAR(10),
            observaciones VARCHAR(500),
            total_consulta NUMERIC(10,2) DEFAULT 0,
            total_general NUMERIC(10,2) DEFAULT 0,
            activo BOOLEAN DEFAULT true,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_atencion_fecha ON atencion(fecha_atencion);
        CREATE INDEX idx_atencion_paciente ON atencion(paciente_id);
        CREATE INDEX idx_atencion_medico ON atencion(medico_id);
        CREATE INDEX idx_atencion_institucion ON atencion(institucion_id);
    """)
    pc.commit()
    log("✓")
    
    print("\n" + "="*80)
    print("✅ BASE CREADA - LISTO PARA MIGRACIÓN")
    print("="*80 + "\n")
    
    pc.close()

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()