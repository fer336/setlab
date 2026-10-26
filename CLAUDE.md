# SET/LAB — Constructor de sets de techno con IA

> Contexto para Claude Code. Este proyecto se planificó en una conversación con Claude
> (claude.ai) entre el 25 y el 26 de octubre de 2026. Todo lo que se decidió está acá y en
> `docs/`. Leé este archivo completo antes de tocar código.

## Quién es el usuario y cómo trabajar con él

- Habla español rioplatense (Argentina). **Respondé siempre en español, con voseo.**
- **No programa.** Le gusta la música electrónica (sobre todo techno) pero no sabe mezclar.
  Usa Mixxx desde la compu, sin controladora. Todo el código lo escribe la IA.
- Juzga los resultados **de oído**. Cada fase tiene que terminar con algo que pueda escuchar
  o ver, y explicarle en palabras simples qué hacer y qué revisar.
- Prefiere Python; TypeScript está bien para la interfaz.
- Le gusta que le pregunten antes de decisiones grandes, pero no lo llenes de preguntas
  técnicas: decidí lo técnico vos y explicale el porqué en una línea.

## La idea

Una web app **personal** (solo para él, sin cuentas ni cobro) en su servidor:

1. Sube 10 a 25 temas (lo que dure un set de 1 o 2 horas).
2. Se analizan una sola vez: BPM, tonalidad (notación Camelot), energía, compases y secciones.
3. Escribe un **prompt narrativo** ("arranque hipnótico y oscuro, subida lenta, pico
   industrial a los 70 minutos, cierre melódico") y la IA arma un plan: orden de temas,
   curva de energía, tipo de transición y efectos de cada mezcla.
4. Opcional: retoca el plan en un editor de línea de tiempo.
5. Se renderiza el set (MP3 320 + WAV).
6. Lo ve en un **reproductor estilo Mixxx** (dos decks, mixer, rack de efectos que se mueven
   solos siguiendo el plan) y lo comparte con un link que **vence a los 7 días**.

Diferencial frente a lo existente (DJ.Studio, djay, rekordbox, VirtualDJ): el prompt
narrativo + editor + publicación propia. Ver `docs/plan.md` (estudio de mercado incluido).

**Música:** propia o con licencia (confirmado por el usuario), por eso compartir por link
está bien. No agregues funciones para bajar música de YouTube/Spotify ni nada parecido.

## Infraestructura del usuario

| Recurso | Detalle |
| --- | --- |
| Servidor | 8 GB RAM, 4 u 8 núcleos (sin confirmar, pedirle `nproc`), 160 GB disco, **sin GPU** |
| Contenedores | Docker gestionado con **Portainer** (stacks) |
| Almacenamiento | **MinIO** compatible S3 en `s3.qeva.xyz` |
| Links de descarga | URLs firmadas de S3: el máximo es exactamente 7 días. Más regla de ciclo de vida en el bucket que borre a los 7 días |

Nunca escribas credenciales en el código ni en commits: usar variables de entorno / `.env`
(con `.env.example` sin valores reales).

## Arquitectura decidida (para las fases 1+)

Un solo stack de Portainer con 5 servicios:

| Servicio | Tecnología |
| --- | --- |
| web | React + TypeScript + wavesurfer.js |
| api | Python + FastAPI |
| worker | Python, proceso aparte para análisis y render (con `mem_limit`, ej. 6 GB) |
| cola | Redis + RQ (o Celery) |
| db | PostgreSQL (o SQLite al principio) |

Archivos (temas, stems, sets) en MinIO; el disco local solo temporal.
El "cerebro" del prompt es la API de Claude: recibe el análisis de los temas + el prompt y
devuelve un **plan de set en JSON** (no mezcla audio). El motor de audio ejecuta el plan.
El editor de la Fase 3 modifica ese mismo JSON.

Librerías de audio: las de la Fase 0 (librosa, pedalboard, scipy, pyloudnorm, ffmpeg) +
para la Fase 1: `allin1` (secciones intro/break/drop/outro y downbeats) y Demucs (stems).
**Ojo con la RAM**: allin1 y Demucs pesan (picos de 3-6 GB); correr de a un tema, en cola, y
guardar el resultado. Plan B si es lento: mandar solo Demucs a una GPU en la nube por uso.

## Estado actual

| Fase | Estado |
| --- | --- |
| 0 — Prueba de sonido (script, 2 temas → transición) | **Hecha y validada con 5 temas reales.** Falta el feedback de oído del usuario |
| 1 — Análisis (subir temas, cola, secciones, página con ondas) | **Siguiente** |
| 2 — MVP: set automático con prompt, render, MinIO, link 7 días, reproductor simple | Pendiente |
| 3 — Editor en línea de tiempo | Pendiente |
| 4 — Reproductor estilo Mixxx + página pública | Pendiente |
| 5 — Mejoras (stems, plantillas por género, prompts favoritos) | Pendiente |

Regla: no pasar a la fase siguiente sin cumplir el criterio de "listo" de la actual
(está en `docs/plan.md`, sección Fases y MVP).

## Fase 0: lo que hay y lo que se aprendió (IMPORTANTE)

Código en `fase0/transicion.py` (CLI). Detalle completo en `docs/fase0/aprendizajes.md`.
Resumen de lo que NO hay que romper al pasar al motor de la app:

1. **Tempo**: no usar `librosa.beat.beat_track` (erró 1 %, = medio segundo de desfase en
   32 compases). Se usa la envolvente de ataques de los graves (<200 Hz) + búsqueda de
   tempo cada 0,005 BPM. Da el BPM exacto en <1 s.
2. **RAM**: `librosa.onset.onset_strength` y `librosa.feature.tempo` con hop 128 usan
   >2 GB por tema. La envolvente se calcula a mano con numpy.
3. **Anclaje de la grilla**: la búsqueda puede engancharse con un bajo a contratiempo
   (pasó con T78 "AC/ID"). Se "dobla" el tema golpe sobre golpe y se busca el ataque del
   bombo (`anclar_en_bombo`): primero el cuerpo grave (40-300 Hz), después el click
   (150-2000 Hz) si se distingue.
4. **Ajuste fino entre temas** (`ajuste_fino`): como el jog de un DJ, compara A y B en toda
   la transición y corre B unos ms. El click pesa 1.0 y los graves 0.25, porque en la
   transición los graves de A y B nunca suenan juntos (se intercambian en la mitad).
   Resultado: clicks alineados a 0-3 ms en las 4 transiciones reales.
5. **Time-stretch**: `pedalboard.time_stretch(..., high_quality=False)`. El motor R3
   (`high_quality=True`) corre los golpes ~15 ms cada 16 compases (bombo doble audible).
6. **Tonalidad**: `chroma_stft` con `n_fft=8192` acierta; `chroma_cqt` falló en la prueba.
7. **Limitador**: el `Limiter` de pedalboard/JUCE lleva la salida a 0 dBFS; se agrega
   `Gain(-1 dB)` después para no recortar en el MP3.
8. Para memoria: medir con `resource.getrusage` en cada etapa nueva; el objetivo es que
   el worker entre cómodo en ~3 GB salvo allin1/Demucs.

Limitaciones conocidas de la Fase 0 (las resuelve la Fase 1):
- Asume 4/4 y que el tema arranca en el primer tiempo.
- El punto de mezcla es "el último bloque de 32 compases", no la sección real. Con un tema
  "preview" cortado (Seat Belt) mezcló sobre el drop en vez de en un outro.
- B queda al tempo de A hasta el final (para encadenar un set hay que volver al tempo
  propio de B o planificar la curva de tempo del set).

Temas reales probados (el usuario los tiene; no están en el repo):
T78 "AC/ID" 127 BPM 10A · Alessio Conti "Boost" 128 BPM 8A · Balthazar & JackRock
"Psychedelic Hypnostate" 130 BPM 8A · ROBPM "Seat Belt" (preview) 130 BPM 3A ·
"I Am Not Regular" 135 BPM 6B. Resultados en `docs/fase0/`.

## Diseño de la interfaz

Tres pantallas diseñadas, en `docs/diseno/` (formato `.dc.html`, se pueden abrir en el
navegador como referencia visual; los datos son de ejemplo):

- `Main.dc.html` — **Reproductor estilo Mixxx**: ondas superpuestas de la transición,
  Deck A (ámbar `#F0A23A`) y Deck B (celeste `#3FC1D6`), mixer con EQ/faders/VU/crossfader,
  2 racks de efectos, línea de tiempo con curva de energía real vs. curva del prompt,
  tracklist.
- `Editor.dc.html` — prompt + "historia del set" en 4 actos, línea de tiempo con 2 carriles,
  estructura por tema, curvas de automatización (filtro, graves, volumen), inspector de la
  transición (tipo, largo 16/32/64, efectos), botón de render parcial.
- `Biblioteca.dc.html` — zona para subir, tabla de temas (BPM, tono, energía, estructura,
  estado del análisis), panel "Nuevo set" (duración, género, prompt, Generar).

Estética: tema oscuro (fondo `#0D0E10`, paneles `#16181B`, bordes `#2B2F35`, texto
`#ECECE8`, secundario `#A2A8B0`), tipografías Archivo + JetBrains Mono (números).
Inspirado en Mixxx pero con diseño propio: **no copiar skins ni logo de Mixxx**.
Nombre provisorio: "SET/LAB" (el nombre final está pendiente).

## Decisiones pendientes (preguntarle al usuario cuando haga falta)

- Nombre definitivo y subdominio (ej. `sets.qeva.xyz`).
- ¿Cuenta de GitHub? ¿API key de Claude (o prefiere otro modelo)?
- Núcleos del servidor (`nproc`).
- ¿La página pública del set con contraseña o alcanza con link secreto?
- Feedback de oído de las 4 transiciones de la Fase 0: bombo doble, coincidencia de BPM/tono
  con Mixxx, qué estilo prefiere (`bajos` o `larga`), cómo suenan las mezclas con tonos que
  chocan (define cuánto pesa la armonía al ordenar).

## Convenciones

- Código y comentarios en español (como `fase0/`), nombres de variables en español.
- Cada fase en su carpeta o paquete, con README en español y pasos para correrlo en el
  servidor (SSH + Docker o stack de Portainer).
- Medir y mostrar números (BPM, ms de desfase, segundos, RAM) al validar: es lo que le da
  confianza al usuario además de escuchar.
- Antes de decir que algo funciona, probalo con audio real o con `fase0/generar_loops.py`.
