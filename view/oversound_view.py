from fastapi.templating import Jinja2Templates
from fastapi import Request
from datetime import datetime

templates = Jinja2Templates(directory="view/templates") # Esta ruta es la que se va a usar para renderizar las plantillas

class View():

    def __init__(self): 
        pass