from flask import Blueprint
rotinas_bp = Blueprint('rotinas', __name__)

@rotinas_bp.route('/')
def index():
    return "Módulo rotinas — em desenvolvimento"
