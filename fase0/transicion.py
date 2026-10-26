#!/usr/bin/env python3
"""
SET/LAB · Fase 0 — Prueba de sonido.

Toma dos temas, los analiza (BPM, compases, tonalidad, volumen) y genera
una transición de N compases con el tempo igualado y efectos de DJ:

  bajos  -> cambio de bajos en la mitad + filtros + reverb de salida (default)
  larga  -> fundido largo de potencia constante con cambio de bajos

Uso:
  python transicion.py temaA.wav temaB.wav
  python transicion.py temaA.mp3 temaB.mp3 --estilo larga --compases 64
  python transicion.py temaA.wav temaB.wav --completo   # A entero + B entero

Salida (carpeta ./salida por defecto):
  transicion.mp3   el audio para escuchar
  analisis.json    lo que detectó de cada tema y el plan de la mezcla
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pedalboard import Gain, HighpassFilter, Limiter, Pedalboard, Reverb, time_stretch
from scipy.signal import butter, sosfiltfilt

SR = 44100
CORTE_GRAVES_HZ = 150          # frontera entre "bajos" y el resto
MAX_DIF_TEMPO = 0.08           # no estirar más de ±8 %

# ----------------------------------------------------------------------------
# Tonalidad y rueda Camelot
# ----------------------------------------------------------------------------
NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PERFIL_MAYOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
PERFIL_MENOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
CAMELOT_MENOR = {"G#": 1, "D#": 2, "A#": 3, "F": 4, "C": 5, "G": 6, "D": 7, "A": 8, "E": 9, "B": 10, "F#": 11, "C#": 12}
CAMELOT_MAYOR = {"B": 1, "F#": 2, "C#": 3, "G#": 4, "D#": 5, "A#": 6, "F": 7, "C": 8, "G": 9, "D": 10, "A": 11, "E": 12}


def camelot(nota: str, modo: str) -> str:
    return f"{CAMELOT_MENOR[nota]}A" if modo == "menor" else f"{CAMELOT_MAYOR[nota]}B"


def compatibilidad(c1: str, c2: str) -> str:
    n1, l1, n2, l2 = int(c1[:-1]), c1[-1], int(c2[:-1]), c2[-1]
    dist = min((n1 - n2) % 12, (n2 - n1) % 12)
    if c1 == c2:
        return "perfecta (mismo tono)"
    if l1 == l2 and dist == 1:
        return "muy buena (tonos vecinos)"
    if n1 == n2:
        return "buena (relativo mayor/menor)"
    if l1 == l2 and dist == 2:
        return "aceptable (energía sube o baja)"
    return "choca (conviene filtro fuerte o corte)"


# ----------------------------------------------------------------------------
# Análisis
# ----------------------------------------------------------------------------
@dataclass
class Analisis:
    archivo: str
    duracion_s: float
    bpm: float
    primer_tiempo_s: float      # primer golpe de la grilla
    fase_compas: int            # qué golpe (0-3) es el "1" del compás
    tono: str
    camelot: str
    lufs: float


def cargar(path: Path) -> np.ndarray:
    y, _ = librosa.load(str(path), sr=SR, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])
    return y.astype(np.float32)


def detectar_grilla(mono: np.ndarray) -> tuple[float, float]:
    """BPM exacto y primer golpe.

    La música electrónica está cuantizada y tiene bombo en negras, así que:
    1) escuchamos solo los graves (el bombo), 2) estimamos un tempo aproximado,
    3) probamos tempos cada 0,005 BPM y todas las fases, y nos quedamos con la
    grilla regular donde más coinciden los golpes de bombo."""
    hop = 128
    fps = SR / hop
    sos = butter(4, 200, "low", fs=SR, output="sos")
    graves = sosfiltfilt(sos, mono).astype(np.float32)
    # Curva de "ataques de bombo": subida de energía de los graves cada 2,9 ms.
    # (Hecho a mano porque librosa a esta resolución usa >2 GB de RAM por tema.)
    n_frames = len(graves) // hop
    energia = np.sqrt((graves[: n_frames * hop].reshape(n_frames, hop) ** 2).mean(axis=1))
    energia = np.log1p(100 * energia / (energia.max() + 1e-9))
    env = np.maximum(np.diff(energia, prepend=energia[0]), 0)
    env = env / (env.max() + 1e-9)

    # Tempo aproximado por autocorrelación, solo entre 100 y 160 BPM
    espectro = np.fft.rfft(env - env.mean(), n=2 * len(env))
    autocorr = np.fft.irfft(np.abs(espectro) ** 2)[: len(env)]
    lag_min, lag_max = int(fps * 60 / 160), int(fps * 60 / 100) + 1
    lag = lag_min + int(np.argmax(autocorr[lag_min:lag_max]))
    aprox = 60 * fps / lag

    def puntaje(bpm: float) -> tuple[float, float]:
        periodo_f = fps * 60.0 / bpm
        n = int((len(env) - 1) / periodo_f) - 1
        fases = np.arange(0, periodo_f, 0.5)
        idx = (fases[:, None] + np.arange(n)[None, :] * periodo_f).round().astype(int)
        s = env[idx].mean(axis=1)
        i = int(np.argmax(s))
        return float(s[i]), float(fases[i] / fps)

    # búsqueda gruesa (±3 BPM cada 0,05) y después fina (±0,1 cada 0,005)
    gruesa = max((puntaje(b)[0], b) for b in np.arange(aprox - 3, aprox + 3, 0.05))[1]
    mejor = max((puntaje(b)[0], b) for b in np.arange(gruesa - 0.1, gruesa + 0.1, 0.005))[1]
    bpm = round(mejor, 2)
    _, t0 = puntaje(bpm)
    periodo = 60.0 / bpm
    t0 = anclar_en_bombo(mono, periodo, t0 % periodo)
    if t0 > periodo - 0.015:          # un golpe que cae justo en 0 s
        t0 = 0.0
    return bpm, t0


def anclar_en_bombo(mono: np.ndarray, periodo: float, t0: float) -> float:
    """Corre la grilla para que cada golpe caiga justo en el ataque del bombo.

    La búsqueda de tempo puede engancharse con una línea de bajo a contratiempo.
    Acá "doblamos" todo el tema golpe sobre golpe y promediamos la energía de
    40-300 Hz: el bombo aparece como un pico claro. El ataque es el punto donde
    esa energía sube a la mitad de su máximo, saliendo de la zona más silenciosa."""
    sos = butter(4, [40, 300], "band", fs=SR, output="sos")
    e = sosfiltfilt(sos, mono) ** 2
    ventana = int(0.004 * SR)                       # suavizado de 4 ms
    c = np.cumsum(np.concatenate([[0.0], e]))
    e = (c[ventana:] - c[:-ventana]) / ventana

    bins = 256
    golpes = t0 + np.arange(int((len(e) / SR - t0) / periodo) - 1) * periodo
    pos = ((golpes[:, None] + np.arange(bins)[None, :] * periodo / bins) * SR).astype(int)
    perfil = e[pos].mean(axis=0)

    perfil_suave = np.convolve(np.tile(perfil, 3), np.ones(9) / 9, mode="same")[bins:2 * bins]
    quieto = int(np.argmin(perfil_suave))
    orden = np.roll(perfil_suave, -quieto)          # arranca en la zona quieta
    umbral = orden.min() + 0.5 * (orden.max() - orden.min())
    ataque = (quieto + int(np.argmax(orden >= umbral))) % bins
    t_cuerpo = (t0 + ataque * periodo / bins) % periodo

    # El "click" del bombo (150-2000 Hz) llega 10-40 ms antes que el cuerpo grave
    # y es lo que el oído usa para sentir si dos bombos van juntos. Si en los
    # 50 ms previos al cuerpo hay un click claro, anclamos ahí.
    sos = butter(2, [150, 2000], "band", fs=SR, output="sos")
    e = np.abs(sosfiltfilt(sos, mono))
    ventana = int(0.003 * SR)
    c = np.cumsum(np.concatenate([[0.0], e]))
    e = (c[ventana:] - c[:-ventana]) / ventana
    paso = 0.0005                                   # resolución de 0,5 ms
    rel = np.arange(-0.05, 0.005, paso)
    golpes = t_cuerpo + periodo + np.arange(int((len(e) / SR - t_cuerpo) / periodo) - 2) * periodo
    pos = ((golpes[:, None] + rel[None, :]) * SR).astype(int)
    click = e[pos].mean(axis=0)
    i_pico = int(np.argmax(click))
    if click[i_pico] > 1.5 * np.median(click) and i_pico > 0:
        base = click[: i_pico + 1].min()
        mitad = base + 0.5 * (click[i_pico] - base)
        i_ini = int(np.argmax(click[: i_pico + 1] >= mitad))
        return float((t_cuerpo + rel[i_ini]) % periodo)
    return float(t_cuerpo)


def detectar_fase_compas(mono: np.ndarray, bpm: float, t0: float) -> int:
    """El '1' del compás: en techno el tema arranca casi siempre en el
    primer tiempo, así que buscamos el primer golpe con bombo fuerte."""
    sos = butter(4, CORTE_GRAVES_HZ, "low", fs=SR, output="sos")
    graves = sosfiltfilt(sos, mono)
    periodo = 60.0 / bpm
    n = int((len(mono) / SR - t0) / periodo)
    win = int(0.05 * SR)
    energia = np.array([np.sqrt(np.mean(graves[int((t0 + i * periodo) * SR):int((t0 + i * periodo) * SR) + win] ** 2))
                        for i in range(n)])
    primero = int(np.argmax(energia > 0.3 * energia.max()))
    return primero % 4


def detectar_tono(mono: np.ndarray) -> tuple[str, str]:
    # 90 s del medio del tema alcanzan y ahorran tiempo
    medio = len(mono) // 2
    trozo = mono[max(0, medio - 45 * SR): medio + 45 * SR]
    # FFT larga (186 ms): separa bien las notas graves del bajo y usa poca RAM
    croma = librosa.feature.chroma_stft(y=trozo, sr=SR, n_fft=8192, hop_length=2048).mean(axis=1)
    mejor = (-2.0, "C", "mayor")
    for i in range(12):
        for perfil, modo in ((PERFIL_MAYOR, "mayor"), (PERFIL_MENOR, "menor")):
            r = np.corrcoef(croma, np.roll(perfil, i))[0, 1]
            if r > mejor[0]:
                mejor = (r, NOTAS[i], modo)
    return mejor[1], mejor[2]


def analizar(path: Path, audio: np.ndarray) -> Analisis:
    mono = audio.mean(axis=0)
    bpm, t0 = detectar_grilla(mono)
    fase = detectar_fase_compas(mono, bpm, t0)
    nota, modo = detectar_tono(mono)
    lufs = pyln.Meter(SR).integrated_loudness(audio.T)
    return Analisis(path.name, round(len(mono) / SR, 2), round(bpm, 2), round(t0, 4), fase,
                    f"{nota} {modo}", camelot(nota, modo), round(float(lufs), 1))


# ----------------------------------------------------------------------------
# Herramientas de mezcla
# ----------------------------------------------------------------------------
def separar_graves(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sos = butter(4, CORTE_GRAVES_HZ, "low", fs=SR, output="sos")
    graves = sosfiltfilt(sos, x, axis=1).astype(np.float32)
    return graves, (x - graves).astype(np.float32)


def barrido_pasa_altos(x: np.ndarray, f_ini: float, f_fin: float, bloque: int = 512) -> np.ndarray:
    """Filtro pasa-altos que se mueve de f_ini a f_fin a lo largo de x."""
    filtro = HighpassFilter(cutoff_frequency_hz=f_ini)
    tablero = Pedalboard([filtro])
    out = np.zeros_like(x)
    n = x.shape[1]
    for i in range(0, n, bloque):
        frac = i / max(n - 1, 1)
        filtro.cutoff_frequency_hz = float(np.exp(np.log(f_ini) + frac * (np.log(f_fin) - np.log(f_ini))))
        out[:, i:i + bloque] = tablero.process(x[:, i:i + bloque], SR, reset=False)
    return out


def rampa(n: int, ini: int, fin: int, v0: float, v1: float) -> np.ndarray:
    """Envolvente de n muestras: v0 antes de ini, rampa hasta fin, v1 después."""
    e = np.full(n, v0, dtype=np.float32)
    fin = max(fin, ini + 1)
    e[ini:fin] = np.linspace(v0, v1, fin - ini, dtype=np.float32)
    e[fin:] = v1
    return e


def ajuste_fino(seg_a: np.ndarray, seg_b: np.ndarray, periodo: float) -> int:
    """Como el jog de un DJ: corre B unos milisegundos hasta que su bombo calce
    con el de A. Compara la envolvente de graves de ambos temas en la primera
    mitad de la transición y devuelve el corrimiento en muestras (+ = B más tarde)."""
    hop = 16
    max_lag = int(0.2 * periodo * SR / hop)      # hasta ±20 % de un golpe
    n = min(seg_a.shape[1], seg_b.shape[1])

    def env(x: np.ndarray, banda: tuple[int, int]) -> np.ndarray:
        sos = butter(2, banda, "band", fs=SR, output="sos")
        g = np.abs(sosfiltfilt(sos, x.mean(axis=0)))
        m = len(g) // hop
        return g[: m * hop].reshape(m, hop).mean(axis=1)

    def correlacion(ea: np.ndarray, eb: np.ndarray) -> np.ndarray:
        ea, eb = ea - ea.mean(), eb - eb.mean()
        cc = np.array([np.dot(ea[max(0, k):len(ea) + min(0, k)], eb[max(0, -k):len(eb) - max(0, k)])
                       for k in range(-max_lag, max_lag + 1)])
        rango = cc.max() - cc.min()
        return (cc - cc.min()) / rango if rango > 0 else np.zeros_like(cc)

    # Bloques de 4 compases: cada uno vota con el click (150-2000 Hz) y el
    # cuerpo grave (40-150 Hz) del bombo; se suman los votos de toda la mezcla.
    # El click pesa más: en la transición los graves de A y B nunca suenan
    # juntos (se intercambian en la mitad), pero los clicks sí se superponen.
    bloque = int(16 * periodo * SR)
    total = np.zeros(2 * max_lag + 1)
    for s in range(0, n - bloque + 1, bloque):
        sa, sb = seg_a[:, s:s + bloque], seg_b[:, s:s + bloque]
        for banda, peso in (((150, 2000), 1.0), ((40, 150), 0.25)):
            total += peso * correlacion(env(sa, banda), env(sb, banda))
    mejor_k = int(np.argmax(total)) - max_lag
    # k > 0: el bombo de B llega antes que el de A -> leer B desde k muestras
    # antes, así su bombo suena k muestras más tarde y calza con A
    return mejor_k * hop


def igualar_tempo(audio: np.ndarray, bpm_origen: float, bpm_destino: float) -> np.ndarray:
    factor = bpm_destino / bpm_origen
    if abs(factor - 1) < 1e-4:
        return audio
    # high_quality=False: el motor R3 de Rubber Band corre los golpes ~15 ms cada
    # 16 compases (bombo doble audible); el R2 mantiene la grilla clavada (±1 ms)
    # y para cambios menores al 8 % suena igual de bien.
    return time_stretch(audio, SR, stretch_factor=factor, high_quality=False).astype(np.float32)


# ----------------------------------------------------------------------------
# La transición
# ----------------------------------------------------------------------------
def planear(a: Analisis, b: Analisis, compases: int) -> dict:
    periodo = 60.0 / a.bpm
    golpes_mezcla = compases * 4
    total_golpes = int((a.duracion_s - a.primer_tiempo_s) / periodo)
    # Inicio de mezcla en A: el último comienzo de frase (múltiplo de 8 compases)
    # que deje la transición entera antes del final del tema.
    candidatos = [g for g in range(total_golpes) if (g - a.fase_compas) % 32 == 0
                  and g + golpes_mezcla <= total_golpes - 2]
    if not candidatos:
        candidatos = [g for g in range(total_golpes) if (g - a.fase_compas) % 4 == 0
                      and g + golpes_mezcla <= total_golpes - 2]
    if not candidatos:
        raise RuntimeError("El tema A es muy corto para una transición de ese largo.")
    golpe_a = candidatos[-1]
    return {
        "bpm_mezcla": a.bpm,
        "compases": compases,
        "inicio_mezcla_a_s": round(a.primer_tiempo_s + golpe_a * periodo, 3),
        "golpe_entrada_b": b.fase_compas,  # B entra en su primer "1"
        "estiramiento_b": round(a.bpm / b.bpm, 5),
        "compatibilidad": compatibilidad(a.camelot, b.camelot),
    }


def mezclar(A: np.ndarray, B: np.ndarray, a: Analisis, b: Analisis, plan: dict,
            estilo: str, previa_s: float | None, posterior_s: float | None) -> np.ndarray:
    bpm = plan["bpm_mezcla"]
    periodo = 60.0 / bpm
    compas = 4 * periodo

    # 1) B al tempo de A
    B = igualar_tempo(B, b.bpm, bpm)
    t0_b = b.primer_tiempo_s * (b.bpm / bpm) + plan["golpe_entrada_b"] * periodo

    # 2) Volumen percibido de B igual al de A
    lufs_b = pyln.Meter(SR).integrated_loudness(B.T)
    B = B * np.float32(10 ** ((a.lufs - lufs_b) / 20))

    ini_a = int(round(plan["inicio_mezcla_a_s"] * SR))
    ini_b = int(round(t0_b * SR))
    L = int(round(plan["compases"] * compas * SR))
    L = min(L, A.shape[1] - ini_a, B.shape[1] - ini_b)
    corrimiento = ajuste_fino(A[:, ini_a:ini_a + L], B[:, ini_b:ini_b + L], periodo)
    ini_b -= corrimiento
    if ini_b < 0:                      # B arranca en 0 s: le agregamos silencio adelante
        B = np.concatenate([np.zeros((2, -ini_b), np.float32), B], axis=1)
        ini_b = 0
    plan["ajuste_fino_ms"] = round(corrimiento / SR * 1000, 1)
    L = min(L, A.shape[1] - ini_a, B.shape[1] - ini_b)
    seg_a, seg_b = A[:, ini_a:ini_a + L], B[:, ini_b:ini_b + L]

    graves_a, agudos_a = separar_graves(seg_a)
    graves_b, agudos_b = separar_graves(seg_b)

    c = lambda n: int(round(n * compas * SR))           # compases -> muestras
    mitad = c(plan["compases"] / 2)
    un_tiempo = int(periodo * SR)

    # Cambio de bajos en la mitad (rápido, en un tiempo, como en un mixer)
    env_graves_a = rampa(L, mitad - un_tiempo, mitad, 1, 0)
    env_graves_b = rampa(L, mitad - un_tiempo, mitad, 0, 1)

    if estilo == "bajos":
        # B entra con sus agudos filtrados que se van abriendo
        agudos_b = barrido_pasa_altos(agudos_b, 900, 25)
        env_agudos_b = np.sqrt(rampa(L, 0, c(plan["compases"] / 4), 0, 1))
        # A se va: baja volumen en la segunda mitad y se cierra con filtro al final
        env_agudos_a = np.sqrt(rampa(L, mitad, L, 1, 0))
        ultimo_cuarto = c(plan["compases"] * 3 / 4)
        agudos_a = np.concatenate([agudos_a[:, :ultimo_cuarto],
                                   barrido_pasa_altos(agudos_a[:, ultimo_cuarto:], 25, 1200)], axis=1)
    else:  # larga: fundido de potencia constante en toda la transición
        x = np.linspace(0, np.pi / 2, L, dtype=np.float32)
        env_agudos_a, env_agudos_b = np.cos(x), np.sin(x)

    mezcla = graves_a * env_graves_a + agudos_a * env_agudos_a + graves_b * env_graves_b + agudos_b * env_agudos_b

    # Reverb en la salida de A (último cuarto), con cola que se derrama sobre B
    cola = c(4)
    if estilo == "bajos":
        desde = c(plan["compases"] * 3 / 4)
        envio = (agudos_a * env_agudos_a)[:, desde:]
        envio = np.concatenate([envio, np.zeros((2, cola), np.float32)], axis=1)
        wet = Pedalboard([Reverb(room_size=0.85, damping=0.4, wet_level=1.0, dry_level=0.0, width=1.0)])(envio, SR)
        wet *= np.float32(0.35)
    else:
        desde, wet = L, np.zeros((2, 0), np.float32)

    # 3) Armar la salida
    pre = A[:, max(0, ini_a - int(previa_s * SR)) if previa_s else 0:ini_a]
    fin_b = B.shape[1] if posterior_s is None else min(B.shape[1], ini_b + L + int(posterior_s * SR))
    post = B[:, ini_b + L:fin_b]
    out = np.concatenate([pre, mezcla, post], axis=1)
    p = pre.shape[1] + desde
    largo = min(wet.shape[1], out.shape[1] - p)
    out[:, p:p + largo] += wet[:, :largo]

    # 4) Limitador final para que nada sature, con 1 dB de margen para el MP3
    #    (el limitador de JUCE lleva la salida a 0 dBFS)
    return Pedalboard([Limiter(threshold_db=-1.0, release_ms=120), Gain(gain_db=-1.0)])(out, SR)


def exportar(audio: np.ndarray, destino: Path) -> None:
    wav = destino.with_suffix(".wav")
    sf.write(wav, audio.T, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "320k", str(destino)], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="SET/LAB Fase 0: transición automática entre dos temas")
    p.add_argument("tema_a", type=Path, help="tema que sale")
    p.add_argument("tema_b", type=Path, help="tema que entra")
    p.add_argument("--estilo", choices=["bajos", "larga"], default="bajos")
    p.add_argument("--compases", type=int, default=32, choices=[16, 32, 64])
    p.add_argument("--completo", action="store_true", help="exportar A entero + B entero")
    p.add_argument("--salida", type=Path, default=Path("salida"))
    args = p.parse_args()

    args.salida.mkdir(parents=True, exist_ok=True)
    t_ini = time.time()

    print("Cargando temas...")
    A, B = cargar(args.tema_a), cargar(args.tema_b)

    print("Analizando...")
    a, b = analizar(args.tema_a, A), analizar(args.tema_b, B)
    for x, et in ((a, "A"), (b, "B")):
        print(f"  {et}: {x.archivo} · {x.bpm} BPM · {x.tono} ({x.camelot}) · {x.lufs} LUFS · {x.duracion_s/60:.1f} min")

    if abs(a.bpm / b.bpm - 1) > MAX_DIF_TEMPO:
        sys.exit(f"Los tempos están muy lejos ({a.bpm} vs {b.bpm}). Probá con temas más cercanos.")

    plan = planear(a, b, args.compases)
    print(f"  Compatibilidad armónica: {plan['compatibilidad']}")
    print(f"  Mezcla desde el minuto {plan['inicio_mezcla_a_s']/60:.2f} de A, {args.compases} compases, estilo '{args.estilo}'")

    print("Mezclando...")
    previa, posterior = (None, None) if args.completo else (30.0, 30.0)
    out = mezclar(A, B, a, b, plan, args.estilo, previa, posterior)

    destino = args.salida / "transicion.mp3"
    exportar(out, destino)
    (args.salida / "analisis.json").write_text(json.dumps(
        {"tema_a": asdict(a), "tema_b": asdict(b), "plan": plan, "estilo": args.estilo},
        indent=2, ensure_ascii=False))

    print(f"Listo en {time.time() - t_ini:.0f} s → {destino} ({out.shape[1]/SR/60:.1f} min)")


if __name__ == "__main__":
    main()
