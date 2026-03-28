import pandas as pd
import random
import pyodbc

# ── Conexión SQL Server ──────────────────────────────────────────

# ── Extraer id_asiento de ventas ─────────────────────────────────
query = """
    SELECT DISTINCT ac.id_asiento, ac.fecha, ac.glosa
    FROM asientos_cabecera ac
    WHERE ac.tipo_asiento = 'Venta'
    ORDER BY ac.id_asiento
"""
df = pd.read_sql(query, conn)

# ── Pool de 60 clientes peruanos ficticios ───────────────────────
clientes = [
    "Distribuidora Los Andes S.A.C.",     "Exportaciones Pacífico E.I.R.L.",
    "Café Selva Norte S.R.L.",            "Granos del Sur S.A.C.",
    "Agrocom Perú S.A.C.",                "Importadora Lima Trading S.A.",
    "Comercial Huallaga E.I.R.L.",        "Distribuciones Arequipa S.R.L.",
    "Inversiones Cusco S.A.C.",           "Proveedores del Norte E.I.R.L.",
    "Alimentos del Valle S.A.C.",         "Corporación Inca Foods S.A.",
    "Distribuidora Majes S.R.L.",         "Agro Exportaciones Piura S.A.C.",
    "Comercial Trujillo E.I.R.L.",        "Inversiones Tacna S.A.C.",
    "Negocios Andinos S.R.L.",            "Distribuciones Puno E.I.R.L.",
    "Alimentos Chanchamayo S.A.C.",       "Exportadora Selva E.I.R.L.",
    "Comercializadora Iquitos S.A.C.",    "Distribuidora Huancayo S.R.L.",
    "Agro Productos Junín S.A.C.",        "Inversiones Loreto E.I.R.L.",
    "Comercial Cajamarca S.R.L.",         "Distribuidora Lambayeque S.A.C.",
    "Proveedores Ancash E.I.R.L.",        "Alimentos Pasco S.A.C.",
    "Exportaciones Madre de Dios S.R.L.", "Comercial Ucayali S.A.C.",
    "Distribuidora Apurímac E.I.R.L.",    "Inversiones Ayacucho S.R.L.",
    "Agro Negocios Huánuco S.A.C.",       "Comercial Tumbes E.I.R.L.",
    "Distribuciones Moquegua S.A.C.",     "Exportadora Ica S.R.L.",
    "Alimentos San Martín S.A.C.",        "Comercial Amazonas E.I.R.L.",
    "Distribuidora La Libertad S.R.L.",   "Inversiones Callao S.A.C.",
    "Agro Productos Moyobamba S.A.C.",    "Comercializadora Tingo María E.I.R.L.",
    "Distribuciones Yurimaguas S.R.L.",   "Exportaciones Bagua S.A.C.",
    "Alimentos Tarapoto S.A.C.",          "Comercial Huaraz E.I.R.L.",
    "Distribuidora Sullana S.R.L.",       "Inversiones Chimbote S.A.C.",
    "Agro Exportaciones Chiclayo S.A.C.", "Comercial Abancay E.I.R.L.",
    "Distribuciones Juliaca S.R.L.",      "Exportadora Pucallpa S.A.C.",
    "Alimentos Huancavelica E.I.R.L.",    "Comercial Chachapoyas S.R.L.",
    "Distribuidora Paita S.A.C.",         "Inversiones Talara E.I.R.L.",
    "Agro Productos Zarumilla S.A.C.",    "Comercializadora Ilave E.I.R.L.",
    "Distribuciones Desaguadero S.R.L.",  "Exportaciones Toquepala S.A.C.",
]

# ── Asignar cliente aleatorio a cada id_asiento (seed fijo = reproducible) ──
random.seed(42)
df["id_cliente"] = [f"CLI-{str(i+1).zfill(4)}" for i in range(len(df))]
df["nombre_cliente"] = [random.choice(clientes) for _ in range(len(df))]

# Extraer número de factura de la glosa
df["nro_factura"] = df["glosa"].str.extract(r"(2026-\d{2}-V\d+|2025-\d{2}-V\d+)")

# ── Crear tabla en SQL Server ─────────────────────────────────────
cursor = conn.cursor()

cursor.execute("""
    IF OBJECT_ID('Clientes_Facturas', 'U') IS NOT NULL
        DROP TABLE Clientes_Facturas
    
    CREATE TABLE Clientes_Facturas (
        id_cliente   VARCHAR(10)  NOT NULL,
        nombre       VARCHAR(100) NOT NULL,
        id_asiento   INT          NOT NULL,
        nro_factura  VARCHAR(30),
        fecha        DATE,
        PRIMARY KEY (id_asiento)
    )
""")

# ── Insertar registros ────────────────────────────────────────────
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO Clientes_Facturas (id_cliente, nombre, id_asiento, nro_factura, fecha)
        VALUES (?, ?, ?, ?, ?)
    """, row["id_cliente"], row["nombre_cliente"], row["id_asiento"], 
         row["nro_factura"], row["fecha"])

conn.commit()
cursor.close()
conn.close()

print(f"✓ {len(df)} facturas insertadas con {df['nombre_cliente'].nunique()} clientes únicos")
df[["id_cliente","nombre_cliente","id_asiento","nro_factura","fecha"]].head(10)