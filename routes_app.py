from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from extensoes import mysql  # ✅ aqui pegamos o mysql
from auth import login_obrigatorio, somente_master
import sqlite3
from flask import Flask
from datetime import datetime
import re




app = Flask(__name__)
# 🔹 Criando o Blueprint
routes = Blueprint('routes', __name__)

# 🔹 Lista fixa de turmas disponíveis
TURMAS = ["1ºA", "1ºB", "1ºC", "2ºA", "2ºB", "2ºC", "3ºA", "3ºB", "3ºC"]

dias_da_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
disciplinas = {
    "Língua Portuguesa": 6,
    "Matemática": 6,
    "Ciências": 4,
    "Geografia": 3,
    "Língua Inglesa": 3,
    "Arte": 2,
    "Educação Física": 3,
    "Filosofia": 3
}

# 🔹 Função para obter a conexão MySQL
def get_mysql():
    from app import mysql
    return mysql

# 🔹 ROTA PRINCIPAL
@routes.route('/')
def index():
    return render_template('index.html')

# 🔹 LOGIN
@routes.route('/login', methods=['GET', 'POST'])
def login():
    mysql = get_mysql()

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cur.fetchone()
        cur.close()

        if usuario and check_password_hash(usuario[3], senha):
            session['usuario_id'] = usuario[0]
            session['usuario_nome'] = usuario[1]
            session['usuario_perfil'] = usuario[4]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('routes.dashboard'))  # ou qualquer página protegida
        else:
            flash("E-mail ou senha inválidos", "danger")

    return render_template('login.html')

@routes.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('routes.login'))

# 🔹 DASHBOARD (exemplo)
@routes.route('/dashboard')
@login_obrigatorio
def dashboard():
    return render_template('dashboard.html')

# 🔹 ADMINISTRADOR (Apenas para "master")
@routes.route('/admin')
@login_obrigatorio
@somente_master
def admin():
    return render_template('admin.html')

# 🔹 CADASTRO DE USUÁRIO
@routes.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    mysql = get_mysql()
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        perfil = request.form['perfil']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        usuario_existente = cur.fetchone()

        if usuario_existente:
            flash('Email já cadastrado!', 'danger')
        else:
            senha_hash = generate_password_hash(senha)
            cur.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s, %s, %s, %s)", 
                        (nome, email, senha_hash, perfil))
            mysql.connection.commit()
            flash('Cadastro realizado com sucesso!', 'success')
        cur.close()
        return redirect(url_for('routes.login'))

    return render_template('cadastro.html')

# 🔹 Conexão com SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 🔹 CRUD de Professores (SQLite)
# 🔹 LISTAR PROFESSORES
@routes.route('/professores')
def listar_professores():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM professores")
    professores = cur.fetchall()
    cur.close()
    return render_template('professores/listar_professores.html', professores=professores)

# 🔹 CADASTRAR PROFESSOR
@routes.route('/cadastrar_professor', methods=['GET', 'POST'])
def cadastrar_professor():
    mysql = get_mysql()

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        cpf = re.sub(r'\D', '', cpf)
        cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        especialidade = request.form['especialidade']
        observacao = request.form['observacao']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Verifica se o CPF já existe
        cur.execute("SELECT id FROM professores WHERE cpf = %s", (cpf,))
        professor_existente = cur.fetchone()

        if professor_existente:
            flash("❗ Já existe um professor com este CPF!", "danger")
        else:
            cur.execute('''
                INSERT INTO professores (nome, cpf, endereco, telefone, email, especialidade, observacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (nome, cpf, endereco, telefone, email, especialidade, observacao))

            mysql.connection.commit()
            flash("✅ Professor cadastrado com sucesso!", "success")

        cur.close()
        return redirect(url_for('routes.listar_professores'))

    return render_template('professores/cadastrar_professor.html')

# 🔹 EDITAR PROFESSOR
@routes.route('/editar_professor/<int:id>', methods=['GET', 'POST'])
def editar_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        dados = (
            request.form['nome'],
            request.form['cpf'],
            request.form['endereco'],
            request.form['telefone'],
            request.form['email'],
            request.form['especialidade'],
            request.form['observacao'],
            id
        )

        cur.execute('''
            UPDATE professores 
            SET nome = %s, cpf = %s, endereco = %s, telefone = %s, email = %s, especialidade = %s, observacao = %s
            WHERE id = %s
        ''', dados)
        mysql.connection.commit()
        cur.close()
        flash("Professor atualizado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    cur.execute("SELECT * FROM professores WHERE id = %s", (id,))
    professor = cur.fetchone()
    cur.close()

    if not professor:
        flash("Professor não encontrado!", "danger")
        return redirect(url_for('routes.listar_professores'))

    return render_template('professores/editar_professor.html', professor=professor)

# 🔹 EXCLUIR PROFESSOR
@routes.route('/excluir_professor/<int:id>', methods=['POST'])
def excluir_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM professores WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Professor excluído com sucesso!", "success")
    return redirect(url_for('routes.listar_professores'))


# 🔹 CRUD Alunos (MySQL)
@routes.route('/alunos')
def listar_alunos():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT a.*, s.nome AS sala_nome
        FROM alunos a
        LEFT JOIN salas s ON a.sala_id = s.id
    """)
    alunos = cur.fetchall()
    cur.close()
    return render_template('alunos/listar_alunos.html', alunos=alunos)


@routes.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        data_nascimento = request.form['data_nascimento']
        sala_id = request.form.get('sala_id') or None

        # 🔸 Formatar CPF (opcional, para garantir padrão)
        cpf = cpf.strip().replace("-", "").replace(".", "")
        cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        # 🔸 Verifica duplicidade de CPF (bloqueia)
        cur.execute("SELECT id FROM alunos WHERE cpf = %s", (cpf,))
        aluno_existente = cur.fetchone()
        if aluno_existente:
            flash("⚠️ Já existe um aluno com este CPF!", "danger")
            cur.close()
            return redirect(url_for('routes.cadastrar_aluno'))

        # 🔸 Verifica duplicidade de nome (somente alerta)
        cur.execute("SELECT id FROM alunos WHERE nome = %s", (nome,))
        nome_duplicado = cur.fetchone()
        if nome_duplicado:
            flash("ℹ️ Atenção: já existe um aluno com este nome!", "warning")

        # 🔸 Cadastrar aluno
        cur.execute("""
            INSERT INTO alunos (nome, cpf, endereco, telefone, email, data_nascimento, sala_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, cpf, endereco, telefone, email, data_nascimento, sala_id))
        mysql.connection.commit()
        cur.close()

        flash("✅ Aluno cadastrado com sucesso!", "success")
        return redirect(url_for('routes.listar_alunos'))

    cur.close()
    return render_template('alunos/cadastrar_aluno.html', salas=salas)



@routes.route('/editar_aluno/<int:id>', methods=['GET', 'POST'])
def editar_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM alunos WHERE id = %s", (id,))
    aluno = cur.fetchone()

    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        data_nascimento = request.form.get('data_nascimento')
        sala_id = request.form.get('sala_id') or None

        cur.execute("""
            UPDATE alunos 
            SET nome=%s, endereco=%s, telefone=%s, email=%s, data_nascimento=%s, sala_id=%s
            WHERE id=%s
        """, (nome, endereco, telefone, email, data_nascimento, sala_id, id))

        mysql.connection.commit()
        flash("Aluno atualizado com sucesso!", "success")
        cur.close()
        return redirect(url_for('routes.listar_alunos'))

    cur.close()
    return render_template('alunos/editar_aluno.html', aluno=aluno, salas=salas)


@routes.route('/excluir_aluno/<int:id>', methods=['POST'])
def excluir_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alunos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Aluno excluído com sucesso!', 'success')
    return redirect(url_for('routes.listar_alunos'))

@app.template_filter('date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

# 🔹 CRUD Usuários (MySQL)
@routes.route('/usuarios')
@login_obrigatorio
@somente_master
def gerenciar_usuarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('usuarios.html', usuarios=usuarios)

@routes.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def cadastrar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        perfil = request.form['perfil']

        senha_hash = generate_password_hash(senha)

        mysql = get_mysql()
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s, %s, %s, %s)",
                    (nome, email, senha_hash, perfil))
        mysql.connection.commit()
        cur.close()

        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_usuarios'))

    return render_template('cadastrar_usuario.html')

@routes.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def editar_usuario(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        perfil = request.form['perfil']

        cur.execute("UPDATE usuarios SET nome=%s, email=%s, perfil=%s WHERE id=%s",
                    (nome, email, perfil, id))
        mysql.connection.commit()
        cur.close()

        flash("Usuário atualizado com sucesso!", "info")
        return redirect(url_for('routes.gerenciar_usuarios'))

    cur.execute("SELECT * FROM usuarios WHERE id = %s", (id,))
    usuario = cur.fetchone()
    cur.close()

    return render_template('cadastrar_usuario.html', usuario=usuario, editar=True)

@routes.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_obrigatorio
@somente_master
def excluir_usuario(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash("Usuário excluído!", "danger")
    return redirect(url_for('routes.gerenciar_usuarios'))


@routes.route('/horario/<int:turma_id>')
def visualizar_horario(turma_id):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT nome, ano FROM turmas WHERE id = %s", (turma_id,))
    turma = cursor.fetchone()

    cursor.execute("""
        SELECT dia_da_semana, aula_numero, materia
        FROM horarios
        WHERE turma_id = %s
        ORDER BY 
            FIELD(dia_da_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
            aula_numero
    """, (turma_id,))
    resultados = cursor.fetchall()
    cursor.close()

    horarios = {
        'Segunda': [''] * 6,
        'Terça': [''] * 6,
        'Quarta': [''] * 6,
        'Quinta': [''] * 6,
        'Sexta': [''] * 6
    }

    for dia, numero, materia in resultados:
        horarios[dia][numero - 1] = materia

    return render_template('horario_turma.html', turma=turma, horarios=horarios)


@routes.route('/turmas')
@login_obrigatorio
def listar_turmas():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('listar_salas.html', salas=salas)


@routes.route('/turmas/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
def cadastrar_turma():
    if request.method == 'POST':
        nome = request.form['nome']
        ano = request.form['ano']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO turmas (nome, ano) VALUES (%s, %s)", (nome, ano))
        mysql.connection.commit()
        cur.close()
        flash('Turma cadastrada com sucesso!', 'success')
        return redirect(url_for('routes.listar_turmas'))
    
    return render_template('turmas/cadastrar_turma.html')

@routes.route('/gerar_horarios')
def exibir_salas_para_geracao():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('gerar_horarios.html', salas=salas)


@routes.route('/gerar_horario/<int:sala_id>')
def gerar_horario(sala_id):
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    materias = ['Língua Portuguesa', 'Matemática', 'Ciências', 'Geografia',
                'Língua Inglesa', 'Arte', 'Educação Física', 'Filosofia']

    import random
    cur = mysql.connection.cursor()

    # Limpar horários anteriores da sala
    cur.execute("DELETE FROM horarios WHERE sala_id = %s", (sala_id,))
    for dia in dias_semana:
        aulas_do_dia = random.sample(materias, 6)  # 6 matérias por dia
        for i, materia in enumerate(aulas_do_dia, start=1):
            cur.execute(
                "INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia) VALUES (%s, %s, %s, %s)",
                (sala_id, dia, i, materia)
            )

    mysql.connection.commit()
    cur.close()

    flash('Horário gerado com sucesso!', 'success')
    return redirect(url_for('routes.exibir_salas_para_geracao'))


# 📥 Cadastrar sala
@routes.route('/salas/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
@somente_master
def cadastrar_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        ano = request.form['ano'].strip()
        capacidade = request.form['capacidade'].strip()

        # Verifica duplicidade
        cur.execute("SELECT * FROM salas WHERE nome = %s", (nome,))
        if cur.fetchone():
            flash('Já existe uma sala com esse nome!', 'danger')
            return redirect(url_for('routes.cadastrar_sala'))

        cur.execute("INSERT INTO salas (nome, ano, capacidade) VALUES (%s, %s, %s)", (nome, ano, capacidade))
        mysql.connection.commit()
        cur.close()
        flash("Sala cadastrada com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_salas'))

    # 🔹 Ano padrão atual
    ano_padrao = datetime.now().year
    return render_template('salas/cadastrar_sala.html', ano_padrao=ano_padrao)

@routes.route('/salas/<int:sala_id>/alunos')
@login_obrigatorio
def visualizar_alunos_da_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Busca nome da sala
    cur.execute("SELECT nome FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.gerenciar_salas'))

    # Busca alunos da sala
    cur.execute("SELECT * FROM alunos WHERE sala_id = %s", (sala_id,))
    alunos = cur.fetchall()
    cur.close()

    return render_template('salas/visualizar_alunos.html', sala=sala, alunos=alunos)



# 📋 Listar salas com quantidade de alunos
@routes.route('/salas')
@login_obrigatorio
def gerenciar_salas():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('salas/gerenciar_salas.html', salas=salas)



# ✏️ Editar sala
@routes.route('/salas/editar/<int:sala_id>', methods=['GET', 'POST'])
def editar_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome']
        ano = request.form['ano']
        capacidade = request.form['capacidade']

        cur.execute("UPDATE salas SET nome=%s, ano=%s, capacidade=%s WHERE id=%s", (nome, ano, capacidade, sala_id))
        mysql.connection.commit()
        flash("Sala atualizada com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_salas'))

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()
    return render_template('editar_sala.html', sala=sala)


# 🗑️ Excluir sala
@routes.route('/salas/excluir/<int:sala_id>', methods=['POST'])
def excluir_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM salas WHERE id = %s", (sala_id,))
    mysql.connection.commit()
    flash("Sala excluída!", "danger")
    return redirect(url_for('routes.gerenciar_salas'))