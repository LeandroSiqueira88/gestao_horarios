from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from extensoes import mysql  # ✅ aqui pegamos o mysql
from auth import login_obrigatorio, somente_master
import sqlite3


# 🔹 Criando o Blueprint
routes = Blueprint('routes', __name__)

# 🔹 Lista fixa de turmas disponíveis
TURMAS = ["1ºA", "1ºB", "1ºC", "2ºA", "2ºB", "2ºC", "3ºA", "3ºB", "3ºC"]

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
@routes.route('/professores')
def listar_professores():
    conn = get_db_connection()
    professores = conn.execute('SELECT * FROM professores').fetchall()
    conn.close()
    return render_template('professores.html', professores=professores)

@routes.route('/cadastrar_professor', methods=['GET', 'POST'])
def cadastrar_professor():
    if request.method == 'POST':
        dados = (
            request.form['nome'],
            request.form['cpf'],
            request.form['endereco'],
            request.form['telefone'],
            request.form['email'],
            request.form['especialidade'],
            request.form['observacao']
        )
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO professores (nome, cpf, endereco, telefone, email, especialidade, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', dados)
        conn.commit()
        conn.close()
        flash("Professor cadastrado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    return render_template('cadastrar_professor.html')

@routes.route('/editar_professor/<int:id>', methods=['GET', 'POST'])
def editar_professor(id):
    conn = get_db_connection()
    professor = conn.execute('SELECT * FROM professores WHERE id = ?', (id,)).fetchone()

    if not professor:
        flash("Professor não encontrado!", "danger")
        return redirect(url_for('routes.listar_professores'))

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
        conn.execute('''
            UPDATE professores 
            SET nome = ?, cpf = ?, endereco = ?, telefone = ?, email = ?, especialidade = ?, observacao = ?
            WHERE id = ?
        ''', dados)
        conn.commit()
        conn.close()
        flash("Professor atualizado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    return render_template('editar_professor.html', professor=professor)

@routes.route('/excluir_professor/<int:id>', methods=['POST'])
def excluir_professor(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM professores WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Professor excluído com sucesso!", "success")
    return redirect(url_for('routes.listar_professores'))

# 🔹 CRUD Alunos (MySQL)
@routes.route('/alunos')
def listar_alunos():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM alunos")
    alunos = cur.fetchall()
    cur.close()
    return render_template('alunos.html', alunos=alunos)

@routes.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    mysql = get_mysql()
    if request.method == 'POST':
        dados = {
            'nome': request.form['nome'].strip(),
            'cpf': request.form['cpf'].strip(),
            'endereco': request.form['endereco'].strip(),
            'telefone': request.form['telefone'].strip(),
            'email': request.form['email'].strip(),
            'data_nascimento': request.form['data_nascimento'].strip(),
            'turma': request.form['turma']
        }

        if not all(dados.values()):
            flash('Todos os campos são obrigatórios!', 'danger')
            return redirect(url_for('routes.cadastrar_aluno'))

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id FROM alunos WHERE cpf = %s OR email = %s", (dados['cpf'], dados['email']))
        if cur.fetchone():
            flash('Aluno já cadastrado com este CPF ou e-mail!', 'danger')
        else:
            cur.execute("""
                INSERT INTO alunos (nome, cpf, endereco, telefone, email, data_nascimento, turma) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, tuple(dados.values()))
            mysql.connection.commit()
            flash('Aluno cadastrado com sucesso!', 'success')

        cur.close()
        return redirect(url_for('routes.listar_alunos'))

    return render_template('cadastrar_aluno.html', turmas=TURMAS)

@routes.route('/editar_aluno/<int:id>', methods=['GET', 'POST'])
def editar_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        dados = (
            request.form['nome'],
            request.form['endereco'],
            request.form['telefone'],
            request.form['email'],
            request.form.get('data_nascimento', ''),
            request.form['turma'],
            id
        )
        cur.execute("""
            UPDATE alunos 
            SET nome=%s, endereco=%s, telefone=%s, email=%s, data_nascimento=%s, turma=%s 
            WHERE id=%s
        """, dados)
        mysql.connection.commit()
        flash('Dados do aluno atualizados com sucesso!', 'success')
        return redirect(url_for('routes.listar_alunos'))

    cur.execute("SELECT * FROM alunos WHERE id = %s", (id,))
    aluno = cur.fetchone()
    cur.close()

    if not aluno:
        flash('Aluno não encontrado!', 'danger')
        return redirect(url_for('routes.listar_alunos'))

    return render_template('editar_aluno.html', aluno=aluno, turmas=TURMAS)

@routes.route('/excluir_aluno/<int:id>', methods=['POST'])
def excluir_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alunos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Aluno excluído com sucesso!', 'success')
    return redirect(url_for('routes.listar_alunos'))

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
