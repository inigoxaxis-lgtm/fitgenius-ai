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
import base64  
from io import BytesIO
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

#-----------------------------------#
# 3. PROMPT DE SISTEMA EXPERTO      #
#-----------------------------------#

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
        messages = []
        messages.append({"role": "user", "parts": [f"Contexto: {system_prompt}"]})

        # Agregar historial de chat
        for msg in chat_history:
            if "Usuario:" in msg:
                messages.append({"role": "user", "parts": [msg.replace("Usuario: ", "")]})
            elif "Asistente:" in msg:
                messages.append({"role": "model", "parts": [msg.replace("Asistente: ", "")]})

         # Agregar mensaje actual
        messages.append({"role": "user", "parts": [user_message]})

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

def image_to_base64(image):
    """Convierte imagen a base64 para mostrarla en el chat"""
    buffered = BytesIO()
    if image.mode in ("RGBA", "P", "LA"):
        image = image.convert("RGB")
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()
        
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


#-----------------------------------------#
# 6. Input de Chat + Subida de imágenes #
#-----------------------------------------#
#Crear container para el input box
chat_container = st.container()

with chat_container:
    #Dividir en una sección textual y otra para botón de carga
    col1, col2 = st.columns([6, 1])
    with col1:
        #Input de texto
        user_input = st.chat_input(
            "Escribe tu mensaje aquí...",
            key="main_chat_input"
        )

    with col2:
        #Botón para subir imágenes
        st.markdown(
            """
            <style>
            .upload-btn {
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                cursor: pointer;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        #El botón con "File uploader" en hidden
        upload_clicked = st.button("📷", key="upload_btn", help="Subir imagen")

        #Mostrar "File uploader" si se clickea al botón
        if upload_clicked:
            uploaded_file = st.file_uploader(
                "",
                type=['jpg', 'jpeg', 'png', 'webp'],
                label_visibility="collapsed",
                key="inline_image_uploader"
            )
        else:
            uploaded_file = None

#---------------------------#
# 8. Procesamiento de texto #
#---------------------------#

if user_input and user_input.strip():
    #Añadir mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append(f"Usuario: {user_input}")

    #Generar respuesta
    with st.spinner("🤔 Pensando..."):
        try:
            assistant_response = get_ai_response(
                f"Usuario: {user_input}",
                st.session_state.chat_history
            )

            #Añadir respuesta al historial
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            st.session_state.chat_history.append(f"Asistente: {assistant_response}")

            #Forzar rerun

        except Exception as e:
            error_msg=f"Error: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.rerun()

#----------------------------#
# 9. Procesamiento de imagen #
#----------------------------#
#Verificar si hay una imagen subida en el inline_image_uploader
if 'inline_image_uploader' in st.session_state and st.session_state.inline_image_uploader is not None:
    uploaded_file = st.session_state.inline_image_uploader

    if uploaded_file is not None:
        #Convertir imagen a b64
        image = Image.open(uploaded_file)
        image_base64 = f"data:image/jpeg;base64,{image_to_base64(image)}"

        #Añadir imagen a historial
        st.session_state.messages.append({
            "role": "user",
            "content": image_base64,
            "type": "image"
        })

        #Crear área para pregunta sobre la imagen
        st.info("📷 **Imagen cargada.** ¿Qué quieres preguntar sobre esta foto?")

        #Input de texto para consulta de imagen
        col1, col2 = st.columns([3, 1])
        with col1:
            image_question = st.text_input(
                "Pregunta sobre la imagen (opcional):",
                placeholder="Ej: ¿Cómo uso este equipo correctamente?",
                key="image_question_input"
            )
        with col2:
            analyze_btn = st.button("🔍 Analizar", key="analyze_image_btn")

        #Procesar imagen al presionar botón
        if analyze_btn:
            # Guardar imagen temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            #Procesar imagen
            with st.spinner("🔍 Analizando imagen..."):
                try:
                    #Añadir pregunta SI existe
                    if image_question:
                        st.session_state.messages.append({
                            "role": "user",
                            "content": f"Pregunta sobre la imagen: {image_question}"
                        })

                    #Obtener respuesta
                    img_response = process_image_with_gemini(tmp_path, image_question)

                    #Guardar en historial
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"**Análisis de imagen:**\n\n{img_response}"
                    })

                    #Limpiar uploader
                    st.session_state.inline_image_uploader = None

                    #Limpiar archivo temporal
                    os.unlink(tmp_path)

                    st.rerun()

                except Exception as e:
                    st.error(f"Error al procesar imagen: {e}")

#-------------------#
# 10. Barra lateral #
#-------------------#

with st.sidebar:
    st.header("⚙ Configuración")

    #Botón nueva conversación
    if st.button("🔃 Nueva Conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.messages.append({"role": "assistant", "content": "¡Hola, soy FitGenius! Entrenador Personal con IA. ¿Qué tipo de rutina de ejercicios necesitas hoy?"})
        st.rerun()

    st.divider()

    #Estadísticasz
    st.subheader("Estadísticas")
    st.write(f"**Mensajes:** {len(st.session_state.messages)}")
    st.write(f"**Imágenes analizadas:** {sum(1 for msg in st.session_state.messages if isinstance(msg.get('content'), str) and msg['content'].startswith('data:image'))}")

    st.divider()

    #Ejemplos rápidos
    st.subheader("**Ejemplos de uso:**")

    if st.button("Rutina para Principiantes", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Quiero una rutina para ganar músculo en gimnasio, nivel principiante, 4 días por semana"
        })
        st.rerun()

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
st.caption("FitGenius AI V2.0 - Desarrollado con Google Gemini API | Proyecto de IA")
st.caption("Aplicación desarrollada para fines de aprendizaje por AJLM, UGMA 2025.")

