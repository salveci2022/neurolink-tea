from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from app.models import db, Crianca, NivelTEA
from app.utils.decorators import tenant_ativo

criancas_bp = Blueprint('criancas', __name__)

@criancas_bp.route('/')
@login_required
@tenant_ativo
def index():
    criancas = Crianca.query.filter_by(tenant_id=current_user.tenant_id, ativo=True).all()
    return render_template('criancas/index.html', criancas=criancas)

@criancas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
@tenant_ativo
def nova():
    if request.method == 'POST':
        nome  = request.form.get('nome', '').strip()
        nasc  = request.form.get('data_nascimento')
        nivel = request.form.get('nivel_tea')
        desc  = request.form.get('descricao', '')
        s_som   = int(request.form.get('sensibilidade_som', 3))
        s_luz   = int(request.form.get('sensibilidade_luz', 3))
        s_toque = int(request.form.get('sensibilidade_toque', 3))

        if not nome:
            flash('O nome é obrigatório.', 'danger')
            return render_template('criancas/nova.html')

        crianca = Crianca(
            tenant_id=current_user.tenant_id,
            nome=nome,
            data_nascimento=date.fromisoformat(nasc) if nasc else None,
            nivel_tea=nivel,
            descricao=desc,
            sensibilidade_som=s_som,
            sensibilidade_luz=s_luz,
            sensibilidade_toque=s_toque,
        )
        crianca.responsaveis.append(current_user)
        db.session.add(crianca)
        db.session.commit()
        flash(f'{nome} cadastrado(a) com sucesso!', 'success')
        return redirect(url_for('dashboard.familia'))

    return render_template('criancas/nova.html')

@criancas_bp.route('/<int:id>')
@login_required
@tenant_ativo
def detalhe(id):
    crianca = Crianca.query.get_or_404(id)
    return render_template('criancas/detalhe.html', crianca=crianca)
