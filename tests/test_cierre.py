"""Cerrar la app de verdad.

En el navegador, cerrar la pestaña no le avisaba a nadie, y como el binario no
tiene consola quedaba un servidor corriendo para siempre: uno más por cada doble
clic. En la ventana nativa, cerrar a mitad de un relevamiento lo perdía sin
preguntar. Acá se prueba la decisión con un reloj de mentira, sin esperar
minutos de verdad.
"""

import launcher as L
import server as backend


def _andar(v, desde, hasta, ultimo, trabajando=False):
    """Hace andar al vigía de a un paso, como el launcher; devuelve cuándo cerró."""
    t = desde
    while t <= hasta:
        if v.hay_que_cerrar(t, ultimo, trabajando):
            return t
        t += L.PASO_VIGIA
    return None


def test_si_la_ventana_nunca_abrio_se_espera_y_se_cierra():
    v = L.Vigia(0.0)
    cerro = _andar(v, 0.0, 3600.0, None)
    assert cerro is not None and L.GRACIA_SIN_VENTANA < cerro <= L.GRACIA_SIN_VENTANA + L.PASO_VIGIA


def test_mientras_la_ventana_late_no_se_cierra():
    v = L.Vigia(0.0)
    for t in range(0, 3600, 5):
        assert not v.hay_que_cerrar(float(t), float(t), False)


def test_cuando_deja_de_latir_se_cierra_despues_del_silencio():
    v = L.Vigia(0.0)
    ahora = 0.0
    while ahora <= 60:  # la ventana abrió y latió un minuto
        assert not v.hay_que_cerrar(ahora, ahora, False)
        ahora += 5
    ultimo = 60.0
    while ahora - ultimo <= L.SILENCIO_MAXIMO:
        assert not v.hay_que_cerrar(ahora, ultimo, False), f"cerró a los {ahora - ultimo} s de silencio"
        ahora += 5
    assert v.hay_que_cerrar(ahora, ultimo, False)


def test_con_un_trabajo_corriendo_no_se_cierra_nunca():
    """Cerrar a mitad de un relevamiento lo pierde; el trabajo termina igual."""
    v = L.Vigia(0.0)
    assert _andar(v, 0.0, 3600.0, 5.0, trabajando=True) is None
    # Terminó el trabajo: recién ahí empieza a contar el silencio.
    cerro = _andar(v, 3605.0, 7200.0, 5.0)
    assert cerro is not None and cerro - 3600.0 > L.SILENCIO_MAXIMO


def test_despues_de_una_suspension_no_cierra_de_golpe():
    """Con la máquina dormida, los relojes de la página también: al despertar,
    el silencio acumulado no es una ventana cerrada."""
    v = L.Vigia(0.0)
    assert not v.hay_que_cerrar(5.0, 5.0, False)
    assert not v.hay_que_cerrar(5.0 + 8 * 3600, 5.0, False)
    # Y si de verdad no hay ventana, se cierra después del silencio normal.
    despierto = 5.0 + 8 * 3600
    t = despierto
    while t - despierto <= L.SILENCIO_MAXIMO:
        t += 5
        assert v.hay_que_cerrar(t, 5.0, False) is (t - despierto > L.SILENCIO_MAXIMO)


class _Hilo:
    def __init__(self):
        self.vivo = True

    def is_alive(self):
        return self.vivo


def test_esperar_ventanas_vuelve_cuando_no_queda_ninguna(monkeypatch):
    reloj = {"t": 0.0}
    monkeypatch.setattr(backend.ESTADO, "ultimo_latido", 0.0)

    def dormir(s):
        reloj["t"] += s

    L.esperar_ventanas(_Hilo(), reloj=lambda: reloj["t"], dormir=dormir)
    assert L.SILENCIO_MAXIMO < reloj["t"] <= L.SILENCIO_MAXIMO + 2 * L.PASO_VIGIA


def test_esperar_ventanas_vuelve_si_el_servidor_ya_se_cayo():
    hilo = _Hilo()
    hilo.vivo = False
    L.esperar_ventanas(hilo, reloj=lambda: 0.0, dormir=lambda s: None)


def test_el_latido_queda_registrado():
    antes = backend.ESTADO.ultimo_latido
    try:
        assert backend.api_latido() == {"ok": True}
        assert backend.ESTADO.ultimo_latido is not None
    finally:
        backend.ESTADO.ultimo_latido = antes


def test_el_latido_pasa_por_el_token():
    """Si otra página pudiera latir, podría mantener viva la app para siempre.
    Va entre las rutas que pasan por el control de token de `_post`."""
    assert "/api/latido" in backend.RUTAS_POST_SIN_BODY


# ============================================================
# La ventana nativa pregunta antes de perder un trabajo
# ============================================================


class _Ventana:
    def __init__(self, respuesta=True, falla=False):
        self.respuesta = respuesta
        self.falla = falla
        self.preguntas = []

    def create_confirmation_dialog(self, titulo, mensaje):
        self.preguntas.append((titulo, mensaje))
        if self.falla:
            raise RuntimeError("sin diálogo")
        return self.respuesta


def test_sin_trabajo_se_cierra_sin_preguntar(monkeypatch):
    monkeypatch.setattr(backend.JOBS, "activos", lambda: [])
    v = _Ventana()
    assert L.al_cerrar(v)() is True
    assert v.preguntas == []


def test_con_un_trabajo_pregunta_y_respeta_la_respuesta(monkeypatch):
    monkeypatch.setattr(backend.JOBS, "activos", lambda: ["un trabajo"])
    no = _Ventana(respuesta=False)
    assert L.al_cerrar(no)() is False
    assert len(no.preguntas) == 1
    assert L.al_cerrar(_Ventana(respuesta=True))() is True


def test_si_no_se_puede_preguntar_se_cierra_como_antes(monkeypatch):
    monkeypatch.setattr(backend.JOBS, "activos", lambda: ["un trabajo"])
    assert L.al_cerrar(_Ventana(falla=True))() is True
    assert L.al_cerrar(object())() is True
