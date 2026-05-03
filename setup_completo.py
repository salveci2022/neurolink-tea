"""
NeuroLink TEA — Setup completo
Execute: python setup_completo.py
"""
import os
import sys

# Fix encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Garantir .env correto
env_content = (
    'SECRET_KEY=neurolink2025spynet\n'
    'DATABASE_URL=sqlite:///neurolink_tea.db\n'
    'FLASK_ENV=development\n'
    'ANTHROPIC_API_KEY=\n'
)
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)
print("OK - .env criado")

from app import create_app
from app.models import db, User, Tenant, UserPerfil, TenantTipo, PlanoTipo

app = create_app('development')

with app.app_context():
    # Criar tabelas
    db.create_all()
    print("OK - Tabelas criadas")

    # Criar tenant e usuario se nao existir
    if not Tenant.query.filter_by(slug='spynet').first():
        t = Tenant(nome='SPYNET', slug='spynet',
                   tipo=TenantTipo.FAMILIA, plano=PlanoTipo.GRATIS)
        db.session.add(t)
        db.session.flush()

        u = User(tenant_id=t.id, nome='Salveci',
                 email='salvecidossantos454@gmail.com',
                 perfil=UserPerfil.PAI_MAE)
        u.set_senha('senha123')
        db.session.add(u)
        db.session.commit()
        print("OK - Usuario criado")
    else:
        # Garantir que usuario existe
        t = Tenant.query.filter_by(slug='spynet').first()
        if not User.query.filter_by(email='salvecidossantos454@gmail.com').first():
            u = User(tenant_id=t.id, nome='Salveci',
                     email='salvecidossantos454@gmail.com',
                     perfil=UserPerfil.PAI_MAE)
            u.set_senha('senha123')
            db.session.add(u)
            db.session.commit()
            print("OK - Usuario criado")
        else:
            print("OK - Usuario ja existe")

print()
print("=" * 40)
print("SETUP CONCLUIDO!")
print("=" * 40)
print("Email: salvecidossantos454@gmail.com")
print("Senha: senha123")
print()
print("Agora execute: python run.py")
print("Acesse: http://localhost:5000/login")
