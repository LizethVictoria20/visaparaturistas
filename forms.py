from wtforms import Form, StringField, IntegerField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, NumberRange, Length, EqualTo
from flask_wtf import FlaskForm

# Formulario de inicio de sesión
class LoginForm(Form):
  username = StringField('Username', [DataRequired()])
  password = PasswordField('Password', [DataRequired()])
  submit = SubmitField('Login')

# Formulario de cuestionario

class CuestionarioForm(Form):
  nombre = StringField('Nombre', [DataRequired()])
  apellidos = StringField('Apellidos', [DataRequired()])
  email = StringField('Email', [DataRequired(), Email()])
  telefono = StringField('Teléfono', [DataRequired()])
  pais_residencia = StringField('País de Residencia', [DataRequired()])
  fecha = StringField('Fecha', [DataRequired()])
  edad = IntegerField('Edad', [DataRequired(), NumberRange(min=18, max=100)])
  estado_civil = StringField('Estado Civil', [DataRequired()])
  hijos = StringField('¿Tiene hijos? Si la respuesta es sí, ¿cuántos?', [DataRequired()])
  vivienda = StringField('¿Con quién comparte su vivienda actualmente?', [DataRequired()])
  profesion = StringField('Profesión u ocupación', [DataRequired()])
  nivel_educacion = StringField('¿Cuál es su nivel de educación?', [DataRequired()])
  tiempo_empleo = StringField('¿Cuánto tiempo lleva trabajando en su empleo actual?', [DataRequired()])
  propietario = StringField('¿Es propietario o socio de alguna empresa?', [DataRequired()])
  ingresos = IntegerField('Ingresos mensuales aproximados', [DataRequired(), NumberRange(min=0)])
  impuestos = StringField('¿Paga impuestos en su país de origen y no participa en algún programa de asistencia social gubernamental?', [DataRequired()])
  propiedades = StringField('¿Posee propiedades inmobiliarias y/o vehículos en su país de residencia?', [DataRequired()])
  viajes = StringField('¿Ha viajado al extranjero anteriormente? Indique cuántos países:', [DataRequired()])
  familiares_eeuu = StringField('¿Tiene familiares que residan en los Estados Unidos?', [DataRequired()])
  familiares_visa = StringField('¿Tiene familiares que cuenten con una visa de turismo para los Estados Unidos?', [DataRequired()])
  visa_negada = StringField('¿Le ha sido negada una visa de turismo para los Estados Unidos anteriormente?', [DataRequired()])
  antecedentes = StringField('¿Tiene antecedentes judiciales o ha estado involucrado en procesos de embargo?', [DataRequired()])
  enfermedades = StringField('¿Padece alguna enfermedad crónica o preexistente de base?', [DataRequired()])
  visa_otra = StringField('¿Tiene algún tipo de visa o permiso de residencia vigente para otro país?', [DataRequired()])
  problemas_migratorios = StringField('¿Ha tenido problemas o dificultades con las autoridades migratorias en cualquier país?', [DataRequired()])
  nacionalidad = StringField('¿Cuál es su nacionalidad?', [DataRequired()])
  calificacion = IntegerField('Calificación del evaluador', [DataRequired()])
  submit = SubmitField('Enviar')
  
  
class UserCreationForm(FlaskForm):
  username = StringField('Username', validators=[DataRequired(), Length(min=3, max=25)])
  password_hash = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
  confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password_hash')])
  roles = SelectField('Roles', choices=[('user', 'User'), ('admin', 'Administrator')], validators=[DataRequired()])
  submit = SubmitField('Create User')

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Cambiar contraseña')
