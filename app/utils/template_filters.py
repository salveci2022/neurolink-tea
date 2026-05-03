def register_filters(app):
    @app.template_filter('data_br')
    def data_br(d):
        if not d: return ''
        return d.strftime('%d/%m/%Y')
    @app.template_filter('hora')
    def hora(d):
        if not d: return ''
        return d.strftime('%H:%M')
    @app.template_filter('nivel_tea_label')
    def nivel_tea_label(n):
        return {'1':'Leve','2':'Moderado','3':'Severo'}.get(str(n),'—')
