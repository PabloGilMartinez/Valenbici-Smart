import streamlit as st
import pandas as pd
import joblib
import folium
import requests
import os          # <--- NUEVO
import gdown       # <--- NUEVO
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
import datetime

# -----------------------
# DICCIONARIO DE IDIOMAS
# -----------------------
TRANSLATIONS = {
    "Español": {
        "title_desc": "La forma inteligente de moverte por Valencia. ValenBici Smart te permite planificar tus rutas en bicicleta y saber con antelación si habrá bicis o espacios disponibles en cada estación para que te desplaces sin sorpresas.",
        "file_error": "⚠️ No se encontró el archivo 'título.png'. Por favor, verifica la ruta.",
        "sidebar_header": "Preparación del viaje",
        "origin_station": "Estación de origen",
        "dest_station": "Estación de destino",
        "date": "Fecha",
        "departure_time": "**Hora de salida**",
        "hour": "Hora",
        "minute": "Minuto",
        "heavy_rain": "Lluvia fuerte",
        "rain": "Lluvia",
        "clear": "Despejado",
        "clear_night": "Noche despejada",
        "bikes_origin": "Bicicletas Disponibles (Origen)",
        "slots_dest": "Plazas Disponibles (Destino)",
        "trip_details": "Detalles del Trayecto",
        "route_dist": "Distancia de la ruta",
        "est_time": "Tiempo estimado",
        "eta": "Hora de llegada",
        "est_cal": "Calorías estimadas",
        "route_map": "Mapa de Ruta",
        "recommended": "RECOMENDADA",
        "origin": "ORIGEN",
        "dest": "DESTINO",
        "rain_alert": "🌧️ **Aviso Meteorológico:** Parece que va a llover, ten cuidado en tu ruta.",
        "low_bikes": "⚠️ Habrá pocas bicicletas en el origen. Te recomendamos buscar en una estación cercana.",
        "low_slots": "🚨 Habrá pocos huecos libres en el destino. ¡Es posible que no encuentres dónde aparcar!",
        "alt_header": "Otras estaciones cercanas para aparcar (A menos de 1km)",
        "no_alt": "No hay estaciones a menos de 1km de distancia.",
        "col_slots": "Huecos Libres Estimados",
        "col_dist": "Distancia (km)",
        "col_dir": "Dirección"
    },
    "English": {
        "title_desc": "The smart way to move around Valencia. Smart ValenBici allows you to plan your bike routes and know in advance if there will be bikes or parking spots available at each station so you can commute without surprises.",
        "file_error": "⚠️ 'título.png' file not found. Please check the path.",
        "sidebar_header": "Trip Preparation",
        "origin_station": "Origin Station",
        "dest_station": "Destination Station",
        "date": "Date",
        "departure_time": "**Departure Time**",
        "hour": "Hour",
        "minute": "Minute",
        "heavy_rain": "Heavy rain",
        "rain": "Rain",
        "clear": "Clear",
        "clear_night": "Clear night",
        "bikes_origin": "Available Bikes (Origin)",
        "slots_dest": "Available Spots (Destination)",
        "trip_details": "Trip Details",
        "route_dist": "Route Distance",
        "est_time": "Estimated Time",
        "eta": "Estimated Time of Arrival",
        "est_cal": "Estimated Calories",
        "route_map": "Route Map",
        "recommended": "RECOMMENDED",
        "origin": "ORIGIN",
        "dest": "DESTINATION",
        "rain_alert": "🌧️ **Weather Warning:** It looks like it's going to rain, be careful on your route.",
        "low_bikes": "⚠️ There will be few bikes at the origin. We recommend looking at a nearby station.",
        "low_slots": "🚨 There will be few free spots at the destination. You might not find a place to park!",
        "alt_header": "Other nearby stations to park (Under 1km)",
        "no_alt": "There are no stations within a 1km distance.",
        "col_slots": "Est. Available Spots",
        "col_dist": "Distance (km)",
        "col_dir": "Address"
    }
}

# -----------------------
# CONSTANTES DE COLOR
# -----------------------
COLOR_ROSA = "#ff66c4"
COLOR_AZUL = "#004ea7"

# -----------------------
# FUNCIONES AUXILIARES
# -----------------------
def haversine(lon1, lat1, lon2, lat2):
    """Calcula la distancia en km entre dos puntos geográficos"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radio de la Tierra en km
    return c * r

@st.cache_data
def get_bike_route(lat_origen, lon_origen, lat_destino, lon_destino):
    """Obtiene la ruta real en bici, distancia y duración usando la API de OSRM."""
    url = f"http://router.project-osrm.org/route/v1/bicycle/{lon_origen},{lat_origen};{lon_destino},{lat_destino}?overview=full&geometries=geojson"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            route = data['routes'][0]
            
            # Extraemos coordenadas
            coords = route['geometry']['coordinates']
            ruta = [[coord[1], coord[0]] for coord in coords]
            
            # Extraemos distancia (metros) y duración (segundos)
            distancia_m = route['distance']
            duracion_s = route['duration']
            
            return ruta, distancia_m, duracion_s
    except Exception as e:
        print(f"Error al obtener la ruta: {e}")
    
    # Fallback: Si la API falla, devolvemos una línea recta y 0 en métricas
    return [[lat_origen, lon_origen], [lat_destino, lon_destino]], 0.0, 0.0

@st.cache_data
def get_weather_forecast(lat, lon, fecha, hora):
    """Obtiene la temperatura y precipitación esperada para una fecha y hora dadas."""
    fecha_str = fecha.strftime('%Y-%m-%d')
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation&start_date={fecha_str}&end_date={fecha_str}&timezone=Europe%2FMadrid"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            hora_str = f"{fecha_str}T{hora:02d}:00"
            
            if hora_str in data['hourly']['time']:
                idx = data['hourly']['time'].index(hora_str)
                temp = data['hourly']['temperature_2m'][idx]
                precip = data['hourly']['precipitation'][idx]
                return temp, precip
    except Exception as e:
        print(f"Error al obtener el clima: {e}")
        
    return 20.0, 0.0 # Fallback si falla la API

# Guardar en caché para que cargue rápido
@st.cache_data
def load_data():
    df_estaciones = pd.read_csv("estaciones.csv")
    df_promedios = pd.read_csv("promedios_historicos.csv")
    return df_estaciones, df_promedios

# -----------------------
# CARGA DE DATOS Y MODELOS
# -----------------------
st.set_page_config(page_title="Smart Valenbisi", layout="wide")

df, df_promedios = load_data()

# --- NUEVO CÓDIGO PARA DESCARGAR MODELOS DESDE DRIVE ---
@st.cache_resource
def cargar_modelos_drive():
    # 1. Modelo de Bicis
    id_bicis = '1l4SysWc7TSoKfpqW2omc7HGKXHs20lxj'  # <--- CAMBIA ESTO
    url_bicis = f'https://drive.google.com/uc?id={id_bicis}'
    ruta_bicis = 'model_bicis.pkl'
    
    if not os.path.exists(ruta_bicis):
        with st.spinner('Descargando Modelo de Bicis desde Google Drive (solo la primera vez)...'):
            gdown.download(url_bicis, ruta_bicis, quiet=False)
            
    # 2. Modelo de Huecos
    id_huecos = '1pIqzwQVew8XCCT4MIZO_v_XBpZawAyoj' # <--- CAMBIA ESTO
    url_huecos = f'https://drive.google.com/uc?id={id_huecos}'
    ruta_huecos = 'model_huecos.pkl'
    
    if not os.path.exists(ruta_huecos):
        with st.spinner('Descargando Modelo de Huecos...'):
            gdown.download(url_huecos, ruta_huecos, quiet=False)

    # Cargar en memoria
    mod_bicis = joblib.load(ruta_bicis)
    mod_huecos = joblib.load(ruta_huecos)
    
    return mod_bicis, mod_huecos

# Ejecutamos la función
model_bicis, model_huecos = cargar_modelos_drive()
# --------------------------------------------------------

# -----------------------
# BARRA LATERAL (SELECTOR DE IDIOMA Y MENÚ)
# -----------------------

idioma_seleccionado = st.sidebar.radio("Elige tu idioma", ["Español", "English"], label_visibility="collapsed")
t = TRANSLATIONS[idioma_seleccionado] # Instancia de traducción actual

st.sidebar.markdown("---")

# -----------------------
# TÍTULO PRINCIPAL (LOGO CENTRADO)
# -----------------------
col_logo1, col_logo2, col_logo3 = st.columns([1, 3, 1])

with col_logo2:
    try:
        st.image("título.png", use_container_width=True)
    except FileNotFoundError:
        st.error(t["file_error"])

st.write(f"<div style='text-align: center;'>{t['title_desc']}</div>", unsafe_allow_html=True)
st.markdown("---")


clima_top = st.sidebar.container()

st.sidebar.header(t["sidebar_header"])

estaciones = sorted(df["direccion"].unique())

origen = st.sidebar.selectbox(t["origin_station"], estaciones)
destino = st.sidebar.selectbox(t["dest_station"], estaciones)
fecha = st.sidebar.date_input(t["date"], value=datetime.date.today())

st.sidebar.markdown(t["departure_time"])
col_h, col_m = st.sidebar.columns(2)

with col_h:
    hora_manual = st.number_input(t["hour"], min_value=0, max_value=23, value=12, step=1)
with col_m:
    minuto_manual = st.number_input(t["minute"], min_value=0, max_value=59, value=0, step=1)

hora_salida = datetime.time(hora_manual, minuto_manual)
hora = hora_salida.hour

# --- LÓGICA DE MODO OSCURO CON TRANSICIÓN ---
es_noche = hora < 7 or hora >= 20

bg_color = "#1a1c23" if es_noche else "#ffffff"
sidebar_color = "#121318" if es_noche else "#f0f2f6"
text_color = "#f0f2f6" if es_noche else "#31333F"

css_dinamico = f"""
<style>
    [data-testid="stAppViewContainer"] {{
        background-color: {bg_color};
        transition: background-color 0.8s ease-in-out;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: {sidebar_color};
        transition: background-color 0.8s ease-in-out;
    }}
    
    h1, h2, h3, h4, p, label, .stMarkdown, .stText {{
        color: {text_color} !important;
        transition: color 0.8s ease-in-out;
    }}

    [data-testid="stMetricValue"] div {{
        color: {text_color} !important;
        transition: color 0.8s ease-in-out;
    }}
    [data-testid="stMetricLabel"] div p {{
        color: {text_color} !important;
        transition: color 0.8s ease-in-out;
    }}
    
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0);
    }}
    
    iframe {{
        animation: fadeIn 0.8s ease-in-out;
    }}
    
    @keyframes fadeIn {{
        0% {{ opacity: 0.5; }}
        100% {{ opacity: 1; }}
    }}
</style>
"""
st.markdown(css_dinamico, unsafe_allow_html=True)

# -----------------------
# INFORMACIÓN DE LAS ESTACIONES
# -----------------------
est_origen = df[df["direccion"] == origen].iloc[0]
est_destino = df[df["direccion"] == destino].iloc[0]

# -----------------------
# FEATURES DEL MODELO Y CLIMA
# -----------------------
dia_semana = fecha.weekday()
mes = fecha.month

temp_esperada, precip_esperada = get_weather_forecast(
    est_origen["latitud"], est_origen["longitud"], fecha, hora
)

if precip_esperada > 2.0:
    emoji_clima = "⛈️"
    desc_clima = f"{t['heavy_rain']} ({precip_esperada} mm)"
elif precip_esperada > 0.1:
    emoji_clima = "🌧️"
    desc_clima = f"{t['rain']} ({precip_esperada} mm)"
else:
    if 7 <= hora <= 20:
        emoji_clima = "☀️"
        desc_clima = t["clear"]
    else:
        emoji_clima = "🌙"
        desc_clima = t["clear_night"]

with clima_top:
    st.markdown(f"<h1 style='text-align: center; margin-bottom: 0px; font-size: 3rem;'>{emoji_clima} {temp_esperada}°C</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray; margin-top: 0px;'>{desc_clima}</p>", unsafe_allow_html=True)
    st.markdown("---")

filtro_origen = (
    (df_promedios["numero"] == est_origen["numero"]) & 
    (df_promedios["hora"] == hora) & 
    (df_promedios["dia_semana"] == dia_semana) & 
    (df_promedios["mes"] == mes)
)

hist_bicis = df_promedios.loc[filtro_origen, "media_hist_bicis"].values[0] if not df_promedios[filtro_origen].empty else 0

filtro_destino = (
    (df_promedios["numero"] == est_destino["numero"]) & 
    (df_promedios["hora"] == hora) & 
    (df_promedios["dia_semana"] == dia_semana) & 
    (df_promedios["mes"] == mes)
)

hist_huecos = df_promedios.loc[filtro_destino, "media_hist_huecos"].values[0] if not df_promedios[filtro_destino].empty else 0

X_origen = pd.DataFrame([{
    "numero": est_origen["numero"],
    "hora": hora,
    "dia_semana": dia_semana,
    "mes": mes,
    "temperatura": temp_esperada,
    "precipitacion": precip_esperada,
    "media_hist_bicis": hist_bicis
}])

X_destino = pd.DataFrame([{
    "numero": est_destino["numero"],
    "hora": hora,
    "dia_semana": dia_semana,
    "mes": mes,
    "temperatura": temp_esperada,
    "precipitacion": precip_esperada,
    "media_hist_huecos": hist_huecos
}])

# -----------------------
# PREDICCIONES
# -----------------------
bicis_pred = max(0, model_bicis.predict(X_origen)[0])
huecos_pred = max(0, model_huecos.predict(X_destino)[0])

# -----------------------
# CÁLCULO DE ALTERNATIVAS CERCANAS
# -----------------------
alternativas = None
if huecos_pred < 3:
    df['distancia_km'] = df.apply(lambda row: haversine(est_destino['longitud'], est_destino['latitud'], row['longitud'], row['latitud']), axis=1)
    cercanas = df[(df['distancia_km'] < 1.0) & (df['direccion'] != destino)].copy()
    
    if not cercanas.empty:
        hist_huecos_cercanas = []
        for num in cercanas["numero"]:
            filtro = (df_promedios["numero"] == num) & (df_promedios["hora"] == hora) & (df_promedios["dia_semana"] == dia_semana) & (df_promedios["mes"] == mes)
            if not df_promedios[filtro].empty:
                hist_huecos_cercanas.append(df_promedios.loc[filtro, "media_hist_huecos"].values[0])
            else:
                hist_huecos_cercanas.append(0)

        X_cercanas = pd.DataFrame({
            "numero": cercanas["numero"],
            "hora": hora,
            "dia_semana": dia_semana,
            "mes": mes,
            "temperatura": temp_esperada,
            "precipitacion": precip_esperada,
            "media_hist_huecos": hist_huecos_cercanas
        })
        
        cercanas[t["col_slots"]] = model_huecos.predict(X_cercanas).round().astype(int)
        cercanas[t["col_dist"]] = cercanas['distancia_km'].round(2)
        cercanas[t["col_dir"]] = cercanas["direccion"]
        
        alternativas = cercanas.sort_values(t["col_slots"], ascending=False).head(3)

# -----------------------
# ESTADO DE LAS ESTACIONES (NÚMEROS GRANDES SIMPLES)
# -----------------------
num_bicis = int(round(bicis_pred))
num_huecos = int(round(huecos_pred))

col_origen, col_destino = st.columns(2)

with col_origen:
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <p style="font-size: 1.1rem; color: gray; margin-bottom: -15px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">{t["bikes_origin"]}</p>
        <p style="font-size: 6.5rem; font-weight: 800; color: {COLOR_ROSA}; margin: 0; line-height: 1.2;">{num_bicis}</p>
    </div>
    """, unsafe_allow_html=True)

with col_destino:
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <p style="font-size: 1.1rem; color: gray; margin-bottom: -15px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">{t["slots_dest"]}</p>
        <p style="font-size: 6.5rem; font-weight: 800; color: {COLOR_AZUL}; margin: 0; line-height: 1.2;">{num_huecos}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True) # Espaciado limpio antes de la siguiente sección

# -----------------------
# LÓGICA DE LA RUTA
# -----------------------
puntos_ruta, distancia_m, duracion_s = get_bike_route(
    est_origen["latitud"], est_origen["longitud"],
    est_destino["latitud"], est_destino["longitud"]
)

distancia_km = distancia_m / 1000
velocidad_rapida = 15.0  
velocidad_tranquila = 10.0

tiempo_minimo = max(1, int((distancia_km / velocidad_rapida) * 60))
tiempo_maximo = max(1, int((distancia_km / velocidad_tranquila) * 60))

intervalo_texto = f"{tiempo_minimo} - {tiempo_maximo} min" if tiempo_minimo != tiempo_maximo else f"{tiempo_minimo} min"

fecha_hora_salida = datetime.datetime.combine(fecha, hora_salida)
llegada_minima = fecha_hora_salida + datetime.timedelta(minutes=tiempo_minimo)
llegada_maxima = fecha_hora_salida + datetime.timedelta(minutes=tiempo_maximo)

if tiempo_minimo == tiempo_maximo:
    intervalo_llegada = llegada_minima.strftime("%H:%M")
else:
    intervalo_llegada = f"{llegada_minima.strftime('%H:%M')} - {llegada_maxima.strftime('%H:%M')}"

peso_estimado_kg = 70.0 
met_tranquilo = 5.8 
calorias_min = int((tiempo_maximo / 60) * met_tranquilo * peso_estimado_kg)

met_rapido = 8.0  
calorias_max = int((tiempo_minimo / 60) * met_rapido * peso_estimado_kg)

if calorias_min > calorias_max:
    calorias_min, calorias_max = calorias_max, calorias_min

intervalo_calorias = f"{calorias_min} - {calorias_max} kcal" if calorias_min != calorias_max else f"{calorias_min} kcal"

# -----------------------
# DETALLES DEL TRAYECTO (RECUADRADO Y SIN EMOJIS)
# -----------------------
st.subheader(t["trip_details"])
with st.container(border=True):
    col_dist, col_time, col_eta, col_cal = st.columns(4)
    with col_dist:
        st.metric(t["route_dist"], f"{distancia_km:.2f} km")
    with col_time:
        st.metric(t["est_time"], intervalo_texto)
    with col_eta:
        st.metric(t["eta"], intervalo_llegada)
    with col_cal:
        st.metric(t["est_cal"], intervalo_calorias)

# -----------------------
# MAPA OPTIMIZADO (CON PALETA DE COLORES PERSONALIZADA)
# -----------------------
VALENCIA_LAT = 39.4699
VALENCIA_LON = -0.3763

estilo_mapa = "CartoDB dark_matter" if es_noche else "CartoDB positron"

m = folium.Map(
    location=[VALENCIA_LAT, VALENCIA_LON], 
    zoom_start=13,                       
    tiles=estilo_mapa, 
    min_zoom=12,                         
    max_bounds=True,                     
    max_lat=39.52, min_lat=39.42,
    max_lon=-0.32, min_lon=-0.43
)

fa_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>'
m.get_root().header.add_child(folium.Element(fa_css))

if es_noche:
    map_bg_color = "#1a1c23" 
    leaflet_dark_fix = f"""
    <style>
        .leaflet-container {{
            background: {map_bg_color} !important;
            background-color: {map_bg_color} !important;
        }}
    </style>
    """
    m.get_root().header.add_child(folium.Element(leaflet_dark_fix))

for _, row in df.iterrows():
    if row["direccion"] != origen and row["direccion"] != destino:
        
        es_alternativa = False
        if alternativas is not None and not alternativas.empty:
            if row["direccion"] in alternativas[t["col_dir"]].values:
                es_alternativa = True
                
        if es_alternativa:
            folium.Marker(
                [row["latitud"], row["longitud"]],
                popup=f"{t['recommended']}: {row['direccion']}",
                icon=folium.DivIcon(
                    icon_size=(24, 24),
                    icon_anchor=(12, 12),
                    html=f'''<div style="background-color: {COLOR_AZUL}; width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; box-shadow: 0px 0px 4px rgba(0,0,0,0.5);"><i class="fa-solid fa-star"></i></div>'''
                )
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[row["latitud"], row["longitud"]],
                radius=3,
                color=COLOR_AZUL,
                weight=1,
                fill=True,
                fill_color=COLOR_AZUL,
                fill_opacity=0.6,
                popup=row["direccion"]
            ).add_to(m)

folium.Marker(
    [est_origen["latitud"], est_origen["longitud"]],
    popup=f"{t['origin']}: {origen}",
    icon=folium.DivIcon(
        icon_size=(34, 34),
        icon_anchor=(17, 17),
        html=f'''<div style="background-color: {COLOR_ROSA}; width: 34px; height: 34px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; box-shadow: 0px 0px 5px rgba(0,0,0,0.6);"><i class="fa-solid fa-bicycle"></i></div>'''
    )
).add_to(m)

folium.Marker(
    [est_destino["latitud"], est_destino["longitud"]],
    popup=f"{t['dest']}: {destino}",
    icon=folium.DivIcon(
        icon_size=(34, 34),
        icon_anchor=(17, 17),
        html=f'''<div style="background-color: {COLOR_AZUL}; width: 34px; height: 34px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; box-shadow: 0px 0px 5px rgba(0,0,0,0.6);"><i class="fa-solid fa-flag"></i></div>'''
    )
).add_to(m)

color_ruta = COLOR_ROSA if es_noche else COLOR_AZUL

folium.PolyLine(
    locations=puntos_ruta,
    color=COLOR_ROSA,
    weight=6,                
    opacity=0.85,            
    popup=f"{distancia_km:.2f} km"
).add_to(m)

st.subheader(t["route_map"])
st_folium(m, width=1200, height=500, returned_objects=[])

# -----------------------
# AVISOS Y ALERTAS
# -----------------------
if precip_esperada > 0.5:
    st.info(t["rain_alert"])

if bicis_pred < 3:
    st.warning(t["low_bikes"])

if huecos_pred < 3:
    st.error(t["low_slots"])

# -----------------------
# TABLA DE ALTERNATIVAS CERCANAS
# -----------------------
if huecos_pred < 3:
    st.subheader(t["alt_header"])
    if alternativas is not None and not alternativas.empty:
        st.dataframe(alternativas[[t["col_dir"], t["col_slots"], t["col_dist"]]], hide_index=True)
    else:
        st.write(t["no_alt"])
