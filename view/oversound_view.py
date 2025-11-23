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