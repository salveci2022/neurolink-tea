"""
NeuroLink TEA — API REST v1
Usada pelo PWA / app mobile da criança e pelos pais.
Autenticação: Bearer token (simples, sem JWT por ora).
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app.models import (db, User, Crianca, Rotina, Atividade,
                         RegistroAtividade, RegistroCrise, Localizacao,
                         StatusAtividade, TipoCrise)

api_bp = Blueprint('api', __name__)


def api_error(msg, code=400):
    return jsonify({'ok': False, 'erro': msg}), code

def api_ok(data=None, **kwargs):
    resp = {'ok': True}
    if data is not None:
        resp['data'] = data
    resp.update(kwargs)
    return jsonify(resp)


# ─── AUTH SIMPLES POR TOKEN ───────────────────────────────────────────────────
def token_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return api_error('Token não informado.', 401)
        # TODO: implementar JWT; por ora usa session do Flask-Login
        return f(*args, **kwargs)
    return decorated


# ─── ROTINAS ──────────────────────────────────────────────────────────────────
@api_bp.route('/rotinas/<int:crianca_id>/hoje', methods=['GET'])
@login_required
def rotinas_hoje(crianca_id):
    """Retorna atividades de hoje para a criança."""
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return api_error('Sem permissão.', 403)

    hoje = date.today()
    dia  = str(hoje.isoweekday())  # 1=seg ... 7=dom

    rotinas = (Rotina.query
        .filter_by(crianca_id=crianca_id, ativa=True)
        .filter(Rotina.dias_semana.contains(dia))
        .all())

    resultado = []
    for r in rotinas:
        atividades = []
        for a in r.atividades.order_by(Atividade.ordem).all():
            reg = (RegistroAtividade.query
                .filter_by(atividade_id=a.id, data=hoje)
                .first())
            atividades.append({
                'id':         a.id,
                'nome':       a.nome,
                'icone':      a.icone,
                'cor':        a.cor,
                'duracao_min':a.duracao_min,
                'aviso_min':  a.aviso_min,
                'status':     reg.status if reg else StatusAtividade.PENDENTE,
                'audio_url':  a.audio_url,
                'imagem_url': a.imagem_url,
            })
        resultado.append({
            'rotina_id':  r.id,
            'nome':       r.nome,
            'atividades': atividades,
        })

    return api_ok(resultado)


@api_bp.route('/atividades/<int:atividade_id>/status', methods=['POST'])
@login_required
def atualizar_status(atividade_id):
    """Marca atividade como concluída, pulada etc."""
    dados  = request.get_json() or {}
    status = dados.get('status', StatusAtividade.CONCLUIDA)

    atividade = Atividade.query.get_or_404(atividade_id)
    crianca   = atividade.rotina.crianca
    if crianca.tenant_id != current_user.tenant_id:
        return api_error('Sem permissão.', 403)

    hoje = date.today()
    reg  = RegistroAtividade.query.filter_by(
        atividade_id=atividade_id, data=hoje
    ).first()

    if not reg:
        reg = RegistroAtividade(atividade_id=atividade_id, data=hoje)
        db.session.add(reg)

    reg.status       = status
    reg.observacao   = dados.get('observacao')
    if status == StatusAtividade.CONCLUIDA:
        reg.concluida_em = datetime.utcnow()

    db.session.commit()
    return api_ok({'status': reg.status})


# ─── GPS ──────────────────────────────────────────────────────────────────────
@api_bp.route('/gps/<int:crianca_id>/update', methods=['POST'])
@login_required
def gps_update(crianca_id):
    """Recebe nova localização do dispositivo da criança."""
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return api_error('Sem permissão.', 403)

    dados = request.get_json() or {}
    lat   = dados.get('latitude')
    lng   = dados.get('longitude')
    if not lat or not lng:
        return api_error('Latitude e longitude obrigatórios.')

    loc = Localizacao(
        crianca_id=crianca_id,
        latitude=float(lat),
        longitude=float(lng),
        precisao_m=dados.get('precisao_m'),
    )
    db.session.add(loc)
    db.session.commit()

    # Verificar cercas virtuais
    alertas = _verificar_cercas(crianca, float(lat), float(lng))

    return api_ok({'id': loc.id, 'alertas': alertas})


@api_bp.route('/gps/<int:crianca_id>/ultima', methods=['GET'])
@login_required
def gps_ultima(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return api_error('Sem permissão.', 403)

    loc = crianca.localizacoes.order_by(Localizacao.criado_em.desc()).first()
    if not loc:
        return api_ok(None)

    return api_ok({
        'latitude':   loc.latitude,
        'longitude':  loc.longitude,
        'criado_em':  loc.criado_em.isoformat(),
    })


# ─── CRISES ───────────────────────────────────────────────────────────────────
@api_bp.route('/crises', methods=['POST'])
@login_required
def registrar_crise():
    """Abre um registro de crise."""
    dados = request.get_json() or {}
    crianca_id = dados.get('crianca_id')
    if not crianca_id:
        return api_error('crianca_id obrigatório.')

    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return api_error('Sem permissão.', 403)

    crise = RegistroCrise(
        crianca_id     = crianca_id,
        registrado_por = current_user.id,
        tipo           = dados.get('tipo', TipoCrise.SENSORIAL),
        intensidade    = dados.get('intensidade', 3),
        gatilho        = dados.get('gatilho'),
        observacao     = dados.get('observacao'),
    )
    db.session.add(crise)
    db.session.commit()

    # Notificar responsáveis via WhatsApp
    _notificar_crise(crianca, crise)

    return api_ok({'id': crise.id}, status_code=201)


@api_bp.route('/crises/<int:crise_id>/resolver', methods=['POST'])
@login_required
def resolver_crise(crise_id):
    from app.models import RegistroCrise
    crise = RegistroCrise.query.get_or_404(crise_id)
    dados = request.get_json() or {}

    crise.resolveu_em  = datetime.utcnow()
    crise.duracao_min  = dados.get('duracao_min')
    crise.estrategia   = dados.get('estrategia')
    db.session.commit()

    return api_ok({'duracao_min': crise.duracao_min})


# ─── HELPERS PRIVADOS ─────────────────────────────────────────────────────────
import math

def _haversine(lat1, lng1, lat2, lng2):
    """Distância em metros entre dois pontos GPS."""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lng2 - lng1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _verificar_cercas(crianca, lat, lng):
    from app.models import CercaVirtual
    alertas = []
    for cerca in CercaVirtual.query.filter_by(crianca_id=crianca.id, ativa=True).all():
        dist = _haversine(lat, lng, cerca.latitude, cerca.longitude)
        if dist > cerca.raio_metros:
            alertas.append({
                'cerca': cerca.nome,
                'distancia_m': round(dist),
                'raio_m': cerca.raio_metros,
            })
            _notificar_fuga(crianca, cerca, dist)
    return alertas


def _notificar_crise(crianca, crise):
    """Envia alerta WhatsApp via Z-API para responsáveis."""
    from flask import current_app
    import requests as req
    instance = current_app.config.get('ZAPI_INSTANCE_ID')
    token    = current_app.config.get('ZAPI_TOKEN')
    if not instance or not token:
        return

    msg = (f"🚨 *NeuroLink TEA — Alerta de Crise*\n\n"
           f"A criança *{crianca.nome}* está passando por uma crise.\n"
           f"Tipo: {crise.tipo} | Intensidade: {crise.intensidade}/5\n"
           f"Hora: {crise.iniciou_em.strftime('%H:%M')}\n\n"
           f"Acesse o app para acompanhar.")

    for resp in crianca.responsaveis.all():
        if resp.telefone:
            try:
                req.post(
                    f"{current_app.config['ZAPI_BASE_URL']}/{instance}/token/{token}/send-text",
                    json={'phone': resp.telefone, 'message': msg},
                    timeout=5
                )
            except Exception:
                pass


def _notificar_fuga(crianca, cerca, distancia):
    from flask import current_app
    import requests as req
    instance = current_app.config.get('ZAPI_INSTANCE_ID')
    token    = current_app.config.get('ZAPI_TOKEN')
    if not instance or not token:
        return

    msg = (f"🚨 *NeuroLink TEA — Alerta de Localização*\n\n"
           f"*{crianca.nome}* saiu da área segura *{cerca.nome}*.\n"
           f"Distância atual: {round(distancia)}m (limite: {round(cerca.raio_metros)}m)\n"
           f"Abra o app para ver a localização em tempo real.")

    for resp in crianca.responsaveis.all():
        if resp.telefone:
            try:
                req.post(
                    f"{current_app.config['ZAPI_BASE_URL']}/{instance}/token/{token}/send-text",
                    json={'phone': resp.telefone, 'message': msg},
                    timeout=5
                )
            except Exception:
                pass
