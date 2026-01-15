#venv\Scripts\activate
#streamlit run app.py

import streamlit as st
import google.generativeai as genai
import os
import tempfile
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import hashlib
import time

#-------------------------------------------#
# 1. CONFIG. INICIAL                        #
#-------------------------------------------#
#Carga de API Key (en variable de entorno)
load_dotenv()

#SETUP de Pagina
st.set_page_config(
    page_title="FitGenius AI Team - Asistencia de Entrenamiento Personal",
    page_icon="💪",
    layout="centered"
)

#Titulo de Pagina
st.title("💪 FitGenius AI Team")
st.subheader("Entrenamiento Personal Inteligente")

#-----------------------#
# 2. Config Gemini      #
#-----------------------#
#Configuracion de API KEY
try:
    if "GOOGLE_API_KEY" in st.secrets:
        #Tratar de cargar key desde secrets
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.sidebar.success("MODO API REMOTA")
    else:
        #Para desarrollo no-remoto, buscar api local
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            st.sidebar.info("MODO API LOCAL")
except:
    #Opción prueba local
    api_key = os.getenv("GOOGLE_APY_KEY")

#No API -> Error ->
if not api_key:
    st.error("No se encontró GOOGLE_API_KEY")
    st.info("Por favor, agregar API KEY al archivo .env")
    st.stop()

try:
    genai.configure(api_key=api_key)
    st.sidebar.success("Conectado a Google Gemini")
except Exception as e:
    st.error(f"Error al conectar a Gemini: {e}")
    st.stop()

#----------------------#
# 3. PROMPT DE SISTEMA #
#----------------------#

system_prompt = """Eres FitGenius, un entrenador personal y nutricionista certificado con años de experiencia. Tu especialidad es crear rutinas de ejercicio efectivas, y planes dietarios óptimizados.

INSTRUCCIONES:
1. Genera rutinas de ejercicio estructuradas y profesionales
2. Incluye series, repeticiones y descansos
3. Sé específico y técnico, pero con un vocabulario accesible y amistoso
4. Responde SIEMPRE en español
5.Si el usuario no da información suficiente, pregunta por:
    -Objetivos (ganar músculo, perder grasa, definir, etc.)
    -Nivel de experiencia (principiante, intermedio, avanzado)
    -Equipamiento disponible (gimnasio, casa, pesas, peso corporal, etc.)
    -Días disponibles por semana

FORMATO DE RESPUESTA:
-Título claro y conciso de la rutina
-Días de entrenamiento
-Ejercicios con cantidad de series (normales, drop-set, etc.) y repeticiones
-Descansos recomendados
-Consejos de Ejecución

MANTÉN LAS RESPUESTAS ORGANIZADAS, FÁCILES DE SEGUIR POR FAVOR Y DIRECTO AL GRANO!!!

Saluda y presentate de forma breve, NO DEBES DECORAR LA RESPUESTA GENERADA CON DESCRIPCIONES INNECESARIAMENTE LARGAS."""

system_prompt_vision = """Eres FitGenius, un experto en fitness y equipamiento de gimnasio con certificación.

**TUS ESPECIALIDADES:**
1. Identificación de equipos de gimnasio
2. Análisis de técnica en ejercicios
3. Corección de postura y forma durante ejecución
4. Planificación de rutinas con equipos específicos
5. Seguridad y Prevención de lesiones

**CUANDO EL USUARIO SUBA UNA IMAGEN, ANALÍZALA Y HAZ LO SIGUIENTE:**
1. Si se muestra un equipo de gimnasio o un ejercicio, identificalo por su nombre y determina su modo correcto de uso.
2. De ser posible, sugiere alternativas a otros equipos o ejercicios que trabajen los mismos grupos musculares.
3. Si es una persona, comenta cálidamente sobre su estado físico y analiza cuáles podrían ser sus siguientes pasos para mejorarlo (si es posible mejorar).
4. Da consejos de seguridad

**RESPONDE EN ESPAÑOL, usa lenguaje técnico y claro. Solo respuestas cortas.**"""

#-------------------------------------------------#
# 4. Funciones de procesamiento (texto e imagenes)#
#-------------------------------------------------#

#Procesamiento imágenes
def process_image_with_gemini(image_path, user_prompt=""):
    """Envía imagen a Gemini Vision para análisis"""
    try:
        #Cargar imagen
        img = Image.open(image_path)

        #Crear modelo multimodal
        model = genai.GenerativeModel('gemini-2.5-flash')
        #Preparar prompt
        full_prompt = f"{system_prompt_vision}\n\nUsuario pregunta: {user_prompt}\n\nAnaliza esta imagen y proporciona una explicación detallada."
        #Generar respuesta
        response = model.generate_content([full_prompt, img])

        return response.text

    except Exception as e:
        return f"Error al procesar la imagen: {str(e)}"

def get_ai_response(user_message, chat_history=None):
    """Envía mensaje a Gemini y obtiene respuesta"""
    try:
        #Crear modelo
        model = genai.GenerativeModel('gemini-2.5-flash')

        #Preparar el historial de chat
        if chat_history is None:
            chat_history = []

        #Crear contexto
        messages = [system_prompt] + chat_history + [user_message]
        context = "\n".join(messages)

        #Generación de respuestas
        response = model.generate_content(
            messages,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p= 0.8,
                top_k=40,
                max_output_tokens=800,
                #max tokens final 3000
            )
        )
        
        return response.text

    except Exception as e:
        return f"Error al generar respuesta: {str(e)}"
        
#-------------------------------------#
# 5. Intefaz de Usuario con Streamlit #
#-------------------------------------#
#SETUP del historial del chatbox
if "messages" not in st.session_state:
    st.session_state.messages = []
    #Mensaje inicial del chatbox
    st.session_state.messages.append({"role": "assistant", "content": "¡Hola, soy FitGenius! Entrenador Personal con IA. ¿Qué tipo de rutina de ejercicios necesitas hoy?"})

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

#----------------------------------#
# 6. Subida de imágenes en sidebar #
#----------------------------------#
st.sidebar.header("📸 Analizar Imágenes")

# Opción para subir imagen
uploaded_file = st.sidebar.file_uploader(
    "Sube una imagen de equipo o ejercicio",
    type=['jpg', 'jpeg', 'png', 'webp'],
    help="Toma una foto de un equipo de gimnasio o ejercicio para análisis"
)

if uploaded_file is not None:
    # Mostrar vista previa
    st.sidebar.image(uploaded_file, caption="Vista previa", use_column_width=True)
    
    # Campo para pregunta adicional sobre la imagen
    image_question = st.sidebar.text_input(
        "¿Qué quieres saber sobre esta imagen?",
        placeholder="Ej: ¿Cómo uso este equipo? ¿Es para principiantes?"
    )
    
    # Botón para analizar imagen
    if st.sidebar.button("🔍 Analizar Imagen", use_container_width=True):
        # Guardar imagen temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Mostrar en chat que se subió imagen
        st.session_state.messages.append({
            "role": "user", 
            "content": f"📸 [Imagen subida: {uploaded_file.name}]" + (f"\nPregunta: {image_question}" if image_question else "")
        })
        
        with st.chat_message("user"):
            st.write(f"📸 Subí una imagen: {uploaded_file.name}")
            if image_question:
                st.write(f"❓ {image_question}")
        
        # Procesar imagen
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analizando imagen..."):
                try:
                    # Obtener respuesta de Gemini Vision
                    img_response = process_image_with_gemini(tmp_path, image_question)
                    
                    # Mostrar respuesta
                    st.write(img_response)
                    
                    # Guardar en historial
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"**Análisis de imagen:**\n\n{img_response}"
                    })
                    
                    # Limpiar archivo temporal
                    os.unlink(tmp_path)
                    
                except Exception as e:
                    st.error(f"Error al procesar imagen: {e}")

#-------------------------------#
# 7. Interfaz de chat principal #
#-------------------------------#
# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Verificar si es una imagen
        if isinstance(message["content"], str) and message["content"].startswith("📸"):
            # Extraer nombre de archivo
            lines = message["content"].split('\n')
            st.write(lines[0])
            if len(lines) > 1:
                st.write(lines[1])
        else:
            st.write(message["content"])

# Input de texto para chat
user_input = st.chat_input("Escribe tu mensaje o pregunta aquí...")

if user_input:
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.write(user_input)
    
    # Agregar al historial
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append(f"Usuario: {user_input}")

    #Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("🤔 Pensando..."):
            try:
                #Obtener respuesta de Gemini
                assistant_response = get_ai_response(
                    f"Usuario: {user_input}",
                    st.session_state.chat_history
                )

                #Añadir respuesta al historial
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                st.session_state.chat_history.append(f"Asistente: {assistant_response}")

                #Forzar rerun
                st.rerun()

            except Exception as e:
                error_msg=f"Error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.rerun()

#-------------------#
# 8. Barra lateral #
#-------------------#

with st.sidebar:
    st.divider()
    st.header("⚙ Configuración")

    #Botón nueva conversación
    if st.button("🔃 Nueva Conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.messages.append({"role": "assistant", "content": "¡Hola, soy FitGenius! Entrenador Personal con IA. ¿Qué tipo de rutina de ejercicios necesitas hoy?"})
        st.rerun()

    st.divider()

    #Estadísticas
    st.subheader("Estadísticas")
    st.write(f"**Mensajes:** {len(st.session_state.messages)}")
    st.write(f"**Imágenes analizadas:** {sum(1 for msg in st.session_state.messages if isinstance(msg.get('content'), str) and msg['content'].startswith('data:image'))}")

    st.divider()

    #Ejemplos rápidos
    st.subheader("**Ejemplos de uso:**")

    st.subheader("💬 Preguntas de texto:")
    example_texts = [
        "Crear rutina para principiante en casa",
        "Cómo hacer sentadillas correctamente",
        "Rutina para ganar músculo en gimnasio (4 días)"
    ]

    st.divider()

    #Información
    st.subheader("Cómo usar imágenes:")
    st.write("1. Haz clic en 📷 en el chat")
    st.write("2. Selecciona una imagen")
    st.write("3. Haz una pregunta (opcional)")
    st.write("4. Presiona 'Analizar")

    st.divider()

    #Info del modelo Gemini Usado
    st.header("Información Técnica")
    st.write("**MODELO:** Gemini 2.5 Flash")
    st.write("Características:")
    st.write("· Análisis de imágenes")
    st.write("· Rutinas personalizadas")
    st.write("· Correción de técnica")
    st.write("**ESTADO:** CONECTADO")

#-------------------#
# 11. Pie de Página #
#-------------------#

st.divider()
st.caption("FitGenius AI V1.8 - Desarrollado con Google Gemini API | Proyecto de IA")
st.caption("Aplicación desarrollada para fines de aprendizaje por AJLM, UGMA 2025.")

