# CHANGELOG — LOTIQ

---

## 2026-03-22 — Rebranding CABATECH → LOTIQ

### Cambios aplicados
- **Nombre:** CABATECH → LOTIQ (Lote + IQ)
- **Alcance expandido:** CABA solamente → AMBA hasta 2do cordón + Gran La Plata (City Bell, Gonnet, Villa Elisa)
- **CLAUDE.md:** todas las referencias actualizadas, sección "Fases geográficas" agregada
- **Archivos renombrados:**
  - `TABLEAU_CABATECH_MASTER.csv` → `TABLEAU_LOTIQ_MASTER.csv`
  - `POWERBI_CABATECH_MASTER.xlsx` → `POWERBI_LOTIQ_MASTER.xlsx`

### Fases geográficas definidas
| Fase | Alcance | Estado |
|---|---|---|
| Fase 1 | CABA — 48 barrios, 168 subzonas | ✅ Completada |
| Fase 2 | Primer cordón GBA | 🔜 Próximo |
| Fase 3 | Segundo cordón GBA + Gran La Plata | 🔜 Futuro |

### Estado al momento del rebranding
- 5 capas de datos integradas (transporte, FOT/FOS, densidad, POIs, absorción)
- Dataset master: 168 subzonas × 87 columnas
- Exports: Tableau CSV + Power BI XLSX (3 tablas)

---

## 2026-03-22 — Exportación Power BI (10_exportar_powerbi.py)

### `src/10_exportar_powerbi.py` ✅

**Input:** `data/output/TABLEAU_CABATECH_MASTER.csv` (168×87)
**Output:** `data/output/POWERBI_CABATECH_MASTER.xlsx` (90.4 KB, 3 hojas)

**Hojas generadas:**

| Hoja | Tabla Excel | Filas | Cols | Descripción |
|---|---|---|---|---|
| Master | `tbl_subzonas` | 168 | 87 | Dataset completo sin transformaciones |
| Barrios | `tbl_barrios` | 48 | 34 | Agregado por barrio (mean/sum según métrica) |
| Diccionario | `tbl_diccionario` | 87 | 4 | Metadata: columna, tipo, descripción, fuente |

**Hoja Barrios — agregaciones:**
- `mean`: precio_m2, precio_venta_m2, roi, cap_rate, sharpe, rentabilidad, payback, score_inversion, scores × 6, dist_subte_m, cant_estaciones_800m, fot_promedio, fos_promedio, m2_edif_estimado, densidad_pob_km2, pct_nbi, area_km2, idx_equipamiento, precio_m2_zonaprop, precio_usd_zonaprop
- `sum`: poblacion, area_km2, stock_avisos, poi_escuelas, poi_hospitales, poi_restaurantes, poi_comercios, poi_parques, subte_5min, subte_10min
- `count`: n_subzonas (cantidad de subzonas por barrio)

**Formato Excel:**
- Tablas Excel con nombre (`tbl_*`) → Power BI las detecta automáticamente en "Obtener datos"
- Estilo `TableStyleMedium2` (Master), `TableStyleMedium7` (Barrios), `TableStyleLight1` (Diccionario)
- Freeze pane en fila 1 (Master y Barrios)
- Auto-ajuste de ancho de columnas (máx 40 caracteres)

**Diccionario:** 87 entradas con fuente clasificada:
- Base: 46 columnas (dataset PropTech original + métricas financieras)
- Capa 1 (Transporte): 6 columnas
- Capa 2 (FOT/FOS): 10 columnas
- Capa 3 (Densidad/Censo): 9 columnas
- Capa 4 (POIs/Equipamiento): 12 columnas
- Capa 5 (Absorción): 4 columnas

---

## 2026-03-21 — Exportación Tableau (09_exportar_tableau.py)

### `src/09_exportar_tableau.py` ✅

**Input:** `data/output/subzonas_completo.csv` (168×85)
**Output:** `data/output/TABLEAU_CABATECH_MASTER.csv` (168×87, 72 KB, utf-8-sig)

**Transformaciones aplicadas:**
- Nombres de columna: todos snake_case válidos — ya estaban limpios (0 renombres)
- Booleanos → int 0/1: `emergente`, `subte_5min`, `subte_10min`
- StringDtype (pandas) → str Python puro: 10 columnas de texto
- 44 columnas float redondeadas a 2 decimales
- Sin caracteres problemáticos en valores (\\n, \\t, \\0, comillas anidadas) — ✓
- Unicode normalizado a NFC (forma canónica compuesta, máxima compatibilidad)
- Orden de columnas reorganizado: geográficas → categóricas → precios → scores → capas

**Nuevas columnas derivadas:**
| Columna | Lógica | Distribución |
|---|---|---|
| `categoria_precio` | Premium >4000, Medio 2000-4000, Economico <2000 | 7 / 89 / 72 subzonas |
| `categoria_score` | Alto >65, Medio 40-65, Bajo <40 | 16 / 148 / 4 subzonas |

**Tipos finales en el CSV:**
- `float64`: 44 columnas (métricas continuas)
- `int64`: 31 columnas (enteros, booleanos 0/1, POIs)
- `str`: 12 columnas (textos: barrio, subzona, perfil, etc.)

**Nulos documentados:**
- FOT/FOS: 13 subzonas sin datos CUR (4 barrios: Villa Gral. Mitre, La Paternal, San Cristóbal, Parque Patricios)
- Absorción: 28 subzonas sin datos ZonaProp (9 barrios sin avisos en snapshot)
- Resto: 0 nulos

**Columnas para Tableau (87 total):**
- Dimensiones geográficas: barrio, subzona, lat, lon
- Dimensiones categóricas: categoria, categoria_precio, categoria_score, perfil, emergente, clase_gentrif, zona_cur, linea_subte_cercana
- Medidas de precio: precio_m2, precio_venta_m2, precio_m2_zonaprop, precio_usd_zonaprop
- Medidas de rentabilidad: roi, cap_rate, sharpe, var95, payback, margen
- Score: score_inversion + 5 sub-scores
- Transporte, FOT/FOS, Densidad, POIs, Absorción

---

## 2026-03-21 — Integración Capa 5 + Master v2 (5 capas, 85 columnas)

### Resumen sesión (continuación)
- `05_unificar_capas.py` actualizado con Capa 5 (absorción ZonaProp)
- Score recalculado con 6 componentes: base 50% + transporte 15% + equipamiento 15% + FOT 10% + densidad 5% + absorción 5%
- Dataset master regenerado: `subzonas_completo.csv` **168 × 85 columnas**

---

### `src/05_unificar_capas.py` — Actualización a 6 componentes ✅

**Cambios respecto a v1 (4 capas):**
- Peso `score_base` bajó de 55% → 50%
- Se agrega `score_absorcion` (5%) = liquidez de mercado (más stock ZonaProp = más líquido)
- Aliases ZonaProp → barrio oficial: abasto→balvanera, once→balvanera, congreso→balvanera,
  tribunales→san nicolas, centro/microcentro→san nicolas, barrio norte→recoleta,
  barrio parque→palermo, caballito norte/sur→caballito, lomas de nunez→nunez, etc.
- Antes del merge: ZonaProp agrega micro-zonas al barrio oficial (sum stock, mean precio_m2)

**Cobertura Capa 5:**
- 39/48 barrios con datos ZonaProp del snapshot
- 9 barrios sin avisos: Agronomía, Nueva Pompeya, Parque Avellaneda, Versalles,
  Villa Gral. Mitre, Villa Lugano, Villa Real, Villa Riachuelo, Villa Soldati
- Imputación: barrios sin datos reciben `stock_mediana` del snapshot (≈17 avisos) para score_absorcion

**Nuevas columnas (Capa 5):**
`stock_avisos`, `precio_m2_zonaprop`, `precio_usd_zonaprop`, `sup_prom_zonaprop`

**Pesos del score:**
| Componente | Peso | Lógica |
|---|---|---|
| score_original (base) | 50% | Dataset PropTech original |
| score_transporte | 15% | Dist. subte inversa (más cerca = 100) |
| score_equipamiento | 15% | idx_equipamiento OSM normalizado |
| score_fot | 10% | FOT promedio del barrio normalizado |
| score_densidad | 5% | Densidad hab/km² inversa |
| score_absorcion | 5% | Stock ZonaProp (más stock = más liquidez) |

**Promedios de componentes:**
- Score base: 61.9 | Transporte: 71.7 | FOT: 42.7 | Densidad: 57.0
- Equipamiento: 27.5 | Absorción: 12.6
- **Score final promedio: 53.6**

**TOP 5 — Mayor score de inversión:**
| # | Barrio — Subzona | Score | Precio/m² | ROI | Subte | Stock ZP |
|---|---|---|---|---|---|---|
| 1 | San Nicolás — Tribunales | 73.4 | USD 2.025 | 23.9% | 16 m | 6 avisos |
| 2 | San Nicolás — Obelisco | 72.4 | USD 2.430 | 22.2% | 16 m | 6 avisos |
| 3 | San Nicolás — Av. Santa Fe | 72.4 | USD 2.362 | 22.5% | 16 m | 6 avisos |
| 4 | San Nicolás — Av. Corrientes | 71.9 | USD 2.520 | 21.9% | 16 m | 6 avisos |
| 5 | Constitución — Estación | 70.6 | USD 1.378 | 34.6% | 306 m | 3 avisos |

**BOTTOM 5 — Menor score:**
| # | Barrio — Subzona | Score | Precio/m² | Subte | FOT |
|---|---|---|---|---|---|
| 1 | Puerto Madero — Dique 3-4 | 20.9 | USD 6.890 | 1.339 m | 0 |
| 2 | Puerto Madero — Dique 1-2 | 21.4 | USD 6.644 | 1.339 m | 0 |
| 3 | Puerto Madero — Madero Este | 28.4 | USD 5.660 | 1.339 m | 0 |
| 4 | Puerto Madero — Costanera Sur | 29.9 | USD 5.414 | 1.339 m | 0 |
| 5 | Versalles — J.B. Justo | 40.1 | USD 2.121 | 4.839 m | s/d |

**Mayores bajadas con Capa 5:** Villa Lugano (−33 pts) y Villa Soldati (−31 pts)
→ Sin datos ZonaProp: score_absorcion imputado con mediana baja + sin premiación por liquidez

**Output master:**
- `data/output/subzonas_completo.csv` — **168 filas × 85 columnas** (5 capas integradas)
- `data/output/subzonas_completo.geojson` — 168 features con polígono de barrio

---

### Estado del proyecto — cierre de sesión 2026-03-21

| Capa | Estado | Output |
|---|---|---|
| Capa 1 — Transporte (subte) | ✅ | `transporte_subte_barrios.csv` |
| Capa 2 — FOT/FOS/CUR | ✅ | `fot_fos_barrios.csv` (48×16) |
| Capa 3 — Densidad poblacional | ✅ | `censo_densidad_barrios.csv` (48×13) |
| Capa 4 — POIs urbanos | ✅ | `pois_barrios.csv` |
| Capa 5 — Absorción ZonaProp | ✅ snapshot | `absorcion_barrios.csv` (51×9) |
| **Master integrado** | ✅ | `subzonas_completo.csv` (168×85) |

**Pendiente:**
- Acumular 2-3 snapshots quincenales → absorción real (variación de stock entre fechas)
- Dashboard / visualización Streamlit o Leaflet

---

## 2026-03-21 — Capa 5: Absorción de mercado (ZonaProp snapshot)

### Resumen sesión
- Capa 5 implementada: scraping de ZonaProp con `undetected-chromedriver` (bypasea Cloudflare)
- Snapshot único: 592 listings de departamentos en venta en CABA (20 páginas)
- Workflow N8N template creado para ejecución automática quincenal

---

### `src/08_absorcion_zonaprop.py` — Capa 5: Absorción ZonaProp ✅

**Método de scraping:** `undetected-chromedriver` v3.5.5 + Chrome 146 (`version_main=146`)
- `requests` puro da 403 Forbidden (Cloudflare)
- UC simula Chrome real, bypasea anti-bot sin proxies pagos
- `WinError 6` al cerrar Chrome es cosmético (handle Windows), no afecta datos

**Selectores BS4 validados (HTML real ZonaProp):**
- Precio: `data-qa="POSTING_CARD_PRICE"` → "USD 148.000" (separador miles = punto)
- Features: `data-qa="POSTING_CARD_FEATURES"` → spans `"71 m² tot."`, `"4 amb."`
- Barrio: `data-qa="POSTING_CARD_LOCATION"` → "Almagro, Capital Federal"
- Card: `data-id` + `data-posting-type` → 30 por página

**Configuración:** 20 páginas, delay 2.5–5s aleatorio, timeout 20s, deduplicación por id

**Outputs:**
- `data/raw/zonaprop_snapshot_2026-03-21.csv` — **592 filas × 9 columnas**
  Campos: `id`, `url`, `titulo`, `barrio`, `precio_usd`, `superficie_m2`, `precio_m2`, `ambientes`, `fecha_snapshot`
- `data/processed/absorcion_barrios.csv` — **51 barrios** con stock y precios

**Cobertura del snapshot:**
- Precio USD: 99% (588/592) | Superficie: 100% | Precio/m²: 99% | Ambientes: 99%
- Precio/m² mediana global CABA: **USD 2.667**

**TOP 10 por stock:**

| Barrio | Stock | Precio/m² med | Sup. prom. |
|---|---|---|---|
| Palermo | 115 | USD 3.192 | 90 m² |
| Belgrano | 70 | USD 2.989 | 107 m² |
| Recoleta | 52 | USD 2.745 | 106 m² |
| Caballito | 41 | USD 2.300 | 81 m² |
| Villa Urquiza | 24 | USD 2.873 | 71 m² |
| Núñez | 23 | USD 3.378 | 102 m² |
| Villa Crespo | 22 | USD 2.426 | 69 m² |
| Puerto Madero | 20 | USD 5.754 | 119 m² |
| Almagro | 18 | USD 2.024 | 70 m² |
| Colegiales | 16 | USD 2.677 | 88 m² |

**Menor stock (≥3 avisos):** Villa Pueyrredón, San Telmo, Villa Luro, Parque Chacabuco, Constitución

---

### `n8n/workflow_zonaprop.json` — Template workflow N8N ✅

**Nodos implementados:**
1. `Cron` — disparo día 1 y 16 de cada mes, 08:00 AR (`0 8 1,16 * *`)
2. `Set` — parámetros configurables (URL, páginas, delay)
3. `SplitInBatches` — itera las 20 páginas secuencialmente
4. `Code` — construye URL de página (pág 1 / pág N)
5. `HTTP Request` — descarga HTML con headers Chrome reales
6. `Code` — parsea listings (JSON embebido → regex fallback)
7. `Wait` — delay 3s entre páginas
8. `Merge` — consolida todos los listings
9. `Code` — agrega por barrio (stock, precio med/prom)
10. `WriteBinaryFile` × 2 — guarda raw y processed
11. `Set` — placeholder para notificación email/Slack/Telegram
12. `Set` (error) — captura errores HTTP

**Nota N8N Cloud:** WriteBinaryFile sin acceso a filesystem local → reemplazar por Google Drive / S3.

---

### Dependencias instaladas

```
pip install beautifulsoup4 lxml undetected-chromedriver selenium setuptools
```
`setuptools` necesario porque `distutils` fue removido en Python 3.12.

---

### Estado del proyecto — cierre de sesión 2026-03-21

| Capa | Estado | Output |
|---|---|---|
| Capa 1 — Transporte (subte) | ✅ | `transporte_subte_barrios.csv` |
| Capa 2 — FOT/FOS/CUR | ✅ | `fot_fos_barrios.csv` (48×16) |
| Capa 3 — Densidad poblacional | ✅ | `censo_densidad_barrios.csv` (48×13) |
| Capa 4 — POIs urbanos | ✅ | `pois_barrios.csv` |
| Capa 5 — Absorción ZonaProp | ✅ snapshot | `zonaprop_snapshot_2026-03-21.csv` (592×9) |

**Dataset master:** `subzonas_completo.csv` — 168 × 80 cols (sin Capa 5 aún — pendiente unificación)

**Pendiente:**
- Integrar `absorcion_barrios.csv` en `05_unificar_capas.py` → recalcular score con Capa 5
- Acumular 2-3 snapshots quincenales para calcular absorción real (`stock_t - stock_t-1`)
- Dashboard / visualización con datos consolidados

---

## 2026-03-20 — Capas 2, 3 + Master final (4 capas integradas)

### Resumen sesión
- Capa 2 (FOT/FOS/CUR): descarga, parseo NDJSON y agregación de normativa urbanística
- Capa 3 (Densidad): 3554 radios censales → métricas de población por barrio
- Master unificado: Capas 1+2+3+4 integradas, score de 5 componentes

---

### `src/07_censo_densidad.py` — Capa 3: Densidad poblacional ✅

**Fuente:** `CABA_rc.geojson` — 3554 radios censales, Censo 2010 (BA Data)
**URL:** `http://cdn.buenosaires.gob.ar/datosabiertos/datasets/informacion-censal-por-radio/CABA_rc.geojson`
**Tamaño:** 3.6 MB | CRS: EPSG:4326 nativo | Campo `BARRIO` incluido → no requiere spatial join

**Nota Censo 2022:** INDEC solo publicó resultados 2022 a nivel nacional/provincial.
Los radios censales del Censo 2010 son la fuente más granular disponible públicamente.

**Output:** `data/processed/censo_densidad_barrios.csv` — **48 filas × 13 columnas**
Campos: `barrio`, `n_radios`, `poblacion`, `viviendas`, `hogares`, `hogares_nbi`,
`area_km2_censo`, `densidad_pob_km2`, `densidad_viv_km2`, `pct_nbi`, `pob_por_hogar`,
`viv_por_habitante`, `score_densidad`

Población total CABA (2010): **2.890.151** | Densidad prom: **14.180 hab/km²** | NBI: **6.0%**
Más denso: Almagro (32.517 hab/km²) | Menos denso: Puerto Madero (1.239 hab/km²)
Mayor NBI: Constitución (24.3%) → La Boca (21.2%) → Monserrat (19.2%)

---

### `src/05_unificar_capas.py` — Master final con 5 componentes ✅

**Score de inversión — evolución de pesos:**
| Componente | v1 (Capa1+4) | v2 (+Capa2) | v3 (+Capa3) |
|---|---|---|---|
| score_base | 70% | 60% | **55%** |
| score_transporte (subte) | 15% | 15% | 15% |
| score_fot (FOT/CUR) | — | 10% | 10% |
| score_densidad (hab/km², inv.) | — | — | **5%** |
| score_equipamiento (POIs) | 15% | 15% | 15% |

**Nota `score_densidad`:** el score de densidad es **inverso** — menor densidad = mayor score.
Lógica: zonas menos densas tienen más disponibilidad de suelo/terreno para desarrollo.

**Output master:** `data/output/subzonas_completo.csv` — **168 filas × 80 columnas**
`data/output/subzonas_completo.geojson` — 168 features con geometría de barrio

**Promedios del score:**
- Score base: 61.9 | Transporte: 71.7 | FOT: 42.7 | Densidad: 57.0 | Equipamiento: 27.5
- **Score final promedio: 56.1**

**TOP 5 score_inversion:**
1. San Nicolás — Tribunales: **76.2** (USD 2.025, ROI 23.9%, subte 16m, FOT 4.17)
2. San Nicolás — Obelisco: **75.1**
3. San Nicolás — Av. Santa Fe: **75.1**
4. Constitución — Estación: **74.8** (USD 1.378, ROI 34.6%, subte 306m)
5. San Nicolás — Av. Corrientes: **74.5**

**BOTTOM 5 score_inversion:**
1. Puerto Madero — Dique 3-4: **20.4** (USD 6.890, ROI 1.5%, subte 1.339m, FOT 0)
2. Puerto Madero — Dique 1-2: **20.9**
3. Puerto Madero — Madero Este: **28.6**
4. Puerto Madero — Costanera Sur: **30.3**
5. Versalles — J.B. Justo: **42.9** (subte 4.838m)

**Mayores subidas:** San Nicolás +17 pts | Puerto Madero +15 pts (por score_densidad alto)
**Mayores bajadas:** Villa Lugano −29 pts | Villa Soldati −27 pts

---

### Estado del proyecto — cierre de sesión 2026-03-20

| Capa | Estado | Output |
|---|---|---|
| Capa 1 — Transporte (subte) | ✅ | `transporte_subte_barrios.csv` |
| Capa 2 — FOT/FOS/CUR | ✅ | `fot_fos_barrios.csv` (48×16) |
| Capa 3 — Densidad poblacional | ✅ | `censo_densidad_barrios.csv` (48×13) |
| Capa 4 — POIs urbanos | ✅ | `pois_barrios.csv` |
| Capa 5 — Absorción de mercado | ⏳ | Pipeline N8N + scraping ZonaProp |

**Dataset master:** `subzonas_completo.csv` — **168 × 80 columnas** (4 capas integradas)

---

## 2026-03-20 — Capa 2: FOT/FOS/CUR

### Resumen
Implementación de la Capa 2 (normativa urbanística) usando el dataset de Código Urbanístico
de BA Data. Se resolvieron 3 problemas técnicos del archivo fuente antes de procesar.

---

### 1. Dataset fuente — `codigo_urbanistico_caba.geojson`

**URL:** `https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/codigo-urbanistico/codigo-urbanistico.geojson`

- Tamaño: **5.5 MB** | Última actualización BA Data: **2025-05-14**
- **2.541 features** (polígonos de zona urbanística) × **52 columnas**
- **Campos clave:** `fot_em_1` (FOT edificación múltiple), `alicuota` (FOS),
  `plano_l` (altura máxima plano límite en metros), `dist_cpu_1` (distrito CUR)
- Campo `barrio` incluido en cada feature → no requiere spatial join

**Problemas técnicos del archivo fuente resueltos:**

1. **Formato NDJSON no estándar:** el archivo no es un GeoJSON válido. Es un listado de Features
   con una línea por feature, donde cada línea termina con coma trailing (`...} },`).
   `gpd.read_file()` lo rechaza. Solución: parseo línea a línea con `json.loads(linea.rstrip(", "))`.

2. **Línea 0 truncada:** la primera línea del archivo está cortada a mitad de un feature
   (empieza con `grp": "U", ...`). Se descarta por no contener `"type": "Feature"`.
   5 líneas en total descartadas (1 truncada + 4 con errores JSON).

3. **CRS no declarado con sistema local GCBA:** las coordenadas son métricas locales
   (x~98k-120k, y~95k-115k), sistema propio de GCBA sin EPSG estándar.
   **Solución adoptada:** innecesario — el campo `barrio` en cada feature permite
   agregar por barrio directamente, sin reproyectar ni hacer spatial join.

---

### 2. `src/06_fot_fos_cur.py` — Capa 2: FOT/FOS/CUR ✅

**Metodología:** agrupación por campo `barrio` del propio dataset CUR (no spatial join).
Normalización de nombres con función `normalizar_barrio()` — alias añadido: `"boca" → "la boca"`.

**Exclusiones aplicadas:**
- 26 parcelas con `fot_em_1 < 0` (valores erróneos) → excluidas del cálculo
- `plano_l = 0` → excluido de promedios de altura (cero = sin restricción, no es medida real)

**Outputs:**
- `data/raw/codigo_urbanistico_caba.geojson` — raw descargado (5.5 MB)
- `data/processed/fot_fos_barrios.csv` — **48 filas × 16 columnas**

**Columnas del output:**
`barrio`, `n_parcelas`, `fot_promedio`, `fot_mediana`, `fot_maximo`, `fot_minimo`,
`fos_promedio`, `fos_minimo`, `fos_maximo`, `altura_max_promedio`, `altura_max_mediana`,
`altura_max_absoluta`, `pct_parcelas_sin_altura`, `dist_cur_dominante`, `n_distritos_cur`,
`m2_edif_estimado`

**Cobertura:** 44 de 48 barrios con datos reales. 4 barrios sin datos en el CUR:
Villa General Mitre, La Paternal, San Cristóbal, Parque Patricios → `NaN` en el output.

---

### 3. Resultados

**Estadísticas globales:**
- FOT promedio CABA: **1.70**
- FOS promedio CABA: **0.23** (23.4%)
- Altura promedio CABA: **21.1 m**
- m2 edificables (lote 200 m²): **341 m2** promedio
- Total features procesados: **2.541** (polígonos de zona)

**Top 5 mayor FOT (más edificable):**

| Barrio | FOT prom. | Altura prom. | Distrito | m2 lote 200 |
|---|---|---|---|---|
| San Nicolás | 4.17 | 35.1 m | C2 | 834 m2 |
| Recoleta | 3.65 | 34.0 m | R2a I | 730 m2 |
| Caballito | 3.20 | 33.6 m | R2a II | 639 m2 |
| Almagro | 3.19 | 30.9 m | R2a II | 638 m2 |
| Balvanera | 3.00 | 30.0 m | C3 I | 600 m2 |

**Top 5 menor FOT (menos edificable):**
Villa Ortúzar (0.00) → San Telmo (0.00) → Retiro (0.00) → Puerto Madero (0.00) → Villa Soldati (0.33)

*Nota: 4 barrios con FOT=0 tienen muy pocas features (1-4 zonas) — probablemente cobertura parcial del CUR, no FOT real.*

---

### 4. Estado del proyecto — cierre de sesión 2026-03-20

| Capa | Estado | Outputs |
|---|---|---|
| Capa 1 — Transporte (subte) | ✅ Completa | `transporte_subte_barrios.csv`, `transporte_subte_subzonas.csv` |
| Capa 2 — FOT/FOS/CUR | ✅ Completa | `fot_fos_barrios.csv` (48×16) |
| Capa 3 — Densidad poblacional | ⏳ Pendiente | Radios censales INDEC Censo 2022 |
| Capa 4 — POIs urbanos | ✅ Completa | `pois_barrios.csv`, `pois_caba.geojson` |
| Capa 5 — Absorción de mercado | ⏳ Pendiente | Pipeline N8N + scraping |

**Dataset master:** pendiente actualizar `05_unificar_capas.py` para incluir Capa 2.

---

## 2026-03-16 — Sesión de trabajo inicial

### Resumen
Primera sesión de trabajo productiva. Se organizó el proyecto desde cero, se resolvieron
problemas de datos, y se ejecutaron 3 scripts que completan Capa 1 (Transporte), Capa 4
(POIs urbanos) y la unificación de capas en un dataset master de 168 subzonas × 60 columnas.

---

### 1. Organización del proyecto

**Problema inicial:** todos los archivos estaban sueltos en la raíz sin estructura de carpetas.

**Estructura creada** (según CLAUDE.md):
```
data/raw/   data/processed/   data/output/
notebooks/  src/  geojson/  csv/  qgis/
```

**Archivos movidos a `data/raw/`:** todos los GeoJSON, CSV, XLSX, ZIP y PNG que estaban en raíz.

**Notebooks:** renombrados con extensión `.ipynb` y movidos a `notebooks/`.

**Eliminados:**
- `lineas-de-subte (1).xlsx` — duplicado exacto de `lineas-de-subte.xlsx`
- `data/subte_estaciones.geojson` (245 B) — placeholder vacío
- `data/subte_lineas.geojson` (245 B) — placeholder vacío
- `.ipynb_checkpoints/` — checkpoint obsoleto

**Pendiente:** `caba_48_barrios.geojson` y `168_subzonas_proptech.geojson` quedaron
duplicados en la raíz — bloqueados por proceso externo (probablemente QGIS abierto).
Las copias en `data/raw/` son las canónicas. Eliminar los de la raíz al cerrar QGIS.

---

### 2. Exploración y diagnóstico de datos base

#### `data/raw/estaciones_de_subte.csv`
- Encoding: `utf-8-sig`
- Columnas: `id`, `estacion`, `linea`, `geometry` (WKT Point)
- **90 estaciones** en 6 líneas

| Línea | Estaciones |
|---|---|
| A | 18 |
| B | 17 |
| C | 9 |
| D | 16 |
| E | 18 |
| H | 12 |

#### `data/raw/caba_48_barrios.geojson`
- 48 barrios oficiales ✓ | CRS: EPSG:4326 | Geometría: Polygon
- Área total CABA: **205.7 km²** | Barrio más grande: Palermo (15.9 km²)

#### `data/raw/168_subzonas_proptech.geojson` — Diagnóstico crítico
- Geometría tipo **Point** (no Polygon)
- **Todos los puntos dentro de un barrio son idénticos** — 48/48 barrios con 1 solo
  punto compartido entre sus 3-5 subzonas
- `estacion_subte = 0` en todos los registros → placeholder sin valor real
- `dist_subte` original: valores arbitrarios, no calculados con precisión geométrica
- **Limitación:** métricas de distancia son iguales para todas las subzonas del mismo
  barrio hasta disponer de polígonos subzonales reales

---

### 3. Problemas técnicos resueltos

#### Encoding cp1252 en Windows
- **Problema:** `print()` con caracteres Unicode (✓, →, ▸) fallaba con
  `UnicodeEncodeError: 'charmap' codec can't encode character`
- **Solución:** agregar `sys.stdout.reconfigure(encoding="utf-8")` al inicio de cada script

#### Nombres de barrios sin match en merge
- **Problema:** 11 barrios no coincidían entre el CSV de subzonas y los archivos
  procesados por diferencias de tildes y abreviaturas
- Ejemplos: `"San Nicolas"` vs `"San Nicolás"`, `"Constitucion"` vs `"Constitución"`,
  `"Nuñez"` vs `"Núñez"`, `"Villa Del Parque"` vs `"Villa del Parque"`
- **Solución parcial:** función `normalizar_barrio()` con `unicodedata.normalize("NFKD")`
  que elimina tildes y pasa a minúsculas → resolvió 9 de 11 casos
- **Dos casos persistentes** que requirieron alias explícitos:
  - `"Paternal"` → `"La Paternal"` (nombre corto vs nombre oficial)
  - `"Villa Gral. Mitre"` → `"Villa General Mitre"` (abreviatura vs nombre completo)
- **Solución final:** diccionario `ALIAS` hardcodeado en la función de normalización

---

### 4. `src/03_transporte_subte.py` — Capa 1: Transporte subte ✅

**Metodología:**
- CRS de cálculo: **EPSG:22185** (Gauss-Krüger faja 5) — metros reales
- Centroides de barrios calculados desde polígonos oficiales con GeoPandas
- Umbrales: 5 min = 400 m | 10 min = 800 m

**Outputs:**
- `data/processed/transporte_subte_barrios.csv` — 48 filas
- `data/processed/transporte_subte_subzonas.csv` — 168 filas

**Campos calculados:** `dist_subte_m`, `linea_subte_cercana`, `estacion_cercana`,
`cant_estaciones_800m`, `subte_5min`, `subte_10min`

**Resultados — 48 barrios:**

| Métrica | Valor |
|---|---|
| Distancia promedio | 1.658 m |
| Distancia mediana | 1.301 m |
| Más cercano | San Nicolás — **16 m** (Línea B, C. Pellegrini) |
| Más lejano | Villa Riachuelo — **5.401 m** |
| Subte ≤ 5 min (400 m) | 14 / 48 (29%) |
| Subte ≤ 10 min (800 m) | 21 / 48 (44%) |

Top 5 más cerca: San Nicolás → Monserrat → San Cristóbal → Chacarita → Balvanera

Top 5 más lejos: Villa Riachuelo → Villa Real → Versalles → Liniers → Mataderos
(todos con 0 estaciones dentro de 800 m)

Línea más cercana por barrios: A (13), B (12), E (9), D (5), H (5), C (4)

---

### 5. `src/04_pois_osm.py` — Capa 4: POIs urbanos ✅

**Fuente:** OpenStreetMap via Overpass API (`overpass-api.de`)
**Bounding box:** `-34.7059,-58.5315,-34.5265,-58.3351`

**Descarga — 10 categorías:**

| Categoría | Tag OSM | Descargados | En barrios |
|---|---|---|---|
| Comercios | `shop=*` | 20.283 | 17.889 |
| Restaurantes | `amenity=restaurant` | 2.732 | 2.510 |
| Escuelas | `amenity=school` | 1.951 | 1.771 |
| Cafés | `amenity=cafe` | 1.649 | 1.599 |
| Parques | `leisure=park` | 1.547 | 1.199 |
| Farmacias | `amenity=pharmacy` | 1.000 | 860 |
| Bancos | `amenity=bank` | 807 | 729 |
| Clínicas | `amenity=clinic` | 353 | 264 |
| Hospitales | `amenity=hospital` | 142 | 112 |
| Universidades | `amenity=university` | 113 | 104 |
| **Total** | | **30.577** | **27.037** |

3.540 POIs descartados por caer en bordes fuera de polígonos (`sjoin predicate="within"`).

**Índice de equipamiento urbano:**
```
idx_raw = (escuelas×3 + hospitales×5 + universidades×4 + clínicas×2
         + gastronomía×1 + comercios×0.5 + bancos×2 + farmacias×2
         + parques×3) / área_km²

idx_equipamiento = normalizado 0–100
```

**Top 5 mejor equipados:** San Nicolás (100.0) → Monserrat (66.3) → Balvanera (62.4)
→ San Telmo (61.3) → Recoleta (59.5)

**Bottom 5:** Villa Riachuelo (0.0) → Villa Soldati (5.6) → Puerto Madero (8.7)
→ Agronomía (9.2) → La Paternal (9.3)

**Outputs:**
- `data/raw/pois_caba.geojson` — **30.577 features** con geometría OSM original (7.6 MB)
- `data/processed/pois_barrios.csv` — 48 barrios con conteos por categoría e índice

**Nota:** la API devolvió errores 429 (rate limit) y un 504 (timeout). El script los
manejó con lógica de reintentos — ninguna categoría se perdió.

---

### 6. `src/05_unificar_capas.py` — Unificación master ✅

**Fuentes mergeadas:**
- `data/raw/168_subzonas_proptech.csv` (base, 43 columnas)
- `data/processed/transporte_subte_barrios.csv` (+6 columnas de transporte)
- `data/processed/pois_barrios.csv` (+13 columnas de POIs + área)

**Columnas eliminadas del CSV base** (reemplazadas por datos calculados con precisión):
`dist_subte`, `subte_5min`, `subte_10min`, `linea_subte`, `estacion_subte`,
`dist_hospital`, `hospital_cercano`

**Score de inversión recalculado:**

| Componente | Peso | Método |
|---|---|---|
| score_original | 70% | Campo `score` del CSV base |
| score_transporte | 15% | `dist_subte_m` normalizado inversamente (más cerca = 100) |
| score_equipamiento | 15% | `idx_equipamiento` (ya normalizado 0–100) |

| Métrica | Valor |
|---|---|
| Promedio score base | 61.9 |
| Promedio score transporte | 71.7 |
| Promedio score equipamiento | 27.5 |
| **Promedio score nuevo** | **58.2** |

**Mayor subida:** San Nicolás (+12.9 pts) — score base subestimado, ahora refleja
subte a 16 m e idx_equipamiento = 100

**Mayor bajada:** Villa Lugano y Villa Riachuelo (−21.6 pts) — score base alto por
ROI, penalizado fuertemente por subte > 3.700 m y equipamiento < 10

**Outputs:**
- `data/output/subzonas_completo.csv` — **168 filas × 60 columnas** (49.6 KB)
- `data/output/subzonas_completo.geojson` — 168 features con polígono de barrio (1.4 MB)

---

### Estado del proyecto — cierre de sesión 2026-03-16

#### Capas de datos

| Capa | Estado | Outputs |
|---|---|---|
| Capa 1 — Transporte (subte) | ✅ Completa | `transporte_subte_barrios.csv`, `transporte_subte_subzonas.csv` |
| Capa 2 — FOT/FOS por parcela | ⏳ Pendiente | Descargar parcelas CABA + plancheta CUR (BA Data) |
| Capa 3 — Densidad poblacional | ⏳ Pendiente | Radios censales INDEC Censo 2022 + join espacial |
| Capa 4 — POIs urbanos | ✅ Completa | `pois_barrios.csv`, `pois_caba.geojson` |
| Capa 5 — Absorción de mercado | ⏳ Pendiente | Pipeline N8N + scraping ZonaProp/Argenprop |

#### Unificación

| Tarea | Estado |
|---|---|
| Dataset master 168 subzonas | ✅ `data/output/subzonas_completo.csv` (60 cols) |
| GeoJSON master con polígonos | ✅ `data/output/subzonas_completo.geojson` |
| Score con Capa 2 y Capa 3 | ⏳ Pendiente (recalcular cuando estén disponibles) |

#### Deuda técnica

- Las subzonas no tienen polígonos propios — el GeoJSON master usa el polígono del
  barrio para todas sus subzonas. Las métricas geoespaciales (distancia al subte, POIs
  por subzona) son iguales dentro de cada barrio. Se resolverá con cartografía subzonal.
- `src/03_transporte_subte.py` — bloque de subzonas usa el Point del GeoJSON original
  en vez del centroide del polígono oficial. Pendiente actualizar (bajo impacto mientras
  no haya polígonos subzonales reales).
- `caba_48_barrios.geojson` y `168_subzonas_proptech.geojson` duplicados en raíz
  (bloqueados por QGIS). Eliminar al cerrar QGIS.
