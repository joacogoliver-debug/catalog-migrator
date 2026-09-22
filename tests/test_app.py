# -*- coding: utf-8 -*-
"""Backend de la app. Trabajos en segundo plano y servidor HTTP. Sin red externa.

Levanta el servidor real en un puerto libre de localhost y le pega con urllib.
No necesita claves ni internet.

Cubre lo que sostiene la app.
  - trabajos en segundo plano, progreso, resultado, error y cancelación
  - que el log del trabajo no crezca sin límite
  - la cadena del idioma, instalador, config, entorno y sistema
  - ruteo, 404 y errores de API con mensaje mostrable
  - las tres defensas del servidor local, token, Host y CSP
  - que no se pueda leer nada fuera de app/web
  - el endpoint que recupera el catálogo tras recargar la página
  - la descarga del ZIP con sus cabeceras
"""

import http.client
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

import pytest

import i18n
import jobs as J
import productos as P
import server as backend
from conftest import _esperar, _track


# ============================================================
# Trabajos en segundo plano
# ============================================================


@pytest.fixture
def registro():
    return J.Registry()


def test_trabajo_que_termina_bien(registro):
    def ok(job):
        job.avance("empezando", 0.1)
        job.avance("mitad", 0.5)
        return {"valor": 42}

    j = registro.lanzar("prueba", ok)
    _esperar(lambda: j.estado in ("listo", "error"))

    assert j.estado == "listo"
    assert j.resultado == {"valor": 42}
    assert j.progreso == 1.0
    assert "mitad" in j.log

    d = j.a_dict(con_log=True)
    assert d["resultado"] == {"valor": 42}
    assert "log" in d


def test_trabajo_que_falla_deja_el_mensaje_y_esconde_el_traceback(registro):
    def falla(job):
        raise RuntimeError("se rompió algo")

    j = registro.lanzar("prueba", falla)
    _esperar(lambda: j.estado in ("listo", "error"))

    assert j.estado == "error"
    assert j.error == "se rompió algo"
    assert any("TRACEBACK" in x for x in j.log)
    # El dict de un trabajo con error NO debe traer resultado.
    assert "resultado" not in j.a_dict()


def test_cancelacion(registro):
    arranco = threading.Event()

    def largo(job):
        arranco.set()
        for i in range(1000):
            job.avance(f"paso {i}", i / 1000)
            time.sleep(0.01)
        return "no deberia llegar"

    j = registro.lanzar("prueba", largo)
    assert arranco.wait(30)
    time.sleep(0.05)
    j.cancelar()
    _esperar(lambda: j.estado in ("cancelado", "listo", "error"))

    assert j.estado == "cancelado"
    assert j.resultado is None


def test_el_log_del_trabajo_no_crece_sin_limite(registro):
    def charlatan(job):
        for i in range(J.MAX_LOG * 3):
            job.avance(f"linea {i}")
        return True

    j = registro.lanzar("prueba", charlatan)
    _esperar(lambda: j.estado in ("listo", "error"), segundos=60)

    assert j.estado == "listo"
    assert len(j.log) <= J.MAX_LOG
    # Conserva el arranque y la cola, que es donde está lo que importa.
    assert j.log[0] == "linea 0"
    assert "linea " + str(J.MAX_LOG * 3 - 1) in j.log[-1]


def test_un_trabajo_inexistente_devuelve_none(registro):
    assert registro.get("nohay") is None


# ============================================================
# La cadena del idioma
# ============================================================
#
# Es la promesa central de la app bilingüe. Quien elige "English" en el
# instalador tiene que encontrarse la app entera en inglés, incluido lo que
# descarga. Esa cadena pasa por cuatro fuentes con prioridades distintas y no
# hay forma de verla de punta a punta sin instalar de verdad, así que se prueba
# la función que las resuelve.


@pytest.fixture
def entorno_de_idioma(monkeypatch, tmp_path):
    """Aísla la config y la raíz, para no leer ni escribir las del usuario."""
    datos = tmp_path / "datos"
    datos.mkdir()
    monkeypatch.setattr(backend, "dir_datos", lambda: str(datos))
    monkeypatch.setattr(backend, "_RAIZ", str(tmp_path))
    monkeypatch.delenv("MIGRADOR_IDIOMA", raising=False)

    class Entorno:
        raiz = str(tmp_path)

        @staticmethod
        def config(valor):
            ruta = datos / "config.json"
            if valor is None:
                ruta.unlink(missing_ok=True)
            else:
                ruta.write_text(json.dumps({"idioma": valor}), encoding="utf-8")

        @staticmethod
        def instalador(valor):
            ruta = tmp_path / "idioma.txt"
            if valor is None:
                ruta.unlink(missing_ok=True)
            else:
                ruta.write_text(valor, encoding="utf-8")

    yield Entorno
    backend.idioma_guardado()


def test_sin_nada_manda_el_sistema_operativo(entorno_de_idioma):
    """Lo único exigible es que devuelva un idioma que la app tenga."""
    entorno_de_idioma.config(None)
    entorno_de_idioma.instalador(None)
    assert backend.idioma_guardado() in i18n.IDIOMAS


def test_el_instalador_deja_su_eleccion_al_lado_del_ejecutable(entorno_de_idioma):
    entorno_de_idioma.config(None)
    entorno_de_idioma.instalador("en")
    assert backend.idioma_guardado() == "en"


def test_un_idioma_txt_con_basura_no_rompe_nada(entorno_de_idioma):
    entorno_de_idioma.config(None)
    entorno_de_idioma.instalador("klingon")
    assert backend.idioma_guardado() in i18n.IDIOMAS


def test_empaquetado_el_idioma_del_instalador_se_busca_al_lado_del_exe(entorno_de_idioma, monkeypatch):
    """No es la misma rama. Empaquetado, la carpeta sale de `sys.executable` y
    no de `_RAIZ`, que apunta adentro del bundle temporal de PyInstaller. Si
    esta rama estuviera mal, el instalador escribiría el idioma.txt donde nadie
    lo lee, y es justo lo único que no se puede ver corriendo desde el código."""
    entorno_de_idioma.instalador("en")
    monkeypatch.setattr(backend, "_RAIZ", os.path.join(entorno_de_idioma.raiz, "no-es-aca"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", os.path.join(entorno_de_idioma.raiz, "Migrador de Catalogos.exe"))

    assert backend.idioma_del_instalador() == "en"


def test_sin_congelar_ese_mismo_idioma_txt_se_busca_en_la_raiz(entorno_de_idioma):
    entorno_de_idioma.instalador("en")
    assert backend.idioma_del_instalador() == "en"


def test_lo_que_el_usuario_eligio_le_gana_al_instalador(entorno_de_idioma):
    entorno_de_idioma.instalador("en")
    entorno_de_idioma.config("es")
    assert backend.idioma_guardado() == "es"


def test_la_variable_de_entorno_le_gana_a_todo(entorno_de_idioma, monkeypatch):
    entorno_de_idioma.instalador("es")
    entorno_de_idioma.config("es")
    monkeypatch.setenv("MIGRADOR_IDIOMA", "en")
    assert backend.idioma_guardado() == "en"


def test_el_endpoint_de_idioma_valida_y_guarda(entorno_de_idioma):
    entorno_de_idioma.config(None)
    entorno_de_idioma.instalador(None)

    assert backend.api_idioma({"idioma": "en"})["idioma"] == "en"
    assert backend.leer_config().get("idioma") == "en"

    with pytest.raises(ValueError):
        backend.api_idioma({"idioma": "klingon"})
    assert backend.leer_config().get("idioma") == "en"


def test_el_cambio_de_idioma_alcanza_a_lo_que_se_descarga(entorno_de_idioma):
    """Los nombres de archivo del ZIP se arman de este lado."""
    import paquete

    entorno_de_idioma.config(None)
    backend.api_idioma({"idioma": "en"})
    assert paquete.nombres_archivos()["validacion"].startswith("_Pre-delivery")


# ============================================================
# Servidor HTTP
# ============================================================


class Cliente:
    """Un cliente mínimo contra el servidor real, con el token de la sesión.

    Los tests leen el token del módulo, que es justo lo que una página abierta
    en otra pestaña del navegador no puede hacer.
    """

    def __init__(self, puerto):
        self.puerto = puerto
        self.base = f"http://127.0.0.1:{puerto}"

    def cab(self, extra=None):
        h = {"X-App-Token": backend.TOKEN}
        if extra:
            h.update(extra)
        return h

    def get(self, ruta):
        # Reintento ante cortes de conexión. Con keep-alive en Windows una
        # consulta suelta puede abortar (WinError 10053). Acá probamos la lógica
        # del backend, no la sincronización de sockets del sistema.
        for intento in range(4):
            try:
                pedido = urllib.request.Request(f"{self.base}{ruta}", headers=self.cab())
                with urllib.request.urlopen(pedido, timeout=20) as r:
                    return r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                return e.code, e.read(), dict(e.headers)
            except (ConnectionError, OSError):
                if intento == 3:
                    raise
                time.sleep(0.2)

    def post(self, ruta, cuerpo):
        req = urllib.request.Request(
            f"{self.base}{ruta}",
            data=json.dumps(cuerpo).encode(),
            headers=self.cab({"Content-Type": "application/json"}),
            method="POST",
        )
        for intento in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                try:
                    return e.code, json.loads(e.read())
                except ValueError:
                    return e.code, {}
            except (ConnectionError, OSError):
                if intento == 3:
                    raise
                time.sleep(0.2)

    def crudo(self, metodo, ruta, cabeceras=None, datos=None):
        """Sin token ni cabeceras, salvo las que se pasen. Para las defensas."""
        req = urllib.request.Request(f"{self.base}{ruta}", data=datos, headers=cabeceras or {}, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            e.read()
            return e.code


@pytest.fixture(scope="module")
def productos_servidor():
    return P.group_products(
        [
            _track(
                "Tema A",
                "Disco Uno",
                2020,
                isrc="ARABC2000001",
                upc="036000291452",
                vid="a1",
                date="2020-01-01",
            ),
            _track(
                "Tema B",
                "Disco Uno",
                2020,
                isrc="ARABC2000002",
                upc="036000291452",
                vid="a2",
                date="2020-01-02",
            ),
            _track("Single", "", 2021, isrc="MALFORMADO", vid="b1", dist="DistroKid", date="2021-01-01"),
        ],
        artist="Artista Test",
    )


@pytest.fixture(scope="module")
def cliente(productos_servidor):
    """El servidor real, con un catálogo ya cargado en memoria."""
    backend.ESTADO.productos = productos_servidor
    backend.ESTADO.artista = "Artista Test"

    srv = backend.crear_servidor(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Cliente(srv.server_address[1])

    def responde():
        try:
            req = urllib.request.Request(f"{c.base}/api/config", headers=c.cab())
            urllib.request.urlopen(req, timeout=2).read()
            return True
        except Exception:
            return False

    assert _esperar(responde, 30, 0.05), "el servidor no respondió"
    yield c

    srv.shutdown()
    srv.server_close()
    backend.ESTADO.limpiar()


# ---- estáticos ----


def test_la_pagina_se_sirve(cliente):
    cod, cuerpo, _ = cliente.get("/")
    assert cod == 200
    assert b"Migrador de Cat" in cuerpo


@pytest.mark.parametrize("ruta", ["/app.css", "/app.js", "/tokens/colors.css"])
def test_los_estaticos_se_sirven(cliente, ruta):
    assert cliente.get(ruta)[0] == 200


def test_un_estatico_inexistente_es_404(cliente):
    assert cliente.get("/no-existe.js")[0] == 404


@pytest.mark.parametrize(
    "intento",
    [
        "/../server.py",
        "/../../relevar_core.py",
        "/%2e%2e/server.py",
        "/..%2f..%2fvalidar.py",
        "/web/../../server.py",
    ],
)
def test_no_se_puede_leer_nada_fuera_de_app_web(cliente, intento):
    assert cliente.get(intento)[0] == 404


# ---- las tres defensas ----


def test_sin_token_no_se_toca_la_api(cliente):
    """Una página cualquiera abierta en el navegador puede pegarle a 127.0.0.1,
    así que «escucha sólo en localhost» no alcanza como defensa."""
    assert cliente.crudo("GET", "/api/config") == 403
    assert cliente.crudo("POST", "/api/validar", {"Content-Type": "application/json"}, b"{}") == 403


def test_con_un_token_equivocado_tampoco(cliente):
    assert cliente.crudo("GET", "/api/config", {"X-App-Token": "no-es-el-token"}) == 403


def test_un_host_ajeno_se_rechaza(cliente):
    """Rebinding de DNS. El pedido llega con un Host que no es localhost."""
    assert (
        cliente.crudo("GET", "/api/config", {"X-App-Token": backend.TOKEN, "Host": "evil.example.com"}) == 403
    )


def test_los_estaticos_no_piden_token_pero_si_controlan_el_host(cliente):
    assert cliente.crudo("GET", "/app.css") == 200
    assert cliente.crudo("GET", "/app.css", {"Host": "evil.example.com"}) == 403


def test_el_token_viaja_adentro_de_la_pagina(cliente):
    """Si el marcador quedara sin reemplazar, el frontend mandaría "{{TOKEN}}" y
    todo daría 403."""
    _cod, cuerpo, _ = cliente.get("/")
    assert backend.TOKEN.encode() in cuerpo
    assert b"{{TOKEN}}" not in cuerpo


# ---- API ----


def test_config(cliente):
    cod, cuerpo, _ = cliente.get("/api/config")
    cfg = json.loads(cuerpo)
    assert cod == 200
    assert cfg["version"] == backend.VERSION
    assert cfg["catalogo_cargado"] is True
    assert cfg["audio_habilitado"] is False, "el audio debe venir apagado por defecto"


def test_el_audio_pedido_con_el_modulo_apagado_no_lo_activa(cliente):
    assert backend.AUDIO_HABILITADO is False


def test_los_terminos_no_se_aceptan_solos(cliente):
    assert cliente.post("/api/terminos", {})[0] == 400


def test_el_catalogo_se_recupera_tras_recargar_la_pagina(cliente):
    """El relevamiento cuesta cuota de YouTube y no queremos repetirlo por un F5
    accidental."""
    cod, cuerpo, _ = cliente.get("/api/catalogo")
    cat = json.loads(cuerpo)
    assert cod == 200
    assert cat["artista"] == "Artista Test"
    assert len(cat["productos"]) == 2
    assert "distribuidoras" in cat["filtros"]
    assert len(cat["productos"][0]["detalle"]) >= 1


def test_validar(cliente, productos_servidor):
    cod, res = cliente.post("/api/validar", {"ids": [p["product_id"] for p in productos_servidor]})
    assert cod == 200
    assert any(h["codigo"] == "isrc_invalido" for h in res["hallazgos"])
    assert res["apto"] is False


def test_una_seleccion_vacia_da_un_error_mostrable(cliente):
    cod, res = cliente.post("/api/validar", {"ids": ["noexiste"]})
    assert cod == 400
    assert "seleccionados" in res.get("error", "")


def test_relevar_sin_url_da_un_error_mostrable(cliente):
    cod, res = cliente.post("/api/relevar", {"url": ""})
    assert cod == 400
    assert "link" in res.get("error", "").lower()


def test_una_ruta_de_api_inexistente_es_404(cliente):
    assert cliente.post("/api/nada", {})[0] == 404


def test_preparar_sin_pedir_nada_es_un_error(cliente, productos_servidor):
    cod, _res = cliente.post(
        "/api/preparar",
        {"ids": [productos_servidor[0]["product_id"]], "planilla": False, "portadas": False, "audio": False},
    )
    assert cod == 400


def test_un_body_invalido_es_400(cliente):
    req = urllib.request.Request(
        f"{cliente.base}/api/validar",
        data=b"{no es json}",
        headers=cliente.cab({"Content-Type": "application/json"}),
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=10)
    assert exc.value.code == 400


# ---- preparar de verdad, sin red ----


@pytest.fixture(scope="module")
def paquete_listo(cliente, productos_servidor):
    """Arma el ZIP con sólo la planilla y espera a que el trabajo termine."""
    cod, res = cliente.post(
        "/api/preparar",
        {
            "ids": [p["product_id"] for p in productos_servidor],
            "planilla": True,
            "portadas": False,
            "audio": False,
        },
    )
    assert cod == 200
    job_id = res["job"]["id"]

    estado = {}

    def termino():
        _c, cuerpo, _h = cliente.get(f"/api/job/{job_id}")
        estado.update(json.loads(cuerpo))
        return estado["estado"] in ("listo", "error")

    assert _esperar(termino, 120, 0.05), "el trabajo no terminó"
    assert estado["estado"] == "listo", estado.get("error")
    return {"job_id": job_id, "resultado": estado["resultado"]}


def test_el_paquete_se_arma(paquete_listo):
    res = paquete_listo["resultado"]
    assert res["bytes"] > 0
    assert res["validacion"]["resumen"]["errores"] >= 1


def test_la_descarga_trae_sus_cabeceras(cliente, paquete_listo):
    cod, cuerpo, hdr = cliente.get(paquete_listo["resultado"]["descarga"])
    assert cod == 200
    assert hdr.get("Content-Type") == "application/zip"
    assert int(hdr["Content-Length"]) == len(cuerpo)

    disp = hdr.get("Content-Disposition") or ""
    assert "attachment" in disp
    # El nombre del archivo que se baja también sigue al idioma. Nada lo cubría,
    # y el sufijo estaba escrito a mano en castellano, así que la app en inglés
    # bajaba un "...-migracion.zip".
    assert "-%s.zip" % i18n.T("paq.f_zip_sufijo") in disp
    assert i18n.T("paq.f_zip_sufijo").isalnum()


def test_el_zip_descargado_esta_integro_y_trae_lo_pedido(cliente, paquete_listo):
    _cod, cuerpo, _hdr = cliente.get(paquete_listo["resultado"]["descarga"])
    z = zipfile.ZipFile(io.BytesIO(cuerpo))
    nombres = z.namelist()

    assert z.testzip() is None
    assert any("Validacion" in n for n in nombres)
    assert any("ingesta" in n for n in nombres)
    assert any("Disco Uno" in n for n in nombres)
    # No pedimos portadas ni audio, así que no deben aparecer.
    assert not any(n.endswith("portada.jpg") for n in nombres)


def test_un_trabajo_largo_por_vez(cliente):
    """Dos relevamientos simultáneos gastan cuota de YouTube por duplicado y
    escriben sobre el mismo catálogo en memoria, así que gana el que termine
    último. Se rechaza el segundo con un mensaje, en vez de dejarlo pasar."""
    lento = backend.JOBS.lanzar("prueba", lambda job: _esperar(lambda: job.cancelado, 5, 0.05))
    try:
        cod, res = cliente.post("/api/relevar", {"url": "https://youtube.com/@x"})
        assert cod == 400
        assert "en curso" in res.get("error", "")
    finally:
        lento.cancelar()


def test_un_trabajo_o_una_descarga_que_no_existen_son_404(cliente):
    assert cliente.get("/api/job/deadbeef")[0] == 404
    assert cliente.get("/api/descargar/deadbeef")[0] == 404


def test_cancelar_por_http(cliente, paquete_listo):
    assert cliente.post(f"/api/job/{paquete_listo['job_id']}/cancelar", {})[0] == 200
    assert cliente.post("/api/job/deadbeef/cancelar", {})[0] == 404


# ---- keep-alive ----


def test_el_cuerpo_se_consume_aunque_la_ruta_no_lo_use(cliente):
    """Bug real. Las rutas «sin body» no leían el cuerpo, y con HTTP/1.1 esos
    bytes quedaban en el socket y se metían adelante del pedido siguiente. El
    método se parseaba como '{}POST' y el servidor devolvía 501. Se veía como un
    error aleatorio de Tidal que se arreglaba al reintentar, porque el reintento
    abría otra conexión. Por eso hay que probar DOS pedidos sobre LA MISMA
    conexión.
    """
    conn = http.client.HTTPConnection("127.0.0.1", cliente.puerto, timeout=20)
    try:
        cuerpo = json.dumps({}).encode()
        conn.request(
            "POST",
            "/api/tidal/desconectar",
            body=cuerpo,
            headers=cliente.cab({"Content-Type": "application/json", "Content-Length": str(len(cuerpo))}),
        )
        r1 = conn.getresponse()
        r1.read()
        assert r1.status == 200

        # Sobre la MISMA conexión, otra ruta. Un id inexistente da un 400
        # determinístico, que prueba que la ruta corrió y produjo SU error, y no
        # un error de parseo del pedido.
        cuerpo2 = json.dumps({"ids": ["noexiste"]}).encode()
        for esperado in ("segunda", "tercera"):
            conn.request(
                "POST",
                "/api/validar",
                body=cuerpo2,
                headers=cliente.cab(
                    {"Content-Type": "application/json", "Content-Length": str(len(cuerpo2))}
                ),
            )
            r = conn.getresponse()
            r.read()
            assert r.status != 501, (
                f"la {esperado} dio {r.status} {r.reason!r}: el cuerpo anterior "
                "contaminó el parseo del pedido siguiente"
            )
            assert r.status == 400
    finally:
        conn.close()


# ============================================================
# La tercera defensa, la CSP
# ============================================================
#
# El token y el Host cortan a quien quiera *entrar* desde afuera. La CSP corta
# lo contrario, que la propia página pida o ejecute algo de afuera. Importa
# porque el contenido que la app muestra viene de YouTube, de Deezer y de Apple,
# y un título con HTML adentro no tiene que poder traer un script ni llamar a
# ningún lado.
#
# Es la defensa más fácil de romper sin darse cuenta, porque es un string suelto
# adentro de un método, y hasta acá no la miraba ningún test.


def _csp(cliente):
    _cod, _cuerpo, hdr = cliente.get("/")
    return hdr.get("Content-Security-Policy") or ""


def test_la_pagina_declara_una_csp(cliente):
    assert _csp(cliente)


@pytest.mark.parametrize(
    "directiva",
    [
        "default-src 'self'",  # nada de afuera, salvo lo que se abra abajo
        "img-src 'self' data:",  # data: lo necesitan las portadas ya descargadas
        "font-src 'self'",  # las tipografías viajan adentro
        "connect-src 'self'",  # la página no puede llamar a ningún lado
        "form-action 'none'",  # ni mandar un formulario afuera
        "base-uri 'none'",  # ni cambiar la base de las URLs relativas
    ],
)
def test_la_csp_declara_la_directiva(cliente, directiva):
    assert directiva in _csp(cliente)


def test_la_csp_no_habilita_ningun_origen_externo(cliente):
    """Si alguna directiva dejara entrar un dominio, un CDN o un comodín, la app
    dejaría de funcionar sin internet y además se abriría la puerta que esto
    cierra."""
    politica = _csp(cliente)
    assert "http://" not in politica
    assert "https://" not in politica
    assert "*" not in politica


def test_los_scripts_inline_siguen_prohibidos(cliente):
    """`'unsafe-inline'` está sólo para los estilos, que la interfaz usa para
    cosas como el ancho de la barra de progreso. Si apareciera en `default-src`
    o en un `script-src`, un título de YouTube con un `<script>` adentro pasaría
    a ejecutarse."""
    directivas = {}
    for parte in _csp(cliente).split(";"):
        parte = parte.strip()
        if parte:
            nombre, _, valores = parte.partition(" ")
            directivas[nombre] = valores

    assert "'unsafe-inline'" not in directivas.get("default-src", "")
    assert "'unsafe-inline'" not in directivas.get("script-src", "")
    assert "'unsafe-inline'" in directivas.get("style-src", "")


def test_la_csp_viaja_junto_al_token_y_no_en_lugar_de_el(cliente):
    """Las tres defensas son tres, no una lista de la que se elige. Este test
    existe para que sacar cualquiera de ellas se note acá."""
    _cod, cuerpo, hdr = cliente.get("/")
    assert hdr.get("Content-Security-Policy")
    assert backend.TOKEN.encode() in cuerpo
    assert cliente.crudo("GET", "/api/config", {"Host": "evil.example.com"}) == 403


def test_la_pagina_cumple_su_propia_csp():
    """Una CSP que la página incumple es una CSP que alguien va a aflojar.

    Se mira el archivo y no la respuesta: lo que importa es que nadie agregue un
    `<script>` inline o un recurso por CDN, que en el navegador fallarían en
    silencio para quien no tenga la consola abierta.
    """
    import re
    from conftest import RAIZ

    html = open(os.path.join(RAIZ, "app", "web", "index.html"), encoding="utf-8").read()

    # Ningún <script> con código adentro. Los tres que hay son archivos.
    inline = [m for m in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S) if m.strip()]
    assert inline == []

    # Ningún recurso de afuera. Los enlaces de navegación (un <a href>) no
    # cuentan: la CSP no los bloquea y no cargan nada.
    externos = [u for u in re.findall(r'\bsrc="([^"]+)"', html) if "//" in u]
    externos += [u for u in re.findall(r'<link[^>]+href="([^"]+)"', html) if "//" in u]
    assert externos == []


def test_las_tipografias_no_vienen_de_ningun_cdn():
    """`font-src 'self'` sería mentira si el CSS pidiera una fuente afuera, y la
    app dejaría de verse igual sin internet."""
    import glob
    import re
    from conftest import RAIZ

    urls = []
    for ruta in glob.glob(os.path.join(RAIZ, "app", "web", "*.css")) + glob.glob(
        os.path.join(RAIZ, "app", "web", "tokens", "*.css")
    ):
        with open(ruta, encoding="utf-8") as f:
            urls += [u for u in re.findall(r"url\(['\"]?([^'\")]+)", f.read()) if "//" in u]
    assert urls == []
