"""
NeuroLink TEA — Dashboards por Perfil
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, timedelta

from app.models import (db, Crianca, RegistroCrise, RegistroAtividade,
                         Sessao, User, StatusAtividade, Rotina, Atividade)
from app.utils.decorators import perfil_requerido, tenant_ativo
from app.models import UserPerfil

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/familia')
@login_required
@tenant_ativo
@perfil_requerido(UserPerfil.PAI_MAE, UserPerfil.CUIDADOR)
def familia():
    criancas = current_user.criancas.filter_by(ativo=True).all()
    hoje = date.today()
    dados = []
    for c in criancas:
        # Query simplificada sem join problemático
        total = 0
        concluidas = 0
        try:
            rotinas = Rotina.query.filter_by(crianca_id=c.id, ativa=True).all()
            for r in rotinas:
                for a in r.atividades.all():
                    reg = RegistroAtividade.query.filter_by(
                        atividade_id=a.id, data=hoje).first()
                    total += 1
                    if reg and reg.status == StatusAtividade.CONCLUIDA:
                        concluidas += 1
        except Exception:
            pass

        ultima_loc = c.localizacoes.order_by(
            db.text('criado_em desc')).first()

        crises_semana = c.crises.filter(
            RegistroCrise.iniciou_em >= (date.today() - timedelta(days=7))
        ).count()

        dados.append({
            'crianca':       c,
            'concluidas':    concluidas,
            'total_ativ':    total,
            'ultima_loc':    ultima_loc,
            'crises_semana': crises_semana,
        })

    return render_template('dashboard/familia.html', dados=dados, hoje=hoje)


@dashboard_bp.route('/escola')
@login_required
@tenant_ativo
@perfil_requerido(UserPerfil.PROFESSOR, UserPerfil.COORDENADOR)
def escola():
    tenant_id = current_user.tenant_id
    hoje = date.today()
    total_alunos = Crianca.query.filter_by(tenant_id=tenant_id, ativo=True).count()
    crises_hoje = (db.session.query(func.count(RegistroCrise.id))
        .join(Crianca)
        .filter(Crianca.tenant_id == tenant_id,
                func.date(RegistroCrise.iniciou_em) == hoje)
        .scalar())
    semana_atras = date.today() - timedelta(days=7)
    top_crises = (db.session.query(Crianca, func.count(RegistroCrise.id).label('n'))
        .join(RegistroCrise)
        .filter(Crianca.tenant_id == tenant_id,
                RegistroCrise.iniciou_em >= semana_atras)
        .group_by(Crianca.id)
        .order_by(func.count(RegistroCrise.id).desc())
        .limit(5).all())
    professores = (User.query
        .filter_by(tenant_id=tenant_id, ativo=True)
        .filter(User.perfil.in_([UserPerfil.PROFESSOR, UserPerfil.COORDENADOR]))
        .count())
    return render_template('dashboard/escola.html',
        total_alunos=total_alunos, crises_hoje=crises_hoje,
        top_crises=top_crises, professores=professores, hoje=hoje)


@dashboard_bp.route('/clinica')
@login_required
@tenant_ativo
@perfil_requerido(UserPerfil.TERAPEUTA, UserPerfil.PSICOLOGO)
def clinica():
    tenant_id = current_user.tenant_id
    hoje = date.today()
    total_pacientes = Crianca.query.filter_by(tenant_id=tenant_id, ativo=True).count()
    sessoes_hoje = (Sessao.query
        .join(Sessao.prontuario).join('crianca')
        .filter(Crianca.tenant_id == tenant_id, Sessao.data_sessao == hoje)
        .count())
    sessoes_semana = (Sessao.query
        .join(Sessao.prontuario).join('crianca')
        .filter(Crianca.tenant_id == tenant_id,
                Sessao.data_sessao >= date.today() - timedelta(days=7))
        .count())
    proximas = []
    return render_template('dashboard/clinica.html',
        total_pacientes=total_pacientes, sessoes_hoje=sessoes_hoje,
        sessoes_semana=sessoes_semana, proximas=proximas, hoje=hoje)


@dashboard_bp.route('/institucional')
@login_required
@tenant_ativo
@perfil_requerido(UserPerfil.GESTOR, UserPerfil.ADMIN)
def institucional():
    tenant_id = current_user.tenant_id
    hoje = date.today()
    total_beneficiarios = Crianca.query.filter_by(tenant_id=tenant_id, ativo=True).count()
    total_tecnicos = User.query.filter_by(tenant_id=tenant_id, ativo=True).count()
    crises_mes = (db.session.query(func.count(RegistroCrise.id))
        .join(Crianca)
        .filter(Crianca.tenant_id == tenant_id,
                RegistroCrise.iniciou_em >= date(hoje.year, hoje.month, 1))
        .scalar())
    crises_por_tipo = []
    return render_template('dashboard/institucional.html',
        total_beneficiarios=total_beneficiarios, total_tecnicos=total_tecnicos,
        crises_mes=crises_mes, crises_por_tipo=crises_por_tipo, hoje=hoje)
