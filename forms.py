from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length

class UsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[Length(min=6)])
    perfil = SelectField('Perfil', choices=[('usuario', 'Usuário'), ('master', 'Master')])
    submit = SubmitField('Salvar')
