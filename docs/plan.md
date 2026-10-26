# Plan: AI Set Builder (techno)

Plan original del 25 de octubre de 2026 (exportado del documento "Plan: AI Set Builder").

## Resumen y decisiones

Una web app personal, alojada en tu servidor, que analiza entre 10 y 25 temas, los ordena como una historia y los mezcla en un set de 1 a 2 horas que se puede retocar a mano y compartir por link con vencimiento a 7 días.

El diferencial frente a lo que ya existe es el **prompt narrativo**: describís lo que querés transmitir (por ejemplo "arranque hipnótico y oscuro, subida lenta, pico industrial a los 70 minutos, cierre melódico") y la IA traduce eso a orden de temas, curva de energía, tipo de transiciones y efectos.

| Tema | Decisión |
| --- | --- |
| Usuario | Solo vos (sin cuentas ni cobro) |
| Control | La IA arma todo; editás orden, puntos de mezcla y efectos en una línea de tiempo |
| Plataforma | Web app en tu servidor, desplegada como stack en Portainer |
| Géneros | Techno, tech house, minimal, dark techno (ampliable) |
| Música | Propia o con licencia, así compartir por link no tiene problema legal |
| Almacenamiento | MinIO en s3.qeva.xyz, links firmados que vencen a los 7 días |
| Desarrollo | Lo construye la IA; stack en Python (backend y audio) + TypeScript (interfaz) |
| Formato de entrada | WAV o FLAC si los podés bajar así; MP3 320 kbps también sirve |
| Formato de salida | MP3 320 kbps para compartir + WAV opcional para archivo |

Sobre el formato: los temas se re-procesan (cambio de tempo, efectos) y se vuelven a comprimir al final. Partir de WAV o FLAC evita perder calidad dos veces; con MP3 320 la diferencia es chica y aceptable para empezar.

## Estudio de mercado

Ya existen herramientas que mezclan automáticamente, pero ninguna combina las tres cosas que querés: control por prompt narrativo, línea de tiempo editable y publicación propia con link que vence. El competidor más cercano es DJ.Studio; el resto mezcla en vivo o arma playlists.

| Herramienta | Qué hace | Precio aprox. | Qué le falta para tu caso |
| --- | --- | --- | --- |
| [DJ.Studio](https://dj.studio/blog/mixing-software-practical-guide-ui-pricing) | Mezcla en línea de tiempo, automix armónico, stems, exporta audio y a Mixcloud | Suscripción \~29 USD/mes o licencia desde \~99 USD | Sin prompt narrativo; app de escritorio; el orden se basa en tonalidad y energía, no en una historia |
| [djay Pro AI](https://help.algoriddim.com/user-manual/djay-pro-windows/mixing-basics/using-automix) | Automix en vivo con transiciones tipo filtro, eco, riser y separación de stems | Gratis + Pro \~7 USD/mes | Pensado para tocar en vivo, no para producir y editar un set terminado |
| [VirtualDJ 2026](https://www.digitaldjtips.com/virtualdj-2026/) | Agrega armado de playlists por lenguaje natural | Licencia | El prompt elige temas de tu biblioteca, no diseña transiciones ni la curva del set |
| rekordbox / Serato | Software profesional de DJ en vivo; rekordbox tiene auto mix por frases | Gratis + planes | Requiere saber mezclar; automix básico |
| Mixxx (lo usás) | DJ en vivo open source con automix por fundido | Gratis | Transiciones simples, sin análisis de estructura ni IA |
| [Rave.DJ](https://djmag.com/news/website-uses-artificial-intelligence-create-your-own-mixes-and-mash-ups) | Mashups automáticos desde links | Gratis / pago | Resultado tipo mashup, poco controlable, no apto para techno serio |
| [Generadores de setlists con IA](https://app.acquire.com/startup/nwenk0xU6EN8cRpz3Xsn3oDDiAy1/X4iog8XtAoQE7KrOoVKO) | Convierten un prompt en una lista de temas con BPM y tonalidad | Suscripción | Solo dan la lista; no producen audio |

**Conclusión:** para uso personal, construirlo tiene sentido. Lo que hace DJ.Studio por suscripción lo podés tener propio, y le sumás el prompt narrativo y el link de descarga en tu infraestructura. Como referencia de mercado, un generador de setlists por prompt se vende con unos 71.000 USD de ingresos anuales, lo que muestra que hay demanda si algún día querés abrirlo a otros.

**Recomendación práctica:** probá la versión de prueba de DJ.Studio una tarde antes de empezar. Te va a mostrar cómo se ve una buena línea de tiempo de mezcla y qué te gustaría distinto.

## Cómo funciona

El análisis se hace una sola vez por tema; después cada set nuevo es un prompt, un plan y un render de pocos minutos.

Flujo del set (6 pasos): 1. Subir temas (WAV/FLAC/MP3, 10 a 25) → 2. Análisis, una sola vez por tema (BPM, tonalidad, energía, compases, secciones, stems) → 3. Plan con IA a partir del prompt narrativo (orden, curva de energía, transiciones y efectos) → 4. Editor opcional (ajustar orden, puntos de mezcla y efectos) → 5. Render del set (tempo, filtros, volumen; MP3 320 y WAV) → 6. Compartir (MinIO + página del set, link que vence a 7 días).

El paso clave es el 3, donde la IA no mezcla audio: arma un plan que el motor de audio ejecuta.

1. **Lee tu prompt** y lo traduce a una curva de energía objetivo por minuto (intro, desarrollo, pico, cierre).
2. **Ordena los temas** buscando el camino que mejor siga esa curva respetando compatibilidad armónica (rueda Camelot: misma tonalidad o vecinas) y saltos de BPM chicos.
3. **Elige cada transición** según las secciones de los dos temas: dónde sale uno (salida o break) y dónde entra el otro (intro), largo en compases (16, 32 o 64) y estilo.
4. **Asigna efectos** con criterio de techno: filtro pasa-bajos en la entrada, cambio de bajos para que no choquen dos bombos, reverb o delay para salidas, riser antes del pico.

El plan queda guardado como datos editables, así que el editor de la fase 3 modifica el mismo plan que generó la IA y solo se vuelve a renderizar lo que cambió.

## Interfaz estilo Mixxx

Se puede, y le suma mucho: la web tiene una vista **Reproductor** que muestra el set terminado sonando como si un DJ lo estuviera mezclando en Mixxx, con los controles moviéndose solos.

| Vista | Para qué |
| --- | --- |
| Biblioteca | Temas subidos con su análisis (BPM, tonalidad, energía, secciones) |
| Editor | Línea de tiempo para ajustar orden, transiciones y efectos |
| Reproductor estilo Mixxx | Ver y escuchar el set terminado; es también la página pública que compartís |

**Qué se ve en el Reproductor:**

- Dos decks (A y B) con onda en movimiento, portada, BPM, tonalidad y tiempo restante.
- Ondas superpuestas alineadas por compás, para ver cómo encajan los temas en cada transición.
- Mixer virtual: crossfader, volumen y EQ de 3 bandas que se mueven siguiendo el plan.
- Rack de efectos: perillas de filtro, reverb, delay y demás que se encienden y giran cuando el plan los usa.
- Línea de tiempo del set completo abajo, con la curva de energía y las transiciones marcadas; clic para saltar.
- Tracklist al costado con el tema actual resaltado.

**Cómo funciona:** el set ya está renderizado en un solo archivo de audio. La interfaz lee el plan (qué suena en cada deck, qué efecto y con cuánta intensidad) y anima los controles sincronizados con la reproducción. No se mezcla en vivo en el navegador, así que corre fluido en cualquier compu o celular.

**Librería de efectos:** el motor de efectos de Mixxx está escrito en C++ dentro de la app y no se puede enchufar directo en Python. Replicamos su catálogo con Pedalboard: filtros pasa-bajos y pasa-altos, filtro resonante, EQ, reverb, delay y eco, chorus, phaser, distorsión, bitcrusher y compresor. Pedalboard además carga plugins VST3, por si más adelante querés sumar efectos de terceros.

**Sobre copiar el diseño:** tomamos la disposición y estética de Mixxx como inspiración (dos decks, mixer al centro, rack de efectos, tema oscuro) pero con diseño propio, sin usar sus skins ni su logo. Así queda con identidad propia si algún día lo abrís a otros.

## Arquitectura técnica y stack

Cinco contenedores en un solo stack de Portainer: interfaz web, API, worker de audio, cola y base de datos; los archivos viven en tu MinIO, no en el disco del servidor.

| Pieza | Tecnología | Para qué |
| --- | --- | --- |
| Interfaz | React + TypeScript + wavesurfer.js | Subir temas, escribir el prompt, editar la línea de tiempo y ver el set en el reproductor estilo Mixxx |
| API | Python + FastAPI | Proyectos, temas, sets, links de descarga |
| Worker de audio | Python (proceso separado) | Análisis, plan y render del set; tareas largas en segundo plano |
| Cola | Redis + RQ o Celery | Encolar análisis y renders sin colgar la web |
| Base de datos | PostgreSQL (o SQLite al inicio) | Metadatos de temas, análisis, versiones del set |
| Archivos | MinIO (s3.qeva.xyz) | Temas originales, stems, sets renderizados, portadas |
| Cerebro del prompt | API de Claude | Convertir tu descripción en un plan de set estructurado (JSON) |

**Librerías de audio (todas open source):**

- **Essentia**: BPM, tonalidad con perfiles para música electrónica, energía, brillo y ritmo.
- **[allin1](https://pypi.org/project/allin1/)**: golpes, primer tiempo de cada compás y secciones (intro, desarrollo, break, salida).
- **Demucs**: separa cada tema en bombo/bajo, batería, melodías y voces; permite transiciones finas como cambiar el bajo de un tema por el del otro.
- **Rubber Band**: cambia el tempo sin cambiar el tono, para igualar BPM.
- **Pedalboard** (de Spotify): filtros, EQ, reverb, delay y compresión.
- **pyloudnorm + FFmpeg**: igualar volumen percibido entre temas y exportar MP3/WAV.

**Links que vencen:** S3 y MinIO permiten links firmados con validez máxima de exactamente 7 días, que coincide con lo que querés. Se suma una regla de ciclo de vida en el bucket para borrar los sets a los 7 días y no llenar el almacenamiento.

## Límites del servidor y solución

Tu servidor (8 GB de RAM, 4-8 núcleos, sin GPU, 160 GB) alcanza para todo el proyecto si el análisis pesado se hace una sola vez por tema y en segundo plano. El cuello de botella es la separación en stems, no el render.

| Tarea | Costo en tu servidor (aprox.) | Cómo lo resolvemos |
| --- | --- | --- |
| BPM, tonalidad, energía (Essentia) | Segundos por tema | Sin problema |
| Estructura y stems (allin1 + Demucs) | Varios minutos por tema y picos de 3-6 GB de RAM | Un tema a la vez, en cola; se guarda el resultado y nunca se repite |
| Plan con IA (API de Claude) | Se procesa fuera de tu servidor | Sin carga local; costo de centavos por set |
| Render del set de 2 h | Varios minutos | Sin problema; se procesa por tramos para no llenar la RAM |
| Espacio | Un set de 2 h en WAV pesa \~1,2 GB; los stems multiplican por 4 cada tema | Todo se guarda en MinIO; el disco local es solo temporal |

Las cifras son estimaciones; las medimos en la fase 1 con tus temas reales.

**Plan B si el análisis resulta lento:** mandar solo la separación de stems a una GPU en la nube que se cobra por segundo de uso (por ejemplo Modal o Replicate). Se activa únicamente al subir temas nuevos, así que el costo mensual sería bajo. Lo decidimos con datos, no ahora.

**Uso de Portainer:** el worker de audio lleva un límite de memoria (por ejemplo 6 GB) para que un análisis pesado nunca tire abajo tus otros proyectos.

## Fases y MVP

El MVP es la fase 2: subir temas, escribir un prompt y descargar un set mezclado que suene bien, aunque todavía sin editor. Cada fase termina con algo que podés escuchar y juzgar.

1. **Fase 0 — Prueba de sonido (sin interfaz).** Un script que toma 2 temas tuyos y genera una transición de 32 compases con BPM igualado y filtros. Objetivo: confirmar que el sonido te convence y medir tiempos reales en tu servidor.
   - Listo cuando: escuchás la transición y no notás el corte.
2. **Fase 1 — Análisis.** Subir temas, analizarlos en cola y guardar BPM, tonalidad (en notación Camelot), energía, compases y secciones. Página simple que muestra cada tema con su onda y secciones coloreadas.
   - Listo cuando: los BPM y tonalidades coinciden con lo que muestra Mixxx.
3. **Fase 2 — MVP: set automático.** Prompt narrativo, orden automático por compatibilidad armónica y curva de energía, transiciones automáticas, render a MP3/WAV, subida a MinIO, link de 7 días y reproductor simple del set terminado con onda y tracklist.
   - Listo cuando: un set de 1 hora suena continuo y sigue la historia que pediste.
4. **Fase 3 — Editor en línea de tiempo.** Arrastrar temas, mover puntos de entrada y salida, elegir tipo de transición, dibujar curvas de filtro y volumen, previsualizar solo una transición sin renderizar todo.
   - Listo cuando: corregís una transición en menos de 2 minutos.
5. **Fase 4 — Reproductor estilo Mixxx y página pública.** Reproductor completo estilo Mixxx (dos decks, mixer, rack de efectos animado) usado también como página pública del set, con portada, tracklist con tiempos, botón de descarga y cuenta regresiva hasta el vencimiento.
6. **Fase 5 — Mejoras.** Transiciones con stems (cambio de bajos, quitar voces), plantillas de estilo por género, guardar prompts favoritos, reanálisis con correcciones manuales.

**Cómo lo construimos:** cada fase se arma con Claude Code sobre un repositorio en GitHub, con un `docker-compose` que importás en Portainer. Vos solo probás y das feedback de oído.

## Riesgos y decisiones pendientes

El riesgo principal es que las transiciones automáticas suenen "de máquina"; por eso la fase 0 prueba el sonido antes de construir cualquier interfaz.

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Transiciones poco naturales | Alto | Reglas de DJ de techno (mezclas largas, cambio de bajos, filtros) + editor manual en fase 3 |
| Análisis lento o sin RAM en el servidor | Medio | Un tema por vez, límite de memoria, análisis guardado; plan B con GPU en la nube |
| Detección de tonalidad o compases errónea | Medio | Corrección manual por tema; comparar con Mixxx en fase 1 |
| La IA interpreta mal el prompt | Medio | El plan se muestra antes de renderizar y se puede ajustar |
| Proyecto que crece sin terminar | Medio | Cada fase entrega algo usable; no pasar a la siguiente sin el criterio de "listo" |
| Música sin licencia compartida por error | Bajo | Solo subís temas propios o con licencia; links privados y con vencimiento |

**Decisiones pendientes:**

- [ ] Nombre del proyecto y subdominio (por ejemplo sets.qeva.xyz)
- [ ] ¿Tenés cuenta en GitHub y en la API de Claude (o preferís otro modelo)?
- [ ] Confirmar si el servidor tiene 4 u 8 núcleos (`nproc` en la terminal)
- [ ] Elegir 2 temas de prueba para la fase 0, idealmente en WAV
- [ ] ¿La página del set debe tener contraseña o alcanza con el link secreto?
