"""Mide la alineación de bombos (click y graves) en las 4 transiciones de prueba.

Uso: python medir_alineacion.py <carpeta_con_temas> [--ajuste]
Espera los archivos 1_T78_ACID.mp3, 2_Boost.mp3, 3_Hypnostate.mp3, 4_SeatBelt.mp3 y
5_IAmNotRegular.mp3 (editá la lista de pares al final para usar otros temas).
"""
import sys, numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import transicion as T
from pathlib import Path
from scipy.signal import butter, sosfiltfilt
D = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'temas/'
D = D if D.endswith('/') else D + '/'
usar_ajuste = '--ajuste' in sys.argv
hop = 16
def env(x, banda):
    g = np.abs(sosfiltfilt(butter(2, banda, 'band', fs=T.SR, output='sos'), x.mean(0)))
    n = len(g) // hop; return g[:n*hop].reshape(n, hop).mean(1)
def lag(ea, eb, m):
    ea = ea - ea.mean(); eb = eb - eb.mean()
    cc = [np.dot(ea[max(0,k):len(ea)+min(0,k)], eb[max(0,-k):len(eb)-max(0,k)]) for k in range(-m, m+1)]
    return (int(np.argmax(cc)) - m) * hop / T.SR * 1000
for a_, b_ in [('1_T78_ACID','2_Boost'),('2_Boost','3_Hypnostate'),('3_Hypnostate','4_SeatBelt'),('4_SeatBelt','5_IAmNotRegular')]:
    A = T.cargar(Path(D+a_+'.mp3')); B = T.cargar(Path(D+b_+'.mp3'))
    a = T.analizar(Path(a_), A); b = T.analizar(Path(b_), B); plan = T.planear(a, b, 32)
    B2 = T.igualar_tempo(B, b.bpm, a.bpm); per = 60/a.bpm
    ia = int(round(plan['inicio_mezcla_a_s']*T.SR)); ib = int(round((b.primer_tiempo_s*b.bpm/a.bpm + plan['golpe_entrada_b']*per)*T.SR))
    L = int(128*per*T.SR); c = 0
    if usar_ajuste:
        c = T.ajuste_fino(A[:, ia:ia+L], B2[:, ib:ib+L], per); ib -= c
    if ib < 0: B2 = np.concatenate([np.zeros((2, -ib), np.float32), B2], 1); ib = 0
    m = int(0.2*per*T.SR/hop); cl = []; gr = []
    for bar in range(0, 32, 4):
        s = int(bar*4*per*T.SR); n = int(4*4*per*T.SR)
        sa, sb = A[:, ia+s:ia+s+n], B2[:, ib+s:ib+s+n]
        cl.append(lag(env(sa, (150, 2000)), env(sb, (150, 2000)), m)); gr.append(lag(env(sa, (40, 150)), env(sb, (40, 150)), m))
    print(f'{a_:>14} -> {b_:16} ajuste {c/T.SR*1000:+5.1f} | click (ms): {np.round(cl).astype(int).tolist()} | graves (ms): {np.round(gr).astype(int).tolist()}', flush=True)
