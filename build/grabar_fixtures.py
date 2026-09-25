"""
Graba respuestas reales de Deezer, de iTunes y de la YouTube Data API para los
tests de contrato.

    python build/grabar_fixtures.py              Deezer e iTunes
    python build/grabar_fixtures.py --youtube    la YouTube Data API

Esto es lo ÚNICO del repositorio que toca la red. Los tests no: leen los
archivos que este script deja en `tests/fixtures/` y no salen a ningún lado.

Por qué existe
--------------
Los tests construían sus dobles a mano, con la forma que el código espera. Eso
prueba que el código es consistente consigo mismo, no que entienda lo que las
APIs devuelven de verdad. El día que Deezer renombre un campo, un doble escrito
a mano sigue pasando y el usuario se entera solo.

Grabar la respuesta tal como llegó cierra esa distancia, y deja además la
evidencia a la vista: cualquiera puede abrir el JSON y comparar.

Qué se graba y qué no
---------------------
Se graba la respuesta **completa**, sin recortar campos. Recortarla a lo que hoy
leemos anularía el sentido del ejercicio, porque el test dejaría de ver la parte
de la respuesta que todavía no usamos y que mañana vamos a querer usar.

Son APIs públicas y sin clave, y lo que devuelven es metadata de catálogo
publicada (título, artista, ISRC, UPC, duración). No hay nada personal ni nada
de un catálogo privado: son discos conocidos, elegidos justamente para que
cualquiera pueda verificar que los datos son los que dicen ser.

YouTube necesita clave, y la clave NUNCA entra al repositorio. Se lee de la
variable `MIGRADOR_CLAVE_YT` o `YOUTUBE_API_KEY`, viaja en una cabecera (no en
la URL que queda escrita en cada fixture), y antes de guardar se verifica que
no aparezca en ningún lado. Grabarlo cuesta unas 105 unidades de la cuota del
día: la búsqueda del canal Topic cuesta 100.

Si alguna respuesta cambia y un test se cae, la pregunta correcta no es «cómo
actualizo la fixture» sino «qué cambió en la API y qué hay que arreglar en el
código». Volver a correr este script es el último paso, no el primero.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "tests", "fixtures")

sys.path.insert(0, os.path.join(RAIZ, "src"))

from migrador.portadas import USER_AGENT as UA_ITUNES  # noqa: E402
from migrador.relevar_core import DEEZER_API  # noqa: E402
from migrador.relevar_core import USER_AGENT as UA_DEEZER  # noqa: E402

ITUNES = "https://itunes.apple.com"

# El caso de prueba. Un disco conocido, con ISRC y UPC públicos, para que
# cualquiera pueda verificar que la fixture dice la verdad.
ARTISTA = "Daft Punk"
ALBUM = "Random Access Memories"
TRACK = "Get Lucky"


# El canal Topic de Daft Punk: un catálogo conocido y público, el mismo artista
# de las fixtures de Deezer. Con doce videos por página alcanza para ver la
# paginación sin grabar quinientos.
TOPIC = "UCRr1xG_2WIDs18a6cIiCxeA"
POR_PAGINA = 12
YOUTUBE = "https://www.googleapis.com/youtube/v3"


def pedir(url, user_agent, cabeceras=None):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, **(cabeceras or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def guardar(nombre, url, datos):
    """Deja el JSON con una cabecera que dice de dónde salió y cuándo."""
    os.makedirs(DESTINO, exist_ok=True)
    ruta = os.path.join(DESTINO, nombre)
    envoltorio = {
        "_grabado": {
            "url": url,
            "fecha": time.strftime("%Y-%m-%d"),
            "como": "python build/grabar_fixtures.py",
        },
        "respuesta": datos,
    }
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(envoltorio, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    print(f"    {nombre:34} {os.path.getsize(ruta) / 1024:6.1f} KB")


def grabar_youtube():
    """Las respuestas de la YouTube Data API que usa el relevamiento."""
    clave = (os.environ.get("MIGRADOR_CLAVE_YT") or os.environ.get("YOUTUBE_API_KEY") or "").strip()
    if not clave:
        sys.exit("Falta la clave: poné MIGRADOR_CLAVE_YT o YOUTUBE_API_KEY en el entorno.")

    def yt(nombre, endpoint, **params):
        url = f"{YOUTUBE}/{endpoint}?{urllib.parse.urlencode(params)}"
        datos = pedir(url, UA_DEEZER, {"X-Goog-Api-Key": clave, "Accept": "application/json"})
        # La última puerta: si la clave apareciera en la URL o en la respuesta,
        # no se escribe nada. Una clave que llega a un commit ya está filtrada.
        if clave in url or clave in json.dumps(datos):
            sys.exit(f"La clave apareció en {nombre}: no lo guardo.")
        guardar(nombre, url, datos)
        return datos

    canal = yt("youtube_channels.json", "channels", part="snippet,contentDetails", id=TOPIC)
    subidas = canal["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pag1 = yt(
        "youtube_playlist_1.json",
        "playlistItems",
        part="contentDetails",
        maxResults=POR_PAGINA,
        playlistId=subidas,
    )
    yt(
        "youtube_playlist_2.json",
        "playlistItems",
        part="contentDetails",
        maxResults=POR_PAGINA,
        playlistId=subidas,
        pageToken=pag1["nextPageToken"],
    )
    ids = ",".join(i["contentDetails"]["videoId"] for i in pag1["items"])
    yt("youtube_videos.json", "videos", part="snippet,statistics,contentDetails", id=ids)
    yt(
        "youtube_search_topic.json",
        "search",
        part="snippet",
        q="Daft Punk - Topic",
        type="channel",
        maxResults=10,
    )
    # Un canal que no existe: la API contesta 200 sin items, y es contrato.
    yt("youtube_channels_vacio.json", "channels", part="snippet,contentDetails", id="UC" + "0" * 22)


def main():
    print(f">>> Grabando fixtures en {os.path.relpath(DESTINO, RAIZ)}")
    if "--youtube" in sys.argv:
        grabar_youtube()
        print("\n    Listo. Revisá el diff antes de commitear.")
        return 0

    # --- Deezer -----------------------------------------------------------
    # 1. La búsqueda estricta, que es la que el código intenta primero.
    q = urllib.parse.quote(f'track:"{TRACK}" artist:"{ARTISTA}"')
    url = f"{DEEZER_API}/search?q={q}&limit=5"
    estricta = pedir(url, UA_DEEZER)
    guardar("deezer_search_estricta.json", url, estricta)

    # 2. La búsqueda libre, que es a la que cae cuando la estricta no devuelve
    #    nada. Vale la pena grabar las dos: el respaldo existe porque el filtro
    #    estricto falla seguido, y una fixture de sólo el camino feliz no lo
    #    demostraría.
    q2 = urllib.parse.quote(f"{TRACK} {ARTISTA}")
    url = f"{DEEZER_API}/search?q={q2}&limit=5"
    libre = pedir(url, UA_DEEZER)
    guardar("deezer_search_libre.json", url, libre)

    items = (libre.get("data") or []) or (estricta.get("data") or [])
    if not items:
        sys.exit("Deezer no devolvió nada. Sin eso no se puede grabar el resto.")
    track_id = items[0]["id"]
    album_id = (items[0].get("album") or {}).get("id")

    # 3. El track suelto, que el código pide cuando la búsqueda no trae el ISRC.
    url = f"{DEEZER_API}/track/{track_id}"
    guardar("deezer_track.json", url, pedir(url, UA_DEEZER))

    # 4. El álbum, que es de donde sale el UPC.
    url = f"{DEEZER_API}/album/{album_id}"
    album = pedir(url, UA_DEEZER)
    guardar("deezer_album.json", url, album)

    # --- iTunes -----------------------------------------------------------
    upc = album.get("upc") or ""

    # 5. La búsqueda por texto, con el mismo limit que usa el código.
    params = {"term": f"{ARTISTA} {ALBUM}", "entity": "album", "limit": 25}
    url = f"{ITUNES}/search?{urllib.parse.urlencode(params)}"
    guardar("itunes_search.json", url, pedir(url, UA_ITUNES))
    time.sleep(3)  # Apple limita ~20 pedidos por minuto sin clave

    # 6. El lookup por UPC, que es el camino exacto y sin ambigüedad.
    if upc:
        url = f"{ITUNES}/lookup?{urllib.parse.urlencode({'upc': upc})}"
        guardar("itunes_lookup_upc.json", url, pedir(url, UA_ITUNES))
    else:
        print("    (Deezer no trajo UPC: no grabo el lookup de iTunes)")

    # 7. Una búsqueda que no encuentra nada. El camino del error también es
    #    contrato, y es el que nadie graba.
    params = {"term": "zzzz qqqq no existe este disco 12345", "entity": "album", "limit": 25}
    url = f"{ITUNES}/search?{urllib.parse.urlencode(params)}"
    guardar("itunes_search_vacia.json", url, pedir(url, UA_ITUNES))

    print("\n    Listo. Revisá el diff antes de commitear: si algo cambió, la")
    print("    pregunta es qué cambió en la API, no cómo actualizar el archivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
