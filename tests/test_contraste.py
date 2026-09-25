"""El contraste de los tokens, medido sobre `colors.css` y no escrito a mano.

Los números del comentario de la paleta y de DESIGN.md se calcularon una vez y
después nadie los volvió a mirar: el borde de los campos quedó en 1,3 a 1 y el
botón principal en claro en 1 a 1, hueso sobre hueso, sin que nada avisara.
Acá se leen los colores del archivo real, en los dos temas, y se exige lo que
pide WCAG: 4,5 a 1 para el texto (1.4.3) y 3 a 1 para lo que dice «esto es un
control» (1.4.11).
"""

import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLORES = os.path.join(RAIZ, "app", "web", "tokens", "colors.css")

# Las superficies donde puede caer un control o un texto.
SUPERFICIES = ("lienzo", "panel", "panel-alto")


def _bloques():
    css = re.sub(r"/\*.*?\*/", "", open(COLORES, encoding="utf-8").read(), flags=re.S)
    oscuro = re.search(r":root\s*\{(.*?)\}", css, re.S)
    claro = re.search(r'\[data-theme="claro"\]\s*\{(.*?)\}', css, re.S)
    assert oscuro and claro, "colors.css cambió de forma: el test tiene que seguirlo"
    base = dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", oscuro.group(1)))
    # El tema claro pisa sólo lo que redefine; la marca y las rampas vienen de :root.
    return {
        "oscuro": base,
        "claro": {**base, **dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", claro.group(1)))},
    }


def _hex(tema, nombre, vistos=()):
    v = tema[nombre].strip()
    m = re.fullmatch(r"var\(--([\w-]+)\)", v)
    if m:
        assert m.group(1) not in vistos, f"ciclo de variables en --{nombre}"
        return _hex(tema, m.group(1), (*vistos, nombre))
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", v), f"--{nombre} no es un color plano: {v}"
    return v


def _luminancia(h):
    def canal(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(h[i : i + 2]) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


TEMAS = _bloques()


@pytest.mark.parametrize("tema", ["oscuro", "claro"])
@pytest.mark.parametrize("token", ["borde-control", "borde-control-hover"])
def test_el_borde_de_los_controles_se_ve(tema, token):
    t = TEMAS[tema]
    for s in SUPERFICIES:
        r = contraste(_hex(t, token), _hex(t, s))
        assert r >= 3, f"{tema}: --{token} sobre --{s} da {r:.2f}, y WCAG 1.4.11 pide 3"


@pytest.mark.parametrize("tema", ["oscuro", "claro"])
def test_el_boton_principal_se_ve_en_los_dos_temas(tema):
    t = TEMAS[tema]
    for s in SUPERFICIES:
        r = contraste(_hex(t, "primario"), _hex(t, s))
        assert r >= 3, f"{tema}: el botón principal sobre --{s} da {r:.2f}"
    r = contraste(_hex(t, "sobre-primario"), _hex(t, "primario"))
    assert r >= 4.5, f"{tema}: el texto del botón principal da {r:.2f}"


@pytest.mark.parametrize("tema", ["oscuro", "claro"])
@pytest.mark.parametrize("token", ["texto", "texto-2", "texto-3"])
def test_el_texto_llega_a_aa_sobre_cualquier_superficie(tema, token):
    t = TEMAS[tema]
    for s in SUPERFICIES:
        r = contraste(_hex(t, token), _hex(t, s))
        assert r >= 4.5, f"{tema}: --{token} sobre --{s} da {r:.2f}"


def test_el_calculo_es_el_de_wcag():
    # Los dos extremos conocidos: blanco sobre negro es 21 a 1, y un color
    # contra sí mismo es 1 a 1.
    assert contraste("#FFFFFF", "#000000") == pytest.approx(21)
    assert contraste("#767471", "#767471") == pytest.approx(1)


def test_los_controles_usan_esos_tokens():
    """Medir el token no sirve si el CSS dibuja el control con otro."""
    css = open(os.path.join(RAIZ, "app", "web", "app.css"), encoding="utf-8").read()

    def regla(selector):
        m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert m, f"no está la regla {selector}"
        return m.group(1)

    assert "var(--borde-control)" in regla(".input")
    assert "var(--borde-control)" in regla('.check input[type="checkbox"]')
    primario = regla(".btn-primary")
    assert "var(--primario)" in primario and "var(--sobre-primario)" in primario


def _mezcla(tema, nombre):
    """Resuelve un `color-mix(in srgb, var(--a) N%, var(--b))` como lo hace CSS:
    promedio de los canales ya codificados, sin pasar a lineal."""
    v = tema[nombre].strip()
    m = re.fullmatch(r"color-mix\(in srgb, var\(--([\w-]+)\) (\d+)%, var\(--([\w-]+)\)\)", v)
    assert m, f"--{nombre} no es la mezcla que el test sabe leer: {v}"
    a, p, b = _hex(tema, m.group(1)), int(m.group(2)) / 100, _hex(tema, m.group(3))
    canales = (round(int(a[i : i + 2], 16) * p + int(b[i : i + 2], 16) * (1 - p)) for i in (1, 3, 5))
    return "#" + "".join(f"{x:02X}" for x in canales)


# Cada estado se escribe con su color saturado sobre su propio relleno.
ESTADOS = [("negativo", "mal-fondo"), ("atencion", "warn-fondo"), ("positivo", "ok-fondo")]


def _peor_par(tema):
    t = TEMAS[tema]
    pares = [contraste(_hex(t, x), _hex(t, s)) for x in ("texto", "texto-2", "texto-3") for s in SUPERFICIES]
    pares += [contraste(_hex(t, c), _mezcla(t, f)) for c, f in ESTADOS]
    return min(pares)


@pytest.mark.parametrize("tema", ["oscuro", "claro"])
@pytest.mark.parametrize(("color", "relleno"), ESTADOS)
def test_cada_estado_se_lee_sobre_su_relleno(tema, color, relleno):
    t = TEMAS[tema]
    r = contraste(_hex(t, color), _mezcla(t, relleno))
    assert r >= 4.5, f"{tema}: --{color} sobre --{relleno} da {r:.2f}"


@pytest.mark.parametrize(
    ("archivo", "coma"),
    [
        (os.path.join("app", "web", "tokens", "colors.css"), True),
        (os.path.join("docs", "DESIGN.md"), True),
        (os.path.join("docs", "DESIGN.en.md"), False),
    ],
)
def test_el_peor_par_escrito_es_el_que_se_mide(archivo, coma):
    """El «peor par» estaba escrito con tres números distintos en tres lugares."""
    texto = open(os.path.join(RAIZ, archivo), encoding="utf-8").read()
    for tema in ("oscuro", "claro"):
        numero = f"{_peor_par(tema):.1f}"
        if coma:
            numero = numero.replace(".", ",")
        assert numero in texto, f"{archivo} no dice {numero} para el tema {tema}"
