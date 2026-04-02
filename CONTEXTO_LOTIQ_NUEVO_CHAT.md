# LOTIQ — Contexto para nuevo chat
> Última actualización: 2026-03-30

---

## Estado general

**Fase 1 CABA completada al 100%:**
- 48 barrios oficiales
- 168 subzonas PropTech
- 5 capas de datos construidas e integradas
- Dataset master exportado para Tableau y Power BI

---

## Dataset master

**Archivo principal:** `data/output/TABLEAU_LOTIQ_MASTER.xlsx`
- **Shape:** 168 filas × 87 columnas
- **Unidad:** subzona (cada barrio tiene ~3-4 subzonas)
- **Encoding:** UTF-8 con BOM (`utf-8-sig`) — leer siempre con `encoding='utf-8-sig'`
- **Exportar siempre como .xlsx** (openpyxl, sin índice) — Tableau Public no parsea CSV correctamente en Windows

### Grupos de columnas
| Grupo | Columnas clave |
|---|---|
| Identificación | `barrio`, `subzona`, `lat`, `lon` |
| Clasificación | `categoria`, `perfil`, `emergente`, `clase_gentrif` |
| Financiero | `precio_m2`, `rentabilidad`, `roi`, `cap_rate`, `sharpe`, `payback`, `costo_total`, `ingresos` |
| Edificabilidad | `pisos`, `n_pisos`, `altura_max`, `m2_vendibles`, `fot_promedio`, `fos_promedio` |
| Scores | `score_inversion`, `score_transporte`, `score_fot`, `score_densidad`, `score_equipamiento`, `score_absorcion` |
| Subte | `dist_subte_m`, `cant_estaciones_800m`, `linea_subte_cercana`, `estacion_cercana`, `subte_5min`, `subte_10min` |
| Censo | `poblacion`, `densidad_pob_km2`, `pct_nbi`, `area_km2` |
| POIs | `poi_escuelas`, `poi_hospitales`, `poi_restaurantes`, `poi_cafes`, `poi_comercios`, `idx_equipamiento` |
| ZonaProp | `stock_avisos`, `precio_m2_zonaprop`, `precio_usd_zonaprop`, `sup_prom_zonaprop` |

---

## 5 Capas completadas

### Capa 1 — Transporte (subte)
- Distancia a estación más cercana, isócronas 5/10 min, línea y estación cercana
- Archivos: `data/processed/transporte_subte_barrios.csv`, `transporte_subte_subzonas.csv`

### Capa 2 — FOT/FOS (normativa CUR)
- FOT promedio/mediana/máximo, FOS, altura máxima por subzona
- Fuente: `codigo_urbanistico_caba.geojson`
- Archivo: `data/processed/fot_fos_barrios.csv`

### Capa 3 — Densidad poblacional (Censo 2022)
- Población, viviendas, hogares, NBI, densidad por km²
- Fuente: `radios_censales_caba.geojson`
- Archivo: `data/processed/censo_densidad_barrios.csv`

### Capa 4 — POIs urbanos (OpenStreetMap)
- Escuelas, universidades, hospitales, clínicas, restaurantes, cafés, comercios, bancos, farmacias, parques
- Archivo: `data/processed/pois_barrios.csv`

### Capa 5 — Absorción de mercado (ZonaProp)
- Stock de avisos, precio publicado m², precio USD, superficie promedio
- Snapshot: `data/raw/zonaprop_snapshot_2026-03-21.csv`
- Archivo: `data/processed/absorcion_barrios.csv`
- **Nota:** algunas subzonas tienen NaN (cobertura incompleta del scraping)

---

## Archivos de output

| Archivo | Descripción | Uso |
|---|---|---|
| `data/output/TABLEAU_LOTIQ_MASTER.xlsx` | Dataset completo 168×87 | Tableau — fuente principal |
| `data/output/TABLEAU_LOTIQ_MASTER.csv` | Backup del master | Solo backup |
| `data/output/TABLEAU_BARRIOS_48.xlsx` | Métricas agregadas por barrio (48×7) | Tableau — vista barrio |
| `data/output/LOTIQ_MAPA_BARRIOS.geojson` | GeoJSON 48 barrios + métricas | Tableau / QGIS — mapas |
| `data/output/subzonas_completo.csv/.geojson` | GeoJSON 168 subzonas + métricas | Tableau / QGIS — mapas granulares |
| `data/output/POWERBI_LOTIQ_MASTER.xlsx` | Dataset para Power BI | Power BI |
| `data/raw/caba_48_barrios_fix.geojson` | GeoJSON barrios CABA normalizado | Join con datasets |

### Convención de nombres normalizados
Todos los nombres de barrios están **normalizados**: minúsculas, sin tildes, sin caracteres especiales.
- Ejemplo: `Agronomía` → `agronomia`, `Núñez` → `nunez`, `Villa Gral. Mitre` (abreviado)
- El GeoJSON original (`caba_48_barrios.geojson`) está en UTF-8 pero con nombres con tildes — usar siempre `_fix.geojson`

---

## Dashboards Tableau — Estado actual

### D6 — Dashboard principal (casi completo)
- Mapa coroplético de CABA por score de inversión
- Filtros por categoría, perfil, zona
- KPIs: precio_m2, ROI, rentabilidad, cap_rate, payback
- **Pendiente:** ajuste de tooltips y paleta de colores final

### Top10_Oportunidades (en construcción)
- Ranking de subzonas por score_inversion
- Barras comparativas con métricas financieras
- **Pendiente:** completar visualización y conectar filtro global del dashboard

---

## Próximos pasos

- [ ] Completar D6 (tooltips + paleta)
- [ ] Completar Top10_Oportunidades
- [ ] Publicar dashboard en Tableau Public
- [ ] Iniciar Fase 2: primer cordón GBA (Vicente López, San Isidro, Avellaneda, etc.)

---

## Comandos útiles de referencia

```python
# Leer dataset master
import pandas as pd
df = pd.read_excel(r'data/output/TABLEAU_LOTIQ_MASTER.xlsx')

# Leer GeoJSON normalizado
import json
with open(r'data/raw/caba_48_barrios_fix.geojson', encoding='utf-8') as f:
    gj = json.load(f)

# Exportar a Tableau
df.to_excel(r'data/output/TABLEAU_LOTIQ_MASTER.xlsx', index=False, engine='openpyxl')
```

---

## Contexto del desarrollador
- Arquitecto último año + Data Analyst semi-senior, Buenos Aires
- Dominio normativa urbanística CABA (CUR, FOT/FOS) y BIM (Revit/Dynamo)
- Stack: Python, Pandas, GeoPandas, Tableau, Power BI, QGIS
- Comunicación y commits en español
