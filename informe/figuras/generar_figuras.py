# -*- coding: utf-8 -*-
"""Genera las figuras del informe y la presentación (PDF vectorial).

Los datos provienen de experimentos/resultados/ (los archivos crudos se
parsean cuando existen; los valores del experimento 1 se transcriben del
informe porque su JSON de métricas quedó vacío al capturarlo).

Uso:  python informe/figuras/generar_figuras.py
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
RES = RAIZ / "experimentos" / "resultados"

# ── Identidad visual (color = importancia, no identidad) ─────────────────────
TINTA = "#1C2026"        # texto principal (usachdark)
TINTA2 = "#52514E"       # texto secundario
SUAVE = "#898781"        # ejes y etiquetas menores
GRILLA = "#E1E0D9"       # líneas de grilla
NEUTRO = "#BDBBB4"       # barras sin estado (normal)
TEAL = "#009B8A"         # acento USACH (serie principal)
AMBAR = "#E8A013"        # estado advertencia
ROJO = "#D03B3B"         # estado crítico
NORMAL_BG = "#EDECE7"    # celda "normal" del timeline

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 9,
    "text.color": TINTA,
    "axes.edgecolor": SUAVE,
    "axes.labelcolor": TINTA2,
    "axes.titlesize": 9.5,
    "axes.titlecolor": TINTA,
    "xtick.color": TINTA2,
    "ytick.color": TINTA2,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "axes.grid": False,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "pdf.fonttype": 42,
})

ETAPAS = ["fileteado", "envasado", "sellado", "esterilizacion"]
NOMBRES = {"fileteado": "Fileteado", "envasado": "Envasado",
           "sellado": "Sellado", "esterilizacion": "Esterilización"}
CICLOS = {"fileteado": 4, "envasado": 12, "sellado": 3, "esterilizacion": 7}


def num(x, dec=1):
    """Formatea con coma decimal (convención del informe)."""
    return f"{x:.{dec}f}".replace(".", ",")


def sin_marco(ax, izquierda=True, abajo=True):
    for lado in ["top", "right"] + ([] if izquierda else ["left"]) + ([] if abajo else ["bottom"]):
        ax.spines[lado].set_visible(False)


def cargar_metricas(nombre):
    with open(RES / nombre, encoding="utf-8") as f:
        return json.load(f)


# Datos experimentos 1–3 (espera promedio por etapa, ventana 60 s)
m2 = cargar_metricas("exp2-envasado2-metricas.json")
m3 = cargar_metricas("exp3-envasado3-metricas.json")
esperas = {
    1: {"fileteado": 0.66, "envasado": 67.78, "sellado": 0.68, "esterilizacion": 0.88},
    2: {e: m2["etapas"][e]["espera_promedio_s"] for e in ETAPAS},
    3: {e: m3["etapas"][e]["espera_promedio_s"] for e in ETAPAS},
}
lead = {1: 82.9, 2: m2["lead_time_promedio_s"], 3: m3["lead_time_promedio_s"]}
cuellos = {1: "envasado", 2: "esterilizacion", 3: "esterilizacion"}


def estado_de(espera, etapa):
    if espera >= 3 * CICLOS[etapa]:
        return "critico"
    if espera >= 1.5 * CICLOS[etapa]:
        return "advertencia"
    return "normal"


COLOR_ESTADO = {"normal": NEUTRO, "advertencia": AMBAR, "critico": ROJO}

# ── Figura 1: espera por etapa según réplicas (paneles) ──────────────────────
fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.5), sharey=True)
for ax, reps in zip(axes, [1, 2, 3]):
    vals = [esperas[reps][e] for e in ETAPAS]
    colores = [COLOR_ESTADO[estado_de(v, e)] for v, e in zip(vals, ETAPAS)]
    barras = ax.bar(range(4), vals, width=0.62, color=colores, zorder=3)
    for i, (v, e) in enumerate(zip(vals, ETAPAS)):
        ax.text(i, v + 1.5, num(v), ha="center", va="bottom", fontsize=8,
                color=TINTA if e == cuellos[reps] else TINTA2,
                fontweight="bold" if e == cuellos[reps] else "normal")
    icuello = ETAPAS.index(cuellos[reps])
    ax.text(icuello, vals[icuello] + 9, "cuello", ha="center", va="bottom",
            fontsize=7.5, color=ROJO, fontweight="bold")
    ax.set_title(f"{reps} réplica{'s' if reps > 1 else ''} de envasado", pad=10)
    ax.set_xticks(range(4))
    ax.set_xticklabels([NOMBRES[e][:6] + "." if len(NOMBRES[e]) > 7 else NOMBRES[e]
                        for e in ETAPAS], fontsize=7.6)
    ax.set_ylim(0, 84)
    ax.grid(axis="y", color=GRILLA, lw=0.7, zorder=0)
    sin_marco(ax)
    ax.tick_params(length=0)
axes[0].set_ylabel("Espera promedio (s)")
leyenda = [Patch(fc=NEUTRO, label="normal"), Patch(fc=AMBAR, label="advertencia"),
           Patch(fc=ROJO, label="crítico")]
fig.legend(handles=leyenda, loc="upper right", bbox_to_anchor=(1.0, 1.10),
           ncol=3, frameon=False, fontsize=8)
fig.savefig(AQUI / "fig_espera_replicas.pdf")
plt.close(fig)

# ── Figura 2: lead time según réplicas ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(4.6, 1.9))
ys = [2, 1, 0]
vals = [lead[1], lead[2], lead[3]]
ax.barh(ys, vals, height=0.55, color=[NEUTRO, TEAL, TEAL], zorder=3)
etq = ["1 réplica", "2 réplicas", "3 réplicas"]
deltas = ["", "−21 %", "−5 % adicional"]
for y, v, d in zip(ys, vals, deltas):
    ax.text(v + 1, y, f"{num(v)} s" + (f"   {d}" if d else ""), va="center",
            fontsize=8.5, color=TINTA, fontweight="bold")
ax.set_yticks(ys)
ax.set_yticklabels(etq, fontsize=8.5)
ax.set_xlim(0, 108)
ax.set_xlabel("Lead time promedio de una orden (s)")
ax.grid(axis="x", color=GRILLA, lw=0.7, zorder=0)
sin_marco(ax, izquierda=False)
ax.tick_params(length=0)
fig.savefig(AQUI / "fig_leadtime.pdf")
plt.close(fig)

# ── Figura 3: espera vs. servicio con 2 réplicas (el criterio) ───────────────
fig, ax = plt.subplots(figsize=(5.4, 2.3))
x = range(4)
serv = [m2["etapas"][e]["servicio_promedio_s"] for e in ETAPAS]
espe = [m2["etapas"][e]["espera_promedio_s"] for e in ETAPAS]
w = 0.36
b1 = ax.bar([i - w / 2 - 0.015 for i in x], serv, w, color=NEUTRO, zorder=3,
            label="servicio (duración de la tarea)")
b2 = ax.bar([i + w / 2 + 0.015 for i in x], espe, w,
            color=[ROJO if e == "esterilizacion" else TINTA2 for e in ETAPAS],
            zorder=3, label="espera (tiempo en cola)")
for i, v in zip(x, serv):
    ax.text(i - w / 2 - 0.015, v + 0.5, num(v), ha="center", fontsize=7.6, color=TINTA2)
for i, (v, e) in enumerate(zip(espe, ETAPAS)):
    destaca = e == "esterilizacion"
    ax.text(i + w / 2 + 0.015, v + 0.5, num(v), ha="center", fontsize=7.6,
            color=ROJO if destaca else TINTA2,
            fontweight="bold" if destaca else "normal")
ax.annotate("ciclo más largo,\npero sin atasco", xy=(0.80, 13.2), xytext=(-0.42, 17.5),
            fontsize=7.8, color=TINTA2,
            arrowprops=dict(arrowstyle="-", color=SUAVE, lw=0.8))
ax.annotate("el cuello real", xy=(3.05, 26.3), xytext=(2.2, 28.6), fontsize=8,
            color=ROJO, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=ROJO, lw=0.8))
ax.set_xticks(list(x))
ax.set_xticklabels([NOMBRES[e] for e in ETAPAS], fontsize=8.5)
ax.set_ylabel("Tiempo (s) — 2 réplicas")
ax.set_ylim(0, 31)
ax.grid(axis="y", color=GRILLA, lw=0.7, zorder=0)
sin_marco(ax)
ax.tick_params(length=0)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.savefig(AQUI / "fig_espera_vs_servicio.pdf")
plt.close(fig)

# ── Figura 4: capacidad por etapa vs. ritmo de llegada ───────────────────────
fig, ax = plt.subplots(figsize=(5.6, 2.3))
nombres = ["Fileteado", "Envasado\n×1 réplica", "Envasado\n×2 réplicas",
           "Envasado\n×3 réplicas", "Sellado", "Esterilización"]
caps = [60 / 4, 60 / 12, 2 * 60 / 12, 3 * 60 / 12, 60 / 3, 60 / 7]
llegada = 12.0
colores = [ROJO if c < llegada else NEUTRO for c in caps]
ax.bar(range(6), caps, width=0.6, color=colores, zorder=3)
for i, c in enumerate(caps):
    ax.text(i, c + 0.4, num(c), ha="center", fontsize=7.8,
            color=ROJO if c < llegada else TINTA2,
            fontweight="bold" if c < llegada else "normal")
ax.axhline(llegada, color=TINTA, lw=1.1, ls=(0, (5, 3)), zorder=4)
ax.text(7.15, llegada, "llegada:\n12 lotes/min", fontsize=8, color=TINTA,
        fontweight="bold", ha="right", va="center")
ax.set_xticks(range(6))
ax.set_xticklabels(nombres, fontsize=7.8)
ax.set_ylabel("Capacidad (lotes/min)")
ax.set_ylim(0, 22)
ax.set_xlim(-0.6, 7.25)
ax.grid(axis="y", color=GRILLA, lw=0.7, zorder=0)
sin_marco(ax)
ax.tick_params(length=0)
fig.savefig(AQUI / "fig_capacidad.pdf")
plt.close(fig)

# ── Figura 5: réplica lenta (balanceo por demanda) ───────────────────────────
crudo = (RES / "exp4-replica-lenta.txt").read_text(encoding="utf-8").splitlines()
lotes, nombres4 = [], []
for linea in crudo:
    m = re.match(r"(envasado\S*)\s+(\d+)", linea)
    if m:
        nombres4.append("réplica lenta\n(ciclo 12 s)" if "lento" in m.group(1)
                        else "réplica normal\n(ciclo 6 s)")
        lotes.append(int(m.group(2)))
fig, ax = plt.subplots(figsize=(4.6, 2.3))
colores = [AMBAR if "lenta" in n else TEAL for n in nombres4]
ax.bar(range(len(lotes)), lotes, width=0.55, color=colores, zorder=3)
for i, v in enumerate(lotes):
    ax.text(i, v + 0.25, str(v), ha="center", fontsize=9, fontweight="bold", color=TINTA)
ax.axhline(10, color=TINTA, lw=1.1, ls=(0, (5, 3)), zorder=4)
ax.text(2.72, 10.3, "round-robin: 10 c/u", fontsize=8, color=TINTA,
        fontweight="bold", ha="right")
ax.set_xticks(range(len(lotes)))
ax.set_xticklabels(nombres4, fontsize=8)
ax.set_ylabel("Lotes procesados (de 30)")
ax.set_ylim(0, 14.5)
ax.set_xlim(-0.55, 2.8)
ax.grid(axis="y", color=GRILLA, lw=0.7, zorder=0)
sin_marco(ax)
ax.tick_params(length=0)
fig.savefig(AQUI / "fig_replica_lenta.pdf")
plt.close(fig)

# ── Figura 6: saturación y recuperación (timeline de estados) ────────────────
crudo = (RES / "exp5-saturacion.txt").read_text(encoding="utf-8").splitlines()
tiempos, estados, cuellos5 = [], [], []
for linea in crudo:
    m = re.match(r"t=(\d+)s\s+cuello=(\S+)\s+(.*)", linea)
    if m:
        tiempos.append(int(m.group(1)))
        cuellos5.append(None if m.group(2) == "None" else m.group(2))
        estados.append(dict(p.split(":") for p in m.group(3).split()))
fig, ax = plt.subplots(figsize=(6.6, 2.1))
paso = 15.4  # separación media entre sondas
for j, (t, est) in enumerate(zip(tiempos, estados)):
    for i, e in enumerate(ETAPAS):
        ax.add_patch(Rectangle((t - paso / 2 + 0.6, 3 - i - 0.42), paso - 1.2, 0.84,
                               fc=COLOR_ESTADO.get(est[e], NEUTRO) if est[e] != "normal"
                               else NORMAL_BG, ec="none", zorder=2))
    if cuellos5[j]:
        i = ETAPAS.index(cuellos5[j])
        ax.plot(t, 3 - i, marker="o", ms=3.4, color=TINTA, zorder=4)
ax.set_yticks([3, 2, 1, 0])
ax.set_yticklabels([NOMBRES[e] for e in ETAPAS], fontsize=8.5)
ax.set_xlim(-8, 302)
ax.set_ylim(-0.65, 3.65)
ax.set_xlabel("Segundos desde la ráfaga de 25 órdenes")
ax.axvline(0, color=TINTA, lw=1.0, ls=(0, (4, 3)))
ax.text(4, 3.68, "ráfaga", fontsize=7.8, color=TINTA, fontweight="bold", va="bottom")
ax.axvline(278, color=TINTA2, lw=1.0, ls=(0, (4, 3)))
ax.text(274, 3.68, "278 s: todo normal, sin intervención", fontsize=7.8,
        color=TINTA2, ha="right", va="bottom")
ax.set_ylim(-0.65, 4.05)
leyenda = [Patch(fc=NORMAL_BG, label="normal"), Patch(fc=AMBAR, label="advertencia"),
           Patch(fc=ROJO, label="crítico"),
           Line2D([], [], marker="o", ls="none", ms=4, color=TINTA,
                  label="cuello detectado")]
ax.legend(handles=leyenda, frameon=False, fontsize=7.6, ncol=4,
          loc="upper center", bbox_to_anchor=(0.5, 1.22))
sin_marco(ax)
ax.tick_params(length=0)
fig.savefig(AQUI / "fig_saturacion.pdf")
plt.close(fig)

print("Figuras generadas en", AQUI)
