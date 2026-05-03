# NeuroLink TEA 🧠
**Ecossistema SaaS para suporte ao Transtorno do Espectro Autista**
Desenvolvido por SPYNET Tecnologia Forense & Soluções Digitais Ltda

---

## Segmentos atendidos
| Segmento | Perfis | Planos |
|---|---|---|
| Famílias | pai_mae, cuidador | Grátis / Família / Família Plus |
| Escolas | professor, coordenador | Escola P / Pro / Rede |
| Clínicas | terapeuta, psicologo | Autônomo / Clínica / Enterprise |
| Instituições | gestor | Associação / Municipal / Estadual |

---

## Stack
- **Backend:** Flask 3 + SQLAlchemy + PostgreSQL
- **Auth:** Flask-Login + Bcrypt
- **Migrations:** Flask-Migrate (Alembic)
- **IA:** Anthropic API (claude-sonnet-4)
- **WhatsApp:** Z-API
- **GPS:** coordenadas via API REST + Google Maps
- **Deploy:** Render.com (Procfile incluso)

---

## Instalação local

```bash
# 1. Clonar e criar ambiente virtual
git clone https://github.com/salveci2022/neurolink-tea
cd neurolink-tea
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# edite .env com suas credenciais

# 4. Criar banco de dados PostgreSQL
createdb neurolink_tea_dev  # ou via pgAdmin

# 5. Rodar migrações
flask db init
flask db migrate -m "inicial"
flask db upgrade

# 6. Popular com dados de exemplo
flask seed

# 7. Iniciar
python run.py
```

Acesse: http://localhost:5000

---

## Estrutura do projeto

```
neurolink-tea/
├── app/
│   ├── models/          # User, Tenant, Crianca, Rotina, Crise, GPS, Prontuario
│   ├── routes/
│   │   ├── auth.py      # Login, registro, logout (multi-tenant)
│   │   ├── dashboard.py # Dashboards por perfil
│   │   ├── criancas.py  # CRUD de crianças
│   │   ├── rotinas.py   # Gestão de rotinas e atividades
│   │   ├── gps.py       # Mapa em tempo real + cercas virtuais
│   │   ├── clinica.py   # Prontuário, sessões, relatórios
│   │   ├── ia.py        # Assistente IA + geração de relatórios
│   │   ├── admin.py     # Painel SPYNET / superadmin
│   │   └── api.py       # API REST para PWA mobile
│   ├── utils/
│   │   ├── decorators.py       # perfil_requerido, tenant_ativo, mesmo_tenant
│   │   └── template_filters.py # data_br, hora, nivel_tea_label
│   └── templates/       # Jinja2 por módulo
├── config.py            # Dev / Prod / Testing
├── run.py               # Entrypoint + CLI (seed, criar-db)
├── Procfile             # Render.com
└── requirements.txt
```

---

## API REST (mobile)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/rotinas/{id}/hoje` | Atividades do dia da criança |
| POST | `/api/v1/atividades/{id}/status` | Marcar atividade concluída |
| POST | `/api/v1/gps/{id}/update` | Atualizar localização |
| GET | `/api/v1/gps/{id}/ultima` | Última localização |
| POST | `/api/v1/crises` | Registrar crise |
| POST | `/api/v1/crises/{id}/resolver` | Encerrar crise |

---

## Módulo IA

| Endpoint | Função |
|---|---|
| POST `/ia/chat` | Chat com streaming (SSE) |
| POST `/ia/sugestao-rotina` | Rotina personalizada em JSON |
| POST `/ia/gerar-relatorio` | Relatório terapêutico em texto |

---

## Deploy no Render.com

1. Novo Web Service → conectar repo GitHub
2. Build command: `pip install -r requirements.txt`
3. Start command: (usar Procfile)
4. Adicionar variáveis de ambiente do `.env.example`
5. Criar PostgreSQL no Render e conectar via `DATABASE_URL`

---

## Licença
Proprietário — SPYNET Tecnologia Forense & Soluções Digitais Ltda  
CNPJ 64.000.808/0001-51 — Brasília-DF
