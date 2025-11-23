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
