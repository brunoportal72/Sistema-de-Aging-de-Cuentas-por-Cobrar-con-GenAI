# Sistema de Aging de Cuentas por Cobrar con GenAI
### Accounts Receivable Aging System with GenAI

> **Comercial Andina S.A.C.** — Distribuidora peruana de café (empresa ficticia)  
> Stack: `SQL Server` · `Python` · `Power BI` · `n8n` · `Groq API` · `Excel`

---

## ¿Qué resuelve? / What does it solve?

Las empresas peruanas gestionan sus cuentas por cobrar en Excel sin inteligencia. Este sistema automatiza la clasificación, scoring crediticio y comunicación de cobranza usando IA generativa.

*Peruvian companies manage accounts receivable in plain Excel with no intelligence. This system automates classification, credit scoring, and collection communication using generative AI.*

---

## Arquitectura / Architecture

```
SQL Server (asientos contables)
      │
      ▼
aging_generator.py
  ├── Calcula vencimientos y tramos de aging
  ├── Asigna estado de pago (Pagado / Pendiente)
  └── scoring_bancario.py → score crediticio 0–100
      │
      ▼
Excel (3 hojas)          JSON (cartera_pendiente.json)
  ├── Aging Detalle            │
  ├── Resumen General          ▼
  └── Cartera Pendiente     n8n Workflow
      │                       ├── Lee JSON
      ▼                       ├── Groq API → genera email personalizado
Power BI Dashboard             └── Gmail → envío automático
  ├── Dashboard general
  └── Drillthrough por cliente
```

---

## Stack tecnológico / Tech stack

| Capa | Herramienta | Rol |
|---|---|---|
| Base de datos | SQL Server Express | Asientos contables reales |
| Procesamiento | Python 3.13 + pandas | Pipeline de aging y scoring |
| Visualización | Power BI Desktop | Dashboard gerencial interactivo |
| Automatización | n8n (Docker) | Orquestación del flujo de emails |
| IA Generativa | Groq API (Llama 3.3) | Redacción de emails de cobranza |
| Exportación | openpyxl | Formato Excel profesional |

---

## Scoring crediticio / Credit scoring

El módulo `scoring_bancario.py` evalúa a cada cliente en escala 0–100 con 4 factores de riesgo puro:

*The `scoring_bancario.py` module evaluates each client on a 0–100 scale using 4 pure risk factors:*

| Factor | Peso | Lógica |
|---|---|---|
| Historial de pagos | 40% | % pagado sobre facturas **exigibles** únicamente (excluye facturas aún no vencidas) |
| Días vencidos promedio | 25% | Escala continua: `100 × max(0, 1 − días/180)` — sin saltos artificiales |
| Rotación / Estabilidad | 20% | N° de facturas como proxy de antigüedad comercial |
| Tendencia reciente | 15% | Últimos 30 días, mínimo 3 facturas para ser estadísticamente válido |

**Decisión de diseño clave:** el volumen (monto facturado) no forma parte del score de riesgo. Un cliente grande que no paga es igual de riesgoso que uno pequeño que no paga.

*Key design decision: volume (invoice amount) is not part of the risk score. A large client that doesn't pay is just as risky as a small one.*

| Score | Categoría |
|---|---|
| 85 – 100 | Excelente |
| 70 – 84 | Bueno |
| 55 – 69 | Aceptable |
| 40 – 54 | Riesgo |
| < 40 | Alto Riesgo |

---

## Archivos del proyecto / Project files

```
├── aging_generator.py       # Pipeline principal
├── scoring_bancario.py      # Módulo de scoring crediticio
├── exportar_json.py         # Exporta cartera pendiente para n8n
├── sql_client_generator.py  # Generador de clientes ficticios (setup)
└── scoring_diagnostico.py   # Script de diagnóstico (desarrollo)
```

---

## Instalación / Setup

```bash
pip install pandas numpy pyodbc openpyxl
```

Requiere SQL Server con base de datos `ComercialAndina` y tabla `Clientes_Facturas`.  
*Requires SQL Server with `ComercialAndina` database and `Clientes_Facturas` table.*

```bash
python aging_generator.py
```

Genera `aging_comercial_andina.xlsx` y `cartera_pendiente.json`.

---

## Roadmap

| Fase | Estado | Descripción |
|---|---|---|
| 1 — MVP | ✅ Completo | Aging + Scoring + Excel + Power BI + Emails automáticos |
| 2 — Pagos reales | ⏳ Pendiente | Tabla `Pagos` en SQL Server, reemplaza estado simulado |
| 3 — Web App | ⏳ Pendiente | Frontend React + Supabase, CRUD de facturas y clientes |
| 4 — ML | ⏳ Pendiente | Predicción de defaults con históricos reales |

---

## Autor / Author

**Bruno Portal** — Estudiante de Contabilidad, ISIL Lima  
Data Analytics · Automatización · FinTech  
[LinkedIn](https://linkedin.com/in/brunoportal72) · [GitHub](https://github.com/brunoportal72)
