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
