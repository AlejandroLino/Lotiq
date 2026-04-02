# LOTIQ — Decision Intelligence para Inversión Inmobiliaria

## Qué es este proyecto
Plataforma de análisis de inversión inmobiliaria para AMBA (CABA + Gran Buenos Aires hasta 2do cordón) y Gran La Plata (City Bell, Gonnet, Villa Elisa).
Caso base: inversor con USD 200k busca terreno → responde dónde, qué construir, costo/margen, proyección 3-5 años.
Diferencial: combina análisis de mercado + viabilidad arquitectónica (BIM).

Fases producto: 1) Herramienta propia → 2) Portfolio profesional → 3) Producto vendible.

**LOTIQ es un proyecto separado de PropTech CABA** (que es el de Tableau/dashboards).
LOTIQ apunta a AMBA completo + La Plata y es la evolución con data engineering serio.

---

## Fases geográficas

| Fase | Alcance | Estado |
|---|---|---|
| **Fase 1** | CABA — 48 barrios, 168 subzonas | ✅ Completada (5 capas + exports) |
| **Fase 2** | Primer cordón GBA — Lomas de Zamora, Lanús, Avellaneda, La Matanza (zona E), Tres de Febrero, San Martín, Vicente López, San Isidro | 🔜 Próximo |
| **Fase 3** | Segundo cordón GBA + Gran La Plata — Morón, Merlo, Quilmes, Berazategui, Tigre, Pilar, City Bell, Gonnet, Villa Elisa | 🔜 Futuro |

> **Datos por fase:** cada fase agrega su propio GeoJSON de polígonos, datos censales (INDEC 2022 radios censales), normativa (código urbano municipal), y datos de mercado (ZonaProp/Argenprop por partido).

---

## Stack técnico

| Capa | Herramientas |
|---|---|
| Lenguaje | Python 3.11+ (Anaconda) |
| Data | Pandas, NumPy, SciPy |
| Geo | GeoPandas 1.1.3, OSMnx 2.1.0, Shapely, Folium |
| ML | XGBoost, scikit-learn |
| GIS | QGIS (proyecto LOTIQ_v1), PostGIS (futuro) |
| DB | PostgreSQL + PostGIS (migración target) |
| Viz | Chart.js, Leaflet, Tableau, Matplotlib |
| Automatización | N8N |
| BIM | Revit, Dynamo |
| Web | Streamlit + FastAPI (futuro) |

---

## Estructura de carpetas

```
LOTIQ/
├── CLAUDE.md                          ← Este archivo
├── data/
│   ├── raw/                           ← NUNCA MODIFICAR - datos originales
│   │   ├── caba_48_barrios.geojson    ← Polígonos oficiales 48 barrios CABA
│   │   ├── subte_estaciones.geojson   ← 90 estaciones de subte
│   │   └── ...                        ← Otros datasets descargados
│   ├── processed/                     ← Datos limpios intermedios
│   └── output/                        ← Datos finales para visualización
├── notebooks/
│   ├── 01_base_barrios.ipynb          ← Carga y exploración GeoJSON barrios
│   ├── 02_extraccion_datos.ipynb      ← Descarga de datasets BA Data / OSM
│   ├── 03_transporte.ipynb            ← (próximo) Isócronas subte/tren
│   └── 04_pois.ipynb                  ← (próximo) POIs de OSM
├── src/                               ← Scripts Python reutilizables
├── geojson/                           ← GeoJSON procesados
├── csv/                               ← CSVs de salida
└── qgis/                              ← Proyecto QGIS
    └── LOTIQ_v1.qgs
```

> **IMPORTANTE:** Si la carpeta no tiene esta estructura todavía, crearla antes de empezar.
> Los archivos actuales pueden estar sueltos en la raíz — hay que organizarlos.

---

## Convenciones de código

```python
# Encoding para CSVs argentinos
df.to_csv('archivo.csv', encoding='utf-8-sig', sep=',', index=False)

# Lectura segura
df = pd.read_csv('archivo.csv', encoding='utf-8-sig')

# Tableau: exportar siempre como .xlsx (openpyxl, sin índice)
# El CSV queda como backup pero Tableau Public no parsea CSV correctamente en Windows
df.to_excel('data/output/TABLEAU_LOTIQ_MASTER.xlsx', index=False, engine='openpyxl')

# Fechas siempre ISO
fecha = '2026-03-15'  # YYYY-MM-DD

# Comentarios y docstrings en español
# Commits en español
# Prints de confirmación en cada paso
print(f"✓ Cargados {len(df)} registros")
```

### Reglas estrictas
1. **NUNCA** modificar archivos en `data/raw/`
2. **NUNCA** inventar datos — si falta información, indicar "dato no disponible"
3. **SIEMPRE** validar encoding antes de leer CSV
4. **SIEMPRE** verificar que CABA tiene exactamente **48 barrios oficiales** (Fase 1)
5. **EXCLUIR** sub-zonas comerciales de análisis: Abasto, Once, Congreso, Las Cañitas, Belgrano R
6. **SIEMPRE** usar seeded random o modelos determinísticos (nunca random puro para métricas económicas)

---

## Datos geográficos clave

### CABA: 48 barrios oficiales (Fase 1)
Fuente: `https://data.buenosaires.gob.ar/dataset/barrios`

### 168 subzonas PropTech (Fase 1)
Archivo: `168_subzonas_proptech.csv` y `.geojson`
Cada barrio se subdivide en ~3-4 subzonas para análisis granular.

### Estaciones de subte
Archivo: `subte_estaciones.geojson` (90 estaciones, 6 líneas: A, B, C, D, E, H)

---

## Capas de datos — Roadmap de implementación

### CAPA 1: Transporte (PRIORIDAD ALTA) ← EN PROGRESO
- Distancia a subte por subzona (metros + isócronas 5/10/15 min)
- Red ferroviaria
- Output: `dist_subte`, `subte_5min`, `subte_10min`, `linea_subte`
- Herramientas: OSMnx + GeoPandas

### CAPA 2: FOT/FOS por parcela (VENTAJA DIFERENCIAL)
- Metros edificables reales por lote
- Fuente: parcelas CABA + plancheta CUR | GBA: código urbano municipal
- Output: `fot_real`, `fos_real`, `m2_edif_real`

### CAPA 3: Densidad poblacional (CENSO 2022)
- Radios censales + join espacial
- Output: `poblacion`, `densidad`, `precio_por_hab`

### CAPA 4: POIs urbanos (OpenStreetMap)
- Query Overpass API: escuelas, hospitales, gastronomía, comercios
- Output: `escuelas`, `hospitales`, `gastronomia`, `comercios`, `idx_equipamiento`

### CAPA 5: Absorción de mercado
- Scraping periódico ZonaProp (pipeline N8N)
- Output: `absorcion_pct`, `dias_mercado`, `stock`

---

## Métricas inmobiliarias

| Métrica | Fórmula | Descripción |
|---|---|---|
| Precio/m² | `precio_publicado / superficie` | En USD |
| ROI | `(valor_futuro - inversion) / inversion × 100` | Retorno sobre inversión |
| Sharpe Ratio | `(roi_promedio - tasa_libre_riesgo) / desvio_roi` | Retorno ajustado por riesgo |
| Rentabilidad Bruta | `alquiler_anual / precio_compra × 100` | Yield bruto |
| Cap Rate | `NOI / precio_compra × 100` | Net Operating Income / Precio |
| VaR | Percentil 5 de distribución Monte Carlo | Pérdida máxima al 95% confianza |
| CVaR | Promedio de pérdidas peores que VaR | Expected Shortfall |
| Payback | `inversion / flujo_neto_anual` | Años para recuperar inversión |

### Categorías de precio (USD/m²)
- **Premium:** > $4,000
- **Medio:** $2,000 - $4,000
- **Económico:** < $2,000

### Escenarios de simulación
- Pesimista, Base, Moderado, Optimista

---

## Fuentes de datos

| Fuente | URL | Datos |
|---|---|---|
| BA Data | `data.buenosaires.gob.ar` | GeoJSON barrios CABA, subte, parcelas, etc. |
| INDEC | `indec.gob.ar` | Censo 2022, radios censales (CABA + GBA) |
| OpenStreetMap | Overpass API | POIs (escuelas, hospitales, etc.) |
| ZonaProp | Scraping | Precios publicados de propiedades |
| Argenprop | Scraping | Precios publicados |
| Bluelytics | API | Cotización dólar blue |
| CAC / APYMECO | Manual | Costo de construcción |
| CUR GCBA | Manual | Normativa urbanística CABA (FOT/FOS) |
| Códigos Urbanos GBA | Manual | Normativa por partido (Fase 2-3) |

---

## Comandos custom para Claude Code

### /status
Mostrar estado actual del proyecto: archivos existentes, capas completadas, siguiente paso.

### /check-data
Validar integridad de datos: encoding, cantidad de barrios (debe ser 48 para CABA), columnas esperadas, valores nulos.

### /procesar-capa [nombre]
Ejecutar el notebook correspondiente a una capa de datos (transporte, fot, censo, pois, absorcion).

### /generar-geojson
Unificar todas las capas procesadas en un GeoJSON master con todos los campos.

### /explorar [archivo]
Cargar un archivo y mostrar: shape, dtypes, head, describe, nulos.

---

## Contexto del desarrollador

- Arquitecto en último año + Semi-Senior Data Analyst
- Basado en Buenos Aires
- Conocimiento intermedio-avanzado de Python, Pandas, GIS
- Dominio de normativa urbanística CABA (CUR, FOT/FOS, alturas) y GBA
- Experiencia con BIM (Revit/Dynamo) — ventaja competitiva para viabilidad constructiva
- Comunicación en español, código comentado en español

---

## Principios de trabajo

1. **Precisión > Velocidad** — Verificar datos antes de avanzar
2. **"Error cero"** — Validar cada paso antes de pasar al siguiente
3. **Determinístico > Aleatorio** — Modelos con lógica económica, no random
4. **Datos reales > Estimaciones** — Siempre preferir fuentes oficiales
5. **Código reproducible** — Notebooks con prints de confirmación, try/except
6. **Green = favorable** — En mapas: verde = alto ROI/Score/Sharpe (bueno), rojo = bajo
