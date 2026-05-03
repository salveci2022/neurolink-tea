"""
NeuroLink TEA — Rotas de Autenticação
Registro por tipo de tenant, login com redirecionamento por perfil.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

from app.models import db, User, Tenant, UserPerfil, TenantTipo, PlanoTipo
from app.utils.decorators import logout_required

auth_bp = Blueprint('auth', __name__)


# ─── Mapa: perfil → onde redirecionar após login ──────────────────────────────
REDIRECT_POR_PERFIL = {
    UserPerfil.ADMIN:       'admin.index',
    UserPerfil.GESTOR:      'dashboard.institucional',
    UserPerfil.COORDENADOR: 'dashboard.escola',
    UserPerfil.PROFESSOR:   'dashboard.escola',
    UserPerfil.TERAPEUTA:   'dashboard.clinica',
    UserPerfil.PSICOLOGO:   'dashboard.clinica',
    UserPerfil.PAI_MAE:     'dashboard.familia',
    UserPerfil.CUIDADOR:    'dashboard.familia',
}


# ─── HOME ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return _redirecionar_por_perfil(current_user.perfil)
    return render_template('auth/landing.html')


# ─── LOGIN ────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
@logout_required
def login():
    if request.method == 'POST':
        email  = request.form.get('email', '').strip().lower()
        senha  = request.form.get('senha', '')
        lembrar = request.form.get('lembrar') == 'on'

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_senha(senha):
            flash('E-mail ou senha incorretos.', 'danger')
            return render_template('auth/login.html', email=email)

        if not user.ativo:
            flash('Conta desativada. Entre em contato com o suporte.', 'warning')
            return render_template('auth/login.html', email=email)

        if not user.tenant.ativo:
            flash('Sua organização está com acesso suspenso.', 'warning')
            return render_template('auth/login.html', email=email)

        login_user(user, remember=lembrar)
        user.ultimo_login = datetime.utcnow()
        db.session.commit()

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return _redirecionar_por_perfil(user.perfil)

    return render_template('auth/login.html')


# ─── REGISTRO ─────────────────────────────────────────────────────────────────
@auth_bp.route('/registro', methods=['GET', 'POST'])
@logout_required
def registro():
    if request.method == 'POST':
        tipo_tenant = request.form.get('tipo_tenant')
        nome_org    = request.form.get('nome_org', '').strip()
        nome_user   = request.form.get('nome_user', '').strip()
        email       = request.form.get('email', '').strip().lower()
        senha       = request.form.get('senha', '')
        confirma    = request.form.get('confirma', '')

        # Validações
        erros = []
        if tipo_tenant not in TenantTipo.TODOS:
            erros.append('Tipo de organização inválido.')
        if len(nome_org) < 3:
            erros.append('Nome da organização muito curto.')
        if len(nome_user) < 2:
            erros.append('Informe seu nome completo.')
        if User.query.filter_by(email=email).first():
            erros.append('Este e-mail já está cadastrado.')
        if len(senha) < 8:
            erros.append('A senha deve ter pelo menos 8 caracteres.')
        if senha != confirma:
            erros.append('As senhas não conferem.')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('auth/registro.html', form=request.form)

        # Criar Tenant
        slug = _gerar_slug(nome_org)
        tenant = Tenant(
            nome=nome_org,
            slug=slug,
            tipo=tipo_tenant,
            plano=PlanoTipo.GRATIS,
        )
        db.session.add(tenant)
        db.session.flush()  # pegar o ID

        # Perfil padrão por tipo de tenant
        perfil = _perfil_padrao(tipo_tenant)

        user = User(
            tenant_id=tenant.id,
            nome=nome_user,
            email=email,
            perfil=perfil,
        )
        user.set_senha(senha)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Bem-vindo ao NeuroLink TEA, {nome_user}! 🎉', 'success')
        return _redirecionar_por_perfil(user.perfil)

    return render_template('auth/registro.html')


# ─── CONVITE (adicionar usuário a tenant existente) ───────────────────────────
@auth_bp.route('/convite/<token>', methods=['GET', 'POST'])
@logout_required
def aceitar_convite(token):
    # TODO: implementar sistema de convites por token JWT
    flash('Funcionalidade de convite em desenvolvimento.', 'info')
    return redirect(url_for('auth.login'))


# ─── LOGOUT ───────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com segurança.', 'info')
    return redirect(url_for('auth.login'))


# ─── ESQUECI A SENHA ──────────────────────────────────────────────────────────
@auth_bp.route('/esqueci-senha', methods=['GET', 'POST'])
@logout_required
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email).first()
        # Não revelar se o email existe ou não (segurança)
        flash('Se este e-mail estiver cadastrado, você receberá as instruções em breve.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/esqueci_senha.html')


# ─── HELPERS PRIVADOS ─────────────────────────────────────────────────────────
def _redirecionar_por_perfil(perfil):
    destino = REDIRECT_POR_PERFIL.get(perfil, 'dashboard.familia')
    return redirect(url_for(destino))


def _perfil_padrao(tipo_tenant):
    mapa = {
        TenantTipo.FAMILIA:     UserPerfil.PAI_MAE,
        TenantTipo.ESCOLA:      UserPerfil.COORDENADOR,
        TenantTipo.CLINICA:     UserPerfil.TERAPEUTA,
        TenantTipo.INSTITUICAO: UserPerfil.GESTOR,
    }
    return mapa.get(tipo_tenant, UserPerfil.PAI_MAE)


def _gerar_slug(nome):
    import re
    slug = nome.lower()
    slug = slug.replace(' ', '-')
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    # Garantir unicidade
    base = slug
    n = 1
    while Tenant.query.filter_by(slug=slug).first():
        slug = f'{base}-{n}'
        n += 1
    return slug
