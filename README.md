# 🧠 Sistema de Gestão de Horários Escolares

<!-- Sistema web completo para **gerenciamento de horários escolares**, permitindo o cadastro de professores, alunos, salas, turmas e a geração automática de horários com controle de conflitos.



## 🚀 Funcionalidades

- 📋 Cadastro e edição de Professores, Alunos, Salas, Turmas e Usuários
- 🔐 Login com controle de permissão (Master, Administrativo, Usuário)
- 📆 Geração automática de horários por sala
- 🗓️ Visualização da grade por Sala e por Professor
- ✏️ Edição manual da grade de horário
- ⚠️ Prevenção de conflitos de horário para professores
- 📤 Exportação de horários e alunos por sala em PDF

---

## 🛠️ Tecnologias utilizadas

- **Backend:** Python 3 + Flask
- **Banco de dados:** MySQL
- **Frontend:** HTML5 + Bootstrap 5 + DataTables.js
- **Outros:** FPDF (PDF), Jinja2 (templates)

---

## ✅ Requisitos

- ✅ Python 3.10 ou superior
- ✅ MySQL Server instalado
- ✅ Visual Studio Code (ou outro editor)
- ✅ Git (opcional)

---

## 💾 Como instalar e executar o projeto

### 1. Clone o repositório

```bash
*git clone https://github.com/SEU_USUARIO/gestao_horarios.git
*cd gestao_horarios


### 2. Crie e ative o ambiente virtual
*MySQL 8.0 Command Line Client: python -m venv venv

*Windows cmd: venv\Scripts\activate
*Linux/macOS: source venv/bin/activate

### 3. Instale as dependências
*pip install -r requirements.txt

### 4. Crie o banco de dados no MySQL
*CREATE DATABASE gestao_horarios;

### 5. Restaure o backup
*mysql -u root -p gestao_horarios < backup.sql

### Executando o projeto
*python app.py
*Abra no navegador: http://127.0.0.1:5000

** Usuários de teste
#Perfil         | Email                     | Senha
#Master (admin) | master@admin.com          | 102030
#Administrativo | administrativo@test.com   | 102030
#Assistente     | assistente@test.com       | 102030