"""
NeuroLink TEA — Models
Multi-tenant: cada Tenant é uma organização (escola, clínica, instituição ou família).
Usuários pertencem a um Tenant e têm um Perfil que define o que podem fazer.
"""
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin

db     = SQLAlchemy()
bcrypt = Bcrypt()


# ─────────────────────────────────────────────
# ENUMS / CONSTANTES
# ─────────────────────────────────────────────
class TenantTipo:
    FAMILIA     = 'familia'
    ESCOLA      = 'escola'
    CLINICA     = 'clinica'
    INSTITUICAO = 'instituicao'
    TODOS = [FAMILIA, ESCOLA, CLINICA, INSTITUICAO]

class UserPerfil:
    PAI_MAE     = 'pai_mae'       # acesso família
    CUIDADOR    = 'cuidador'
    PROFESSOR   = 'professor'     # acesso escola
    COORDENADOR = 'coordenador'
    TERAPEUTA   = 'terapeuta'     # acesso clínica
    PSICOLOGO   = 'psicologo'
    GESTOR      = 'gestor'        # acesso institucional
    ADMIN       = 'admin'         # superadmin SPYNET/NeuroLink
    TODOS = [PAI_MAE, CUIDADOR, PROFESSOR, COORDENADOR,
             TERAPEUTA, PSICOLOGO, GESTOR, ADMIN]

class PlanoTipo:
    GRATIS       = 'gratis'
    FAMILIA      = 'familia'
    FAMILIA_PLUS = 'familia_plus'
    ESCOLA_P     = 'escola_pequena'
    ESCOLA_PRO   = 'escola_pro'
    REDE         = 'rede_escolar'
    AUTONOMO     = 'autonomo'
    CLINICA      = 'clinica'
    CLINICA_ENT  = 'clinica_enterprise'
    ASSOCIACAO   = 'associacao'
    MUNICIPAL    = 'municipal'
    ESTADUAL     = 'estadual'

class NivelTEA:
    NIVEL_1 = '1'  # leve
    NIVEL_2 = '2'  # moderado
    NIVEL_3 = '3'  # severo

class StatusAtividade:
    PENDENTE   = 'pendente'
    CONCLUIDA  = 'concluida'
    PULADA     = 'pulada'

class TipoCrise:
    SENSORIAL   = 'sensorial'
    EMOCIONAL   = 'emocional'
    TRANSICAO   = 'transicao'
    ALIMENTACAO = 'alimentacao'
    OUTRO       = 'outro'


# ─────────────────────────────────────────────
# TENANT  (multi-tenant core)
# ─────────────────────────────────────────────
class Tenant(db.Model):
    __tablename__ = 'tenants'

    id           = db.Column(db.Integer, primary_key=True)
    nome         = db.Column(db.String(120), nullable=False)
    slug         = db.Column(db.String(80), unique=True, nullable=False)  # URL-friendly
    tipo         = db.Column(db.String(20), nullable=False)               # TenantTipo
    plano        = db.Column(db.String(30), default=PlanoTipo.GRATIS)
    ativo        = db.Column(db.Boolean, default=True)
    cnpj_cpf     = db.Column(db.String(20))
    telefone     = db.Column(db.String(20))
    cidade       = db.Column(db.String(80))
    estado       = db.Column(db.String(2))
    logo_url     = db.Column(db.String(255))
    plano_expira = db.Column(db.Date)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    usuarios  = db.relationship('User',    back_populates='tenant', lazy='dynamic')
    criancas  = db.relationship('Crianca', back_populates='tenant', lazy='dynamic')

    def __repr__(self):
        return f'<Tenant {self.slug} [{self.tipo}]>'

    def plano_ativo(self):
        if self.plano == PlanoTipo.GRATIS:
            return True
        if self.plano_expira is None:
            return False
        return date.today() <= self.plano_expira

    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome, 'slug': self.slug,
            'tipo': self.tipo, 'plano': self.plano, 'ativo': self.ativo,
        }


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    tenant_id    = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nome         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash   = db.Column(db.String(255), nullable=False)
    perfil       = db.Column(db.String(20), nullable=False)  # UserPerfil
    ativo        = db.Column(db.Boolean, default=True)
    telefone     = db.Column(db.String(20))
    avatar_url   = db.Column(db.String(255))
    ultimo_login = db.Column(db.DateTime)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    tenant    = db.relationship('Tenant', back_populates='usuarios')
    criancas  = db.relationship('Crianca', secondary='crianca_responsavel',
                                 back_populates='responsaveis', lazy='dynamic')

    def set_senha(self, senha):
        self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    def check_senha(self, senha):
        return bcrypt.check_password_hash(self.senha_hash, senha)

    def is_admin(self):
        return self.perfil == UserPerfil.ADMIN

    def pode_acessar(self, recurso):
        """Mapa simples de permissões por perfil."""
        permissoes = {
            UserPerfil.ADMIN:       ['*'],
            UserPerfil.GESTOR:      ['dashboard', 'criancas', 'relatorios', 'usuarios', 'config'],
            UserPerfil.COORDENADOR: ['dashboard', 'criancas', 'relatorios', 'usuarios'],
            UserPerfil.PROFESSOR:   ['dashboard', 'criancas', 'rotinas', 'registro_comportamento'],
            UserPerfil.TERAPEUTA:   ['dashboard', 'criancas', 'prontuario', 'relatorios', 'ia'],
            UserPerfil.PSICOLOGO:   ['dashboard', 'criancas', 'prontuario', 'relatorios'],
            UserPerfil.PAI_MAE:     ['dashboard', 'rotinas', 'comunicador', 'gps', 'crises'],
            UserPerfil.CUIDADOR:    ['dashboard', 'rotinas', 'comunicador'],
        }
        perms = permissoes.get(self.perfil, [])
        return '*' in perms or recurso in perms

    def __repr__(self):
        return f'<User {self.email} [{self.perfil}]>'

    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome, 'email': self.email,
            'perfil': self.perfil, 'tenant_id': self.tenant_id,
        }


# ─────────────────────────────────────────────
# CRIANÇA  (pessoa com TEA)
# ─────────────────────────────────────────────
crianca_responsavel = db.Table(
    'crianca_responsavel',
    db.Column('crianca_id', db.Integer, db.ForeignKey('criancas.id')),
    db.Column('user_id',    db.Integer, db.ForeignKey('users.id')),
)

class Crianca(db.Model):
    __tablename__ = 'criancas'

    id              = db.Column(db.Integer, primary_key=True)
    tenant_id       = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nome            = db.Column(db.String(120), nullable=False)
    data_nascimento = db.Column(db.Date)
    nivel_tea       = db.Column(db.String(1))           # NivelTEA
    foto_url        = db.Column(db.String(255))
    descricao       = db.Column(db.Text)                # notas gerais
    # Perfil sensorial
    sensibilidade_som    = db.Column(db.Integer, default=3)  # 1–5
    sensibilidade_luz    = db.Column(db.Integer, default=3)
    sensibilidade_toque  = db.Column(db.Integer, default=3)
    preferencias_visuais = db.Column(db.Text)           # JSON string
    gatilhos_crise       = db.Column(db.Text)           # JSON string
    ativo        = db.Column(db.Boolean, default=True)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    tenant       = db.relationship('Tenant',  back_populates='criancas')
    responsaveis = db.relationship('User', secondary='crianca_responsavel',
                                    back_populates='criancas', lazy='dynamic')
    rotinas      = db.relationship('Rotina',      back_populates='crianca', lazy='dynamic')
    crises       = db.relationship('RegistroCrise', back_populates='crianca', lazy='dynamic')
    localizacoes = db.relationship('Localizacao',  back_populates='crianca', lazy='dynamic')

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    def __repr__(self):
        return f'<Crianca {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome, 'idade': self.idade,
            'nivel_tea': self.nivel_tea, 'foto_url': self.foto_url,
        }


# ─────────────────────────────────────────────
# ROTINA
# ─────────────────────────────────────────────
class Rotina(db.Model):
    __tablename__ = 'rotinas'

    id          = db.Column(db.Integer, primary_key=True)
    crianca_id  = db.Column(db.Integer, db.ForeignKey('criancas.id'), nullable=False)
    nome        = db.Column(db.String(120), nullable=False)   # ex.: "Rotina da Manhã"
    descricao   = db.Column(db.String(255))
    dias_semana = db.Column(db.String(20), default='1,2,3,4,5')  # 1=seg ... 7=dom
    ativa       = db.Column(db.Boolean, default=True)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)

    crianca     = db.relationship('Crianca', back_populates='rotinas')
    atividades  = db.relationship('Atividade', back_populates='rotina',
                                   order_by='Atividade.ordem', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Rotina {self.nome} / Criança {self.crianca_id}>'


class Atividade(db.Model):
    __tablename__ = 'atividades'

    id           = db.Column(db.Integer, primary_key=True)
    rotina_id    = db.Column(db.Integer, db.ForeignKey('rotinas.id'), nullable=False)
    nome         = db.Column(db.String(120), nullable=False)
    icone        = db.Column(db.String(10), default='⭐')   # emoji
    cor          = db.Column(db.String(7),  default='#1D9E75')
    duracao_min  = db.Column(db.Integer,    default=10)
    aviso_min    = db.Column(db.Integer,    default=5)       # avisar X min antes
    ordem        = db.Column(db.Integer,    default=0)
    audio_url    = db.Column(db.String(255))
    imagem_url   = db.Column(db.String(255))

    rotina       = db.relationship('Rotina', back_populates='atividades')
    registros    = db.relationship('RegistroAtividade', back_populates='atividade',
                                    lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Atividade {self.nome}>'


class RegistroAtividade(db.Model):
    __tablename__ = 'registros_atividade'

    id           = db.Column(db.Integer, primary_key=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividades.id'), nullable=False)
    data         = db.Column(db.Date, default=date.today)
    status       = db.Column(db.String(15), default=StatusAtividade.PENDENTE)
    concluida_em = db.Column(db.DateTime)
    observacao   = db.Column(db.String(255))

    atividade    = db.relationship('Atividade', back_populates='registros')


# ─────────────────────────────────────────────
# REGISTRO DE CRISE
# ─────────────────────────────────────────────
class RegistroCrise(db.Model):
    __tablename__ = 'registros_crise'

    id           = db.Column(db.Integer, primary_key=True)
    crianca_id   = db.Column(db.Integer, db.ForeignKey('criancas.id'), nullable=False)
    registrado_por = db.Column(db.Integer, db.ForeignKey('users.id'))
    tipo         = db.Column(db.String(20), default=TipoCrise.SENSORIAL)
    intensidade  = db.Column(db.Integer, default=3)   # 1–5
    duracao_min  = db.Column(db.Integer)
    gatilho      = db.Column(db.String(255))
    estrategia   = db.Column(db.Text)                 # o que funcionou
    observacao   = db.Column(db.Text)
    iniciou_em   = db.Column(db.DateTime, default=datetime.utcnow)
    resolveu_em  = db.Column(db.DateTime)

    crianca      = db.relationship('Crianca', back_populates='crises')
    autor        = db.relationship('User', foreign_keys=[registrado_por])

    def __repr__(self):
        return f'<Crise {self.tipo} criança {self.crianca_id}>'


# ─────────────────────────────────────────────
# LOCALIZAÇÃO GPS
# ─────────────────────────────────────────────
class Localizacao(db.Model):
    __tablename__ = 'localizacoes'

    id          = db.Column(db.Integer, primary_key=True)
    crianca_id  = db.Column(db.Integer, db.ForeignKey('criancas.id'), nullable=False)
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    precisao_m  = db.Column(db.Float)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)

    crianca     = db.relationship('Crianca', back_populates='localizacoes')


class CercaVirtual(db.Model):
    __tablename__ = 'cercas_virtuais'

    id          = db.Column(db.Integer, primary_key=True)
    crianca_id  = db.Column(db.Integer, db.ForeignKey('criancas.id'), nullable=False)
    nome        = db.Column(db.String(80), nullable=False)
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    raio_metros = db.Column(db.Float, default=200.0)
    ativa       = db.Column(db.Boolean, default=True)

    crianca     = db.relationship('Crianca')


# ─────────────────────────────────────────────
# PRONTUÁRIO CLÍNICO
# ─────────────────────────────────────────────
class Prontuario(db.Model):
    __tablename__ = 'prontuarios'

    id               = db.Column(db.Integer, primary_key=True)
    crianca_id       = db.Column(db.Integer, db.ForeignKey('criancas.id'), nullable=False, unique=True)
    terapeuta_id     = db.Column(db.Integer, db.ForeignKey('users.id'))
    data_diagnostico = db.Column(db.Date)
    cid_10           = db.Column(db.String(10), default='F84.0')
    hipotese_diag    = db.Column(db.Text)
    historico_familia= db.Column(db.Text)
    medicamentos     = db.Column(db.Text)    # JSON string
    alergias         = db.Column(db.Text)
    escola_atual     = db.Column(db.String(120))
    modalidade_terapia = db.Column(db.String(120))  # ABA, TEACCH, Denver...
    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    crianca          = db.relationship('Crianca')
    terapeuta        = db.relationship('User', foreign_keys=[terapeuta_id])
    sessoes          = db.relationship('Sessao', back_populates='prontuario',
                                        lazy='dynamic', cascade='all, delete-orphan')


class Sessao(db.Model):
    __tablename__ = 'sessoes'

    id             = db.Column(db.Integer, primary_key=True)
    prontuario_id  = db.Column(db.Integer, db.ForeignKey('prontuarios.id'), nullable=False)
    terapeuta_id   = db.Column(db.Integer, db.ForeignKey('users.id'))
    data_sessao    = db.Column(db.Date, nullable=False)
    duracao_min    = db.Column(db.Integer, default=50)
    objetivos      = db.Column(db.Text)
    evolucao       = db.Column(db.Text)
    comportamentos = db.Column(db.Text)   # JSON: lista de comportamentos observados
    humor_inicio   = db.Column(db.Integer)  # 1–5
    humor_fim      = db.Column(db.Integer)
    proximos_passos= db.Column(db.Text)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)

    prontuario     = db.relationship('Prontuario', back_populates='sessoes')
    terapeuta      = db.relationship('User', foreign_keys=[terapeuta_id])
