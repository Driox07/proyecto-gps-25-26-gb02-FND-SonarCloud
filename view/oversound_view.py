from fastapi.templating import Jinja2Templates
from fastapi import Request
from datetime import datetime

templates = Jinja2Templates(directory="view/templates") # Esta ruta es la que se va a usar para renderizar las plantillas

class View():

    def __init__(self): 
        pass


    # Renderizar la template de error
    def get_error_view(self, request: Request, userdata: dict, error_message: str, error_details: str = ""):
        data = {"userdata": userdata, "error_message": error_message, "error_details": error_details}
        return templates.TemplateResponse("error.html", {"request": request, "data": data})
    
        # Renderizar la template label_create.html
    def get_label_create_view(self, request: Request, label_info : dict = None, userdata: dict = None, syu_server: str = None):
        data = {"userdata": userdata, "syu_server": syu_server}
        return templates.TemplateResponse("label_create.html", {"request": request, "data": data, "label": label_info})
    
        # Renderizar la template label.html
    def get_label_view(self, request: Request, label_info : dict, is_owner: bool, is_member: bool, userdata: dict = None, syu_server: str = None):
        data = {"userdata": userdata, "syu_server": syu_server}
        return templates.TemplateResponse("label.html", {"request": request, "data": data, "label": label_info, "is_owner": is_owner, "is_member": is_member})
    

    # Renderizar la template shop.html
    def get_shop_view(self, request: Request, userdata: dict, songs, genres, artistas, albums, merch, artists_map=None, genres_map=None, tya_server=None):
        if artists_map is None:
            artists_map = {}
        if genres_map is None:
            genres_map = {}
        data = {"userdata": userdata}
        return templates.TemplateResponse("shop.html", {
            "request": request, 
            "data": data,
            "songs": songs,
            "albums": albums,
            "merch": merch,
            "genres": genres,
            "artists": artistas,
            "artists_map": artists_map, 
            "genres_map": genres_map,
            "tya_server": tya_server
        })
    
    def get_songs_view(self, request: Request, songs):
        return templates.TemplateResponse("main/index.html", {"request" :request, "songs" : songs})
    
    def get_song_view(self, request: Request, song_info : dict, tipoUsuario: int, user : dict, isLiked: bool, inCarrito: bool, syu_server: str = None, metrics: dict = None, tya_server: str = None, rye_server: str = None, pt_server: str = None):
        data = {"userdata": user, "syu_server": syu_server, "pt_server": pt_server, "song": song_info}
        return templates.TemplateResponse("song.html", {"request": request, "data": data, "tipoUsuario": tipoUsuario, "user": user, "isLiked": isLiked, "inCarrito": inCarrito, "stats": metrics, "syu_server": syu_server, "tya_server": tya_server, "rye_server": rye_server})

    # Renderizar la template purchased.html
    def get_purchased_view(self, request: Request, user, songs):
        return templates.TemplateResponse("shop/purchased.html", {"request": request, "usuario": user, "songs": songs})
    
     # Renderizar la template album.html
    def get_album_view(self, request: Request, album_info : dict, tipoUsuario : int, isLiked: bool, inCarrito: bool, tiempo_formateado: str, userdata: dict = None, pt_server: str = None):
        data = {"userdata": userdata, "pt_server": pt_server}
        return templates.TemplateResponse("album.html", {"request": request, "data": data, "album": album_info, "tipoUsuario": tipoUsuario, "isLiked": isLiked, "inCarrito": inCarrito, "duracion_total": tiempo_formateado})
    
        # Renderizar la template merch.html
    def get_merch_view(self, request: Request, merch_info : dict, tipoUsuario : int, isLiked: bool, inCarrito: bool, userdata: dict = None, syu_server: str = None):
        data = {"userdata": userdata, "syu_server": syu_server, "merch": merch_info}
        return templates.TemplateResponse("merch.html", {"request": request, "data": data, "tipoUsuario": tipoUsuario, "isLiked": isLiked, "inCarrito": inCarrito})
    