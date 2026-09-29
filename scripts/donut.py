"""Genera assets/donut.svg: el donut del instalador de dots como SVG animado.

Port de dots/installer/src/donut.rs. GitHub no ejecuta JS en el README, así
que cada cuadro es un <g> y una animación CSS muestra uno por vez.

Uso: python3 scripts/donut.py
"""

from itertools import groupby
from math import cos, sin, tau
from pathlib import Path

RAMP = ".,-~:;=!*#$@"
CLASSES = "abcdefghijkl"  # una clase CSS por nivel de la rampa
TUBE, RING, DEPTH = 1.0, 2.0, 5.0
THETA_STEPS, PHI_STEPS = 90, 314
TILT_A, TILT_B = 1.0, 0.5
CELL_ASPECT = 2.0

COLS, ROWS = 40, 20
FRAMES = 72
# 2 vueltas de pitch por 1 de yaw: la misma proporción que SPIN_A / SPIN_B
# (0.045 / 0.023) y un ciclo que cierra sin salto.
SPIN_A, SPIN_B = 2 * tau / FRAMES, tau / FRAMES
FRAME_SECONDS = 0.075

# Mismo tamaño que el texto de <pre> en GitHub (85% de 16px).
FONT_SIZE = 13.6
CHAR_W, LINE_H = FONT_SIZE * 0.6, FONT_SIZE * 1.2
OUT = Path(__file__).resolve().parent.parent / "assets" / "donut.svg"


class Canvas:
    """Grilla de celdas con z-buffer: gana el punto más cercano a la cámara."""

    def __init__(self):
        self.cells = [[None] * COLS for _ in range(ROWS)]
        self.depth = [[0.0] * COLS for _ in range(ROWS)]

    def plot(self, col, row, inverse_depth, level):
        if not inside(col, row):
            return
        if inverse_depth <= self.depth[row][col]:
            return
        self.depth[row][col] = inverse_depth
        self.cells[row][col] = level


def inside(col, row):
    return 0 <= col < COLS and 0 <= row < ROWS


def angles():
    for i in range(THETA_STEPS):
        for j in range(PHI_STEPS):
            yield tau * i / THETA_STEPS, tau * j / PHI_STEPS


def surface(theta, phi, pitch, yaw):
    """Proyección estándar del toro: rota el punto del tubo en dos ejes.

    Devuelve (x, y, profundidad inversa, luminancia).
    """
    st, ct = sin(theta), cos(theta)
    sp, cp = sin(phi), cos(phi)
    sa, ca = sin(pitch), cos(pitch)
    sb, cb = sin(yaw), cos(yaw)

    ring, tube = RING + TUBE * ct, TUBE * st
    x = ring * (cb * cp + sa * sb * sp) - tube * ca * sb
    y = ring * (sb * cp - sa * cb * sp) + tube * ca * cb
    inverse_depth = 1.0 / (DEPTH + ca * ring * sp + tube * sa)
    light = cp * ct * sb - ca * ct * sp - sa * st + cb * (ca * st - ct * sa * sp)

    return x, y, inverse_depth, light


def project(x, y, inverse_depth):
    scale = COLS * DEPTH * 3.0 / (8.0 * (TUBE + RING)) * inverse_depth

    return int(COLS / 2 + scale * x), int(ROWS / 2 - scale * y / CELL_ASPECT)


def lit(light):
    """Nivel de la rampa, o None para la cara que no mira a la luz."""
    if light <= 0:
        return None
    return min(int(light * 8), len(RAMP) - 1)


def render(pitch, yaw):
    canvas = Canvas()

    for theta, phi in angles():
        x, y, inverse_depth, light = surface(theta, phi, pitch, yaw)
        level = lit(light)
        if level is not None:
            canvas.plot(*project(x, y, inverse_depth), inverse_depth, level)

    return canvas.cells


def glyph(level):
    return " " if level is None else RAMP[level]


def tspan(level, text):
    return text if level is None else f'<tspan class="{CLASSES[level]}">{text}</tspan>'


def row_svg(index, row):
    """Una fila como <text>, con las celdas del mismo nivel en un solo <tspan>."""
    body = "".join(
        tspan(level, "".join(glyph(cell) for cell in run)) for level, run in groupby(row)
    ).rstrip()

    return f'<text y="{(index + 1) * LINE_H:.1f}">{body}</text>' if body else ""


def frame_svg(index, cells):
    rows = "".join(row_svg(r, row) for r, row in enumerate(cells))

    return f'<g style="animation-delay:{index * FRAME_SECONDS:.2f}s">{rows}</g>'


def style():
    last = len(RAMP) - 1
    # Opacidad = mezcla fondo → acento de Palette::glow, con piso para que el
    # nivel 0 ('.') no desaparezca.
    levels = "".join(f".{CLASSES[n]}{{opacity:{max(n / last, 0.12):.2f}}}" for n in range(len(RAMP)))

    return (
        f"text{{font:{FONT_SIZE}px ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "'Liberation Mono',monospace;white-space:pre;fill:#1f2328}"
        "@media (prefers-color-scheme:dark){text{fill:#e6edf3}}"
        f"g{{visibility:hidden;animation:spin {FRAMES * FRAME_SECONDS:.2f}s steps(1,end) infinite}}"
        f"@keyframes spin{{0%{{visibility:visible}}{100 / FRAMES:.4f}%{{visibility:hidden}}}}"
        f"{levels}"
    )


def main():
    width, height = COLS * CHAR_W, ROWS * LINE_H + FONT_SIZE * 0.4
    frames = "".join(
        frame_svg(k, render(TILT_A + k * SPIN_A, TILT_B + k * SPIN_B)) for k in range(FRAMES)
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}"><style>{style()}</style>{frames}</svg>\n'
    )
    print(f"{OUT} {OUT.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
