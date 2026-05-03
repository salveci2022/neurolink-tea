"""
NeuroLink TEA — Módulo IA (Anthropic API)
Assistente especializado em TEA para terapeutas, professores e pais.
"""
from flask import Blueprint, request, jsonify, render_template, stream_with_context, Response
from flask_login import login_required, current_user
import anthropic
import json

from app.models import Crianca, RegistroCrise, Sessao, UserPerfil
from app.utils.decorators import tenant_ativo

ia_bp = Blueprint('ia', __name__)

SYSTEM_PROMPT = """Você é o NeuroLink AI, um assistente especializado em Transtorno do Espectro Autista (TEA).
Você apoia pais, professores, terapeutas e gestores de instituições com:
- Estratégias baseadas em evidências (ABA, TEACCH, Denver, RDI)
- Sugestões de manejo de crises sensoriais e comportamentais
- Orientações sobre comunicação alternativa e aumentativa (CAA)
- Análise de padrões de comportamento
- Redação de relatórios e laudos terapêuticos
- Dicas de rotina visual e previsibilidade

Seja sempre empático, objetivo e baseado em práticas validadas pela ciência.
Responda em português brasileiro. Nunca substitua a orientação de profissionais especializados.
Quando adequado, peça mais contexto sobre o perfil específico da criança."""


@ia_bp.route('/')
@login_required
@tenant_ativo
def index():
    return render_template('ia/chat.html')


@ia_bp.route('/chat', methods=['POST'])
@login_required
@tenant_ativo
def chat():
    """Chat com streaming para o assistente IA."""
    dados = request.get_json() or {}
    mensagens   = dados.get('mensagens', [])
    crianca_id  = dados.get('crianca_id')

    if not mensagens:
        return jsonify({'erro': 'Mensagens vazias.'}), 400

    # Adiciona contexto da criança se informada
    system = SYSTEM_PROMPT
    if crianca_id:
        ctx = _contexto_crianca(crianca_id)
        if ctx:
            system += f"\n\n--- CONTEXTO DA CRIANÇA ---\n{ctx}"

    def gerar():
        try:
            from flask import current_app
            client = anthropic.Anthropic(
                api_key=current_app.config.get('ANTHROPIC_API_KEY')
            )
            with client.messages.stream(
                model='claude-sonnet-4-20250514',
                max_tokens=1500,
                system=system,
                messages=mensagens,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'erro': str(e)})}\n\n"

    return Response(stream_with_context(gerar()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache',
                             'X-Accel-Buffering': 'no'})


@ia_bp.route('/sugestao-rotina', methods=['POST'])
@login_required
@tenant_ativo
def sugestao_rotina():
    """Gera sugestão de rotina personalizada para uma criança."""
    dados      = request.get_json() or {}
    crianca_id = dados.get('crianca_id')
    contexto   = dados.get('contexto', '')

    if not crianca_id:
        return jsonify({'erro': 'crianca_id obrigatório.'}), 400

    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'erro': 'Sem permissão.'}), 403

    ctx = _contexto_crianca(crianca_id)
    prompt = f"""Com base no perfil desta criança com TEA:

{ctx}

Contexto adicional: {contexto}

Crie uma rotina matinal estruturada e detalhada (das 7h às 12h), com:
1. Lista de atividades com duração estimada e emoji representativo
2. Estratégias de transição entre atividades
3. Pontos de atenção específicos para este perfil sensorial
4. Sugestões de avisos antecipados

Formato: JSON com estrutura [{{nome, icone, duracao_min, aviso_min, dicas}}]"""

    from flask import current_app
    client = anthropic.Anthropic(api_key=current_app.config.get('ANTHROPIC_API_KEY'))

    try:
        resp = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        texto = resp.content[0].text
        # Tentar extrair JSON
        try:
            inicio = texto.find('[')
            fim    = texto.rfind(']') + 1
            rotina_json = json.loads(texto[inicio:fim])
        except Exception:
            rotina_json = None

        return jsonify({'ok': True, 'sugestao': texto, 'rotina': rotina_json})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


@ia_bp.route('/gerar-relatorio', methods=['POST'])
@login_required
@tenant_ativo
def gerar_relatorio():
    """Gera rascunho de relatório terapêutico em texto."""
    dados      = request.get_json() or {}
    crianca_id = dados.get('crianca_id')
    tipo       = dados.get('tipo', 'evolucao')  # evolucao | escola | laudo

    if not crianca_id:
        return jsonify({'erro': 'crianca_id obrigatório.'}), 400

    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'erro': 'Sem permissão.'}), 403

    ctx     = _contexto_crianca(crianca_id)
    sessoes = _ultimas_sessoes(crianca_id, n=5)

    tipo_prompt = {
        'evolucao': 'relatório de evolução terapêutica para compartilhar com a família',
        'escola':   'relatório de acompanhamento para a escola, com orientações pedagógicas',
        'laudo':    'laudo clínico formal seguindo normas do CFP/CFO',
    }

    prompt = f"""Profissional: {current_user.nome} ({current_user.perfil})
Criança: {crianca.nome}, {crianca.idade} anos, TEA nível {crianca.nivel_tea or '?'}

{ctx}

Últimas sessões:
{sessoes}

Gere um {tipo_prompt.get(tipo, 'relatório')} completo, profissional e estruturado.
Use linguagem técnica mas acessível. Inclua: observações, evolução, pontos de atenção e recomendações."""

    from flask import current_app
    client = anthropic.Anthropic(api_key=current_app.config.get('ANTHROPIC_API_KEY'))

    try:
        resp = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return jsonify({'ok': True, 'relatorio': resp.content[0].text})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _contexto_crianca(crianca_id):
    crianca = Crianca.query.get(crianca_id)
    if not crianca:
        return ''

    crises_recentes = crianca.crises.order_by('iniciou_em desc').limit(5).all()
    resumo_crises = ', '.join(
        f"{c.tipo}(intensidade {c.intensidade})" for c in crises_recentes
    ) or 'nenhuma recente'

    return (
        f"Nome: {crianca.nome} | Idade: {crianca.idade} anos | Nível TEA: {crianca.nivel_tea or 'não informado'}\n"
        f"Sensibilidade sonora: {crianca.sensibilidade_som}/5 | "
        f"Sensibilidade luminosa: {crianca.sensibilidade_luz}/5 | "
        f"Sensibilidade ao toque: {crianca.sensibilidade_toque}/5\n"
        f"Crises recentes: {resumo_crises}\n"
        f"Notas: {crianca.descricao or 'sem notas'}"
    )


def _ultimas_sessoes(crianca_id, n=5):
    from app.models import Prontuario
    prontuario = Prontuario.query.filter_by(crianca_id=crianca_id).first()
    if not prontuario:
        return 'Sem sessões registradas.'

    sessoes = prontuario.sessoes.order_by(Sessao.data_sessao.desc()).limit(n).all()
    if not sessoes:
        return 'Sem sessões registradas.'

    linhas = []
    for s in sessoes:
        linhas.append(
            f"- {s.data_sessao.strftime('%d/%m/%Y')}: {s.evolucao or 'sem registro'}"
            f" | Humor: {s.humor_inicio}→{s.humor_fim}"
        )
    return '\n'.join(linhas)
