import os
import sys

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

from app import create_app
from app.models import db, User, Tenant, UserPerfil, TenantTipo, PlanoTipo

app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.cli.command('seed')
def seed():
    with app.app_context():
        db.create_all()
        if not Tenant.query.filter_by(slug='demo').first():
            t = Tenant(nome='Demo', slug='demo',
                      tipo=TenantTipo.FAMILIA, plano=PlanoTipo.GRATIS)
            db.session.add(t)
            db.session.flush()
            u = User(tenant_id=t.id, nome='Salveci',
                    email='salvecidossantos454@gmail.com',
                    perfil=UserPerfil.PAI_MAE)
            u.set_senha('senha123')
            db.session.add(u)
            db.session.commit()
            print('Seed OK!')

# Criar tabelas automaticamente
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)))
