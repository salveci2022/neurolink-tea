"""
NeuroLink TEA — GPS completo com PDF via ReportLab
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime
from io import BytesIO
import math

from app.models import db, Crianca, Localizacao, CercaVirtual
from app.utils.decorators import tenant_ativo

gps_bp = Blueprint('gps', __name__)


def haversine(lat1, lng1, lat2, lng2):
    R = 6371000
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ── PÁGINAS ───────────────────────────────────────────────
@gps_bp.route('/')
@login_required
@tenant_ativo
def index():
    criancas = current_user.criancas.filter_by(ativo=True).all()
    return render_template('gps/index.html', criancas=criancas)


@gps_bp.route('/<int:crianca_id>')
@login_required
@tenant_ativo
def mapa(crianca_id):
    crianca  = Crianca.query.get_or_404(crianca_id)
    ultima   = crianca.localizacoes.order_by(Localizacao.criado_em.desc()).first()
    cercas   = CercaVirtual.query.filter_by(crianca_id=crianca_id, ativa=True).all()
    historico = crianca.localizacoes.order_by(Localizacao.criado_em.desc()).limit(50).all()
    return render_template('gps/mapa.html',
        crianca=crianca, ultima=ultima,
        cercas=cercas, historico=historico)


# ── /save ─────────────────────────────────────────────────
@gps_bp.route('/save', methods=['POST'])
@login_required
def save():
    dados = request.get_json() or {}
    lat   = dados.get('latitude')
    lng   = dados.get('longitude')
    crianca_id = dados.get('crianca_id')

    if not lat or not lng:
        return jsonify({'ok': False, 'erro': 'Coordenadas obrigatorias'}), 400

    crianca = Crianca.query.get(crianca_id)
    if not crianca or crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False, 'erro': 'Sem permissao'}), 403

    loc = Localizacao(
        crianca_id = crianca_id,
        latitude   = float(lat),
        longitude  = float(lng),
        precisao_m = dados.get('precisao_m'),
    )
    db.session.add(loc)
    db.session.commit()

    alertas = []
    for cerca in CercaVirtual.query.filter_by(crianca_id=crianca_id, ativa=True).all():
        dist = haversine(float(lat), float(lng), cerca.latitude, cerca.longitude)
        if dist > cerca.raio_metros:
            alertas.append({'nome': cerca.nome,
                            'distancia_m': round(dist),
                            'raio_m': cerca.raio_metros})

    return jsonify({'ok': True, 'id': loc.id,
                    'criado_em': loc.criado_em.strftime('%H:%M:%S'),
                    'alertas': alertas})


# ── /list ─────────────────────────────────────────────────
@gps_bp.route('/list/<int:crianca_id>', methods=['GET'])
@login_required
def list_locs(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False}), 403

    locs = crianca.localizacoes.order_by(
        Localizacao.criado_em.desc()).limit(200).all()

    return jsonify({'ok': True, 'total': len(locs), 'dados': [
        {'id': l.id,
         'latitude':  l.latitude,
         'longitude': l.longitude,
         'precisao':  l.precisao_m,
         'criado_em': l.criado_em.strftime('%d/%m/%Y %H:%M:%S')}
        for l in locs
    ]})


# ── /clear ────────────────────────────────────────────────
@gps_bp.route('/limpar/<int:crianca_id>', methods=['DELETE'])
@login_required
def limpar(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False}), 403

    total = Localizacao.query.filter_by(crianca_id=crianca_id).count()
    Localizacao.query.filter_by(crianca_id=crianca_id).delete()
    db.session.commit()
    return jsonify({'ok': True, 'apagados': total})


# ── /pdf ──────────────────────────────────────────────────
@gps_bp.route('/pdf/<int:crianca_id>', methods=['GET'])
@login_required
def gerar_pdf(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False}), 403

    locs = crianca.localizacoes.order_by(
        Localizacao.criado_em.desc()).limit(500).all()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                         Paragraph, Spacer, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        TEAL   = colors.HexColor('#0F6E56')
        TEAL_L = colors.HexColor('#E1F5EE')
        GRAY   = colors.HexColor('#5F5E5A')
        DARK   = colors.HexColor('#1a1a18')

        titulo_style = ParagraphStyle('titulo', fontSize=20, textColor=TEAL,
            fontName='Helvetica-Bold', spaceAfter=4)
        sub_style    = ParagraphStyle('sub',    fontSize=11, textColor=GRAY,
            fontName='Helvetica', spaceAfter=16)
        label_style  = ParagraphStyle('label',  fontSize=10, textColor=GRAY,
            fontName='Helvetica')
        sec_style    = ParagraphStyle('sec',    fontSize=12, textColor=TEAL,
            fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=8)

        story = []

        # Cabeçalho
        story.append(Paragraph('📍 Relatório de Rastreamento GPS', titulo_style))
        story.append(Paragraph(
            f'NeuroLink TEA · Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}',
            sub_style))
        story.append(HRFlowable(width='100%', thickness=1,
            color=TEAL, spaceAfter=12))

        # Informações
        story.append(Paragraph('Informações do Rastreamento', sec_style))
        info_data = [
            ['Criança:', crianca.nome],
            ['Nível TEA:', f'Nível {crianca.nivel_tea}' if crianca.nivel_tea else 'Não informado'],
            ['Responsável:', current_user.nome],
            ['Total de pontos:', str(len(locs))],
            ['Período:', f'{locs[-1].criado_em.strftime("%d/%m/%Y %H:%M")} → {locs[0].criado_em.strftime("%d/%m/%Y %H:%M")}' if locs else '—'],
        ]
        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME',  (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE',  (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,-1), GRAY),
            ('TEXTCOLOR', (1,0), (1,-1), DARK),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, TEAL_L]),
            ('TOPPADDING',  (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        # Distância total
        dist_total = 0
        locs_list  = list(reversed(locs))
        for i in range(1, len(locs_list)):
            dist_total += haversine(
                locs_list[i-1].latitude, locs_list[i-1].longitude,
                locs_list[i].latitude,   locs_list[i].longitude)
        dist_fmt = f'{dist_total/1000:.2f} km' if dist_total >= 1000 else f'{dist_total:.0f} m'

        story.append(Paragraph('Estatísticas', sec_style))
        stat_data = [
            ['Pontos registrados', 'Distância total', 'Precisão média'],
            [str(len(locs)), dist_fmt,
             f'{sum(l.precisao_m for l in locs if l.precisao_m)/max(len([l for l in locs if l.precisao_m]),1):.0f} m'
             if any(l.precisao_m for l in locs) else '—'],
        ]
        stat_table = Table(stat_data, colWidths=[5.3*cm, 5.3*cm, 5.3*cm])
        stat_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,0), TEAL),
            ('TEXTCOLOR',    (0,0), (-1,0), colors.white),
            ('BACKGROUND',   (0,1), (-1,1), TEAL_L),
            ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME',     (0,1), (-1,1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,-1), 11),
            ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING',   (0,0), (-1,-1), 8),
            ('BOTTOMPADDING',(0,0), (-1,-1), 8),
            ('GRID',         (0,0), (-1,-1), 0.5, colors.white),
        ]))
        story.append(stat_table)
        story.append(Spacer(1, 0.5*cm))

        # Tabela de pontos
        story.append(Paragraph(
            f'Histórico de Localizações {"(últimos 200)" if len(locs) > 200 else ""}',
            sec_style))

        table_data = [['#', 'Data/Hora', 'Latitude', 'Longitude', 'Precisão']]
        for i, loc in enumerate(locs[:200], 1):
            table_data.append([
                str(i),
                loc.criado_em.strftime('%d/%m %H:%M:%S'),
                f'{loc.latitude:.6f}',
                f'{loc.longitude:.6f}',
                f'~{loc.precisao_m:.0f}m' if loc.precisao_m else '—',
            ])

        col_widths = [1*cm, 4*cm, 4*cm, 4*cm, 2.5*cm]
        locs_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        row_colors = []
        for i in range(1, len(table_data)):
            bg = colors.white if i % 2 == 0 else TEAL_L
            row_colors.append(('BACKGROUND', (0,i), (-1,i), bg))

        locs_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), TEAL),
            ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE',      (0,0), (-1,-1), 9),
            ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
            *row_colors,
        ]))
        story.append(locs_table)

        # Rodapé
        story.append(Spacer(1, 0.8*cm))
        story.append(HRFlowable(width='100%', thickness=0.5,
            color=GRAY, spaceAfter=6))
        story.append(Paragraph(
            'NeuroLink TEA · SPYNET Tecnologia Forense & Soluções Digitais Ltda · '
            'CNPJ 64.000.808/0001-51 · Brasília-DF',
            ParagraphStyle('footer', fontSize=8, textColor=GRAY,
                fontName='Helvetica', alignment=TA_CENTER)))

        doc.build(story)
        buf.seek(0)

        nome_arquivo = f'GPS_{crianca.nome.replace(" ","_")}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        return send_file(buf, as_attachment=True,
                         download_name=nome_arquivo,
                         mimetype='application/pdf')

    except ImportError:
        return jsonify({'ok': False,
                        'erro': 'ReportLab nao instalado. Execute: pip install reportlab'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


# ── CERCA ─────────────────────────────────────────────────
@gps_bp.route('/cerca/nova', methods=['POST'])
@login_required
def nova_cerca():
    dados = request.get_json() or {}
    crianca = Crianca.query.get_or_404(dados.get('crianca_id'))
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False}), 403
    cerca = CercaVirtual(
        crianca_id  = crianca.id,
        nome        = dados.get('nome', 'Zona segura'),
        latitude    = float(dados.get('latitude')),
        longitude   = float(dados.get('longitude')),
        raio_metros = float(dados.get('raio_metros', 200)),
    )
    db.session.add(cerca)
    db.session.commit()
    return jsonify({'ok': True, 'id': cerca.id})


# ── ÚLTIMA POSIÇÃO ────────────────────────────────────────
@gps_bp.route('/ultima/<int:crianca_id>', methods=['GET'])
@login_required
def ultima(crianca_id):
    crianca = Crianca.query.get_or_404(crianca_id)
    if crianca.tenant_id != current_user.tenant_id:
        return jsonify({'ok': False}), 403
    loc = crianca.localizacoes.order_by(Localizacao.criado_em.desc()).first()
    if not loc:
        return jsonify({'ok': False, 'erro': 'Sem localizacao'})
    return jsonify({'ok': True, 'latitude': loc.latitude,
                    'longitude': loc.longitude,
                    'criado_em': loc.criado_em.strftime('%d/%m/%Y %H:%M:%S')})
