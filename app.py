from flask import Flask
from extensoes import mysql
from routes_app import routes  # não usa mais 'gestao_horarios.routes_app'
from datetime import datetime

app = Flask(__name__)

# 🔐 Configurações do banco e chave secreta
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'gestao_horarios'
app.config['SECRET_KEY'] = 'sua_chave_secreta'

# 🔌 Inicializa o MySQL com o app
mysql.init_app(app)

# 🔗 Registra o blueprint de rotas
app.register_blueprint(routes, url_prefix='/')


# ✅ REGISTRO DO FILTRO DE DATA PARA JINJA2
@app.template_filter('date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, str):
        try:
            # Tenta converter string ISO para datetime
            value = datetime.strptime(value[:10], '%Y-%m-%d')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

# 🚀 Início do app
if __name__ == '__main__':
    app.run(debug=True)
