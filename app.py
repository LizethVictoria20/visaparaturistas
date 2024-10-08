from functools import wraps
from flask import Flask, abort, current_app, render_template, request, send_file, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed, Identity, identity_changed, AnonymousIdentity
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
import matplotlib
from werkzeug.security import generate_password_hash
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sqlite3
import os
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from openai import OpenAI
from weasyprint import HTML
from database import delete_record_by_id
from io import BytesIO
import io
import subprocess
import pandas as pd
from models import db, User, FormResult, Roles
from forms import LoginForm, CuestionarioForm, UserCreationForm, UpdatePasswordForm

# Cargar variables de entorno desde el archivo .env
load_dotenv(dotenv_path='.env')

# Crear una instancia del cliente OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///form_results.db?timeout=20'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)
principals = Principal(app)


# Definir permisos por roles
admin_permission = Permission(RoleNeed('admin'))
user_permission = Permission(RoleNeed('user'))
bcrypt = Bcrypt(app)

# Evento que se ejecuta cuando se carga la identidad del usuario
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user
    
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.name))


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/detail/<int:id>')
@login_required
def detail(id):
    result = FormResult.query.get_or_404(id)
    return render_template('detail.html', result=result)

def calificar_respuesta(client, respuesta, prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un especialista en migración y visados de turismo a EE.UU."},
                {"role": "user", "content": f"{prompt}: {respuesta}"}
            ]
        )
        calificacion = completion.choices[0].message.content.strip()
        return calificacion
    except Exception as e:
        print(f"Error al calificar respuesta: {e}")
        return "0"  # Valor predeterminado en caso de error

def calificar_pais_residencia(client, pais_residencia):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en el país de residencia. El país de residencia de esta persona es '{pais_residencia}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los países con más y menos posibilidades de aprobación de visas, no por nacionalidad sino por residencia, y basado en eso escribe este número. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{pais_residencia}", prompt)

def calificar_edad(client, edad):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la edad. La edad de esta persona es '{edad}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de las edades con más y menos posibilidades de aprobación de visas, no por otros factores sino por edad, y basado en eso escribe este número. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{edad}", prompt)

def calificar_estado_civil(client, estado_civil):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en el estado civil. El estado civil de esta persona es '{estado_civil}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los estados civiles con más y menos posibilidades de aprobación de visas, y basado en eso escribe este número. Ten en cuenta que las personas sin compromisos tienen más posibilidades de convertirse en migrantes irregulares frente a las personas con compromisos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{estado_civil}", prompt)

def calificar_hijos(client, hijos):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basada en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basada en la información sobre hijos. La información sobre hijos de esta persona es '{hijos}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los casos con más y menos posibilidades de aprobación de visas, no por nacionalidad sino por la información sobre hijos, y basado en eso escribe este número. Ten en cuenta que las personas sin compromisos tienen más posibilidades de hacerse migrantes irregulares frente a las personas con compromisos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{hijos}", prompt)

def calificar_vivienda(client, vivienda):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de vivienda. La información de vivienda de esta persona es '{vivienda}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los tipos de vivienda con más y menos posibilidades de aprobación de visas, y basado en eso escribe este número. Ten en cuenta que las personas sin compromisos tienen más posibilidades de hacerse migrantes irregulares frente a las personas con compromisos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{vivienda}", prompt)

def calificar_profesion(client, profesion):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la profesión. La profesión de esta persona es '{profesion}'. Califica en una escala de 4 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de las profesiones con más y menos posibilidades de aprobación de visas, y basado en eso escribe este número. Ten en cuenta que hay profesiones que pueden tener más respeto y que pueden tener una mayor preferencia por el gobierno de Estados Unidos y que tienen menos posibilidad de ser inmigrantes irregulares porque ganan bien en sus países de residencia. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{profesion}", prompt)

def calificar_nivel_educacion(client, nivel_educacion):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en el nivel de educación. El nivel de educación de esta persona es '{nivel_educacion}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad considerando niveles de educación más y menos favorables para la aprobación de visas, y basado en eso escribe este número. Ten en cuenta que hay profesiones que pueden tener más respeto y que pueden tener una mayor preferencia por el gobierno de Estados Unidos. Ten en cuenta que un mayor nivel académico puede indicar mayor capacidad económica y una menor posibilidad de ser inmigrante irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{nivel_educacion}", prompt)

def calificar_tiempo_empleo(client, tiempo_empleo):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en el tiempo de empleo. El tiempo que esta persona lleva en su empleo actual es '{tiempo_empleo}'. Califica en una escala de 4 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad considerando diferentes duraciones de empleo y basado en eso escribe este número. Ten en cuenta que un mayor tiempo en un empleo indica más compromiso, estabilidad y menos posibilidad de ser migrante irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{tiempo_empleo}", prompt)

def calificar_propietario(client, propietario):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en ser propietario. Esta persona indicó lo siguiente sobre si es propietario o socio de una empresa: '{propietario}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad considerando a los propietarios y no propietarios, y basado en eso escribe este número. Ten en cuenta que entre mayor es el patrimonio menor es la posibilidad de inmigración irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{propietario}", prompt)

def calificar_ingresos(client, ingresos):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en los ingresos. Los ingresos de esta persona en USD son '{ingresos}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los ingresos con más y menos posibilidades de aprobación de visas, y basado en eso escribe este número. Ten en cuenta que a mayor ingreso es menor la posibilidad de inmigración irregular, tener presente cuánto puede costar un viaje promedio de una persona a EE.UU. y si esta persona puede costearlo. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{ingresos}", prompt)

def calificar_impuestos(client, impuestos):
    prompt = f"Somos un equipo universitario realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en el pago de impuestos y recepción de ayuda gubernamental. Esta persona declaró: '{impuestos}', frente a la pregunta que le hicimos si pagaba impuestos y NO era participante de programas de ayudas sociales. Califica en una escala de 4 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los casos con más y menos posibilidades de aprobación de visas, no por nacionalidad sino por el pago de impuestos, y basado en eso escribe este número. Ten en cuenta que una persona que paga impuestos y no está en programas sociales es una persona con buenas finanzas y tiene menos posibilidad de ser inmigrante irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{impuestos}", prompt)

def calificar_propiedades(client, propiedades):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en ser propietario. Esta persona indicó lo siguiente sobre si posee propiedades o vehículos: '{propiedades}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad considerando a los propietarios y no propietarios, y basado en eso escribe este número. Ten en cuenta que entre mayor es el patrimonio menor es la posibilidad de inmigración irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{propiedades}", prompt)

def calificar_viajes(client, viajes):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de viajes al exterior. La información de viajes de esta persona indica a continuación los países a los que ha viajado en los últimos 5 años: '{viajes}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Haz una hipótesis de alta probabilidad de acuerdo al número de viajes y tipo de países que visita una persona en los últimos 5 años. Responde solo con el número, máximo 5 caracteres. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{viajes}", prompt)

def calificar_familiares_eeuu(client, familiares_eeuu):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de familiares en EE.UU. Esto respondió la persona al momento de preguntarle si tenía familiares en EE.UU.: '{familiares_eeuu}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los casos con más y menos posibilidades de aprobación de visas, basado en si una persona tiene familiares en EE.UU. y la posibilidad de hacerse inmigrante irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{familiares_eeuu}", prompt)

def calificar_familiares_visa(client, familiares_visa):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de familiares en EE.UU. Esto respondió la persona al momento de preguntarle si tenía familiares en EE.UU. y sobre el estatus migratorio: '{familiares_visa}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los casos con más y menos posibilidades de aprobación de visas, basado en si una persona tiene familiares en EE.UU. y la posibilidad de hacerse inmigrante irregular. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{familiares_visa}", prompt)

def calificar_visa_negada(client, visa_negada):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de visas negadas. La siguiente fue la respuesta de la persona cuando preguntamos si tenía alguna solicitud de visa negada: '{visa_negada}'. Califica en una escala de 4 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de aprobación considerando la información de visas negadas y basado en eso escribe este número. Ten en cuenta que, entre más visas negadas, hay menos posibilidad de conseguir una; estas negaciones indican algún elemento negativo que impide la aprobación. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{visa_negada}", prompt)

def calificar_antecedentes(client, antecedentes):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de antecedentes. Los antecedentes de esta persona son '{antecedentes}'. Califica en una escala de 1 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los antecedentes con más y menos posibilidades de aprobación de visas, y basado en eso escribe este número. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{antecedentes}", prompt)

def calificar_enfermedades(client, enfermedades):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basada en la información de enfermedades. Lo siguiente respondió la persona al preguntarle si tiene alguna enfermedad que pueda afectar la salud pública o el sistema de salud de Estados Unidos: '{enfermedades}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de las enfermedades con más y menos posibilidades de aprobación de visas y, basado en eso, escribe este número. Ten en cuenta que una persona enferma podría ser un problema para el sistema de salud de los Estados Unidos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{enfermedades}", prompt)

def calificar_visa_otra(client, visa_otra):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de otras visas. La siguiente es la respuesta de la persona a la pregunta si tiene visa de otros países: '{visa_otra}'. Califica en una escala de 4 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de las personas con más y menos posibilidades de aprobación de visas basado en la información de otras visas, y basado en eso escribe este número. Ten en cuenta que una visa de turismo a otros países puede indicar que ya ha pasado algunos filtros de otros países para ser admitido como turista y puede ayudar en el proceso de aprobación. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{visa_otra}", prompt)

def calificar_problemas_migratorios(client, problemas_migratorios):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la información de problemas migratorios. La persona respondió lo siguiente luego de preguntarle si antes ha tenido problemas migratorios en Estados Unidos u otros países: '{problemas_migratorios}'. Califica en una escala de 3 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad considerando los problemas migratorios de las personas, y basado en eso escribe este número. Ten en cuenta que tener problemas migratorios puede disminuir la posibilidad de aprobación de visa. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{problemas_migratorios}", prompt)

def calificar_nacionalidad(client, nacionalidad):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en la nacionalidad. La nacionalidad de esta persona es '{nacionalidad}'. Califica en una escala de 1 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de las nacionalidades con más y menos posibilidades de aprobación de visas y, basado en eso, escribe este número. Ten en cuenta que tener nacionales de países con conflictos, con situaciones económicas muy negativas o con situaciones adversas con la política internacional de Estados Unidos disminuye la posibilidad de conseguir una visa de turismo a los Estados Unidos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{nacionalidad}", prompt)

def calificar_criterios_confidenciales(client, calificacion, nacionalidad):
    prompt = f"Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en criterios confidenciales que no queremos sean revelados al público porque pueden ser sensibles. La calificación de este punto se basa en la calificación que le dio el entrevistador, que es: '{calificacion}', y la calificación que pueda tener la nacionalidad del solicitante, que es: '{nacionalidad}'. Ten en cuenta que hay nacionales con más y con menos posibilidades de aprobación de visa de turismo. Califica en una escala de 1 a 10, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 5 caracteres. Haz una hipótesis de alta probabilidad de los países con más y menos posibilidades de aprobación de visas, no por nacionalidad sino por residencia, y basado en eso escribe este número. Tener en cuenta que tener nacionales de países con conflictos, o con situaciones económicas muy negativas o con situaciones adversas con la política internacional de Estados Unidos disminuye la posibilidad de conseguir una visa de turismo a los Estados Unidos. Si envías texto y más de 5 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XX.XX."
    return calificar_respuesta(client, f"{calificacion}, {nacionalidad}", prompt)

def calcular_probabilidad(client, pais_residencia, fecha, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales):
    
    datos_formulario = f"{pais_residencia}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}"
    calificaciones = f"{calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales}"
    
    prompt = f"""Somos un equipo científico realizando un estudio hipotético sobre la probabilidad de obtener una visa de turismo a EE.UU. basado en diversos factores. Sabemos que no es posible calcular esta probabilidad solo con estos datos, pero queremos una estimación. Califica la probabilidad de obtener una visa de turismo a EE.UU. basado en los datos completados en un estudio de perfil para conseguir su visa de turismo a EE.UU. Los datos del formulario son:
    
    Estas son las preguntas realizadas en el estudio de perfil:
    - País de Residencia: ¿Cuál es su país de residencia? {pais_residencia} (Calificación: {calificacion_pais_residencia})
    - Edad: ¿Cuál es su edad? {edad} (Calificación: {calificacion_edad})
    - Estado Civil: ¿Cuál es su estado civil? {estado_civil} (Calificación: {calificacion_estado_civil})
    - Hijos: ¿Cuántos hijos tienes? {hijos} (Calificación: {calificacion_hijos})
    - Vivienda: ¿Con quién comparte su vivienda actualmente? {vivienda} (Calificación: {calificacion_vivienda})
    - Profesión: ¿Cuál es su profesión u ocupación? {profesion} (Calificación: {calificacion_profesion})
    - Nivel de Educación: ¿Cuál es su nivel de educación? {nivel_educacion} (Calificación: {calificacion_nivel_educacion})
    - Tiempo de Empleo: ¿Cuánto tiempo lleva trabajando en su empleo actual? {tiempo_empleo} (Calificación: {calificacion_tiempo_empleo})
    - Propietario: ¿Es propietario o socio de alguna empresa? {propietario} (Calificación: {calificacion_propietario})
    - Ingresos: Ingresos mensuales aproximados en dólares americanos: {ingresos} (Calificación: {calificacion_ingresos})
    - Impuestos: ¿Paga impuestos y no participa en programas de asistencia social? {impuestos} (Calificación: {calificacion_impuestos})
    - Propiedades: ¿Posee propiedades inmobiliarias y/o vehículos en su país de residencia? {propiedades} (Calificación: {calificacion_propiedades})
    - Viajes: ¿En los últimos 5 años, a qué países ha viajado? {viajes} (Calificación: {calificacion_viajes})
    - Familiares en EE.UU.: ¿Tiene familiares que residan en los Estados Unidos? {familiares_eeuu} (Calificación: {calificacion_familiares_eeuu})
    - Familiares con Visa de Turismo: ¿Tiene familiares que cuenten con una visa de turismo a EE.UU.? {familiares_visa} (Calificación: {calificacion_familiares_visa})
    - Visa Negada: ¿Le ha sido negada una visa de turismo para EE.UU. anteriormente? {visa_negada} (Calificación: {calificacion_visa_negada})
    - Antecedentes: ¿Tiene antecedentes judiciales o ha estado en procesos de embargo? {antecedentes} (Calificación: {calificacion_antecedentes})
    - Enfermedades: ¿Padece alguna enfermedad crónica o preexistente de base? {enfermedades} (Calificación: {calificacion_enfermedades})
    - Visa de Otros Países: ¿Tiene algún tipo de visa o permiso de residencia vigente para otro país? {visa_otra} (Calificación: {calificacion_visa_otra})
    - Problemas Migratorios: ¿Ha tenido problemas o dificultades con las autoridades migratorias? {problemas_migratorios} (Calificación: {calificacion_problemas_migratorios})
    - Nacionalidad: ¿Cuál es su nacionalidad? {nacionalidad} (Calificación: {calificacion_nacionalidad})
    - Criterios Confidenciales: {calificacion_criterios_confidenciales}.
    
    Califica en una escala de 1 a 100, solo números, con un máximo de 2 decimales. Responde solo con el número, máximo 6 caracteres. Haz una hipótesis basada en estos datos. Si envías texto y más de 6 caracteres, no se recibirá la respuesta. Ejemplo de respuesta: XXX.XX."""

    return calificar_respuesta(client, f"{pais_residencia}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}, {calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales}", prompt)


def sugerencia_1(client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales):
    prompt = f"""
    Los siguientes son los datos de cómo el sistema calificó las diferentes variables que evaluamos para conocer cuáles son los puntos débiles de una persona que está solicitando su visa de turismo a los Estados Unidos y quiere mejorar su perfil para aumentar las probabilidades.

    Estos son los elementos evaluados:
    - Nivel de Educación: ¿Cuál es su nivel de educación? {nivel_educacion} (Calificación: {calificacion_nivel_educacion})
    - Tiempo de Empleo: ¿Cuánto tiempo lleva trabajando en su empleo actual? {tiempo_empleo} (Calificación: {calificacion_tiempo_empleo}) [Si la sugerencia es sobre este tema invitarlo a buscar otros suporte que le ayuden a demostrar estabilidad y arriegos en sy pais de residencia y a demostrar un buen historial laboral]
    - Propietario: ¿Es propietario o socio de alguna empresa? {propietario} (Calificación: {calificacion_propietario}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Ingresos: Ingresos mensuales aproximados en dólares americanos: {ingresos} (Calificación: {calificacion_ingresos}) [Si la sugerencia es de este punto invitarlo a mejorar sus ingresos]
    - Impuestos: ¿Paga impuestos y no participa en programas de asistencia social? {impuestos} (Calificación: {calificacion_impuestos}) [Si la sugerencia es de este punto invutarlo a mantener en orden sus declaraciones de impuesto y a evitar registrase en programas de aistencia para persoans de escasos recursos]
    - Propiedades: ¿Posee propiedades inmobiliarias y/o vehículos en su país de residencia? {propiedades} (Calificación: {calificacion_propiedades}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Viajes: ¿En los últimos 5 años, a qué países ha viajado? {viajes} (Calificación: {calificacion_viajes})
    - Visa Negada: ¿Le ha sido negada una visa de turismo para EE.UU. anteriormente? {visa_negada} (Calificación: {calificacion_visa_negada}) [Si la sugerencai es sobre este punto invitarlo a mejorar su perfil antes de presentarse de neuvo apra eviatr otra solictud de visa negada.]
    - Antecedentes: ¿Tiene antecedentes judiciales o ha estado en procesos de embargo? {antecedentes} (Calificación: {calificacion_antecedentes}) [si la sugerencia es sobre este punto invitar a regularizar cualquier inconveniente judicial que pueda tener antes de solicitar la visa.]


    Revisa los elementos de menor a mayor puntaje y toma el elemento de este estudio con menor calificación y que, además, sea sumamente importante en las razones por las que niegan la visa de turismo a EE.UU. Escribe una recomendación en un párrafo para mejorar la calificación de ese punto que tiene la peor calificación de todo el estudio y aumentar la posibilidad de aprobación de la visa. Recuerda escoger el punto con la menor calificación. Responde solo en un párrafo, teniendo en cuenta que no solo es importante la calificación sino también el peso de la pregunta; hay preguntas con temas de más importancia a la hora de aprobar una visa de turismo que otras. Trata de acertar en la problemática número uno que tiene el solicitante. Al inicio de la sugerencia, no hacer introducción ni decir directamente la calificación del punto; ser muy claro en cómo este punto afecta la solicitud y lo más importante, cómo mejorarlo. Hablar en términos fáciles de entender ya que las personas que leen esto no tienen muchos conocimientos de estos temas. No mencionar la calificación del punto que estoy evaluando, no quiero poner ese número en la sugerencia. Esta instrucción es para identificar el elemento con el peor puntaje en calificación cuando se llenó el estudio de perfilamiento y dar una sugerencia de qué hacer para mejorar ese punto y aumentar las posibilidades de obtener la visa de turismo a EE.UU. Hablar de manera amable y evitar mensajes que puedan herir la susceptibilidad de las personas que lo leen.
    """
    return calificar_respuesta(client, f"{pais_residencia}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}, {calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales}", prompt)


def sugerencia_2(client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales, sugerencia_1_ChatGPT):
    prompt = f"""
    Los siguientes son los datos de cómo el sistema calificó las diferentes variables que evaluamos para conocer cuáles son los puntos débiles de una persona que está solicitando su visa de turismo a los Estados Unidos y quiere mejorar su perfil para aumentar las probabilidades.

   Estos son los elementos evaluados:
    - Nivel de Educación: ¿Cuál es su nivel de educación? {nivel_educacion} (Calificación: {calificacion_nivel_educacion})
    - Tiempo de Empleo: ¿Cuánto tiempo lleva trabajando en su empleo actual? {tiempo_empleo} (Calificación: {calificacion_tiempo_empleo}) [Si la sugerencia es sobre este tema invitarlo a buscar otros suporte que le ayuden a demostrar estabilidad y arriegos en sy pais de residencia y a demostrar un buen historial laboral]
    - Propietario: ¿Es propietario o socio de alguna empresa? {propietario} (Calificación: {calificacion_propietario}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Ingresos: Ingresos mensuales aproximados en dólares americanos: {ingresos} (Calificación: {calificacion_ingresos}) [Si la sugerencia es de este punto invitarlo a mejorar sus ingresos]
    - Impuestos: ¿Paga impuestos y no participa en programas de asistencia social? {impuestos} (Calificación: {calificacion_impuestos}) [Si la sugerencia es de este punto invutarlo a mantener en orden sus declaraciones de impuesto y a evitar registrase en programas de aistencia para persoans de escasos recursos]
    - Propiedades: ¿Posee propiedades inmobiliarias y/o vehículos en su país de residencia? {propiedades} (Calificación: {calificacion_propiedades}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Viajes: ¿En los últimos 5 años, a qué países ha viajado? {viajes} (Calificación: {calificacion_viajes})
    - Visa Negada: ¿Le ha sido negada una visa de turismo para EE.UU. anteriormente? {visa_negada} (Calificación: {calificacion_visa_negada}) [Si la sugerencai es sobre este punto invitarlo a mejorar su perfil antes de presentarse de neuvo apra eviatr otra solictud de visa negada.]
    - Antecedentes: ¿Tiene antecedentes judiciales o ha estado en procesos de embargo? {antecedentes} (Calificación: {calificacion_antecedentes}) [si la sugerencia es sobre este punto invitar a regularizar cualquier inconveniente judicial que pueda tener antes de solicitar la visa.]


    Revisa los elementos de menor a mayor puntaje y toma el tercer elemento de este estudio con menor calificación y que, además, sea sumamente importante en las razones por las que niegan la visa de turismo a EE.UU. No consideres el primer ni el segundo elemento con menor calificación, ya que ya se trataron en puntos anteriores. Escribe una recomendación en un párrafo para mejorar la calificación de ese punto tres y aumentar la posibilidad de aprobación de la visa. Recuerda escoger el tercer punto con la menor calificación. Responde solo en un párrafo. Trata de acertar en la tercera problemática más importante que tiene el solicitante. Al inicio de la sugerencia no hagas introducción ni menciones directamente la calificación del punto, sé muy claro en cómo este punto afecta la solicitud y, lo más importante, cómo mejorarlo. Habla en términos fáciles de entender, ya que las personas que leen esto no tienen muchos conocimientos sobre estos temas. No mencionar la calificación del punto que estoy evaluando, no quiero poner ese número en la sugerencia. Esta instrucción es para identificar el elemento con el tercer peor puntaje en calificación cuando se llenó el estudio de perfilamiento y dar una sugerencia de qué hacer para mejorar ese punto y aumentar las posibilidades de obtener la visa de turismo a EE.UU. Hablar de manera amable y evitar mensajes que puedan herir la susceptibilidad de las personas que lo leen.

    Esta es la sugerencia 1 para no repetir la misma tematica. ES REGLA QUE NO HABLES DE ESTE TEMA EN LA RESPUESTA QUE VAS A DAR A CONTINUACIÓN:
    {sugerencia_1_ChatGPT}
    """
    return calificar_respuesta(client, f"{pais_residencia}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}, {calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales, sugerencia_1_ChatGPT}", prompt)


def sugerencia_3(client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales, sugerencia_1_ChatGPT, sugerencia_2_ChatGPT):
    prompt = f"""
    Los siguientes son los datos de cómo el sistema calificó las diferentes variables que evaluamos para conocer cuáles son los puntos débiles de una persona que está solicitando su visa de turismo a los Estados Unidos y quiere mejorar su perfil para aumentar las probabilidades.

    Estos son los elementos evaluados:
    - Nivel de Educación: ¿Cuál es su nivel de educación? {nivel_educacion} (Calificación: {calificacion_nivel_educacion})
    - Tiempo de Empleo: ¿Cuánto tiempo lleva trabajando en su empleo actual? {tiempo_empleo} (Calificación: {calificacion_tiempo_empleo}) [Si la sugerencia es sobre este tema invitarlo a buscar otros suporte que le ayuden a demostrar estabilidad y arriegos en sy pais de residencia y a demostrar un buen historial laboral]
    - Propietario: ¿Es propietario o socio de alguna empresa? {propietario} (Calificación: {calificacion_propietario}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Ingresos: Ingresos mensuales aproximados en dólares americanos: {ingresos} (Calificación: {calificacion_ingresos}) [Si la sugerencia es de este punto invitarlo a mejorar sus ingresos]
    - Impuestos: ¿Paga impuestos y no participa en programas de asistencia social? {impuestos} (Calificación: {calificacion_impuestos}) [Si la sugerencia es de este punto invutarlo a mantener en orden sus declaraciones de impuesto y a evitar registrase en programas de aistencia para persoans de escasos recursos]
    - Propiedades: ¿Posee propiedades inmobiliarias y/o vehículos en su país de residencia? {propiedades} (Calificación: {calificacion_propiedades}) [Si la sugerencai es sobre este punto invitarlo a buscar otras formas en que pueda demostrar su estabilidad y buen estado financiero]
    - Viajes: ¿En los últimos 5 años, a qué países ha viajado? {viajes} (Calificación: {calificacion_viajes})
    - Visa Negada: ¿Le ha sido negada una visa de turismo para EE.UU. anteriormente? {visa_negada} (Calificación: {calificacion_visa_negada}) [Si la sugerencai es sobre este punto invitarlo a mejorar su perfil antes de presentarse de neuvo apra eviatr otra solictud de visa negada.]
    - Antecedentes: ¿Tiene antecedentes judiciales o ha estado en procesos de embargo? {antecedentes} (Calificación: {calificacion_antecedentes}) [si la sugerencia es sobre este punto invitar a regularizar cualquier inconveniente judicial que pueda tener antes de solicitar la visa.]

    Estas es la sugerencia 1 y 2 para no repetir estos temas:
    Sugerencia 1 ES REGLA QUE NO HABLES DE ESTE TEMA EN LA RESPUESTA QUE VAS A DAR A CONTINUACIÓN:
    {sugerencia_1_ChatGPT}

    Sugerencai 2 ES REGLA QUE TAMPOCO  HABLES DE ESTE TEMA EN LA RESPUESTA QUE VAS A DAR A CONTINUACIÓN:
    {sugerencia_2_ChatGPT}

    Revisa los elementos de menor a mayor puntaje y toma el tercer elemento de este estudio con menor calificación y que, además, sea sumamente importante en las razones por las que niegan la visa de turismo a EE.UU. No consideres el primer ni el segundo elemento con menor calificación, ya que ya se trataron en puntos anteriores. Escribe una recomendación en un párrafo para mejorar la calificación de ese punto tres y aumentar la posibilidad de aprobación de la visa. Recuerda escoger el tercer punto con la menor calificación. Responde solo en un párrafo. Trata de acertar en la tercera problemática más importante que tiene el solicitante. Al inicio de la sugerencia no hagas introducción ni menciones directamente la calificación del punto, sé muy claro en cómo este punto afecta la solicitud y, lo más importante, cómo mejorarlo. Habla en términos fáciles de entender, ya que las personas que leen esto no tienen muchos conocimientos sobre estos temas. No mencionar la calificación del punto que estoy evaluando, no quiero poner ese número en la sugerencia. Esta instrucción es para identificar el elemento con el tercer peor puntaje en calificación cuando se llenó el estudio de perfilamiento y dar una sugerencia de qué hacer para mejorar ese punto y aumentar las posibilidades de obtener la visa de turismo a EE.UU. Hablar de manera amable y evitar mensajes que puedan herir la susceptibilidad de las personas que lo leen.
    """
    return calificar_respuesta(client, f"{pais_residencia}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}, {calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales, sugerencia_1_ChatGPT, sugerencia_2_ChatGPT}", prompt)

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Buscar al usuario por su nombre de usuario
        user = User.query.filter_by(username=username).first()
        
        # Verificar si el usuario existe y si la contraseña es correcta
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('results'))  # Redirigir a alguna página protegida
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')
  

# Ruta para el logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# Función para emitir el progreso
def emit_progress(message, progress):
    # Emitir el progreso a todos los clientes conectados
    socketio.emit('progress', {'message': message, 'progress': progress})

# Ruta para el formulario principal
@app.route('/', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=403)
def form():
    form = CuestionarioForm(request.form)
    if request.method == 'POST' and form.validate():
        # Datos del formulario
        nombre = form.nombre.data
        apellidos = form.apellidos.data
        email = form.email.data
        telefono = form.telefono.data
        pais_residencia = form.pais_residencia.data
        fecha = form.fecha.data
        edad = form.edad.data
        estado_civil = form.estado_civil.data
        hijos = form.hijos.data
        vivienda = form.vivienda.data
        profesion = form.profesion.data
        nivel_educacion = form.nivel_educacion.data
        tiempo_empleo = form.tiempo_empleo.data
        propietario = form.propietario.data
        ingresos = form.ingresos.data
        impuestos = form.impuestos.data
        propiedades = form.propiedades.data
        viajes = form.viajes.data
        familiares_eeuu = form.familiares_eeuu.data
        familiares_visa = form.familiares_visa.data
        visa_negada = form.visa_negada.data
        antecedentes = form.antecedentes.data
        enfermedades = form.enfermedades.data
        visa_otra = form.visa_otra.data
        problemas_migratorios = form.problemas_migratorios.data
        nacionalidad = form.nacionalidad.data
        calificacion = int(form.calificacion.data)  # Convertir calificación a entero

        try:
            emit_progress('Iniciando Procesando datos con IA.', 1)

            # Calificar cada respuesta utilizando ChatGPT
            calificacion_pais_residencia = calificar_pais_residencia(client, pais_residencia)
            emit_progress('Procesando país de residencia...', 5)

            calificacion_edad = calificar_edad(client, str(edad))
            emit_progress('Procesando edad...', 8)

            calificacion_estado_civil = calificar_estado_civil(client, estado_civil)
            emit_progress('Procesando estado civil...', 10)

            calificacion_hijos = calificar_hijos(client, hijos)
            emit_progress('Procesando detos de hijos...', 13)

            calificacion_vivienda = calificar_vivienda(client, vivienda)
            emit_progress('Procesando datos de vivienda...', 16)

            calificacion_profesion = calificar_profesion(client, profesion)
            emit_progress('Procesando profesión...', 19)

            calificacion_nivel_educacion = calificar_nivel_educacion(client, nivel_educacion)
            emit_progress('Procesando nivel de educación...', 22)

            calificacion_tiempo_empleo = calificar_tiempo_empleo(client, tiempo_empleo)
            emit_progress('Procesando tiempo de empleo...', 25)

            calificacion_propietario = calificar_propietario(client, propietario)
            emit_progress('Procesando propiedad empresarial...', 28)

            calificacion_ingresos = calificar_ingresos(client, str(ingresos))
            emit_progress('Procesando ingresos...', 31)

            calificacion_impuestos = calificar_impuestos(client, impuestos)
            emit_progress('Procesando pago de impuestos...', 34)

            calificacion_propiedades = calificar_propiedades(client, propiedades)
            emit_progress('Procesando propiedades...', 37)

            calificacion_viajes = calificar_viajes(client, viajes)
            emit_progress('Procesando viajes...', 40)

            calificacion_familiares_eeuu = calificar_familiares_eeuu(client, familiares_eeuu)
            emit_progress('Procesando familiares en EE.UU....', 43)

            calificacion_familiares_visa = calificar_familiares_visa(client, familiares_visa)
            emit_progress('Procesando familiares con visa...', 47)

            calificacion_visa_negada = calificar_visa_negada(client, visa_negada)
            emit_progress('Procesando visas negadas...', 49)

            calificacion_antecedentes = calificar_antecedentes(client, antecedentes)
            emit_progress('Procesando antecedentes...', 52)

            calificacion_enfermedades = calificar_enfermedades(client, enfermedades)
            emit_progress('Procesando datos sobre enfermedades...', 55)

            calificacion_visa_otra = calificar_visa_otra(client, visa_otra)
            emit_progress('Procesando otras visas...', 58)

            calificacion_problemas_migratorios = calificar_problemas_migratorios(client, problemas_migratorios)
            emit_progress('Procesando requerimientos migratorios...', 61)

            calificacion_nacionalidad = calificar_nacionalidad(client, nacionalidad)
            emit_progress('Procesando nacionalidad...', 64)

            calificacion_criterios_confidenciales = calificar_criterios_confidenciales(client, str(calificacion), nacionalidad)
            emit_progress('Procesando criterios confidenciales...', 67)

            # Datos del formulario y calificaciones para probabilidad y sugerencias
            datos_formulario = f"{pais_residencia}, {fecha}, {edad}, {estado_civil}, {hijos}, {vivienda}, {profesion}, {nivel_educacion}, {tiempo_empleo}, {propietario}, {ingresos}, {impuestos}, {propiedades}, {viajes}, {familiares_eeuu}, {familiares_visa}, {visa_negada}, {antecedentes}, {enfermedades}, {visa_otra}, {problemas_migratorios}, {nacionalidad}, {calificacion}"
            calificaciones = f"{calificacion_pais_residencia}, {calificacion_edad}, {calificacion_estado_civil}, {calificacion_hijos}, {calificacion_vivienda}, {calificacion_profesion}, {calificacion_nivel_educacion}, {calificacion_tiempo_empleo}, {calificacion_propietario}, {calificacion_ingresos}, {calificacion_impuestos}, {calificacion_propiedades}, {calificacion_viajes}, {calificacion_familiares_eeuu}, {calificacion_familiares_visa}, {calificacion_visa_negada}, {calificacion_antecedentes}, {calificacion_enfermedades}, {calificacion_visa_otra}, {calificacion_problemas_migratorios}, {calificacion_nacionalidad}, {calificacion_criterios_confidenciales}"

            # Calcular probabilidad usando ChatGPT
            probabilidad = calcular_probabilidad(
                client, pais_residencia, fecha, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad,
                calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales
            )
            emit_progress('Calculando probabilidad de aprobación...', 70)

            # Obtener sugerencias usando ChatGPT
            sugerencia_1_ChatGPT = sugerencia_1(
                client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad,
                calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales
            )
            emit_progress('Procesando recomendaciones...', 73)

            sugerencia_2_ChatGPT = sugerencia_2(
                client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad,
                calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales, sugerencia_1_ChatGPT
            )
            emit_progress('Compilando datos...', 76)

            sugerencia_3_ChatGPT = sugerencia_3(
                client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad,
                calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad, calificacion_criterios_confidenciales, sugerencia_1_ChatGPT, sugerencia_2_ChatGPT
            )
            emit_progress('Exportando estudio de perfil con AI.', 80)

            # Generar el PDF
            pdf_path = os.path.join(os.getcwd(), 'resultados', f'{nombre}_{apellidos}.pdf')
            generate_pdf(
                nombre, apellidos, email, telefono, pais_residencia, fecha, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion,
                calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_criterios_confidenciales, probabilidad,
                sugerencia_1_ChatGPT, sugerencia_2_ChatGPT, sugerencia_3_ChatGPT,
                pdf_path
            )
            emit_progress('PDF Generate...', 85)

            # Guardar en la base de datos
            form_result = FormResult(
                nombre=nombre,
                apellidos=apellidos,
                email=email,
                telefono=telefono,
                pais_residencia=pais_residencia,
                fecha=fecha,
                edad=edad,
                estado_civil=estado_civil,
                hijos=hijos,
                vivienda=vivienda,
                profesion=profesion,
                nivel_educacion=nivel_educacion,
                tiempo_empleo=tiempo_empleo,
                propietario=propietario,
                ingresos=ingresos,
                impuestos=impuestos,
                propiedades=propiedades,
                viajes=viajes,
                familiares_eeuu=familiares_eeuu,
                familiares_visa=familiares_visa,
                visa_negada=visa_negada,
                antecedentes=antecedentes,
                enfermedades=enfermedades,
                visa_otra=visa_otra,
                problemas_migratorios=problemas_migratorios,
                nacionalidad=nacionalidad,
                calificacion=calificacion,
                calificacion_pais_residencia_ChatGPT=calificacion_pais_residencia,
                calificacion_edad_ChatGPT=calificacion_edad,
                calificacion_estado_civil_ChatGPT=calificacion_estado_civil,
                calificacion_hijos_ChatGPT=calificacion_hijos,
                calificacion_vivienda_ChatGPT=calificacion_vivienda,
                calificacion_profesion_ChatGPT=calificacion_profesion,
                calificacion_nivel_educacion_ChatGPT=calificacion_nivel_educacion,
                calificacion_tiempo_empleo_ChatGPT=calificacion_tiempo_empleo,
                calificacion_propietario_ChatGPT=calificacion_propietario,
                calificacion_ingresos_ChatGPT=calificacion_ingresos,
                calificacion_impuestos_ChatGPT=calificacion_impuestos,
                calificacion_propiedades_ChatGPT=calificacion_propiedades,
                calificacion_viajes_ChatGPT=calificacion_viajes,
                calificacion_familiares_eeuu_ChatGPT=calificacion_familiares_eeuu,
                calificacion_familiares_visa_ChatGPT=calificacion_familiares_visa,
                calificacion_visa_negada_ChatGPT=calificacion_visa_negada,
                calificacion_antecedentes_ChatGPT=calificacion_antecedentes,
                calificacion_enfermedades_ChatGPT=calificacion_enfermedades,
                calificacion_visa_otra_ChatGPT=calificacion_visa_otra,
                calificacion_problemas_migratorios_ChatGPT=calificacion_problemas_migratorios,
                calificacion_nacionalidad_ChatGPT=calificacion_nacionalidad,
                calificacion_criterios_confidenciales_ChatGPT=calificacion_criterios_confidenciales,
                probabilidad=probabilidad,
                sugerencia_1_ChatGPT=sugerencia_1_ChatGPT,
                sugerencia_2_ChatGPT=sugerencia_2_ChatGPT,
                sugerencia_3_ChatGPT=sugerencia_3_ChatGPT,
                pdf_path=pdf_path
            )
            db.session.add(form_result)
            db.session.commit()
            emit_progress('Datos guardados almacenados', 90)

            flash('Formulario enviado correctamente!', 'success')
            emit_progress('Proceso completado', 100)
            return jsonify({"redirect_url": url_for('thanks', filename=f'{nombre}_{apellidos}.pdf')})

        except Exception as e:
            flash(f'Hubo un error al procesar el formulario: {str(e)}', 'error')


    return render_template('form.html', form=form)

# Ruta de agradecimiento
@app.route('/thanks')
@login_required
def thanks():
    filename = request.args.get('filename', None)
    return render_template('thanks.html', filename=filename)

# Ruta para descargar el PDF
@app.route('/download/<filename>')
@login_required
def download(filename):
    pdf_path = os.path.join(os.getcwd(), 'resultados', filename)
    return send_file(pdf_path, as_attachment=True)

# Ruta para actualizar datos
@app.route('/update', methods=['POST'])
def update():
    field = request.form.get('field')
    value = request.form.get('value')
    id = request.form.get('id')

    print(f"Received update request - ID: {id}, Field: {field}, Value: {value}")  # Mensaje de depuración

    success = update_database(id, field, value)

    if success:
        print(f"Update successful for ID: {id}, Field: {field}, Value: {value}")  # Mensaje de depuración
        return jsonify(success=True)
    else:
        print(f"Update failed for ID: {id}, Field: {field}, Value: {value}")  # Mensaje de depuración
        return jsonify(success=False), 400

def update_database(id, field, value):
    try:
        record = FormResult.query.get(id)
        if record:
            setattr(record, field, value)
            db.session.commit()
            print(f"Database update successful for ID: {id}, Field: {field}, Value: {value}")  # Mensaje de depuración
            return True
        else:
            print(f"No record found with ID: {id}")  # Mensaje de depuración
            return False
    except Exception as e:
        print(f"Error updating database: {e}")  # Mensaje de depuración
        return False

# Ruta para mostrar los resultados
@admin_permission.require(http_exception=403)
@user_permission.require(http_exception=403)
@app.route('/results')
@login_required
def results():
    results = FormResult.query.all()
    return render_template('results.html', results=results)

# Función para generar el PDF
def generate_pdf(nombre, apellidos, email, telefono, pais_residencia, fecha, edad, estado_civil, hijos, vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad, calificacion,
                 calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda, calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades, calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa, calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades, calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_criterios_confidenciales, probabilidad,
                 sugerencia_1_ChatGPT, sugerencia_2_ChatGPT, sugerencia_3_ChatGPT,
                 pdf_path):

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Encabezado del informe
    header_style = ParagraphStyle(
        'header',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor("#007aff"),
        spaceAfter=14,
        alignment=1  # Center alignment
    )
    header = Paragraph("Informe de Solicitud de Visa de Turismo", header_style)
    elements.append(header)
    elements.append(Spacer(1, 12))

    # Información personal
    info_style = ParagraphStyle(
        'info',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=12,
        textColor=colors.black,
        spaceAfter=6,
    )
    info = f"""
    <b>Nombre:</b> {nombre}<br/>
    <b>Apellidos:</b> {apellidos}<br/>
    <b>Email:</b> {email}<br/>
    <b>Teléfono:</b> {telefono}<br/>
    <b>País de Residencia:</b> {pais_residencia}<br/>
    <b>Fecha:</b> {fecha}<br/>
    <b>Edad:</b> {edad}<br/>
    <b>Estado Civil:</b> {estado_civil}<br/>
    <b>Hijos:</b> {hijos}<br/>
    <b>Vivienda:</b> {vivienda}<br/>
    <b>Profesión:</b> {profesion}<br/>
    <b>Nivel de Educación:</b> {nivel_educacion}<br/>
    <b>Tiempo en Empleo:</b> {tiempo_empleo}<br/>
    <b>Propietario o Socio:</b> {propietario}<br/>
    <b>Ingresos:</b> {ingresos}<br/>
    <b>Impuestos:</b> {impuestos}<br/>
    <b>Propiedades:</b> {propiedades}<br/>
    <b>Viajes:</b> {viajes}<br/>
    <b>Familiares en EEUU:</b> {familiares_eeuu}<br/>
    <b>Familiares con Visa:</b> {familiares_visa}<br/>
    <b>Visa Negada:</b> {visa_negada}<br/>
    <b>Antecedentes:</b> {antecedentes}<br/>
    <b>Enfermedades:</b> {enfermedades}<br/>
    <b>Visa Otra:</b> {visa_otra}<br/>
    <b>Problemas Migratorios:</b> {problemas_migratorios}<br/>
    <b>Nacionalidad:</b> {nacionalidad}<br/>
    <b>Calificación del Evaluador:</b> {calificacion}<br/>
    <b>Calificación por país de residencia (ChatGPT):</b> {calificacion_pais_residencia}<br/>
    <b>Calificación por edad (ChatGPT):</b> {calificacion_edad}<br/>
    <b>Calificación por estado civil (ChatGPT):</b> {calificacion_estado_civil}<br/>
    <b>Calificación por hijos (ChatGPT):</b> {calificacion_hijos}<br/>
    <b>Calificación por vivienda (ChatGPT):</b> {calificacion_vivienda}<br/>
    <b>Calificación por profesión (ChatGPT):</b> {calificacion_profesion}<br/>
    <b>Calificación por nivel de educación (ChatGPT):</b> {calificacion_nivel_educacion}<br/>
    <b>Calificación por tiempo de empleo (ChatGPT):</b> {calificacion_tiempo_empleo}<br/>
    <b>Calificación por ser propietario (ChatGPT):</b> {calificacion_propietario}<br/>
    <b>Calificación por ingresos (ChatGPT):</b> {calificacion_ingresos}<br/>
    <b>Calificación por impuestos (ChatGPT):</b> {calificacion_impuestos}<br/>
    <b>Calificación por propiedades (ChatGPT):</b> {calificacion_propiedades}<br/>
    <b>Calificación por viajes (ChatGPT):</b> {calificacion_viajes}<br/>
    <b>Calificación por familiares en EEUU (ChatGPT):</b> {calificacion_familiares_eeuu}<br/>
    <b>Calificación por familiares con visa (ChatGPT):</b> {calificacion_familiares_visa}<br/>
    <b>Calificación por visa negada (ChatGPT):</b> {calificacion_visa_negada}<br/>
    <b>Calificación por antecedentes (ChatGPT):</b> {calificacion_antecedentes}<br/>
    <b>Calificación por enfermedades (ChatGPT):</b> {calificacion_enfermedades}<br/>
    <b>Calificación por otras visas (ChatGPT):</b> {calificacion_visa_otra}<br/>
    <b>Calificación por problemas migratorios (ChatGPT):</b> {calificacion_problemas_migratorios}<br/>
    <b>Calificación por criterios confidenciales (ChatGPT):</b> {calificacion_criterios_confidenciales}<br/>
    <b>Sugerencia 1 (ChatGPT):</b> {sugerencia_1_ChatGPT}<br/>
    <b>Sugerencia 2 (ChatGPT):</b> {sugerencia_2_ChatGPT}<br/>
    <b>Sugerencia 3 (ChatGPT):</b> {sugerencia_3_ChatGPT}<br/>
    """
    info_paragraph = Paragraph(info, info_style)
    elements.append(info_paragraph)
    elements.append(Spacer(1, 12))

    # Tabla de probabilidad
    data = [
        ["Probabilidad de aprobación", probabilidad],
    ]

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#007aff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ])

    table = Table(data, hAlign='LEFT', colWidths=[300, 100])
    table.setStyle(table_style)

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Gráfico de calificación
    fig, ax = plt.subplots(figsize=(6, 3))
    calificacion = max(0, min(calificacion, 100))  # Asegurarse de que la calificación esté en el rango 0-100
    wedges, texts, autotexts = ax.pie(
        [calificacion, 100 - calificacion],
        labels=['Calificación', 'Resto'],
        autopct='%1.1f%%',
        startangle=90,
        colors=['#007aff', '#d1d1d6'],
        textprops=dict(color="w")
    )

    for text in texts:
        text.set_color('black')

    ax.axis('equal')
    plt.setp(autotexts, size=10, weight="bold")

    graph_path = os.path.join(os.getcwd(), 'resultados', 'calificacion.png')
    plt.savefig(graph_path, format='png', bbox_inches='tight')
    plt.close()

    elements.append(Image(graph_path, width=15*cm, height=7.5*cm))
    elements.append(Spacer(1, 12))

    doc.build(elements)
    os.remove(graph_path)
    
    # Obteniendo datos de la base de datos para generar archivo XLS y CSV
@app.route('/export-all-xls', methods=['GET'])
def export_all_XLS():
  all_results = FormResult.query.all()
  data = []
  for result in all_results:
      data.append({
          'Nombre': result.nombre,
          'Apellidos': result.apellidos,
          'Email': result.email,
          'Telefono': result.telefono,
          'Pais residencia': result.pais_residencia,
          'Fecha': result.fecha,
          'Edad': result.edad,
          'Estado Civil': result.estado_civil,
          'Hijos': result.hijos,
          'Vivienda': result.vivienda,
          'Profesion': result.profesion,
          'Nivel_educacion': result.nivel_educacion,
          'Tiempo_empleo': result.tiempo_empleo,
          'Propietario': result.propietario,
          'Ingresos': result.ingresos,
          'Impuestos': result.impuestos,
          'Propiedades': result.propiedades,
          'Viajes': result.viajes,
          'Familiares eeuu': result.familiares_eeuu,
          'Familiares visa': result.familiares_visa,
          'Visa negada': result.visa_negada,
          'Antecedentes': result.antecedentes,
          'Enfermedades': result.enfermedades,
          'Visa otra': result.visa_otra,
          'Problemas migratorios': result.problemas_migratorios,
          'Nacionalidad': result.nacionalidad,
          'Calificacion': result.calificacion,             
      })

  df = pd.DataFrame(data)
  output = BytesIO()
  with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
      df.to_excel(writer, index=False, sheet_name='Sheet1')
  output.seek(0) 

  return send_file(output, 
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    download_name='datos_exportados.xlsx',
                    as_attachment=True)

@app.route('/export-all-csv', methods=['GET'])
def export_all_CSV():
  all_results = FormResult.query.all()
  data = []
  for result in all_results:
      data.append({
          'Nombre': result.nombre,
          'Apellidos': result.apellidos,
          'Email': result.email,
          'Telefono': result.telefono,
          'Pais residencia': result.pais_residencia,
          'Fecha': result.fecha,
          'Edad': result.edad,
          'Estado Civil': result.estado_civil,
          'Hijos': result.hijos,
          'Vivienda': result.vivienda,
          'Profesion': result.profesion,
          'Nivel_educacion': result.nivel_educacion,
          'Tiempo_empleo': result.tiempo_empleo,
          'Propietario': result.propietario,
          'Ingresos': result.ingresos,
          'Impuestos': result.impuestos,
          'Propiedades': result.propiedades,
          'Viajes': result.viajes,
          'Familiares eeuu': result.familiares_eeuu,
          'Familiares visa': result.familiares_visa,
          'Visa negada': result.visa_negada,
          'Antecedentes': result.antecedentes,
          'Enfermedades': result.enfermedades,
          'Visa otra': result.visa_otra,
          'Problemas migratorios': result.problemas_migratorios,
          'Nacionalidad': result.nacionalidad,
          'Calificacion': result.calificacion,             
      })

  df = pd.DataFrame(data)
  output = BytesIO()
  df.to_csv(output, index=False)
  output.seek(0)  

  return send_file(output, 
                    mimetype='text/csv',
                    download_name='datos_exportados.csv',
                    as_attachment=True)


@app.route('/delete', methods=['POST'])
def delete_record():
    record_id = request.form.get('id')
    if not record_id:
        return jsonify({'success': False, 'message': 'ID not provided'}), 400

    confirm_delete = request.form.get('confirm-delete')
    if confirm_delete != 'DELETE':
        return jsonify({'success': False, 'message': 'Confirmation text incorrect'}), 400

    try:
        success = delete_record_by_id(record_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete record'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


        
def delete_record_by_id(record_id):
    try:
        record = FormResult.query.get(record_id)
        if not record:
            return False
        
        db.session.delete(record)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar el registro: {e}")
        return False

    
def emit_progress_regenerar(messageregenerar, progressregenerar):
    # Emitir el progreso a todos los clientes conectados para regenerar
    print(f"Emit progressregenerar: {messageregenerar}, Progress: {progressregenerar}%")  # Línea de impresión para depuración
    socketio.emit('progressregenerar', {'messageregenerar': messageregenerar, 'progressregenerar': progressregenerar})


@app.route('/regenerar/<int:id>', methods=['POST'])
@login_required
def regenerar(id):
    form_result = FormResult.query.get_or_404(id)
    
    try:
        emit_progress_regenerar('Iniciando regeneración de datos con IA.', 1)

        # Datos extraídos del form_result guardado en la base de datos
        nombre = form_result.nombre
        apellidos = form_result.apellidos
        email = form_result.email
        telefono = form_result.telefono
        pais_residencia = form_result.pais_residencia
        fecha = form_result.fecha
        edad = form_result.edad
        estado_civil = form_result.estado_civil
        hijos = form_result.hijos
        vivienda = form_result.vivienda
        profesion = form_result.profesion
        nivel_educacion = form_result.nivel_educacion
        tiempo_empleo = form_result.tiempo_empleo
        propietario = form_result.propietario
        ingresos = form_result.ingresos
        impuestos = form_result.impuestos
        propiedades = form_result.propiedades
        viajes = form_result.viajes
        familiares_eeuu = form_result.familiares_eeuu
        familiares_visa = form_result.familiares_visa
        visa_negada = form_result.visa_negada
        antecedentes = form_result.antecedentes
        enfermedades = form_result.enfermedades
        visa_otra = form_result.visa_otra
        problemas_migratorios = form_result.problemas_migratorios
        nacionalidad = form_result.nacionalidad
        calificacion = form_result.calificacion

        # Recalificación de cada respuesta utilizando ChatGPT
        calificacion_pais_residencia = calificar_pais_residencia(client, pais_residencia)
        emit_progress_regenerar('Procesando país de residencia...', 5)

        calificacion_edad = calificar_edad(client, str(edad))
        emit_progress_regenerar('Procesando edad...', 8)

        calificacion_estado_civil = calificar_estado_civil(client, estado_civil)
        emit_progress_regenerar('Procesando estado civil...', 10)

        calificacion_hijos = calificar_hijos(client, hijos)
        emit_progress_regenerar('Procesando datos de hijos...', 13)

        calificacion_vivienda = calificar_vivienda(client, vivienda)
        emit_progress_regenerar('Procesando datos de vivienda...', 16)

        calificacion_profesion = calificar_profesion(client, profesion)
        emit_progress_regenerar('Procesando profesión...', 19)

        calificacion_nivel_educacion = calificar_nivel_educacion(client, nivel_educacion)
        emit_progress_regenerar('Procesando nivel de educación...', 22)

        calificacion_tiempo_empleo = calificar_tiempo_empleo(client, tiempo_empleo)
        emit_progress_regenerar('Procesando tiempo de empleo...', 25)

        calificacion_propietario = calificar_propietario(client, propietario)
        emit_progress_regenerar('Procesando propiedad empresarial...', 28)

        calificacion_ingresos = calificar_ingresos(client, str(ingresos))
        emit_progress_regenerar('Procesando ingresos...', 31)

        calificacion_impuestos = calificar_impuestos(client, impuestos)
        emit_progress_regenerar('Procesando pago de impuestos...', 34)

        calificacion_propiedades = calificar_propiedades(client, propiedades)
        emit_progress_regenerar('Procesando propiedades...', 37)

        calificacion_viajes = calificar_viajes(client, viajes)
        emit_progress_regenerar('Procesando viajes...', 40)

        calificacion_familiares_eeuu = calificar_familiares_eeuu(client, familiares_eeuu)
        emit_progress_regenerar('Procesando familiares en EE.UU....', 43)

        calificacion_familiares_visa = calificar_familiares_visa(client, familiares_visa)
        emit_progress_regenerar('Procesando familiares con visa...', 47)

        calificacion_visa_negada = calificar_visa_negada(client, visa_negada)
        emit_progress_regenerar('Procesando visas negadas...', 49)

        calificacion_antecedentes = calificar_antecedentes(client, antecedentes)
        emit_progress_regenerar('Procesando antecedentes...', 52)

        calificacion_enfermedades = calificar_enfermedades(client, enfermedades)
        emit_progress_regenerar('Procesando datos sobre enfermedades...', 55)

        calificacion_visa_otra = calificar_visa_otra(client, visa_otra)
        emit_progress_regenerar('Procesando otras visas...', 58)

        calificacion_problemas_migratorios = calificar_problemas_migratorios(client, problemas_migratorios)
        emit_progress_regenerar('Procesando requerimientos migratorios...', 61)

        calificacion_nacionalidad = calificar_nacionalidad(client, nacionalidad)
        emit_progress_regenerar('Procesando nacionalidad...', 64)

        calificacion_criterios_confidenciales = calificar_criterios_confidenciales(client, str(calificacion), nacionalidad)
        emit_progress_regenerar('Procesando criterios confidenciales...', 67)

        probabilidad = calcular_probabilidad(
            client, pais_residencia, fecha, edad, estado_civil, hijos,
            vivienda, profesion, nivel_educacion, tiempo_empleo, propietario, ingresos,
            impuestos, propiedades, viajes, familiares_eeuu, familiares_visa, visa_negada,
            antecedentes, enfermedades, visa_otra, problemas_migratorios, nacionalidad,
            calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil,
            calificacion_hijos, calificacion_vivienda, calificacion_profesion,
            calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario,
            calificacion_ingresos, calificacion_impuestos, calificacion_propiedades,
            calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa,
            calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades,
            calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad,
            calificacion_criterios_confidenciales
        )
        emit_progress_regenerar('Calculando probabilidad de aprobación...', 70)

        sugerencia_1_ChatGPT = sugerencia_1(
            client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion,
            nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades,
            viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades,
            visa_otra, problemas_migratorios, nacionalidad,
            calificacion_pais_residencia, calificacion_edad, calificacion_estado_civil,
            calificacion_hijos, calificacion_vivienda, calificacion_profesion,
            calificacion_nivel_educacion, calificacion_tiempo_empleo, calificacion_propietario,
            calificacion_ingresos, calificacion_impuestos, calificacion_propiedades,
            calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa,
            calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades,
            calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad,
            calificacion_criterios_confidenciales
        )
        emit_progress_regenerar('Procesando recomendaciones sugerencia 1...', 73)

        sugerencia_2_ChatGPT = sugerencia_2(
            client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion,
            nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades,
            viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades,
            visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia,
            calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda,
            calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo,
            calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades,
            calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa,
            calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades,
            calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad,
            calificacion_criterios_confidenciales, sugerencia_1_ChatGPT
        )
        emit_progress_regenerar('Procesando recomendaciones sugerencia 2...', 76)

        sugerencia_3_ChatGPT = sugerencia_3(
            client, pais_residencia, edad, estado_civil, hijos, vivienda, profesion,
            nivel_educacion, tiempo_empleo, propietario, ingresos, impuestos, propiedades,
            viajes, familiares_eeuu, familiares_visa, visa_negada, antecedentes, enfermedades,
            visa_otra, problemas_migratorios, nacionalidad, calificacion_pais_residencia,
            calificacion_edad, calificacion_estado_civil, calificacion_hijos, calificacion_vivienda,
            calificacion_profesion, calificacion_nivel_educacion, calificacion_tiempo_empleo,
            calificacion_propietario, calificacion_ingresos, calificacion_impuestos, calificacion_propiedades,
            calificacion_viajes, calificacion_familiares_eeuu, calificacion_familiares_visa,
            calificacion_visa_negada, calificacion_antecedentes, calificacion_enfermedades,
            calificacion_visa_otra, calificacion_problemas_migratorios, calificacion_nacionalidad,
            calificacion_criterios_confidenciales, sugerencia_1_ChatGPT, sugerencia_2_ChatGPT
        )
        emit_progress_regenerar('Procesando recomendaciones sugerencia 3...', 80)

      
        # Guardar en la base de datos
        form_result.calificacion_pais_residencia_ChatGPT = calificacion_pais_residencia
        form_result.calificacion_edad_ChatGPT = calificacion_edad
        form_result.calificacion_estado_civil_ChatGPT = calificacion_estado_civil
        form_result.calificacion_hijos_ChatGPT = calificacion_hijos
        form_result.calificacion_vivienda_ChatGPT = calificacion_vivienda
        form_result.calificacion_profesion_ChatGPT = calificacion_profesion
        form_result.calificacion_nivel_educacion_ChatGPT = calificacion_nivel_educacion
        form_result.calificacion_tiempo_empleo_ChatGPT = calificacion_tiempo_empleo
        form_result.calificacion_propietario_ChatGPT = calificacion_propietario
        form_result.calificacion_ingresos_ChatGPT = calificacion_ingresos
        form_result.calificacion_impuestos_ChatGPT = calificacion_impuestos
        form_result.calificacion_propiedades_ChatGPT = calificacion_propiedades
        form_result.calificacion_viajes_ChatGPT = calificacion_viajes
        form_result.calificacion_familiares_eeuu_ChatGPT = calificacion_familiares_eeuu
        form_result.calificacion_familiares_visa_ChatGPT = calificacion_familiares_visa
        form_result.calificacion_visa_negada_ChatGPT = calificacion_visa_negada
        form_result.calificacion_antecedentes_ChatGPT = calificacion_antecedentes
        form_result.calificacion_enfermedades_ChatGPT = calificacion_enfermedades
        form_result.calificacion_visa_otra_ChatGPT = calificacion_visa_otra
        form_result.calificacion_problemas_migratorios_ChatGPT = calificacion_problemas_migratorios
        form_result.calificacion_nacionalidad_ChatGPT = calificacion_nacionalidad
        form_result.calificacion_criterios_confidenciales_ChatGPT = calificacion_criterios_confidenciales
        form_result.probabilidad = probabilidad
        form_result.sugerencia_1_ChatGPT = sugerencia_1_ChatGPT
        form_result.sugerencia_2_ChatGPT = sugerencia_2_ChatGPT
        form_result.sugerencia_3_ChatGPT = sugerencia_3_ChatGPT

        db.session.commit()
        emit_progress_regenerar('Datos guardados en la base de datos', 90)
        emit_progress_regenerar('Proceso completado', 100)
        
        flash('Datos regenerados correctamente!', 'success')
        
        return redirect(url_for('detail', id=id))

    except Exception as e:
        flash(f'Ocurrió un error al regenerar los datos: {str(e)}', 'danger')
        print(f"Error durante la regeneración: {e}")
        return redirect(url_for('detail', id=id))


# Añadir la ruta para generar el PDF
@app.route('/create_pdf/<int:id>', methods=['GET'])
@login_required
def create_pdf(id):
    result = FormResult.query.get_or_404(id)
    rendered_html = render_template('detail_pdf.html', result=result)

    # Crear el directorio tmp si no existe
    if not os.path.exists('tmp'):
        os.makedirs('tmp')

    # Generar el gráfico
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])  # Aquí puedes poner los datos que necesitas
    ax.set_title('Sample Chart')

    # Guardar el gráfico en un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_path = 'tmp/chart.png'
    with open(chart_path, 'wb') as f:
        f.write(buf.getbuffer())

    # Incluir el gráfico en el HTML
    rendered_html += f'<img src="{chart_path}" alt="Gráfico">'

    pdf_file_path = f'tmp/{result.nombre}_result.pdf'

    # Generar el PDF
    HTML(string=rendered_html).write_pdf(pdf_file_path)

    return send_file(pdf_file_path, as_attachment=True)

@login_required
@admin_permission.require(http_exception=403)
@app.route("/admin-dashboard", methods=['GET', 'POST'])
def admin_dashboard():
  form = UpdatePasswordForm()
  if request.method == 'POST':
    name = request.form['name']
    username = request.form['username']
    password_hash = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
    email = request.form['email']
    telefono = request.form['telefono']
    role_selected = request.form['roles']  # Obtener el rol seleccionado del formulario ('admin' o 'user')

    if role_selected == 'admin':
        roles = db.session.query(Roles).filter_by(name='admin').first()
    else:
        roles = db.session.query(Roles).filter_by(name='user').first()

    # Crear nuevo usuario
    user = User(name=name, username=username,password_hash=password_hash, email=email, telefono=telefono, roles=[roles])
    db.session.add(user)
    db.session.commit()

    flash('Usuario agregado exitosamente!', 'success')
    return redirect(url_for('admin_dashboard'))

  # Obtener todos los usuarios para mostrarlos en el template
  users = User.query.all()
  return render_template('admin_dashboard.html', users=users, form=form)

@login_required
@user_permission.require(http_exception=403)
@app.route("/user-dashboard", methods=['GET', 'POST'])
def user_dashboard():
  form = UpdatePasswordForm()
  return render_template('user_dashboard.html', form=form)


@login_required
@admin_permission.require(http_exception=403)
@app.route("/delete_user/<int:user_id>", methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    db.session.delete(user)
    db.session.commit()

    flash('Usuario eliminado exitosamente!', 'success')
    return redirect(url_for('admin_dashboard'))



@login_required
@user_permission.require(http_exception=403)
@app.route("/update-password/<int:user_id>", methods=['GET', 'POST'])
def update_password(user_id):
    user = User.query.get_or_404(user_id)
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        new_password = form.new_password.data
        new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password_hash = new_password_hash
        db.session.commit()
        flash('Contraseña actualizada exitosamente', 'success')
        return redirect(url_for('admin_dashboard'))
    if form.errors:
        flash('Hubo un error al actualizar la contraseña. Por favor revisa los campos.', 'danger')
    
    return render_template('update_password.html', form=form, user=user)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5001)