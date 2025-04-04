from flask import Flask
from extensoes import mysql
from routes_app import routes  # não usa mais 'gestao_horarios.routes_app'

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'gestao_horarios'
app.config['SECRET_KEY'] = 'sua_chave_secreta'

mysql.init_app(app)  # ✅ agora usa init_app

app.register_blueprint(routes, url_prefix='/')

if __name__ == '__main__':
    app.run(debug=True)
