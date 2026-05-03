"""
NeuroLink TEA — Módulo de Rotinas Visuais completo
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from app.models import db, Crianca, Rotina, Atividade, RegistroAtividade, StatusAtividade
from app.utils.decorators import tenant_ativo

rotinas_bp = Blueprint('rotinas', __name__)


@rotinas_bp.route('/')
@login_required
@tenant_ativo
def index():
    criancas = current_user.criancas.filter_by(ativo=True).all()
    return render_template('rotinas/index.html', criancas=criancas)


@rotinas_bp.route('/<int:crianca_id>')
@login_required
@tenant_ativo
def ver(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    rotinas = Rotina.query.filter_by(crianca_id=crianca_id, ativa=True).all()
    return render_template('rotinas/ver.html', crianca=crianca, rotinas=rotinas)


@rotinas_bp.route('/<int:crianca_id>/nova', methods=['GET','POST'])
@login_required
@tenant_ativo
def nova(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if request.method == 'POST':
        nome = request.form.get('nome','').strip()
        dias = ','.join(request.form.getlist('dias'))
        if not nome:
            flash('Informe o nome da rotina.', 'danger')
            return render_template('rotinas/nova.html', crianca=crianca)
        r = Rotina(crianca_id=crianca_id, nome=nome,
                   dias_semana=dias or '1,2,3,4,5')
        db.session.add(r)
        db.session.commit()
        flash(f'Rotina "{nome}" criada!', 'success')
        return redirect(url_for('rotinas.editar', rotina_id=r.id))
    return render_template('rotinas/nova.html', crianca=crianca)


@rotinas_bp.route('/editar/<int:rotina_id>', methods=['GET','POST'])
@login_required
@tenant_ativo
def editar(rotina_id):
    rotina  = Rotina.query.get_or_404(rotina_id)
    crianca = rotina.crianca
    if request.method == 'POST':
        acao = request.form.get('acao')
        if acao == 'add_atividade':
            ordem = rotina.atividades.count()
            a = Atividade(
                rotina_id   = rotina_id,
                nome        = request.form.get('nome','Nova atividade'),
                icone       = request.form.get('icone','⭐'),
                cor         = request.form.get('cor','#0F6E56'),
                duracao_min = int(request.form.get('duracao_min', 10)),
                aviso_min   = int(request.form.get('aviso_min', 5)),
                ordem       = ordem,
            )
            db.session.add(a)
            db.session.commit()
            flash(f'Atividade "{a.nome}" adicionada!', 'success')
        elif acao == 'del_atividade':
            aid = int(request.form.get('atividade_id'))
            Atividade.query.filter_by(id=aid).delete()
            db.session.commit()
            flash('Atividade removida.', 'info')
        return redirect(url_for('rotinas.editar', rotina_id=rotina_id))
    atividades = rotina.atividades.order_by(Atividade.ordem).all()
    return render_template('rotinas/editar.html',
        rotina=rotina, crianca=crianca, atividades=atividades)


@rotinas_bp.route('/executar/<int:rotina_id>')
@login_required
@tenant_ativo
def executar(rotina_id):
    rotina     = Rotina.query.get_or_404(rotina_id)
    crianca    = rotina.crianca
    atividades = rotina.atividades.order_by(Atividade.ordem).all()
    hoje       = date.today()
    registros  = {}
    for a in atividades:
        reg = RegistroAtividade.query.filter_by(
            atividade_id=a.id, data=hoje).first()
        registros[a.id] = reg.status if reg else StatusAtividade.PENDENTE
    return render_template('rotinas/executar.html',
        rotina=rotina, crianca=crianca,
        atividades=atividades, registros=registros, hoje=hoje)


# ── API ───────────────────────────────────────────────────
@rotinas_bp.route('/api/concluir/<int:atividade_id>', methods=['POST'])
@login_required
def api_concluir(atividade_id):
    from datetime import datetime
    atividade = Atividade.query.get_or_404(atividade_id)
    hoje = date.today()
    reg  = RegistroAtividade.query.filter_by(
        atividade_id=atividade_id, data=hoje).first()
    if not reg:
        reg = RegistroAtividade(atividade_id=atividade_id, data=hoje)
        db.session.add(reg)
    dados = request.get_json() or {}
    reg.status = dados.get('status', StatusAtividade.CONCLUIDA)
    if reg.status == StatusAtividade.CONCLUIDA:
        reg.concluida_em = datetime.utcnow()
    db.session.commit()
    # Contar progresso
    rotina = atividade.rotina
    total  = rotina.atividades.count()
    concluidas = sum(
        1 for a in rotina.atividades.all()
        if RegistroAtividade.query.filter_by(
            atividade_id=a.id, data=hoje,
            status=StatusAtividade.CONCLUIDA).first()
    )
    return jsonify({'ok': True, 'status': reg.status,
                    'concluidas': concluidas, 'total': total})


@rotinas_bp.route('/api/progresso/<int:rotina_id>')
@login_required
def api_progresso(rotina_id):
    rotina = Rotina.query.get_or_404(rotina_id)
    hoje   = date.today()
    total  = rotina.atividades.count()
    concluidas = sum(
        1 for a in rotina.atividades.all()
        if RegistroAtividade.query.filter_by(
            atividade_id=a.id, data=hoje,
            status=StatusAtividade.CONCLUIDA).first()
    )
    return jsonify({'ok': True, 'concluidas': concluidas, 'total': total,
                    'percent': round(concluidas/total*100) if total else 0})
