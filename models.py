from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SQLAlchemy()



# Modelo de roles de usuario  
class Roles(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    users = db.relationship("User", secondary="user_roles", back_populates="roles")


# Modelo de usuario
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    telefono = db.Column(db.Integer, nullable=False)
    password_hash = db.Column(db.String(130), nullable=False)
    roles = db.relationship("Roles", secondary="user_roles", back_populates="users")

    @hybrid_property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    
    @password.setter
    def password(self, value):
      from app import db, bcrypt
      self.password_hash = bcrypt.generate_password_hash(value).decode('utf-8')

    def check_password(self, password):
      from app import db, bcrypt
      return bcrypt.check_password_hash(self.password_hash, password)

    def has_role(self, role):
      return bool(
        Roles.query
        .join(Roles.users)
        .filter(User.id == self.id)
        .filter(Roles.slug == role)
        .count() == 1
        .exists()
      ).scalar() 

class UserRole(db.Model):
  __tablename__ = 'user_roles'
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
  role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)

# Modelo de formulario
class FormResult(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fecha = db.Column(db.String(50), nullable=False)
  nombre = db.Column(db.String(100), nullable=False)
  apellidos = db.Column(db.String(100), nullable=False)
  email = db.Column(db.String(100), nullable=False)
  telefono = db.Column(db.String(50), nullable=False)
  pais_residencia = db.Column(db.String(100), nullable=False)
  edad = db.Column(db.Integer, nullable=False)
  estado_civil = db.Column(db.String(50), nullable=False)
  hijos = db.Column(db.String(50), nullable=False)
  vivienda = db.Column(db.String(100), nullable=False)
  profesion = db.Column(db.String(100), nullable=False)
  nivel_educacion = db.Column(db.String(100), nullable=False)
  tiempo_empleo = db.Column(db.String(100), nullable=False)
  propietario = db.Column(db.String(50), nullable=False)
  ingresos = db.Column(db.Integer, nullable=False)
  impuestos = db.Column(db.String(50), nullable=False)
  propiedades = db.Column(db.String(100), nullable=False)
  viajes = db.Column(db.String(100), nullable=False)
  familiares_eeuu = db.Column(db.String(100), nullable=False)
  familiares_visa = db.Column(db.String(100), nullable=False)
  visa_negada = db.Column(db.String(100), nullable=False)
  antecedentes = db.Column(db.String(100), nullable=False)
  enfermedades = db.Column(db.String(100), nullable=False)
  visa_otra = db.Column(db.String(100), nullable=False)
  problemas_migratorios = db.Column(db.String(100), nullable=False)
  nacionalidad = db.Column(db.String(100), nullable=False)
  calificacion = db.Column(db.Integer, nullable=False)
  
  # Calificaciones específicas por ChatGPT
  calificacion_pais_residencia_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_edad_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_estado_civil_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_hijos_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_vivienda_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_profesion_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_nivel_educacion_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_tiempo_empleo_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_propietario_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_ingresos_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_impuestos_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_propiedades_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_viajes_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_familiares_eeuu_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_familiares_visa_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_visa_negada_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_antecedentes_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_enfermedades_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_visa_otra_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_problemas_migratorios_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_nacionalidad_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_criterios_confidenciales_ChatGPT = db.Column(db.Text, nullable=True)
  
  # Probabilidad calculada
  probabilidad = db.Column(db.Integer, nullable=False)
  
  # Sugerencias por ChatGPT
  sugerencia_1_ChatGPT = db.Column(db.Text, nullable=True)
  sugerencia_2_ChatGPT = db.Column(db.Text, nullable=True)
  sugerencia_3_ChatGPT = db.Column(db.Text, nullable=True)
  
  # Calificaciones de categorías por ChatGPT
  calificacion_categoria_informacion_demografica_familiar_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_categoria_educacion_empleo_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_categoria_propiedades_activos_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_categoria_antecedentes_experiencia_viaje_ChatGPT = db.Column(db.Text, nullable=True)
  calificacion_categoria_criterios_confidenciales_ChatGPT = db.Column(db.Text, nullable=True)
  
  # Notas adicionales
  notas = db.Column(db.Text, nullable=True)
  
  # Ruta del PDF generado
  pdf_path = db.Column(db.String(200), nullable=False)