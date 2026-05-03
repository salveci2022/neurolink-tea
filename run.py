import os
import sys

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

from app import create_app
from app.models import db, User, Tenant, UserPerfil, TenantTipo, PlanoTipo

app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.cli.command('seed')
def seed():
    t = Tenant(nome='SPYNET Demo', slug='spynet-demo',
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
