from flask import Blueprint
clinica_bp = Blueprint('clinica', __name__)

@clinica_bp.route('/')
def index():
    return "Módulo clinica — em desenvolvimento"
