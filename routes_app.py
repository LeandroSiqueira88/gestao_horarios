import re
import io
import json
import sqlite3
from datetime import datetime
from collections import defaultdict
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, make_response, Response
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
from xhtml2pdf import pisa
from extensoes import mysql
from auth import login_obrigatorio, somente_master, perfil_autorizado


app = Flask(__name__)
# 🔹 Criando o Blueprint
routes = Blueprint('routes', __name__)

# 🔹 Lista fixa de turmas disponíveis
TURMAS = ["1ºA", "1ºB", "1ºC", "2ºA", "2ºB", "2ºC", "3ºA", "3ºB", "3ºC"]

dias_da_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

# 🔹 Função para obter a conexão MySQL
def get_mysql():
    from app import mysql
    return mysql

@app.template_filter('date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

def limpar_html(texto):
    return re.sub(r'<[^>]*>', '', texto or "")



# =======================================
# 🔹 DASHBOARD & ADMIN
# =======================================

# 🔹 ROTA PRINCIPAL – Escolha entre Master e Usuário
@routes.route('/')
def index():
    if session.get('usuario_id'):
        return redirect(url_for('routes.dashboard'))
    return render_template('index.html')

@routes.route('/master', methods=['GET', 'POST'])
def acesso_master():
    return render_template('usuarios/login_master.html')


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

            if usuario[4] == 'master':
                return redirect(url_for('routes.admin'))
            else:
                return redirect(url_for('routes.dashboard'))
        else:
            flash("E-mail ou senha inválidos", "danger")

    return render_template('usuarios/login_publico.html')

# 🔹 LOGOUT
@routes.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('routes.login'))

# 🔹 DASHBOARD
@routes.route('/dashboard')
@login_obrigatorio
def dashboard():
    print("Perfil logado:", session.get('usuario_perfil'))
    return render_template('dashboard.html')


# 🔹 ADMINISTRADOR (Apenas para "master")
@routes.route('/admin')
@login_obrigatorio
@somente_master
def admin():
    return render_template('admin.html')


# =======================================
# 🔹 CRUD USUÁRIOS
# =======================================


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


# 🔹 CRUD Usuários - Cadastrar
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

    return render_template('usuarios/cadastrar_usuario.html')


# 🔹 CRUD Usuários - Listar
@routes.route('/usuarios')
@login_obrigatorio
@somente_master
def gerenciar_usuarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('usuarios/gerenciar_usuarios.html', usuarios=usuarios)


# 🔹 CRUD Usuários - Editar
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

    return render_template('usuarios/cadastrar_usuario.html', usuario=usuario, editar=True)


# 🔹 CRUD Usuários - Excluir
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


# =======================================
# 🔹 CRUD PROFESSORES
# =======================================

# 🔹 CRUD Professores - Listar
@routes.route('/professores')
def listar_professores():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM professores")
    professores = cur.fetchall()
    cur.close()
    return render_template('professores/listar_professores.html', professores=professores)





# 🔹 CRUD Professores - Cadastrar
@routes.route('/cadastrar_professor', methods=['GET', 'POST'])
@login_obrigatorio
def cadastrar_professor():
    if session.get('usuario_perfil') not in ['master', 'administrativo']:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        especialidade = request.form['especialidade']
        observacao = request.form['observacao']

       
        import re
        def formatar_cpf(cpf):
            numeros = re.sub(r'\D', '', cpf)
            return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
        cpf = formatar_cpf(cpf)

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Verificar se nome já existe (apenas alerta, não bloqueia)
        cur.execute("SELECT id FROM professores WHERE nome = %s", (nome,))
        professor_com_nome_igual = cur.fetchone()
        if professor_com_nome_igual:
            flash("⚠️ Já existe um professor com este nome!", "warning")

        # Verificar se CPF já existe (impede)
        cur.execute("SELECT id FROM professores WHERE cpf = %s", (cpf,))
        professor_existente = cur.fetchone()
        if professor_existente:
            flash("❗ Já existe um professor com este CPF!", "danger")
            cur.close()
            return redirect(url_for('routes.cadastrar_professor'))

        # Inserir novo professor
        cur.execute('''
            INSERT INTO professores (nome, cpf, endereco, telefone, email, especialidade, observacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nome, cpf, endereco, telefone, email, especialidade, observacao))

        mysql.connection.commit()
        cur.close()
        flash("✅ Professor cadastrado com sucesso!", "success")
        return redirect(url_for('routes.listar_professores'))

    return render_template('professores/cadastrar_professor.html')


# 🔹 CRUD Professores - Editar
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


# 🔹 CRUD Professores - Excluir
@routes.route('/excluir_professor/<int:id>', methods=['POST'])
def excluir_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM professores WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Professor excluído com sucesso!", "success")
    return redirect(url_for('routes.listar_professores'))

@routes.route('/professor/<int:id>/aulas')
@login_obrigatorio
def ver_aulas_professor(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar o professor
    cur.execute("SELECT * FROM professores WHERE id = %s", (id,))
    professor = cur.fetchone()

    if not professor:
        flash("Professor não encontrado!", "danger")
        return redirect(url_for('routes.listar_professores'))

    # Buscar as aulas cadastradas do professor
    cur.execute("""
        SELECT dia_semana, aula_numero, materia, s.nome AS sala_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        WHERE h.professor_id = %s
        ORDER BY FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'), aula_numero
    """, (id,))
    aulas = cur.fetchall()
    cur.close()

    return render_template('professores/aulas_professor.html', professor=professor, aulas=aulas)


# =======================================
# 🔹 CRUD ALUNOS
# =======================================


# 🔹 CRUD Alunos - Listar
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

# 🔹 CRUD Alunos - Cadastrar
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


# 🔹 CRUD Alunos - Editar
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

# 🔹 CRUD Alunos - Excluir
@routes.route('/excluir_aluno/<int:id>', methods=['POST'])
def excluir_aluno(id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alunos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Aluno excluído com sucesso!', 'success')
    return redirect(url_for('routes.listar_alunos'))



# =======================================
# 🔹 CRUD SALAS
# =======================================


# 🔹 CRUD Salas - Listar/gerenciar salas
@routes.route('/salas')
@login_obrigatorio
def gerenciar_salas():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT s.*, COUNT(a.id) AS qtd_alunos
        FROM salas s
        LEFT JOIN alunos a ON a.sala_id = s.id
        GROUP BY s.id
    """)

    salas = cur.fetchall()
    cur.close()
    return render_template('salas/gerenciar_salas.html', salas=salas)



# 🔹 CRUD Salas - Cadastrar
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


# 🔹 CRUD Salas - Editar
@routes.route('/salas/editar/<int:sala_id>', methods=['GET', 'POST'])
@login_obrigatorio
def editar_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form['nome']
        ano = request.form['ano']
        capacidade = request.form['capacidade']

        cur.execute("""
            UPDATE salas SET nome=%s, ano=%s, capacidade=%s WHERE id=%s
        """, (nome, ano, capacidade, sala_id))
        mysql.connection.commit()
        cur.close()
        flash("Sala atualizada com sucesso!", "success")
        return redirect(url_for('routes.gerenciar_salas'))

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()
    cur.close()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.gerenciar_salas'))

    return render_template('salas/editar_sala.html', sala=sala)


# 🔹 CRUD Salas - Excluir
@routes.route('/salas/excluir/<int:sala_id>', methods=['POST'])
def excluir_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM salas WHERE id = %s", (sala_id,))
    mysql.connection.commit()
    flash("Sala excluída!", "danger")
    return redirect(url_for('routes.gerenciar_salas'))

# 🔹 CRUD Horários - Editar grade da sala
@routes.route('/horario/sala/<int:sala_id>/editar')
@login_obrigatorio
@somente_master
def editar_grade_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Dados da sala
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    # Lista de professores e matérias
    cur.execute("SELECT id, nome, especialidade FROM professores")
    professores = cur.fetchall()

    # Grade de horário atual
    cur.execute("""
        SELECT h.*, p.nome AS professor_nome
        FROM horarios h
        LEFT JOIN professores p ON h.professor_id = p.id
        WHERE h.sala_id = %s
        ORDER BY
            FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
            h.aula_numero
    """, (sala_id,))
    horarios = cur.fetchall()

    cur.close()
    return render_template('horarios/editar_grade.html', sala=sala, horarios=horarios, professores=professores)


# 🔹 CRUD Salas - Visualizar alunos da sala
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

    # Formata data de nascimento (YYYY-MM-DD → DD/MM/YYYY)
    for aluno in alunos:
        data_str = aluno.get("data_nascimento")
        if data_str:
            try:
                data_formatada = datetime.strptime(str(data_str), "%Y-%m-%d").strftime("%d/%m/%Y")
                aluno["data_nascimento"] = data_formatada
            except:
                aluno["data_nascimento"] = data_str  # fallback

    cur.close()
    return render_template('salas/visualizar_alunos.html', sala=sala, alunos=alunos)


# =======================================
# 🔹 CRUD TURMAS
# =======================================

# 🔹 CRUD Turmas - Listar
@routes.route('/turmas')
@login_obrigatorio
def listar_turmas():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('horarios/listar_turmas.html', salas=salas)

# 🔹 CRUD Turmas - Cadastrar
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


# =======================================
# 🔹 CRUD HORÁRIOS
# =======================================


# 🔹 CRUD Horários - Visualizar horário da sala
@routes.route('/horario/<int:sala_id>')
@login_obrigatorio
def visualizar_horario_sala(sala_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    if not sala:
        flash("Sala não encontrada!", "danger")
        return redirect(url_for('routes.listar_turmas'))

    cur.execute("""
    SELECT h.dia_semana, h.aula_numero, h.materia, p.nome AS professor
    FROM horarios h
    LEFT JOIN professores p ON h.professor_id = p.id
    WHERE h.sala_id = %s
    ORDER BY 
        FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
        h.aula_numero
""", (sala_id,))

    resultados = cur.fetchall()
    cur.close()

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    linhas = ['1ª Aula', '2ª Aula', '3ª Aula', '🧃 Intervalo', '4ª Aula', '5ª Aula', '6ª Aula']
    grade = {linha: {dia: '' for dia in dias} for linha in linhas}

    for linha in resultados:
        dia = linha['dia_semana']
        aula = linha['aula_numero']
        materia = linha['materia']
        professor = linha.get('professor', '')
        linha_key = f'{aula}ª Aula'
        grade[linha_key][dia] = f"{materia}<br><small>{professor or '---'}</small>"

    for dia in dias:
        grade['🧃 Intervalo'][dia] = '🧃🍞 Intervalo'

    return render_template('horarios/horario_sala.html', sala=sala, grade=grade, dias=dias)



# 🔹 CRUD Horários - Gerar horários para todas as salas
@routes.route('/gerar_horarios')
@login_obrigatorio
@somente_master
def exibir_salas_para_geracao():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()
    cur.close()
    return render_template('horarios/gerar_horarios.html', salas=salas)


# 🔹 CRUD Horários - Editar grade (geral)
@routes.route('/editar_grade/<int:sala_id>', methods=['GET', 'POST'])
@login_obrigatorio
def editar_grade(sala_id):
    if session.get('usuario_perfil') not in ['master', 'administrativo']:
        flash('Apenas usuários com permissões podem editar a grade.', 'danger')
        return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    aulas = list(range(1, 7))

    if request.method == 'POST':
        conflitos = []

        for dia in dias:
            for aula in aulas:
                especialidade = request.form.get(f'{dia}_{aula}_especialidade')
                professor_nome = request.form.get(f'{dia}_{aula}_professor')

                if not especialidade or not professor_nome:
                    continue

                # Buscar professor_id
                cur.execute("SELECT id FROM professores WHERE nome = %s AND especialidade = %s", (professor_nome, especialidade))
                prof_row = cur.fetchone()
                if not prof_row:
                    continue

                professor_id = prof_row['id']

                # Verifica se o professor já está ocupado nesse horário em outra sala
                cur.execute("""
                    SELECT id FROM horarios 
                    WHERE professor_id = %s AND dia_semana = %s AND aula_numero = %s AND sala_id != %s
                """, (professor_id, dia, aula, sala_id))
                conflito = cur.fetchone()
                if conflito:
                    conflitos.append(f"⚠️ {professor_nome} já tem aula na {aula}ª aula de {dia}.")
                    continue

                # Verifica se já existe uma entrada para este slot
                cur.execute("""
                    SELECT id FROM horarios 
                    WHERE sala_id = %s AND dia_semana = %s AND aula_numero = %s
                """, (sala_id, dia, aula))
                existente = cur.fetchone()

                if existente:
                    cur.execute("""
                        UPDATE horarios SET materia = %s, professor_id = %s 
                        WHERE id = %s
                    """, (especialidade, professor_id, existente['id']))
                else:
                    cur.execute("""
                        INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sala_id, dia, aula, especialidade, professor_id))

        mysql.connection.commit()
        cur.close()

        if conflitos:
            flash("⚠️ Algumas alterações não foram salvas devido a conflitos:", "warning")
            for c in conflitos:
                flash(c, "warning")
        else:
            flash("✅ Grade atualizada com sucesso!", "success")

        return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    # Parte GET
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    cur.execute("""
        SELECT h.*, p.nome AS professor, p.especialidade 
        FROM horarios h
        LEFT JOIN professores p ON h.professor_id = p.id
        WHERE h.sala_id = %s
    """, (sala_id,))
    horarios_raw = cur.fetchall()

    # Organizar grade existente
    horario = {dia: {str(i): {'especialidade': '', 'professor': ''} for i in aulas} for dia in dias}
    for h in horarios_raw:
        dia = h['dia_semana']
        aula = str(h['aula_numero'])
        horario[dia][aula] = {
            'especialidade': h['materia'],
            'professor': h['professor'] or ''
        }

    # Professores para JS (agrupados por especialidade)
    cur.execute("SELECT nome, especialidade FROM professores ORDER BY especialidade, nome")
    professores = cur.fetchall()
    cur.close()

    from collections import defaultdict
    prof_dict = defaultdict(list)
    for prof in professores:
        prof_dict[prof['especialidade']].append(prof['nome'])

    import json
    professores_json = json.dumps(prof_dict, ensure_ascii=False)
    especialidades = sorted(prof_dict.keys())

    return render_template(
        'horarios/editar_grade.html',
        sala=sala,
        horario=horario,
        professores=professores,
        professores_json=professores_json,
        especialidades=especialidades
    )

# 🔹 CRUD Horários - Editar aula individual
@routes.route('/editar_aula/<int:sala_id>')
@login_obrigatorio
def selecionar_aula_para_edicao(sala_id):
    if session.get('usuario_perfil') not in ['master', 'administrativo']:
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    cur.execute("""
        SELECT h.*, p.nome AS professor_nome
        FROM horarios h
        LEFT JOIN professores p ON h.professor_id = p.id
        WHERE h.sala_id = %s
    """, (sala_id,))
    horarios = cur.fetchall()
    cur.close()

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    return render_template('horarios/selecionar_aula.html', sala=sala, horarios=horarios, dias=dias)

# 🔹 CRUD Horários - Editar aula específica
@routes.route('/editar_aula/<int:sala_id>/<dia>/<int:aula>', methods=['GET', 'POST'])
@login_obrigatorio
def editar_aula(sala_id, dia, aula):
    if session.get('usuario_perfil') not in ['master', 'administrativo']:
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        materia = request.form.get("materia")
        professor_id = request.form.get("professor_id")

        # Verifica conflito com outro horário
        cur.execute("""
            SELECT * FROM horarios
            WHERE professor_id = %s AND dia_semana = %s AND aula_numero = %s AND sala_id != %s
        """, (professor_id, dia, aula, sala_id))
        conflito = cur.fetchone()

        if conflito:
            flash("❌ Esse professor já tem aula nesse horário em outra sala.", "danger")
        else:
            cur.execute("""
                DELETE FROM horarios 
                WHERE sala_id = %s AND dia_semana = %s AND aula_numero = %s
            """, (sala_id, dia, aula))

            cur.execute("""
                INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (sala_id, dia, aula, materia, professor_id))
            mysql.connection.commit()
            flash("✅ Aula atualizada com sucesso!", "success")
            return redirect(url_for('routes.visualizar_horario_sala', sala_id=sala_id))

    # Parte GET: buscar dados atuais
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()

    cur.execute("""
        SELECT * FROM horarios WHERE sala_id = %s AND dia_semana = %s AND aula_numero = %s
    """, (sala_id, dia, aula))
    aula_atual = cur.fetchone()

    cur.execute("SELECT id, nome, especialidade FROM professores ORDER BY especialidade, nome")
    professores = cur.fetchall()
    cur.close()

    return render_template('horarios/editar_aula.html',
                           sala=sala, dia=dia, aula_numero=aula,
                           aula_atual=aula_atual, professores=professores)




# 🔹 CRUD Horários horarios - professor
@routes.route('/horarios/professor/<int:professor_id>')
@login_obrigatorio
def visualizar_horario_professor(professor_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar professor
    cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
    professor = cur.fetchone()

    if not professor:
        flash("Professor não encontrado!", "danger")
        cur.close()
        return redirect(url_for('routes.listar_professores_horarios'))

    # Buscar aulas do professor
    cur.execute("""
        SELECT h.dia_semana, h.aula_numero, h.materia, s.nome AS sala_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        WHERE h.professor_id = %s
        ORDER BY FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'), h.aula_numero
    """, (professor_id,))
    resultados = cur.fetchall()
    cur.close()

    # Preparar a grade
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    linhas = ['1ª Aula', '2ª Aula', '3ª Aula', '🧃 Intervalo', '4ª Aula', '5ª Aula', '6ª Aula']
    grade = {dia: {linha: '' for linha in linhas} for dia in dias}

    for row in resultados:
        aula = row['aula_numero']
        dia = row['dia_semana']
        texto = f"{row['materia']}<br><small>{row['sala_nome']}</small>"
        linha = f"{aula}ª Aula"

        if linha in grade[dia]:  # Só adiciona se a linha existir
            grade[dia][linha] = texto

    for dia in dias:
        grade[dia]['🧃 Intervalo'] = '🧃🍞 Intervalo'

    total_aulas = len(resultados)

    return render_template(
    'horarios/horario_professor.html',
    professor=professor,
    horario=grade,
    dias=dias,
    linhas=linhas,
    carga_horaria=len(resultados)
)




# =======================================
# 🔹 EXPORTAÇÕES PDF
# =======================================


# 🔹 Exportações - Alunos por Sala (PDF)
@routes.route('/exportar/alunos_por_sala')
@login_obrigatorio
def exportar_alunos_por_sala():
    import io
    from flask import make_response
    from fpdf import FPDF

    sala_id = request.args.get('sala_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if sala_id:
        cur.execute("""
            SELECT a.nome AS aluno, s.nome AS sala
            FROM alunos a
            JOIN salas s ON a.sala_id = s.id
            WHERE s.id = %s
            ORDER BY a.nome
        """, (sala_id,))
    else:
        cur.execute("""
            SELECT a.nome AS aluno, s.nome AS sala
            FROM alunos a
            LEFT JOIN salas s ON a.sala_id = s.id
            ORDER BY s.nome, a.nome
        """)

    dados = cur.fetchall()
    cur.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4')  # Modo Paisagem
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    if not dados:
        pdf.add_page()
        pdf.cell(0, 10, txt="Nenhum aluno encontrado.", ln=True, align='C')
    else:
        sala_atual = None
        contador_aluno = 1
        alunos_na_pagina = 0

        x_positions = [10, 80, 150, 220]
        largura_coluna = 65

        for row in dados:
            sala_nome = row['sala'] if row['sala'] else "Sala Não Definida"

            if sala_nome != sala_atual:
                pdf.add_page()

                # Marca d'água
                pdf_width = 297  
                pdf_height = 210  
                logo_width = 120
                logo_height = 80
                x_logo = (pdf_width - logo_width) / 2
                y_logo = (pdf_height - logo_height) / 2
                pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)

                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"Alunos da Sala: {sala_nome}", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", size=12)

                sala_atual = sala_nome
                contador_aluno = 1
                alunos_na_pagina = 0

            coluna_atual = alunos_na_pagina // 15
            linha_na_coluna = alunos_na_pagina % 15

            if coluna_atual > 3:
                pdf.add_page()                
                pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"Alunos da Sala: {sala_nome}", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", size=12)

                alunos_na_pagina = 0
                coluna_atual = 0
                linha_na_coluna = 0

            x = x_positions[coluna_atual]
            y = 40 + (linha_na_coluna * 10)

            pdf.set_xy(x, y)
            texto_aluno = f"{contador_aluno}. {row['aluno']}"
            pdf.cell(largura_coluna, 10, txt=texto_aluno, ln=0)

            contador_aluno += 1
            alunos_na_pagina += 1

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_content = pdf_buffer.getvalue()

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=alunos_por_sala.pdf'
    return response


# 🔹 Exportações - Alunos por Sala (HTML)
@routes.route('/exportar/alunos_por_sala_html')
@login_obrigatorio
def exibir_exportar_alunos_por_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM salas ORDER BY nome")
    salas = cur.fetchall()
    cur.close()
    return render_template('exportar/alunos_por_sala.html', salas=salas)


# 🔹 Exportações - Grade de Salas (PDF)
@routes.route('/exportar_grade_salas')
@login_obrigatorio
def exportar_grade_salas():
    import io
    from fpdf import FPDF
    from collections import defaultdict
    from flask import make_response

    sala_id = request.args.get('sala_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if sala_id:
        cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    else:
        cur.execute("SELECT * FROM salas ORDER BY nome")
    salas = cur.fetchall()

    consulta_horarios = """
        SELECT h.*, s.nome AS sala_nome, p.nome AS professor_nome
        FROM horarios h
        JOIN salas s ON h.sala_id = s.id
        LEFT JOIN professores p ON h.professor_id = p.id
        {}
        ORDER BY s.nome,
                 FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                 h.aula_numero
    """.format(f"WHERE s.id = {sala_id}" if sala_id else "")
    cur.execute(consulta_horarios)
    horarios = cur.fetchall()
    cur.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

    aulas_por_sala = defaultdict(lambda: {dia: [''] * 6 for dia in dias})
    for h in horarios:
        texto = f"{h['materia']}\n({h['professor_nome'] or 'Sem prof'})"
        aulas_por_sala[h['sala_nome']][h['dia_semana']][h['aula_numero'] - 1] = texto

    if not salas:
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, txt="Nenhuma sala encontrada.", ln=True)
    else:
        for sala in salas:
            pdf.add_page()

            # Marca d'água
            pdf_width = 297
            pdf_height = 210
            logo_width = 120
            logo_height = 80
            x_logo = (pdf_width - logo_width) / 2
            y_logo = (pdf_height - logo_height) / 2
            pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)

            nome = sala['nome']

            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"Sala: {nome}", ln=True, align='C')
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 10, "Dia", border=1, align='C')
            for i in range(1, 7):
                pdf.cell(40, 10, f"{i}ª Aula", border=1, align='C')
            pdf.ln()

            pdf.set_font("Arial", size=8)
            for dia in dias:
                y_inicial = pdf.get_y()
                pdf.cell(30, 20, dia, border=1, align='C')

                for aula in aulas_por_sala[nome][dia]:
                    if not aula:
                        aula = "-- Livre --"
                    elif len(aula) > 60:
                        aula = aula[:57] + "..."

                    x = pdf.get_x()
                    y = pdf.get_y()

                    pdf.multi_cell(40, 10, aula, border=1, align='C')
                    pdf.set_xy(x + 40, y)

                pdf.set_y(y_inicial + 20)
            pdf.ln(8)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_content = pdf_buffer.getvalue()

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=grade_salas.pdf'
    return response


# 🔹 Exportações - Grade por Sala (HTML)
@routes.route('/exportar/grade_por_sala_html')
@login_obrigatorio
def exibir_exportar_grade_por_sala():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar todas as salas
    cur.execute("SELECT id, nome FROM salas ORDER BY nome")
    salas = cur.fetchall()

    sala_id = request.args.get("sala_id")
    horario = {}
    sala_selecionada = None

    if sala_id:
        # Sala selecionada
        cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
        sala_selecionada = cur.fetchone()

        cur.execute("""
            SELECT * FROM horarios 
            WHERE sala_id = %s 
            ORDER BY 
                FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                aula_numero
        """, (sala_id,))
        dados = cur.fetchall()

        # Estrutura do horário
        horario = {
            'Segunda': [''] * 6,
            'Terça': [''] * 6,
            'Quarta': [''] * 6,
            'Quinta': [''] * 6,
            'Sexta': [''] * 6
        }

        for h in dados:
            texto = f"{h['materia']}<br><small>{h['professor']}</small>"
            horario[h['dia_semana']][h['aula_numero'] - 1] = texto

    cur.close()
    return render_template("exportar/grade_por_sala.html", salas=salas, sala_selecionada=sala_selecionada, horario=horario)

# 🔹 Exportações - Grade de Professores (PDF)
@routes.route('/exportar_grade_professores')
@login_obrigatorio
def exportar_grade_professores():
    import io
    from fpdf import FPDF
    from collections import defaultdict
    from flask import make_response

    professor_id = request.args.get('professor_id')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if professor_id:
        cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
    else:
        cur.execute("SELECT * FROM professores ORDER BY nome")
    professores = cur.fetchall()

    if professor_id:
        cur.execute("""
            SELECT h.*, s.nome AS sala_nome
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            WHERE h.professor_id = %s
            ORDER BY h.dia_semana, h.aula_numero
        """, (professor_id,))
    else:
        cur.execute("""
            SELECT h.*, s.nome AS sala_nome, p.nome AS professor_nome
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            JOIN professores p ON h.professor_id = p.id
            ORDER BY p.nome, h.dia_semana, h.aula_numero
        """)
    horarios = cur.fetchall()
    cur.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']

    horario_por_prof = defaultdict(lambda: {dia: [''] * 6 for dia in dias})
    for h in horarios:
        prof = h.get('professor_nome') or professores[0]['nome']
        texto = f"{h['materia']}\n({h['sala_nome']})"
        horario_por_prof[prof][h['dia_semana']][h['aula_numero'] - 1] = texto

    if not professores:
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, txt="Nenhum professor encontrado.", ln=True)
    else:
        for prof in professores:
            pdf.add_page()

            # Marca d'água
            pdf_width = 297
            pdf_height = 210
            logo_width = 120
            logo_height = 80
            x_logo = (pdf_width - logo_width) / 2
            y_logo = (pdf_height - logo_height) / 2
            pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)

            nome = prof['nome']

            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"Professor: {nome}", ln=True, align='C')
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 10, "Dia", border=1, align='C')
            for i in range(1, 7):
                pdf.cell(40, 10, f"{i}ª Aula", border=1, align='C')
            pdf.ln()

            pdf.set_font("Arial", size=8)
            for dia in dias:
                y_inicial = pdf.get_y()
                pdf.cell(30, 20, dia, border=1, align='C')

                for aula in horario_por_prof[nome][dia]:
                    if not aula:
                        aula = "-- Livre --"
                    elif len(aula) > 60:
                        aula = aula[:57] + "..."

                    x = pdf.get_x()
                    y = pdf.get_y()

                    pdf.multi_cell(40, 10, aula, border=1, align='C')
                    pdf.set_xy(x + 40, y)

                pdf.set_y(y_inicial + 20)
            pdf.ln(8)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_content = pdf_buffer.getvalue()

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=grade_professores.pdf'
    return response



# 🔹 Exportações - Grade por Professor (HTML)
@routes.route('/exportar/grade_por_professor_html')
@login_obrigatorio
def exibir_exportar_grade_por_professor():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT id, nome FROM professores ORDER BY nome")
    professores = cur.fetchall()

    professor_id = request.args.get("professor_id")
    horario = {}
    professor = None

    if professor_id:
        # Buscar professor
        cur.execute("SELECT * FROM professores WHERE id = %s", (professor_id,))
        professor = cur.fetchone()

        cur.execute("""
            SELECT h.*, s.nome AS sala_nome 
            FROM horarios h
            JOIN salas s ON h.sala_id = s.id
            WHERE h.professor_id = %s
            ORDER BY 
                FIELD(h.dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'),
                h.aula_numero
        """, (professor_id,))
        dados = cur.fetchall()

        # Estrutura do horário
        horario = {
            'Segunda': [''] * 6,
            'Terça': [''] * 6,
            'Quarta': [''] * 6,
            'Quinta': [''] * 6,
            'Sexta': [''] * 6
        }

        for h in dados:
            texto = f"{h['materia']}<br><small>{h['sala_nome']}</small>"
            horario[h['dia_semana']][h['aula_numero'] - 1] = texto

    cur.close()
    return render_template("exportar/grade_por_professor.html", professores=professores, professor=professor, horario=horario)


# 🔹 CRUD professores/horarios
@routes.route('/professores/horarios')
@login_obrigatorio
def listar_professores_horarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, nome, especialidade FROM professores ORDER BY nome")
    professores = cur.fetchall()
    cur.close()
    return render_template('horarios/professores_horarios.html', professores=professores)


# 🔹 Exportações - Usuários (PDF)
@routes.route('/exportar/usuarios')
@login_obrigatorio
@somente_master
def exportar_usuarios():
    import io
    from flask import make_response
    from fpdf import FPDF

    perfil_filtro = request.args.get('perfil')
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if perfil_filtro:
        cur.execute("""
            SELECT nome, email, perfil
            FROM usuarios
            WHERE perfil = %s
            ORDER BY nome
        """, (perfil_filtro,))
    else:
        cur.execute("""
            SELECT nome, email, perfil
            FROM usuarios
            ORDER BY nome
        """)

    usuarios = cur.fetchall()
    cur.close()

    pdf = FPDF(orientation='L', unit='mm', format='A4') 
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    if not usuarios:
        pdf.add_page()
        pdf.cell(0, 10, txt="Nenhum usuário encontrado.", ln=True, align='C')
    else:
        perfil_atual = perfil_filtro.capitalize() if perfil_filtro else "Todos os Perfis"
        contador_usuario = 1
        usuarios_na_pagina = 0

        x_positions = [10, 80, 150, 220] 
        largura_coluna = 65

        pdf.add_page()

       
        pdf_width = 297
        pdf_height = 210
        logo_width = 120
        logo_height = 80
        x_logo = (pdf_width - logo_width) / 2
        y_logo = (pdf_height - logo_height) / 2
        pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)

        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Lista de Usuários - {perfil_atual}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)

        for u in usuarios:
            coluna_atual = usuarios_na_pagina // 15
            linha_na_coluna = usuarios_na_pagina % 15

            if coluna_atual > 3:
                pdf.add_page()               
                pdf.image('static/img/logo.png', x=x_logo, y=y_logo, w=logo_width, h=logo_height)
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"Lista de Usuários - {perfil_atual}", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", size=12)

                usuarios_na_pagina = 0
                coluna_atual = 0
                linha_na_coluna = 0

            x = x_positions[coluna_atual]
            y = 40 + (linha_na_coluna * 10)

            pdf.set_xy(x, y)
            texto_usuario = f"{contador_usuario}. {u['nome']} ({u['perfil'].capitalize()})"
            pdf.cell(largura_coluna, 10, txt=texto_usuario, ln=0)

            contador_usuario += 1
            usuarios_na_pagina += 1

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_content = pdf_buffer.getvalue()

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios.pdf'
    return response

    
# 🔹 Exportações - Usuários (HTML)
@routes.route('/exportar/usuarios_html')
@login_obrigatorio
@somente_master
def exibir_exportar_usuarios():
    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, nome FROM usuarios ORDER BY nome")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('exportar/usuarios.html', usuarios=usuarios)

# =======================================
# 🔹 AJAX
# =======================================

# 🔹 CRUD Horários - Professores disponíveis via AJAX
@routes.route('/ajax/professores_disponiveis', methods=['POST'])
@login_obrigatorio
def professores_disponiveis_ajax():
    data = request.get_json()
    especialidade = data.get('especialidade')
    dia = data.get('dia')
    aula = data.get('aula')
    sala_id = data.get('sala_id')

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT p.id, p.nome
        FROM professores p
        WHERE p.especialidade = %s
        AND p.id NOT IN (
            SELECT professor_id FROM horarios
            WHERE dia_semana = %s AND aula_numero = %s AND sala_id != %s
        )
    """, (especialidade, dia, aula, sala_id))

    professores = cur.fetchall()
    cur.close()

    return jsonify(professores)



# =======================================
# 🔹 GERAR GRADES
# =======================================

# 🔹 CRUD Horários - Gerar horário global
@routes.route('/gerar_horarios_global')
@login_obrigatorio
@somente_master
def gerar_horarios_global():
    import random
    from flask import flash, redirect, url_for

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar todas as salas e professores
    cur.execute("SELECT * FROM salas")
    salas = cur.fetchall()

    cur.execute("SELECT id, nome, especialidade FROM professores")
    professores = cur.fetchall()

    cur.execute("DELETE FROM horarios")  # Limpa todos os horários antes de gerar
    mysql.connection.commit()

    # Mapear professores por especialidade
    prof_por_esp = {}
    for prof in professores:
        prof_por_esp.setdefault(prof['especialidade'], []).append(prof)

    carga_horaria = {
        "Língua Portuguesa": 6,
        "Matemática": 6,
        "Inglês": 2,
        "Física": 2,
        "Química": 2,
        "Biologia": 2,
        "História": 2,
        "Geografia": 2,
        "Filosofia": 1,
        "Sociologia": 1,
        "Artes": 1,
        "Educação Física": 2
    }

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    aulas_por_dia = 6

    # Função auxiliar para gerar uma grade para uma sala
    def gerar_grade_sala(sala_id):
        ocupacao_professores = {p['id']: {dia: [False]*aulas_por_dia for dia in dias} for p in professores}
        grade = {dia: [None]*aulas_por_dia for dia in dias}

        blocos = []
        for materia, total in carga_horaria.items():
            if materia in prof_por_esp:
                for _ in range(total // 2):
                    blocos.append((materia, 2))
                if total % 2:
                    blocos.append((materia, 1))

        random.shuffle(blocos)

        for materia, tamanho_bloco in blocos:
            alocado = False
            candidatos = prof_por_esp[materia][:]
            random.shuffle(candidatos)

            for dia in random.sample(dias, len(dias)):
                for i in range(aulas_por_dia - tamanho_bloco + 1):
                    if all(grade[dia][i+j] is None for j in range(tamanho_bloco)):
                        for prof in candidatos:
                            if all(not ocupacao_professores[prof['id']][dia][i+j] for j in range(tamanho_bloco)):
                                for j in range(tamanho_bloco):
                                    grade[dia][i+j] = {'materia': materia, 'professor_id': prof['id']}
                                    ocupacao_professores[prof['id']][dia][i+j] = True
                                alocado = True
                                break
                        if alocado:
                            break
                if alocado:
                    break

        return grade

    # Tentar gerar até 10 vezes por sala
    for sala in salas:
        sucesso = False
        tentativas = 0
        while not sucesso and tentativas < 10:
            tentativas += 1
            grade = gerar_grade_sala(sala['id'])

            if all(all(aula is not None for aula in dia) for dia in grade.values()):
                sucesso = True

        # Salvar no banco
        for dia, aulas in grade.items():
            for idx, aula in enumerate(aulas):
                if aula:
                    cur.execute("""
                        INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sala['id'], dia, idx+1, aula['materia'], aula['professor_id']))
                else:
                    cur.execute("""
                        INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                        VALUES (%s, %s, %s, %s, NULL)
                    """, (sala['id'], dia, idx+1, "Livre"))

    mysql.connection.commit()
    cur.close()

    flash("✅ Horários gerados com sucesso para todas as salas!", "success")
    return redirect(url_for('routes.exibir_salas_para_geracao'))

# 🔹 CRUD Horários - Gerar horário individual de uma sala
@routes.route('/gerar_horario_sala/<int:sala_id>')
@login_obrigatorio
@somente_master
def gerar_horario_sala_individual(sala_id):
    import random
    from flask import flash, redirect, url_for

    mysql = get_mysql()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Buscar a sala
    cur.execute("SELECT * FROM salas WHERE id = %s", (sala_id,))
    sala = cur.fetchone()
    if not sala:
        flash("❌ Sala não encontrada!", "danger")
        return redirect(url_for('routes.exibir_salas_para_geracao'))

    # Buscar professores
    cur.execute("SELECT id, nome, especialidade FROM professores")
    professores = cur.fetchall()

    # Deleta os horários antigos da sala
    cur.execute("DELETE FROM horarios WHERE sala_id = %s", (sala_id,))
    mysql.connection.commit()

    # Mapear professores por especialidade
    prof_por_esp = {}
    for prof in professores:
        prof_por_esp.setdefault(prof['especialidade'], []).append(prof)

    carga_horaria = {
        "Língua Portuguesa": 6,
        "Matemática": 6,
        "Inglês": 2,
        "Física": 2,
        "Química": 2,
        "Biologia": 2,
        "História": 2,
        "Geografia": 2,
        "Filosofia": 1,
        "Sociologia": 1,
        "Artes": 1,
        "Educação Física": 2
    }

    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    aulas_por_dia = 6

    # Função auxiliar para gerar uma grade para a sala
    def gerar_grade():
        ocupacao_professores = {p['id']: {dia: [False]*aulas_por_dia for dia in dias} for p in professores}
        grade = {dia: [None]*aulas_por_dia for dia in dias}

        blocos = []
        for materia, total in carga_horaria.items():
            if materia in prof_por_esp:
                for _ in range(total // 2):
                    blocos.append((materia, 2))
                if total % 2:
                    blocos.append((materia, 1))

        random.shuffle(blocos)

        for materia, tamanho_bloco in blocos:
            alocado = False
            candidatos = prof_por_esp[materia][:]
            random.shuffle(candidatos)

            for dia in random.sample(dias, len(dias)):
                for i in range(aulas_por_dia - tamanho_bloco + 1):
                    if all(grade[dia][i+j] is None for j in range(tamanho_bloco)):
                        for prof in candidatos:
                            if all(not ocupacao_professores[prof['id']][dia][i+j] for j in range(tamanho_bloco)):
                                for j in range(tamanho_bloco):
                                    grade[dia][i+j] = {'materia': materia, 'professor_id': prof['id']}
                                    ocupacao_professores[prof['id']][dia][i+j] = True
                                alocado = True
                                break
                        if alocado:
                            break
                if alocado:
                    break

        return grade

    # Tentativas de geração
    sucesso = False
    tentativas = 0
    while not sucesso and tentativas < 10:
        tentativas += 1
        grade = gerar_grade()

        if all(all(aula is not None for aula in dia) for dia in grade.values()):
            sucesso = True

    # Salvar no banco de dados
    for dia, aulas in grade.items():
        for idx, aula in enumerate(aulas):
            if aula:
                cur.execute("""
                    INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (sala_id, dia, idx+1, aula['materia'], aula['professor_id']))
            else:
                cur.execute("""
                    INSERT INTO horarios (sala_id, dia_semana, aula_numero, materia, professor_id)
                    VALUES (%s, %s, %s, %s, NULL)
                """, (sala_id, dia, idx+1, "Livre"))

    mysql.connection.commit()
    cur.close()

    if sucesso:
        flash(f"✅ Horário gerado com sucesso para a sala {sala['nome']}!", "success")
    else:
        flash(f"⚠️ Horário gerado parcialmente para a sala {sala['nome']}. Nem todas as matérias foram alocadas.", "warning")

    return redirect(url_for('routes.exibir_salas_para_geracao'))

