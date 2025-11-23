import json
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import os
import requests
import view.oversound_view as osv
import controller.msvc_servers as servers

app = FastAPI()
osv = osv.View()

def obtain_user_data(token: str):
    if not token:
        return None
    try:
        resp = requests.get(f"{servers.SYU}/auth", timeout=2, headers={"Accept": "application/json", "Cookie":f"oversound_auth={token}"})
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None

# Configuración de CORS
origins = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
    "http://10.1.1.4:8000",
    "http://10.1.1.4:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Lista de orígenes permitidos
    allow_credentials=True,  # Permitir cookies y credenciales
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Obtener la ruta absoluta del directorio static
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    return osv.get_error_view(request, userdata, "Te has columpiado con la URL", str(exc))

@app.exception_handler(500)
def internal_server_error_handler(request: Request, exc: Exception):
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    return osv.get_error_view(request, userdata, "Algo ha salido mal", str(exc))

@app.exception_handler(422)
def unproc_content_error_handler(request: Request, exce: Exception):
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    return osv.get_error_view(request, userdata, "Te has columpiado", str(exce))

@app.exception_handler(404)
def unproc_content_error_handler(request: Request, exce: Exception):
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    return osv.get_error_view(request, userdata, "Te has columpiado", str(exce))


@app.get("/label/{labelId}")
def get_label(request: Request, labelId: int):
    """
    Ruta para mostrar el perfil de una discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    try:
        # Obtener información de la discográfica
        label_resp = requests.get(f"{servers.TYA}/label/{labelId}", timeout=2, headers={"Accept": "application/json"})
        label_resp.raise_for_status()
        label_data = label_resp.json()
        
        # Resolver artistas de la discográfica
        artists = []
        if label_data.get('artists'):
            for artist_id in label_data['artists']:
                try:
                    artist_resp = requests.get(f"{servers.TYA}/artist/{artist_id}", timeout=2, headers={"Accept": "application/json"})
                    artist_resp.raise_for_status()
                    artists.append(artist_resp.json())
                except requests.RequestException:
                    pass
        label_data['artists'] = artists
        label_data['artists_count'] = len(artists)
        
        # Determinar si es propietario o miembro
        is_owner = userdata and userdata.get('userId') == label_data.get('ownerId')
        is_member = userdata and userdata.get('artistId') in [a.get('artistId') for a in artists]
        
        return osv.get_label_view(request, label_data, is_owner, is_member, userdata, servers.SYU)
        
    except requests.RequestException as e:
        print(e)
        return osv.get_error_view(request, userdata, "No se pudo cargar la discográfica", str(e))



@app.get("/label/create")
def get_label_create(request: Request):
    """
    Ruta para la página de crear discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return RedirectResponse("/login")
    
    # Verificar si el usuario ya tiene una discográfica
    try:
        existing_label_resp = requests.get(f"{servers.TYA}/user/{userdata.get('userId')}/label", timeout=2, headers={"Accept": "application/json"})
        if existing_label_resp.ok:
            existing_label = existing_label_resp.json()
            if existing_label:
                return RedirectResponse(f"/label/{existing_label.get('id')}/edit")
    except requests.RequestException:
        pass
    
    return osv.get_label_create_view(request, None, userdata, servers.SYU)



@app.post("/label/{labelId}/join")
async def join_label(request: Request, labelId: int):
    """
    Ruta para que un artista se una a una discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        # Unirse a la discográfica
        join_resp = requests.post(
            f"{servers.TYA}/label/{labelId}/artist/{userdata.get('artistId')}",
            timeout=2,
            headers={"Accept": "application/json"}
        )
        
        if join_resp.ok:
            return JSONResponse(content={"message": "Te has unido a la discográfica"})
        else:
            error_data = join_resp.json() if join_resp.text else {}
            return JSONResponse(content=error_data, status_code=join_resp.status_code)
    
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": "Error al unirse"}, status_code=500)


@app.post("/label/{labelId}/leave")
async def leave_label(request: Request, labelId: int):
    """
    Ruta para que un artista salga de una discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        # Salir de la discográfica
        leave_resp = requests.delete(
            f"{servers.TYA}/label/{labelId}/artist/{userdata.get('artistId')}",
            timeout=2,
            headers={"Accept": "application/json"}
        )
        
        if leave_resp.ok:
            return JSONResponse(content={"message": "Has salido de la discográfica"})
        else:
            error_data = leave_resp.json() if leave_resp.text else {}
            return JSONResponse(content=error_data, status_code=leave_resp.status_code)
    
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": "Error al salir"}, status_code=500)


@app.delete("/label/{labelId}/artist/{artistId}")
async def remove_artist_from_label(request: Request, labelId: int, artistId: int):
    """
    Ruta para que el propietario elimine un artista de la discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        # Verificar que sea propietario
        label_resp = requests.get(f"{servers.TYA}/label/{labelId}", timeout=2, headers={"Accept": "application/json"})
        label_resp.raise_for_status()
        label_data = label_resp.json()
        
        if label_data.get('ownerId') != userdata.get('userId'):
            return JSONResponse(content={"error": "No tienes permisos"}, status_code=403)
        
        # Eliminar artista
        remove_resp = requests.delete(
            f"{servers.TYA}/label/{labelId}/artist/{artistId}",
            timeout=2,
            headers={"Accept": "application/json"}
        )
        
        if remove_resp.ok:
            return JSONResponse(content={"message": "Artista eliminado"})
        else:
            error_data = remove_resp.json() if remove_resp.text else {}
            return JSONResponse(content=error_data, status_code=remove_resp.status_code)
    
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": "Error al eliminar artista"}, status_code=500)


@app.get("/user/label")
def get_user_label(request: Request):
    """
    Ruta para obtener la discográfica del usuario actual (si existe)
    DEPRECADO: La funcionalidad de discográficas está en proceso de descontinuación.
    Siempre devuelve que no hay discográfica sin consultar el backend.
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # Siempre devolver que no hay discográfica (funcionalidad descontinuada)
    return JSONResponse(content={"has_label": False}, status_code=200)


@app.get("/artist/{artistId}/label")
def get_artist_label(request: Request, artistId: int):
    """
    Ruta para obtener la discográfica de un artista específico
    DEPRECADO: La funcionalidad de discográficas está en proceso de descontinuación.
    Siempre devuelve que no hay discográfica sin consultar el backend.
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    # Determinar si es el propietario (para mantener compatibilidad)
    is_owner = False
    if userdata:
        is_owner = userdata.get('artistId') == artistId
    
    # Siempre devolver que no hay discográfica (funcionalidad descontinuada)
    return JSONResponse(content={
        "label": None,
        "is_owner": is_owner
    })


@app.get("/label/{labelId}/edit")
def get_label_edit(request: Request, labelId: int):
    """
    Ruta para editar una discográfica existente
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return RedirectResponse("/login")
    
    try:
        # Obtener información de la discográfica
        label_resp = requests.get(f"{servers.TYA}/label/{labelId}", timeout=2, headers={"Accept": "application/json"})
        label_resp.raise_for_status()
        label_data = label_resp.json()
        
        # Verificar que sea propietario
        if label_data.get('ownerId') != userdata.get('userId'):
            return osv.get_error_view(request, userdata, "No tienes permisos para editar esta discográfica", "")
        
        return osv.get_label_create_view(request, label_data, userdata, servers.SYU)
        
    except requests.RequestException as e:
        print(e)
        return osv.get_error_view(request, userdata, "No se pudo cargar la discográfica", str(e))
    

@app.put("/label/{labelId}/edit")
async def update_label(request: Request, labelId: int):
    """
    Ruta para actualizar una discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        # Verificar que sea propietario
        label_resp = requests.get(f"{servers.TYA}/label/{labelId}", timeout=2, headers={"Accept": "application/json"})
        label_resp.raise_for_status()
        label_data = label_resp.json()
        
        if label_data.get('ownerId') != userdata.get('userId'):
            return JSONResponse(content={"error": "No tienes permisos"}, status_code=403)
        
        body = await request.json()
        
        # Actualizar la discográfica
        update_resp = requests.put(
            f"{servers.TYA}/label/{labelId}",
            json=body,
            timeout=2,
            headers={"Accept": "application/json"}
        )
        
        if update_resp.ok:
            return JSONResponse(content={"message": "Discográfica actualizada"})
        else:
            error_data = update_resp.json()
            return JSONResponse(content=error_data, status_code=update_resp.status_code)
    
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": "Error al actualizar la discográfica"}, status_code=500)


@app.delete("/label/{labelId}")
async def delete_label(request: Request, labelId: int):
    """
    Ruta para eliminar una discográfica
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        # Verificar que sea propietario
        label_resp = requests.get(f"{servers.TYA}/label/{labelId}", timeout=2, headers={"Accept": "application/json"})
        label_resp.raise_for_status()
        label_data = label_resp.json()
        
        if label_data.get('ownerId') != userdata.get('userId'):
            return JSONResponse(content={"error": "No tienes permisos"}, status_code=403)
        
        # Eliminar la discográfica
        delete_resp = requests.delete(
            f"{servers.TYA}/label/{labelId}",
            timeout=2,
            headers={"Accept": "application/json"}
        )
        
        if delete_resp.ok:
            return JSONResponse(content={"message": "Discográfica eliminada"})
        else:
            error_data = delete_resp.json() if delete_resp.text else {}
            return JSONResponse(content=error_data, status_code=delete_resp.status_code)
    
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": "Error al eliminar la discográfica"}, status_code=500)

# ============ ENDPOINTS DE BÚSQUEDA ============

@app.get("/api/search/song")
def search_songs(q: str = Query(..., min_length=3)):
    """
    Busca canciones por query y devuelve los datos completos
    """
    try:
        # Buscar (devuelve lista de objetos con songId)
        search_resp = requests.get(
            f"{servers.TYA}/song/search",
            params={"q": q},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if not search_resp.ok:
            return JSONResponse(content=[], status_code=200)
        
        song_objects = search_resp.json()
        
        if not song_objects or len(song_objects) == 0:
            return JSONResponse(content=[], status_code=200)
        
        # Extraer IDs de los objetos
        song_ids = [obj.get('songId') for obj in song_objects if obj.get('songId')]
        
        if not song_ids:
            return JSONResponse(content=[], status_code=200)
        
        # Resolver datos completos con IDs separados por comas en el parámetro
        ids_string = ','.join(map(str, song_ids))
        list_resp = requests.get(
            f"{servers.TYA}/song/list",
            params={"ids": ids_string},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if list_resp.ok:
            return JSONResponse(content=list_resp.json(), status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
            
    except requests.RequestException as e:
        print(f"Error buscando canciones: {e}")
        return JSONResponse(content=[], status_code=200)

@app.get("/api/search/album")
def search_albums(q: str = Query(..., min_length=3)):
    """
    Busca álbumes por query y devuelve los datos completos
    """
    try:
        # Buscar (devuelve lista de objetos con albumId)
        search_resp = requests.get(
            f"{servers.TYA}/album/search",
            params={"q": q},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if not search_resp.ok:
            return JSONResponse(content=[], status_code=200)
        
        album_objects = search_resp.json()
        
        if not album_objects or len(album_objects) == 0:
            return JSONResponse(content=[], status_code=200)
        
        # Extraer IDs de los objetos
        album_ids = [obj.get('albumId') for obj in album_objects if obj.get('albumId')]
        
        if not album_ids:
            return JSONResponse(content=[], status_code=200)
        
        # Resolver datos completos con IDs separados por comas en el parámetro
        ids_string = ','.join(map(str, album_ids))
        list_resp = requests.get(
            f"{servers.TYA}/album/list",
            params={"ids": ids_string},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if list_resp.ok:
            return JSONResponse(content=list_resp.json(), status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
            
    except requests.RequestException as e:
        print(f"Error buscando álbumes: {e}")
        return JSONResponse(content=[], status_code=200)

@app.get("/api/search/artist")
def search_artists(q: str = Query(..., min_length=3)):
    """
    Busca artistas por query y devuelve los datos completos
    """
    try:
        # Buscar (devuelve lista de objetos con artistId)
        search_resp = requests.get(
            f"{servers.TYA}/artist/search",
            params={"q": q},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if not search_resp.ok:
            return JSONResponse(content=[], status_code=200)
        
        artist_objects = search_resp.json()
        
        if not artist_objects or len(artist_objects) == 0:
            return JSONResponse(content=[], status_code=200)
        
        # Extraer IDs de los objetos
        artist_ids = [obj.get('artistId') for obj in artist_objects if obj.get('artistId')]
        
        if not artist_ids:
            return JSONResponse(content=[], status_code=200)
        
        # Resolver datos completos con IDs separados por comas en el parámetro
        ids_string = ','.join(map(str, artist_ids))
        list_resp = requests.get(
            f"{servers.TYA}/artist/list",
            params={"ids": ids_string},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if list_resp.ok:
            return JSONResponse(content=list_resp.json(), status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
            
    except requests.RequestException as e:
        print(f"Error buscando artistas: {e}")
        return JSONResponse(content=[], status_code=200)

@app.get("/api/search/merch")
def search_merch(q: str = Query(..., min_length=3)):
    """
    Busca merchandising por query y devuelve los datos completos
    """
    try:
        # Buscar (devuelve lista de objetos con merchId)
        search_resp = requests.get(
            f"{servers.TYA}/merch/search",
            params={"q": q},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if not search_resp.ok:
            return JSONResponse(content=[], status_code=200)
        
        merch_objects = search_resp.json()
        
        if not merch_objects or len(merch_objects) == 0:
            return JSONResponse(content=[], status_code=200)
        
        # Extraer IDs de los objetos
        merch_ids = [obj.get('merchId') for obj in merch_objects if obj.get('merchId')]
        
        if not merch_ids:
            return JSONResponse(content=[], status_code=200)
        
        # Resolver datos completos con IDs separados por comas en el parámetro
        ids_string = ','.join(map(str, merch_ids))
        list_resp = requests.get(
            f"{servers.TYA}/merch/list",
            params={"ids": ids_string},
            timeout=5,
            headers={"Accept": "application/json"}
        )
        
        if list_resp.ok:
            return JSONResponse(content=list_resp.json(), status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
            
    except requests.RequestException as e:
        print(f"Error buscando merchandising: {e}")
        return JSONResponse(content=[], status_code=200)

@app.get("/song/{songId}")
def get_song(request: Request, songId: int):
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    try:
        # Obtener información de la canción
        song_resp = requests.get(f"{servers.TYA}/song/{songId}", timeout=2, headers={"Accept": "application/json"})
        song_resp.raise_for_status()
        song_data = song_resp.json()
        
        # Resolver artista principal
        try:
            artist_resp = requests.get(f"{servers.TYA}/artist/{song_data['artistId']}", timeout=2, headers={"Accept": "application/json"})
            artist_resp.raise_for_status()
            song_data['artist'] = artist_resp.json()
        except requests.RequestException:
            song_data['artist'] = {"artistId": song_data['artistId'], "nombre": "Artista desconocido"}
        
        # Resolver colaboradores
        collaborators = []
        if song_data.get('collaborators'):
            for collab_id in song_data['collaborators']:
                try:
                    collab_resp = requests.get(f"{servers.TYA}/artist/{collab_id}", timeout=2, headers={"Accept": "application/json"})
                    collab_resp.raise_for_status()
                    collaborators.append(collab_resp.json())
                except requests.RequestException:
                    collaborators.append({"artistId": collab_id, "nombre": "Artista desconocido"})
        song_data['collaborators_data'] = collaborators
        
        # Resolver géneros
        genres = []
        if song_data.get('genres'):
            try:
                genres_resp = requests.get(f"{servers.TYA}/genres", timeout=2, headers={"Accept": "application/json"})
                genres_resp.raise_for_status()
                all_genres = genres_resp.json()
                genres = [g for g in all_genres if g['id'] in song_data['genres']]
            except requests.RequestException:
                pass
        song_data['genres_data'] = genres
        
        # Resolver álbum original si existe
        if song_data.get('albumId') is not None:
            try:
                album_resp = requests.get(f"{servers.TYA}/album/{song_data['albumId']}", timeout=2, headers={"Accept": "application/json"})
                album_resp.raise_for_status()
                album_data = album_resp.json()
                
                # Resolver artista del álbum
                try:
                    album_artist_resp = requests.get(f"{servers.TYA}/artist/{album_data['artistId']}", timeout=2, headers={"Accept": "application/json"})
                    album_artist_resp.raise_for_status()
                    album_data['artist'] = album_artist_resp.json()
                except requests.RequestException:
                    album_data['artist'] = {"artistId": album_data['artistId'], "nombre": "Artista desconocido"}
                
                song_data['original_album'] = album_data
            except requests.RequestException:
                song_data['original_album'] = None
        else:
            song_data['original_album'] = None
        
        # Resolver álbumes linkeados
        linked_albums_data = []
        if song_data.get('linked_albums'):
            for linked_album_id in song_data['linked_albums']:
                try:
                    linked_album_resp = requests.get(f"{servers.TYA}/album/{linked_album_id}", timeout=2, headers={"Accept": "application/json"})
                    linked_album_resp.raise_for_status()
                    linked_album_data = linked_album_resp.json()
                    
                    # Resolver artista del álbum linkeado
                    try:
                        linked_artist_resp = requests.get(f"{servers.TYA}/artist/{linked_album_data['artistId']}", timeout=2, headers={"Accept": "application/json"})
                        linked_artist_resp.raise_for_status()
                        linked_album_data['artist'] = linked_artist_resp.json()
                    except requests.RequestException:
                        linked_album_data['artist'] = {"artistId": linked_album_data['artistId'], "nombre": "Artista desconocido"}
                    
                    linked_albums_data.append(linked_album_data)
                except requests.RequestException:
                    pass  # Ignorar álbumes que no se puedan cargar
        song_data['linked_albums_data'] = linked_albums_data
        
        # Asegurarse de que el precio sea un número
        try:
            song_data['price'] = float(song_data.get('price', 0))
        except ValueError:
            song_data['price'] = 0.0
        
        # Determinar si está en favoritos y carrito (por ahora False, implementar después)
        isLiked = False
        inCarrito = False
        
        # Determinar tipo de usuario (0: no autenticado, 1: usuario, 2: artista)
        tipoUsuario = 0
        if userdata:
            tipoUsuario = 1  # TODO: Implementar lógica para distinguir artista

        metrics = None
        try:
            metrics_resp = requests.get(f"{servers.RYE}/statistics/metrics/song/{songId}", timeout=5)
            metrics_resp.raise_for_status()
            metrics_data = metrics_resp.json()
            print(f"[DEBUG] Metrics response data: {metrics_data}")
            metrics = {
            "sales": metrics_data.get("sales", 0),
            "downloads": metrics_data.get("downloads", 0),
            "playbacks": metrics_data.get("playbacks", 0)
            }
        except requests.RequestException as e:
            print(f"Error obteniendo métricas del artista: {e}")
            metrics = {"playbacks": 0, "sales": 0, "downloads": 0}
        
        return osv.get_song_view(request, song_data, tipoUsuario, userdata, isLiked, inCarrito, servers.SYU, metrics, servers.TYA, servers.RYE, servers.PT)
        
    except requests.RequestException as e:
        # En caso de error, mostrar página de error
        print(e)
        return osv.get_error_view(request, userdata, f"No se pudo cargar la canción", str(e))

@app.get("/shop")
def shop(request: Request, 
         page: int = Query(default=1),
         limit: int = Query(default=100)):
    """
    Renderiza la vista de la tienda.
    Una sola llamada a TPP /store obtiene todo: productos, géneros y artistas.
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)

    try:
        # ===== UNA SOLA LLAMADA obtiene todo =====
        store_resp = requests.get(
            f"{servers.TPP}/store",
            params={"page": page, "limit": limit},
            timeout=30,
            headers={"Accept": "application/json"}
        )
        store_resp.raise_for_status()
        store_data = store_resp.json()
        
        # Extraer datos
        productos = store_data.get("data", [])
        pagination = store_data.get("pagination", {})
        all_genres = store_data.get("genres", [])
        all_artists = store_data.get("artists", [])
        
        print(f"[DEBUG] TPP Response: {len(productos)} productos, {len(all_genres)} géneros, {len(all_artists)} artistas")
        
    except requests.RequestException as e:
        print(f"Error obteniendo tienda desde TPP: {e}")
        productos = []
        pagination = {}
        all_genres = []
        all_artists = []
    except Exception as e:
        print(f"Error inesperado en shop: {e}")
        import traceback
        traceback.print_exc()
        productos = []
        pagination = {}
        all_genres = []
        all_artists = []

    # ===== CREAR MAPEOS para resolver IDs (manejo seguro) =====
    artists_map = {}
    for a in all_artists:
        if isinstance(a, dict):
            # Intentar obtener artistId con ambas notaciones
            artist_id = a.get('artistId') or a.get('artist_id')
            artist_name = a.get('artisticName') or a.get('artistic_name')
            if artist_id and artist_name:
                artists_map[artist_id] = artist_name
    
    genres_map = {}
    for g in all_genres:
        if isinstance(g, dict):
            # Obtener id y name del género
            genre_id = g.get('id') or g.get('genre_id')
            genre_name = g.get('name') or g.get('genre_name')
            if genre_id and genre_name:
                genres_map[genre_id] = genre_name

    # ===== SEPARAR por tipo (usando nombres de campo con guiones bajos) =====
    songs = [p for p in productos if p.get('song_id', 0) not in [0, None]]
    albums = [p for p in productos if p.get('album_id', 0) not in [0, None] and p.get('song_id', 0) in [0, None]]
    merch = [p for p in productos if p.get('merch_id', 0) not in [0, None]]

    print(f"[DEBUG] Shop: {len(songs)} songs, {len(albums)} albums, {len(merch)} merch")
    print(f"[DEBUG] Shop: artists_map={len(artists_map)} items, genres_map={len(genres_map)} items")
    if productos:
        print(f"[DEBUG] Sample product keys: {list(productos[0].keys())}")
        print(f"[DEBUG] Sample product artist field: {productos[0].get('artist')} (type: {type(productos[0].get('artist'))})")
    if artists_map:
        print(f"[DEBUG] Sample artists_map keys: {list(artists_map.keys())[:5]}")
    if genres_map:
        print(f"[DEBUG] Sample genres_map keys: {list(genres_map.keys())[:5]}")

    return osv.get_shop_view(
        request, userdata, 
        songs, all_genres, all_artists, albums, merch,
        artists_map, genres_map, servers.TYA
    )

@app.post("/purchase")
async def process_purchase(request: Request):
    """
    Procesa una compra
    Proxea la llamada a TPP POST /purchase
    Body esperado: {cartId, paymentMethodId, shippingAddress}
    """
    token = request.cookies.get("oversound_auth")
    userdata = obtain_user_data(token)
    
    if not userdata:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        body = await request.json()
        # Agregar ID de usuario al body
        body['userId'] = userdata.get('userId')
        
        # Enviar a TPP
        purchase_resp = requests.post(
            f"{servers.TPP}/purchase",
            json=body,
            timeout=5,
            headers={"Accept": "application/json", "Cookie": f"oversound_auth={token}"}
        )
        purchase_resp.raise_for_status()
        return JSONResponse(content=purchase_resp.json(), status_code=purchase_resp.status_code)
    except requests.RequestException as e:
        print(f"Error procesando compra: {e}")
        return JSONResponse(content={"error": "No se pudo procesar la compra"}, status_code=500)
