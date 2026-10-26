# Fase 0 — Qué se probó y qué se aprendió

## Objetivo

Confirmar que una transición automática entre dos temas de techno puede sonar natural,
y medir tiempos y memoria para un servidor de 8 GB sin GPU.

## Cómo funciona `transicion.py`

1. **Carga** los dos temas en estéreo a 44,1 kHz.
2. **Analiza** cada uno:
   - Tempo: envolvente de ataques de graves (<200 Hz, hop 128 = 2,9 ms) → autocorrelación
     entre 100 y 160 BPM → búsqueda gruesa (±3 BPM cada 0,05) y fina (±0,1 cada 0,005)
     de la grilla regular que mejor coincide con los golpes.
   - Anclaje: `anclar_en_bombo` promedia todos los golpes (perfil de 256 posiciones por
     golpe) en 40-300 Hz para ubicar el cuerpo del bombo, y luego busca el click
     (150-2000 Hz) en los 50 ms previos.
   - Compás: el primer golpe con bombo fuerte se toma como "1" (el tema arranca en el 1).
   - Tonalidad: `chroma_stft` (n_fft 8192) de 90 s del medio + perfiles de Krumhansl →
     nota y modo → Camelot.
   - Volumen: LUFS integrado (pyloudnorm).
3. **Planea**: inicio de mezcla en A = último comienzo de frase de 32 compases que deje la
   transición entera antes del final. B entra en su primer "1".
4. **Mezcla**:
   - B al tempo de A con Rubber Band (`high_quality=False`).
   - B al mismo volumen percibido que A.
   - Ajuste fino de B por correlación de click (peso 1) y graves (peso 0,25).
   - Separa graves (<150 Hz) del resto en ambos temas.
   - Estilo `bajos`: B entra con pasa-altos que se abre (900 → 25 Hz) en el primer cuarto;
     cambio de bajos en la mitad (en un tiempo); A baja en la segunda mitad, pasa-altos que
     se cierra (25 → 1200 Hz) en el último cuarto y reverb con cola sobre B.
   - Estilo `larga`: fundido de potencia constante en toda la transición, con el mismo
     cambio de bajos en la mitad.
   - Limitador + 1 dB de margen. Exporta WAV 24 bit y MP3 320.

## Problemas encontrados y cómo se resolvieron

| Problema | Causa | Solución |
| --- | --- | --- |
| BPM 1 % corrido (129,2 en vez de 128) | `beat_track` de librosa | Búsqueda propia de grilla regular sobre ataques de graves |
| Proceso muerto por falta de RAM | `onset_strength` + `tempo` de librosa a hop 128 (>2 GB por tema) | Envolvente calculada con numpy |
| Tonalidad errónea (F# menor en vez de La menor) | `chroma_cqt` | `chroma_stft` con FFT de 8192 |
| Bombo doble que aparece de a poco | Rubber Band R3 corre ~15 ms cada 16 compases | Motor R2 (`high_quality=False`), ±1 ms |
| Salida a 0 dBFS | El limitador de JUCE normaliza a 0 dB | `Gain(-1 dB)` después del limitador |
| Grilla de T78 a mitad de golpe | El acid a contratiempo engancha la búsqueda | Anclaje por perfil de golpe promedio |
| Desfase fijo de 20-55 ms entre temas | Cada diseño de bombo tiene distinto tiempo entre click y cuerpo | Ajuste fino A↔B priorizando el click |

## Resultados

Temas sintéticos (128 y 131 BPM): BPM exacto, tono correcto, desfase 0,8 ms,
18 s de proceso, 0,9 GB de RAM.

Temas reales (desfase de click medido por bloques de 4 compases después del ajuste):

| Transición | BPM | Tono | Ajuste fino | Click A vs B |
| --- | --- | --- | --- | --- |
| T78 AC/ID → Boost | 127 → 128 | 10A → 8A | 0 ms | 0–3 ms (10 al final, con A casi apagado) |
| Boost → Psychedelic Hypnostate | 128 → 130 | 8A → 8A | +42 ms | 0 ms |
| Psychedelic Hypnostate → Seat Belt | 130 → 130 | 8A → 3A | −33 ms | 0–1 ms |
| Seat Belt → I Am Not Regular | 130 → 135 | 3A → 6B | +1 ms | 0–8 ms |

Tiempo por transición con temas reales: 14 a 40 s. RAM máxima del análisis: ~1,2 GB.

`graficos_4_transiciones.png` muestra la energía de graves y agudos de cada transición
(líneas: entra B · cambio de bajos · sale A). `perfil.png` muestra el perfil de golpe
promedio por bandas que se usó para entender el problema del anclaje.

## Para la Fase 1

- Detectar secciones reales con `allin1` (también da downbeats: reemplaza la heurística
  de "el tema arranca en el 1") y elegir puntos de mezcla por sección (outro de A, intro de B).
- Guardar el análisis por tema en la base y no repetirlo.
- Validar BPM y tono contra Mixxx con los temas del usuario.
- Para encadenar un set: decidir la curva de tempo (B vuelve a su tempo después de la
  transición, o el set sube de tempo en forma gradual).
