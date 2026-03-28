"""
EXPORTADOR JSON PARA N8N
========================
Lee el Excel generado por aging_generator.py y exporta
cartera_pendiente.json listo para consumir desde n8n.

Uso en aging_generator.py — agregar al final:
    import exportar_json as ExJ
    ExJ.exportar(df, cartera_pendiente)
"""

import json
import pandas as pd


def exportar(df: pd.DataFrame, cartera_pendiente: pd.DataFrame, 
             output_path: str = "cartera_pendiente.json") -> None:
    """
    Genera cartera_pendiente.json con el tramo más urgente por cliente.
    
    Args:
        df: DataFrame completo de aging (con estado y tramo)
        cartera_pendiente: DataFrame filtrado solo clientes pendientes
        output_path: Ruta de salida del JSON
    """

    # Tramo más urgente por cliente (el de mayor días vencidos)
    orden_tramo = {"+90 días": 0, "61–90 días": 1, "31–60 días": 2, "0–30 días": 3}

    pendientes_df = df[df["estado"] == "Pendiente"].copy()

    df_tramo = (
        pendientes_df
        .groupby("id_cliente")["tramo"]
        .apply(lambda x: sorted(x.dropna(), key=lambda t: orden_tramo.get(t, 99))[0]
               if len(x.dropna()) > 0 else "—")
        .reset_index()
    )
    df_tramo.columns = ["id_cliente", "tramo_principal"]

    # Acción sugerida más urgente por cliente (desde df detalle)
    df_accion = (
        pendientes_df
        .groupby("id_cliente")["accion_sugerida"]
        .first()
        .reset_index()
    )

    # Merge con cartera
    resultado = cartera_pendiente.merge(df_tramo, on="id_cliente", how="left")
    resultado = resultado.merge(df_accion, on="id_cliente", how="left")

    # Seleccionar solo columnas necesarias para n8n
    columnas = [
        "id_cliente",
        "cliente",
        "score",
        "categoria_scoring",
        "monto_pendiente",
        "facturas_pendientes",
        "dias_max_vencidos",
        "tramo_principal",
        "accion_sugerida",
    ]

    output = resultado[columnas].to_dict(orient="records")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"✓ JSON exportado: {output_path} ({len(output)} clientes)")
    import subprocess
    import os    
subprocess.Popen(
    ["python", "-m", "http.server", "8000"],
    cwd=os.path.dirname(os.path.abspath(output_path))
)
print("✓ Servidor HTTP levantado en puerto 8000")