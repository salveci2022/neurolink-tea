"""
NeuroLink TEA — Comunicador Alternativo (CAA)
Pranchas de pictogramas com saída de voz para autistas não verbais.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Crianca
from app.utils.decorators import tenant_ativo

comunicador_bp = Blueprint('comunicador', __name__)

# Pictogramas padrão organizados por categoria
PICTOGRAMAS = {
    'necessidades': [
        {'id':'agua',    'emoji':'💧','label':'Água',      'frase':'Quero água'},
        {'id':'comida',  'emoji':'🍽️','label':'Comida',    'frase':'Quero comer'},
        {'id':'banheiro','emoji':'🚽','label':'Banheiro',  'frase':'Preciso ir ao banheiro'},
        {'id':'dormir',  'emoji':'😴','label':'Dormir',    'frase':'Quero dormir'},
        {'id':'descanso','emoji':'🛋️','label':'Descansar', 'frase':'Quero descansar'},
        {'id':'medico',  'emoji':'🏥','label':'Médico',    'frase':'Preciso de ajuda médica'},
    ],
    'sentimentos': [
        {'id':'feliz',   'emoji':'😊','label':'Feliz',     'frase':'Estou feliz'},
        {'id':'triste',  'emoji':'😢','label':'Triste',    'frase':'Estou triste'},
        {'id':'com_raiva','emoji':'😠','label':'Com raiva', 'frase':'Estou com raiva'},
        {'id':'com_medo','emoji':'😨','label':'Com medo',  'frase':'Estou com medo'},
        {'id':'cansado', 'emoji':'😓','label':'Cansado',   'frase':'Estou cansado'},
        {'id':'dor',     'emoji':'🤕','label':'Dor',       'frase':'Estou com dor'},
        {'id':'ansioso', 'emoji':'😰','label':'Ansioso',   'frase':'Estou ansioso'},
        {'id':'bem',     'emoji':'😌','label':'Bem',       'frase':'Estou bem'},
    ],
    'atividades': [
        {'id':'brincar', 'emoji':'🎮','label':'Brincar',   'frase':'Quero brincar'},
        {'id':'musica',  'emoji':'🎵','label':'Música',    'frase':'Quero ouvir música'},
        {'id':'tv',      'emoji':'📺','label':'TV',        'frase':'Quero assistir TV'},
        {'id':'passear', 'emoji':'🚶','label':'Passear',   'frase':'Quero passear'},
        {'id':'ler',     'emoji':'📚','label':'Ler',       'frase':'Quero ler'},
        {'id':'desenhar','emoji':'🎨','label':'Desenhar',  'frase':'Quero desenhar'},
        {'id':'abraco',  'emoji':'🤗','label':'Abraço',    'frase':'Quero um abraço'},
        {'id':'ajuda',   'emoji':'🙋','label':'Ajuda',     'frase':'Preciso de ajuda'},
    ],
    'lugares': [
        {'id':'casa',    'emoji':'🏠','label':'Casa',      'frase':'Quero ir para casa'},
        {'id':'escola',  'emoji':'🏫','label':'Escola',    'frase':'Vou para a escola'},
        {'id':'parque',  'emoji':'🌳','label':'Parque',    'frase':'Quero ir ao parque'},
        {'id':'carro',   'emoji':'🚗','label':'Carro',     'frase':'Quero entrar no carro'},
        {'id':'quarto',  'emoji':'🛏️','label':'Quarto',    'frase':'Quero ir para o quarto'},
    ],
    'respostas': [
        {'id':'sim',     'emoji':'✅','label':'Sim',       'frase':'Sim'},
        {'id':'nao',     'emoji':'❌','label':'Não',       'frase':'Não'},
        {'id':'talvez',  'emoji':'🤔','label':'Talvez',    'frase':'Talvez'},
        {'id':'espera',  'emoji':'⏳','label':'Espera',    'frase':'Espera um pouco'},
        {'id':'acabou',  'emoji':'🏁','label':'Acabou',    'frase':'Acabou'},
        {'id':'mais',    'emoji':'➕','label':'Mais',      'frase':'Quero mais'},
    ],
}

CATEGORIAS_LABEL = {
    'necessidades': '🔴 Necessidades',
    'sentimentos':  '💛 Sentimentos',
    'atividades':   '🟢 Atividades',
    'lugares':      '🔵 Lugares',
    'respostas':    '⚪ Respostas',
}


@comunicador_bp.route('/')
@login_required
@tenant_ativo
def index():
    criancas = current_user.criancas.filter_by(ativo=True).all()
    return render_template('comunicador/index.html', criancas=criancas)


@comunicador_bp.route('/<int:crianca_id>')
@login_required
@tenant_ativo
def prancha(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    return render_template('comunicador/prancha.html',
        crianca=crianca,
        pictogramas=PICTOGRAMAS,
        categorias=CATEGORIAS_LABEL)


@comunicador_bp.route('/api/pictogramas')
@login_required
def api_pictogramas():
    return jsonify({'ok': True, 'categorias': PICTOGRAMAS})
