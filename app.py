import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import base64
import shutil
from datetime import datetime
from pathlib import Path
import io
from PIL import Image

# -----------------------------
# CONFIGURACIÓN Y DIRECTORIOS
# -----------------------------
st.set_page_config(page_title="Ethnophony", page_icon="logo_1.png", layout="wide")

PROJECTS_DIR = Path("projects")
ARCHIVE_DIR = Path("archives")
PROJECTS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

TEMPLATES = {
    "Paisaje sonoro": ["hora", "ambiente", "actividad", "densidad_sonora"],
    "Ruta sonora": ["orden", "duracion", "transicion"],
    "Memoria sonora": ["informante", "edad", "evento_recordado"],
    "Archivo georreferenciado": ["coleccion", "id_archivo", "formato", "derechos"]
}

# Inicialización de estados
if "show_form" not in st.session_state:
    st.session_state.show_form = False
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

# -----------------------------
# FUNCIONES DE DATOS
# -----------------------------
def load_project_data(p_path):
    data_path = p_path / "data.json"
    if data_path.exists():
        with open(data_path, "r") as f:
            content = json.load(f)
            if isinstance(content, list):
                return {"metadata": {"description": ""}, "points": content}
            return content
    return {"metadata": {"description": ""}, "points": []}

def save_project_data(p_path, data):
    with open(p_path / "data.json", "w") as f:
        json.dump(data, f, indent=4)

# -----------------------------
# BARRA LATERAL: IDENTIDAD Y SECCIONES
# -----------------------------
logo_path = Path("logo.png")
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)

st.sidebar.title("📍 Ethnophony")
st.sidebar.caption("Sistema para la creación de cartografías sonoras")
modo = st.sidebar.radio("Modo de uso", ["🛠️ Edición", "👁️ Visualización"])

st.sidebar.divider()

# Control de tamaño de la ventana del mapa
st.sidebar.subheader("📐 Dimensiones de Interfaz")
map_height = st.sidebar.slider("Altura del mapa (píxeles)", min_value=400, max_value=1200, value=650, step=50)

st.sidebar.divider()

# GESTIÓN DE PROYECTOS
activos = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()]
archivados = [p.name for p in ARCHIVE_DIR.iterdir() if p.is_dir()]

tabs = st.sidebar.tabs(["📁 Activos", "📦 Archivados", "✨ Nuevo"])

with tabs[0]:
    current_project = st.selectbox("Seleccionar Proyecto", [""] + activos)
    if current_project and st.button("📦 Archivar Proyecto"):
        shutil.move(PROJECTS_DIR / current_project, ARCHIVE_DIR / current_project)
        st.rerun()

with tabs[1]:
    proj_arch = st.selectbox("Recuperar", [""] + archivados)
    if proj_arch and st.button("📤 Desarchivar"):
        shutil.move(ARCHIVE_DIR / proj_arch, PROJECTS_DIR / proj_arch)
        st.rerun()

with tabs[2]:
    nuevo = st.text_input("Nombre del nuevo proyecto")
    if st.button("Crear Proyecto") and nuevo:
        p_path = PROJECTS_DIR / nuevo
        (p_path / "media").mkdir(parents=True, exist_ok=True)
        save_project_data(p_path, {"metadata": {"description": ""}, "points": []})
        st.rerun()

# SECCIÓN DE AYUDA Y CRÉDITOS
st.sidebar.divider()
with st.sidebar.expander("❓ Ayuda y FAQ"):
    st.markdown("""
    **¿Cómo editar un punto?**
    En la lista de puntos bajo el mapa, pulsa el botón **✏️**. El formulario de la derecha se llenará con los datos actuales.
    
    **Dimensiones del mapa:**
    Usa el control deslizante de la barra lateral para adaptar la ventana geográfica a tu resolución de pantalla.
    """)

with st.sidebar.expander("🎖️ Créditos"):
    st.markdown("""
    **Ethnophony v1.4**
    Herramienta profesional de cartografía sonora.
    - Python 3.12 / Streamlit
    - Folium / Leaflet GIS
    """)

if not current_project:
    st.info("Comienza tu propio paisaje sonoro. En la barra lateral selecciona un proyecto existente o crea uno nuevo.")
    st.stop()

# Cargar estructura de datos del proyecto activo
project_data = load_project_data(PROJECTS_DIR / current_project)
project_desc = project_data["metadata"].get("description", "")
points = project_data["points"]

# -----------------------------
# MOTOR DE MAPA
# -----------------------------
def create_map(data, proj_title, proj_desc, center=[20, 0], zoom=2):
    m = folium.Map(location=center, zoom_start=zoom, tiles=None)
    
    # SOLUCIÓN: Capas base con 'show' controlado para evitar conflictos visuales
    folium.TileLayer('openstreetmap', name='Mapa de Calles (OSM)', overlay=False, show=False).add_to(m)
    folium.TileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', 
                     attr='OpenTopoMap', name='Topografía/Relieve', overlay=False, show=False).add_to(m)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite',
        name='Satélite (Predeterminado)',
        overlay=False,
        show=True
    ).add_to(m)

    # Cartela flotante con Título y Descripción del Proyecto (Inyectado en HTML final)
    title_box_html = f"""
    <div style="position: fixed; 
                top: 20px; left: 70px; width: 210px; height: auto; 
                background-color: rgba(255, 255, 255, 0.92); z-index:9999; 
                border-radius: 8px; padding: 14px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.25);
                font-family: sans-serif; pointer-events: none;">
        <h3 style="margin:0 0 6px 0; color:#1a252f; font-size:15px; font-weight:bold;">🌍 {proj_title}</h3>
        <p style="margin:0; color:#555; font-size:12px; line-height:1.4; font-style:italic;">{proj_desc if proj_desc else 'Sin descripción general registrada.'}</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_box_html))

    # Marcadores
    for p in data:
        media_html = ""
        if "audio" in p.get("media", {}) and Path(p["media"]["audio"]).exists():
            with open(p["media"]["audio"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                media_html += f'<audio controls style="width:100%"><source src="data:audio/mp3;base64,{b64}"></audio>'
        
        if "image" in p.get("media", {}) and Path(p["media"]["image"]).exists():
            with open(p["media"]["image"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                media_html += f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:5px; margin-top:5px;">'

        # Construcción de Popups estructurados
        extra_info = "".join([f"<li><b>{k.replace('_',' ').title()}:</b> {v}</li>" for k, v in p.get("extra", {}).items() if v])
        desc_html = f"<p style='font-style: italic; color: #34495e; margin: 6px 0;'>{p.get('description', '')}</p>" if p.get('description') else ""
        
        # Inclusión de Metadatos Técnicos
        tech_html = ""
        if p.get("equipment"): tech_html += f"<li><b>Equipo:</b> {p['equipment']}</li>"
        if p.get("tech_notes"): tech_html += f"<li><b>Notas Técnicas:</b> {p['tech_notes']}</li>"

        popup_content = f"""
        <div style="font-family: sans-serif; width: 230px; line-height: 1.4;">
            <h4 style="margin:0 0 5px 0; color:#2c3e50; font-size:14px;">{p['title']}</h4>
            {desc_html}
            {media_html}
            <ul style="font-size:11px; margin-top:10px; padding-left:15px; color:#555;">
                {extra_info}
                {tech_html}
            </ul>
        </div>
        """
        folium.Marker(
            [p["lat"], p["lon"]],
            popup=folium.Popup(popup_content, max_width=260),
            icon=folium.Icon(color="cadetblue", icon="music", prefix="fa")
        ).add_to(m)

    folium.LayerControl(collapsed=False, position='topright').add_to(m)
    return m

# -----------------------------
# INTERFAZ PRINCIPAL
# -----------------------------
avg_lat = sum(p["lat"] for p in points) / len(points) if points else 20
avg_lon = sum(p["lon"] for p in points) / len(points) if points else 0
main_map = create_map(points, current_project, project_desc, center=[avg_lat, avg_lon], zoom=4 if points else 2)

if modo == "👁️ Visualización":
    st.title(f"👁️ Paisaje Sonoro: {current_project}")
    if project_desc:
        st.caption(f"**Descripción del Proyecto:** {project_desc}")
    st_folium(main_map, use_container_width=True, height=map_height, returned_objects=[])

else:
    st.title(f"🛠️ Editor Ethnophony: {current_project}")
    
    with st.expander("📝 Configuración de Información General del Proyecto", expanded=not bool(project_desc)):
        new_desc = st.text_area("Descripción macro del proyecto o campaña de investigación:", value=project_desc)
        if st.button("💾 Guardar Descripción General"):
            project_data["metadata"]["description"] = new_desc
            save_project_data(PROJECTS_DIR / current_project, project_data)
            st.success("Información del proyecto actualizada con éxito.")
            st.rerun()

    st.divider()

    if not st.session_state.show_form:
        if st.button("➕ Añadir nuevo punto", type="primary"):
            st.session_state.editing_id = None
            st.session_state.show_form = True
            st.rerun()
    
    col_map, col_info = st.columns([2, 1])

    with col_map:
        st.caption("Haz clic en el mapa para capturar coordenadas")
        map_res = st_folium(main_map, use_container_width=True, height=map_height)
        
        if points:
            st.subheader("📋 Inventario de puntos")
            for p in points:
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                c1.write(f"**{p['title']}**")
                c2.write(f"{p['lat']:.4f}, {p['lon']:.4f}")
                if c3.button("✏️", key=f"edit_{p['id']}", help="Editar entrada"):
                    st.session_state.editing_id = p['id']
                    st.session_state.show_form = True
                    st.rerun()
                if c4.button("🗑️", key=f"del_{p['id']}", help="Borrar entrada"):
                    for m_path in p.get("media", {}).values():
                        if Path(m_path).exists(): Path(m_path).unlink()
                    project_data["points"] = [x for x in points if x["id"] != p["id"]]
                    save_project_data(PROJECTS_DIR / current_project, project_data)
                    st.rerun()

    with col_info:
        if st.session_state.show_form:
            edit_data = next((x for x in points if x["id"] == st.session_state.editing_id), None) if st.session_state.editing_id else None
            
            st.subheader("📝 " + ("Editar Entrada" if edit_data else "Nueva Entrada"))
            if st.button("Cancelar"):
                st.session_state.show_form = False
                st.session_state.editing_id = None
                st.rerun()
            
            if map_res.get("last_clicked"):
                def_lat, def_lon = map_res["last_clicked"]["lat"], map_res["last_clicked"]["lng"]
            elif edit_data:
                def_lat, def_lon = edit_data["lat"], edit_data["lon"]
            else:
                def_lat, def_lon = 0.0, 0.0

            f_title = st.text_input("Título", value=edit_data["title"] if edit_data else "")
            f_desc = st.text_area("Descripción / Notas de campo del punto", value=edit_data.get("description", "") if edit_data else "")
            
            st.markdown("**⚙️ Metadatos Técnicos**")
            f_equipment = st.text_input("Equipo de captura (Ej: Tascam DR-40, Mic Omnidireccional)", value=edit_data.get("equipment", "") if edit_data else "")
            f_tech_notes = st.text_input("Notas de formato (Ej: WAV Stereo 48kHz / 24bit)", value=edit_data.get("tech_notes", "") if edit_data else "")
            st.markdown("---")
            
            f_lat = st.number_input("Latitud", value=float(def_lat), format="%.6f")
            f_lon = st.number_input("Longitud", value=float(def_lon), format="%.6f")
            
            temp_idx = list(TEMPLATES.keys()).index(edit_data["template"]) if edit_data else 0
            f_temp = st.selectbox("Plantilla conceptual", list(TEMPLATES.keys()), index=temp_idx)
            
            extra_vals = {}
            for field in TEMPLATES[f_temp]:
                val = edit_data["extra"].get(field, "") if edit_data and edit_data["template"] == f_temp else ""
                extra_vals[field] = st.text_input(field, value=val)
            
            st.caption("Subir nuevos archivos reemplazará los anteriores.")
            f_audio = st.file_uploader("Audio", type=["mp3", "wav"])
            f_img = st.file_uploader("Imagen", type=["jpg", "png"])
            
            if st.button("💾 Guardar Cambios", use_container_width=True):
                if f_title:
                    pid = edit_data["id"] if edit_data else datetime.now().strftime("%Y%m%d%H%M%S")
                    media_dict = edit_data["media"].copy() if edit_data else {}
                    
                    for k, f in [("audio", f_audio), ("image", f_img)]:
                        if f:
                            if k in media_dict and Path(media_dict[k]).exists(): Path(media_dict[k]).unlink()
                            p_media = PROJECTS_DIR / current_project / "media" / f"{pid}_{f.name}"
                            with open(p_media, "wb") as b: b.write(f.getbuffer())
                            media_dict[k] = str(p_media)
                    
                    new_entry = {
                        "id": pid, "title": f_title, "description": f_desc,
                        "equipment": f_equipment, "tech_notes": f_tech_notes,
                        "lat": f_lat, "lon": f_lon, "template": f_temp, 
                        "extra": extra_vals, "media": media_dict
                    }
                    
                    if edit_data:
                        idx = next(i for i, x in enumerate(points) if x["id"] == pid)
                        points[idx] = new_entry
                    else:
                        points.append(new_entry)
                    
                    project_data["points"] = points
                    save_project_data(PROJECTS_DIR / current_project, project_data)
                    st.session_state.show_form = False
                    st.session_state.editing_id = None
                    st.rerun()

# -----------------------------
# EXPORTACIÓN
# -----------------------------
st.sidebar.divider()
html_buf = io.BytesIO()
main_map.save(html_buf, close_file=False)
st.sidebar.download_button("🌐 Descargar Mapa HTML", data=html_buf.getvalue(), 
                           file_name=f"{current_project}.html", mime="text/html", use_container_width=True)
