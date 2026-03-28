"""
MÓDULO DE SCORING BANCARIO v3.0 - VERSIÓN DEFINITIVA
=====================================================
Sistema de evaluación de riesgo crediticio — ComercialAndina

COMPONENTES DEL SCORE (4 factores puros de riesgo):
┌─────────────────────────┬────────┬─────────────────────────────────────────────┐
│ Factor                  │  Peso  │ Lógica                                      │
├─────────────────────────┼────────┼─────────────────────────────────────────────┤
│ 1. Historial de Pagos   │  40%   │ % pagado sobre facturas EXIGIBLES (≠ nuevas)│
│ 2. Días Vencidos Prom.  │  25%   │ Promedio días vencidos, escala CONTINUA     │
│ 3. Rotación / Estabilid.│  20%   │ N° de facturas = antigüedad de relación     │
│ 4. Tendencia Reciente   │  15%   │ Últimos 30 días, mínimo 3 facturas p/fiable │
└─────────────────────────┴────────┴─────────────────────────────────────────────┘

NOTA DISEÑO: El volumen (monto facturado) NO forma parte del score de riesgo.
Un cliente grande que paga mal es igual de riesgoso que uno pequeño que paga mal.
El volumen se usa en aging_generator.py solo como criterio de PRIORIZACIÓN de cobranza.

RANGO REAL DE SALIDA: ~20 (mínimo absoluto) — 100 (perfecto)
CATEGORÍAS:
  Excelente   : 85+
  Bueno       : 70 – 84
  Aceptable   : 55 – 69
  Riesgo      : 40 – 54
  Alto Riesgo : < 40

FASE 1 (MVP): Estado de pago estimado hasta que exista tabla Pagos en SQL (Fase 2).
El scoring es internamente coherente; se recalibrará con datos reales en Fase 2.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class ScoringBancario:

    def __init__(self, fecha_hoy=None, debug=False):
        self.fecha_hoy = fecha_hoy or date.today()
        self.debug     = debug
        self.pesos = {
            "historial_pagos": 0.40,
            "dias_vencidos":   0.25,
            "rotacion":        0.20,
            "tendencia":       0.15,
        }

    # ══════════════════════════════════════════════════════════════
    # ENTRY POINT
    # ══════════════════════════════════════════════════════════════

    def calcular_scoring_cliente(self, id_cliente, facturas_cliente):
        if len(facturas_cliente) == 0:
            return {"score_total": 0, "categoria": "Sin Datos", "detalles": {}}

        s_historial = self._calcular_historial_pagos(facturas_cliente)
        s_dias      = self._calcular_dias_vencidos(facturas_cliente)
        s_rotacion  = self._calcular_rotacion(facturas_cliente)
        s_tendencia = self._calcular_tendencia(facturas_cliente)

        score_total = (
            s_historial * self.pesos["historial_pagos"] +
            s_dias      * self.pesos["dias_vencidos"]   +
            s_rotacion  * self.pesos["rotacion"]        +
            s_tendencia * self.pesos["tendencia"]
        )
        score_total = round(max(20.0, min(100.0, score_total)), 1)
        categoria   = self._asignar_categoria(score_total)

        if self.debug:
            nombre = (
                facturas_cliente["cliente"].iloc[0]
                if "cliente" in facturas_cliente.columns
                else str(id_cliente)
            )
            n_total     = len(facturas_cliente)
            n_pagadas   = (facturas_cliente["estado"] == "Pagado").sum()
            n_pendiente = (facturas_cliente["estado"] == "Pendiente").sum()
            logger.info(
                f"\n🔍 {id_cliente} | {nombre}\n"
                f"   Facturas: {n_total} total | {n_pagadas} pagadas | {n_pendiente} pendientes\n"
                f"   Historial Pagos  (40%) : {s_historial:6.1f}\n"
                f"   Días Vencidos    (25%) : {s_dias:6.1f}\n"
                f"   Rotación         (20%) : {s_rotacion:6.1f}\n"
                f"   Tendencia        (15%) : {s_tendencia:6.1f}\n"
                f"   ➜ SCORE TOTAL         : {score_total:6.1f}  [{categoria}]"
            )

        return {
            "score_total": score_total,
            "categoria":   categoria,
            "detalles": {
                "historial_pagos": round(s_historial, 1),
                "dias_vencidos":   round(s_dias, 1),
                "rotacion":        round(s_rotacion, 1),
                "tendencia":       round(s_tendencia, 1),
            },
        }

    # ══════════════════════════════════════════════════════════════
    # COMPONENTE 1 — HISTORIAL DE PAGOS (40%)
    # ══════════════════════════════════════════════════════════════

    def _calcular_historial_pagos(self, facturas):
        """
        % de facturas pagadas sobre el universo EXIGIBLE únicamente.

        Exigible = facturas que ya debieron haberse pagado:
          - estado == "Pagado"       → pagó (cuenta positivo)
          - dias_vencidos > 0        → debió pagar y no ha pagado (cuenta negativo)

        NO exigible = facturas recién emitidas (dias_vencidos == 0, Pendiente):
          → Cliente nuevo que aún no tuvo oportunidad de pagar.
          → Incluirlas distorsionaría el score hacia abajo injustamente.

        Resultado: cliente nuevo sin historial exigible → 100 pts por default.
        Escala continua 0–100 (sin escalones).
        """
        exigibles = facturas[
            (facturas["estado"] == "Pagado") | (facturas["dias_vencidos"] > 0)
        ]

        if len(exigibles) == 0:
            return 100.0  # Sin deuda exigible = historial perfecto

        pagadas = (exigibles["estado"] == "Pagado").sum()
        pct = (pagadas / len(exigibles)) * 100  # 0–100, escala continua

        return pct

    # ══════════════════════════════════════════════════════════════
    # COMPONENTE 2 — DÍAS VENCIDOS PROMEDIO (25%)
    # ══════════════════════════════════════════════════════════════

    def _calcular_dias_vencidos(self, facturas):
        """
        Promedio de días vencidos sobre facturas PENDIENTES.

        Escala CONTINUA (no escalones) para evitar saltos absurdos:
          Fórmula: score = 100 * max(0, 1 - dias_promedio / 180)

          0 días   → 100 pts
          45 días  →  75 pts
          90 días  →  50 pts
          135 días →  25 pts
          180 días →   0 pts (clampeado a 0)

        Sin deuda pendiente → 100 (está completamente al día).
        """
        pendientes = facturas[facturas["estado"] == "Pendiente"]

        if len(pendientes) == 0:
            return 100.0

        dias_promedio = pendientes["dias_vencidos"].mean()
        score = 100.0 * max(0.0, 1.0 - dias_promedio / 180.0)

        return score

    # ══════════════════════════════════════════════════════════════
    # COMPONENTE 3 — ROTACIÓN / ESTABILIDAD (20%)
    # ══════════════════════════════════════════════════════════════

    def _calcular_rotacion(self, facturas):
        """
        Número de facturas como proxy de estabilidad y antigüedad comercial.

        DECISIÓN DE DISEÑO: Se usa conteo de facturas, NO monto facturado.
        Razón: el monto es valor comercial, no indicador de riesgo crediticio.
        Un cliente grande que no paga es igual de riesgoso que uno pequeño.
        El monto se usa por separado como criterio de priorización de cobranza.

        Escala escalonada (aquí sí aplica, es un ordinal discreto):
          ≥ 15 facturas → 100   (cliente consolidado)
          10–14         →  90
           7–9          →  80
           5–6          →  70
           3–4          →  55
           2            →  40
           1            →  25
        """
        n = len(facturas)
        if n >= 15: return 100.0
        if n >= 10: return 90.0
        if n >= 7:  return 80.0
        if n >= 5:  return 70.0
        if n >= 3:  return 55.0
        if n >= 2:  return 40.0
        return 25.0

    # ══════════════════════════════════════════════════════════════
    # COMPONENTE 4 — TENDENCIA RECIENTE (15%)
    # ══════════════════════════════════════════════════════════════

    def _calcular_tendencia(self, facturas):
        """
        Comportamiento de pago en los últimos 30 días.

        REGLA CRÍTICA — Mínimo 3 facturas recientes:
          Con menos de 3 facturas en el período, la tendencia no es
          estadísticamente fiable. Casos patológicos sin este piso:
            · 1 factura pagada   → tendencia = 100 (sobreoptimista)
            · 1 factura pendiente → tendencia = 0   (castigo injusto)
          → Con < 3 facturas recientes: devuelve neutral (70 pts).

        Sin actividad reciente (0 facturas) → neutral (70 pts).
        Escala continua: % pagadas en últimos 30 días → 0–100.
        """
        fecha_hace_30 = pd.Timestamp(self.fecha_hoy) - pd.Timedelta(days=30)
        recientes = facturas[
            pd.to_datetime(facturas["fecha_emision"]) >= fecha_hace_30
        ]

        # Sin datos o muestra insuficiente → puntaje neutral
        if len(recientes) < 3:
            return 70.0

        pagadas_recientes = (recientes["estado"] == "Pagado").sum()
        pct = (pagadas_recientes / len(recientes)) * 100  # 0–100

        return pct

    # ══════════════════════════════════════════════════════════════
    # CATEGORIZACIÓN
    # ══════════════════════════════════════════════════════════════

    def _asignar_categoria(self, score):
        if score >= 85: return "Excelente"
        if score >= 70: return "Bueno"
        if score >= 55: return "Aceptable"
        if score >= 40: return "Riesgo"
        return "Alto Riesgo"

    # ══════════════════════════════════════════════════════════════
    # BATCH — aplica scoring a todo el DataFrame
    # ══════════════════════════════════════════════════════════════

    def aplicar_scoring_dataframe(self, df):
        """
        Agrupa por id_cliente, calcula score de cada uno.
        Retorna DataFrame con: id_cliente | score | categoria_scoring
        """
        scores = []
        for id_cliente, grupo in df.groupby("id_cliente"):
            resultado = self.calcular_scoring_cliente(id_cliente, grupo)
            scores.append({
                "id_cliente":        id_cliente,
                "score":             resultado["score_total"],
                "categoria_scoring": resultado["categoria"],
            })
        return pd.DataFrame(scores)