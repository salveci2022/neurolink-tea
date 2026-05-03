"""
NeuroLink TEA — Script de inicializacao completo
Execute: python iniciar.py
Faz tudo: cria banco, tabelas, usuario e inicia o servidor.
"""
import os
import sys

# Fix encoding Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Garantir .env correto sem caracteres especiais
with open('.env', 'w', encoding='utf-8') as f:
    f.write('SECRET_KEY=neurolink2025spynet\n')
    f.write('DATABASE_URL=sqlite:///neurolink_tea.db\n')
    f.write('FLASK_ENV=development\n')
    f.write('ANTHROPIC_API_KEY=\n')
print("[1/4] .env OK")

from app import create_app
from app.models import db, User, Tenant, UserPerfil, TenantTipo, PlanoTipo

app = create_app('development')

with app.app_context():
    # Criar TODAS as tabelas
    db.create_all()
    print("[2/4] Tabelas criadas: users, tenants, criancas, rotinas, etc.")

    # Criar tenant se nao existir
    tenant = Tenant.query.filter_by(slug='spynet').first()
    if not tenant:
        tenant = Tenant(
            nome='SPYNET',
            slug='spynet',
            tipo=TenantTipo.FAMILIA,
            plano=PlanoTipo.GRATIS,
        )
        db.session.add(tenant)
        db.session.flush()
        print("[3/4] Tenant criado")
    else:
        print("[3/4] Tenant ja existe")

    # Criar usuario se nao existir
    user = User.query.filter_by(
        email='salvecidossantos454@gmail.com').first()
    if not user:
        user = User(
            tenant_id=tenant.id,
            nome='Salveci',
            email='salvecidossantos454@gmail.com',
            perfil=UserPerfil.PAI_MAE,
        )
        user.set_senha('senha123')
        db.session.add(user)
        db.session.commit()
        print("[4/4] Usuario criado")
    else:
        print("[4/4] Usuario ja existe")

print()
print("=" * 45)
print("  SISTEMA PRONTO!")
print("=" * 45)
print("  Login: salvecidossantos454@gmail.com")
print("  Senha: senha123")
print("  URL:   http://localhost:5000/login")
print("=" * 45)
print()

# Iniciar servidor
os.system('python run.py')
