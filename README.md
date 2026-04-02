# LOTIQ — Decision Intelligence para Inversión Inmobiliaria

> ¿Dónde el suelo es barato pero la normativa permite construir mucho?

![Dashboard](docs/d6_preview.png)

## ¿Qué es LOTIQ?

Plataforma de análisis de inversión inmobiliaria en CABA que cruza normativa urbanística (FOT/FOS) con datos de mercado para identificar oportunidades de desarrollo.

**Diferencial:** combina criterios técnicos arquitectónicos (CUR, edificabilidad) con análisis financiero de mercado — algo que ningún producto argentino actual integra.

## Resultados

- 168 subzonas × 48 barrios oficiales de CABA
- 91 métricas por subzona
- 5 capas de datos integradas
- Score de inversión multicapa (0-100)

## Stack

Python · Pandas · GeoPandas · Tableau Public · QGIS · XGBoost · N8N

## Capas de datos

| Capa | Fuente | Descripción |
|---|---|---|
| Transporte | BA Data | Distancias reales a subte, isócronas 5/10 min |
| Normativa | CUR CABA | FOT/FOS/CUR por parcela |
| Densidad | Censo 2022 | Población, NBI, viviendas por km² |
| POIs | OpenStreetMap | 30,577 puntos de interés categorizados |
| Mercado | ZonaProp | Precios publicados, stock, superficie |

## Dashboard

[Ver en Tableau Public](https://public.tableau.com/app/profile/alejandro.lino)

## Estructura
```
lotiq/
├── src/          ← scripts ETL y pipeline
├── data/         ← estructura (datos no incluidos)
├── notebooks/    ← análisis exploratorio
├── n8n/          ← workflows de automatización
└── docs/         ← documentación
```

## Estado

- [x] Fase 1: Dataset CABA completo (168 subzonas)
- [x] Dashboard D6 publicado
- [ ] Fase 2: Primer cordón GBA
- [ ] Integración BIM (Revit/Dynamo)
