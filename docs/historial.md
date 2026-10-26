# Historial de la conversación de planificación

Resumen cronológico de cómo se llegó a cada decisión (claude.ai, 25-26 de octubre de 2026).

1. **Idea inicial.** El usuario quiere armar sets de techno sin saber mezclar: subir temas,
   que se analicen (armonía, compases, BPM, estructura) y que la IA los una con efectos,
   para compartir el set por link con descarga durante 7 días desde su S3.
2. **Primeras preguntas.** Respuestas: herramienta solo para él; la IA arma todo y él
   edita; web app; música propia o con licencia.
3. **Segunda ronda.** No programa (usa IA), prefiere Python; servidor de 8 GB RAM,
   4-8 núcleos, 160 GB; Portainer; MinIO en s3.qeva.xyz; géneros techno, tech house,
   minimal, dark techno; tiene los temas en MP3 (puede bajarlos en otro formato); no
   entiende de teoría musical: quiere que la IA decida lo mejor pero poder ajustar a mano;
   quiere que la IA arme el set como una historia (intro, nudo, desenlace) a partir de un
   prompt; quiere tracklist y página para escuchar; usa Mixxx desde la compu.
4. **Estudio de mercado y plan** → documento "Plan: AI Set Builder" (`docs/plan.md`).
   Competidor más cercano: DJ.Studio.
5. **Agregado:** la web tiene que mostrar el set terminado, con una interfaz similar a Mixxx
   y librerías de efectos. Se agregó la sección "Interfaz estilo Mixxx" y se ajustaron las
   fases (reproductor simple en el MVP, completo en la Fase 4). Efectos con Pedalboard.
6. **Diseño de la interfaz:** 3 pantallas (Reproductor, Editor, Biblioteca), en
   `docs/diseno/`. Al usuario le gustó.
7. **Fase 0:** script de transición, probado primero con loops sintéticos y después con
   5 temas reales que subió el usuario. Ver `docs/fase0/aprendizajes.md`.
8. **Traspaso a Claude Code** (este repositorio).
