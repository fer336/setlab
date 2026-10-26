# SET/LAB · Fase 0 — Prueba de sonido

Toma dos temas y genera una transición de DJ entre ellos: detecta BPM, compases,
tonalidad y volumen, iguala el tempo sin cambiar el tono y mezcla con cambio de
bajos, filtros y reverb.

El objetivo de esta fase es uno solo: **escuchar si la transición suena natural**
con tus temas antes de construir la aplicación.

## Qué genera

En la carpeta `salida/`:

- `transicion.mp3` — 30 s del tema A, la transición y 30 s del tema B (unos 2 min)
- `transicion.wav` — lo mismo en calidad completa
- `analisis.json` — BPM, tono (Camelot), volumen y el plan de la mezcla

## Cómo usarlo en tu servidor

Necesitás entrar por SSH (o la consola de Portainer del host) una sola vez.

```bash
# 1. Copiá esta carpeta al servidor, por ejemplo en /opt/setlab/fase0
# 2. Creá la carpeta de temas y subí dos temas (WAV o FLAC ideal, MP3 320 sirve)
mkdir -p /opt/setlab/temas

# 3. Construí la imagen (tarda unos minutos la primera vez)
cd /opt/setlab/fase0
docker build -t setlab-fase0 .

# 4. Generá la transición
docker run --rm -m 3g -v /opt/setlab/temas:/temas setlab-fase0 temaA.wav temaB.wav
```

El resultado queda en `/opt/setlab/temas/salida/transicion.mp3`.

### Opciones

| Opción | Valores | Qué hace |
| --- | --- | --- |
| `--estilo` | `bajos` (default), `larga` | `bajos`: B entra filtrado, cambio de bajos a la mitad, A sale con filtro y reverb. `larga`: fundido largo y parejo con cambio de bajos. |
| `--compases` | `16`, `32` (default), `64` | Largo de la transición |
| `--completo` | — | Exporta A entero + B entero en vez de solo la zona de la mezcla |

Ejemplo:

```bash
docker run --rm -m 3g -v /opt/setlab/temas:/temas setlab-fase0 temaA.wav temaB.wav --estilo larga --compases 64
```

## Qué revisar cuando escuches

1. **¿Los bombos van juntos?** Si se oye un bombo doble ("flam"), anotá en qué momento.
2. **¿El BPM y el tono coinciden con Mixxx?** Compará con lo que dice `analisis.json`.
3. **¿Dónde empieza la mezcla?** Debería arrancar en el outro de A y en la intro de B.
4. **¿Qué estilo te gusta más?** `bajos` o `larga`, y con qué largo.

## Resultados de la prueba con temas sintéticos

| Medición | Resultado |
| --- | --- |
| BPM detectado (real 128 y 131) | 128,0 y 131,0 |
| Tonalidad (real La menor y Mi menor) | 8A y 9A, compatibles |
| Diferencia entre bombos durante la mezcla | 0,8 ms (inaudible) |
| Tiempo total para dos temas de ~4 min | 18 s |
| Memoria máxima | ~0,9 GB |

## Resultados con temas reales (5 temas de techno)

| Transición | BPM | Tono | Ajuste fino | Click A vs B |
| --- | --- | --- | --- | --- |
| T78 AC/ID → Boost | 127 → 128 | 10A → 8A | 0 ms | 0–3 ms |
| Boost → Psychedelic Hypnostate | 128 → 130 | 8A → 8A | +42 ms | 0 ms |
| Psychedelic Hypnostate → Seat Belt | 130 → 130 | 8A → 3A | −33 ms | 0–1 ms |
| Seat Belt → I Am Not Regular | 130 → 135 | 3A → 6B | +1 ms | 0–8 ms |

Cómo se alinean los bombos:

1. **Tempo**: se escuchan solo los graves y se prueban tempos cada 0,005 BPM.
2. **Anclaje**: se promedian todos los golpes del tema por bandas de frecuencia
   para encontrar el ataque ("click") del bombo, aunque el bajo vaya a contratiempo.
3. **Ajuste fino**: como el jog de un DJ, se comparan los clicks de A y B
   en toda la transición y se corre B unos milisegundos hasta que calcen.

## Limitaciones conocidas (se resuelven en la Fase 1)

- Asume compás de 4/4 y que el tema arranca en el primer tiempo (casi siempre
  es así en techno). Si un tema arranca con un sonido suelto antes del bombo,
  la mezcla puede quedar corrida un tiempo.
- Busca el punto de mezcla por posición (último bloque de 32 compases), no por
  secciones reales. En la Fase 1 se detectan intro, break y outro con IA.
- B queda a la velocidad de A hasta el final.
