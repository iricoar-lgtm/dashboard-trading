import streamlit as st

from textblob import TextBlob
import backtrader as bt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import feedparser
import requests

TELEGRAM_TOKEN = "8562882529:AAGG4oGoUcnQcoZUYAFhY2upgoxcXuCQswk"
TELEGRAM_CHAT_ID = "1638205295"

def enviar_alerta_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"})
    except:
        pass
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from scipy.signal import argrelextrema

st.set_page_config(page_title="Dashboard Trading", layout="wide")
st.title("📈 Dashboard de Análisis Técnico")
tab1, tab2, tab3 = st.tabs(["📊 Análisis Técnico", "📰 Sentimiento de Mercado", "🔬 Backtesting"])

# --- Favoritos ---
import json, os
FAVORITOS_FILE = "C:\\dashboard_trading\\favoritos.json"

def cargar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return json.load(f)
    return ["AAPL", "MSFT", "TSLA"]

def guardar_favoritos(lista):
    with open(FAVORITOS_FILE, "w") as f:
        json.dump(lista, f)

if "favoritos" not in st.session_state:
    st.session_state.favoritos = cargar_favoritos()

with st.sidebar.expander("⭐ Favoritos", expanded=True):
    nuevo = st.text_input("Símbolo a añadir", key="nuevo_fav")
    if st.button("➕ Añadir a favoritos"):
        if nuevo and nuevo.upper() not in st.session_state.favoritos:
            st.session_state.favoritos.append(nuevo.upper())
            guardar_favoritos(st.session_state.favoritos)
            st.rerun()
    st.write("**Mis favoritos:**")
    for i, fav in enumerate(st.session_state.favoritos):
        col_fav, col_del = st.columns([3, 1])
        if col_fav.button(fav, key=f"fav_{i}"):
            st.session_state["ticker_seleccionado"] = fav
            st.rerun()
        if col_del.button("🗑️", key=f"del_{i}"):
            st.session_state.favoritos.pop(i)
            guardar_favoritos(st.session_state.favoritos)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Configuración")
ticker_default = st.session_state.get("ticker_seleccionado", "AAPL")
ticker = st.sidebar.text_input("Símbolo de la acción", value=ticker_default).upper()
periodo = st.sidebar.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=4)

st.sidebar.subheader("Indicadores")
mostrar_sma = st.sidebar.checkbox("SMA 20 y 50", value=True)
mostrar_bb = st.sidebar.checkbox("Bandas de Bollinger", value=False)
mostrar_rsi = st.sidebar.checkbox("RSI", value=True)
mostrar_macd = st.sidebar.checkbox("MACD", value=True)
mostrar_volumen = st.sidebar.checkbox("Volumen", value=True)
mostrar_señales = st.sidebar.checkbox("Señales Compra/Venta", value=True)

st.sidebar.subheader("Figuras")
mostrar_soportes = st.sidebar.checkbox("Soportes y Resistencias", value=True)
mostrar_canales = st.sidebar.checkbox("Canales", value=True)
mostrar_triangulos = st.sidebar.checkbox("Triángulos", value=True)

st.sidebar.subheader("📊 Screener")
usar_screener = st.sidebar.checkbox("Activar Screener", value=False)
tickers_screener = st.sidebar.text_input("Acciones a escanear (separadas por coma)", value="AAPL,MSFT,GOOGL,TSLA,AMZN")

# --- Funciones ---

def detectar_soportes_resistencias(df, ventana=10):
    close = df["Close"].squeeze().values
    idx = df.index
    maximos = argrelextrema(close, np.greater, order=ventana)[0]
    minimos = argrelextrema(close, np.less, order=ventana)[0]
    resistencias = [(idx[i], close[i]) for i in maximos]
    soportes = [(idx[i], close[i]) for i in minimos]
    return soportes, resistencias

def detectar_canal(df, ventana=20):
    close = df["Close"].squeeze().values
    idx = df.index
    n = len(close)
    if n < ventana * 2:
        return None
    x = np.arange(n)
    maximos_idx = argrelextrema(close, np.greater, order=ventana)[0]
    minimos_idx = argrelextrema(close, np.less, order=ventana)[0]
    if len(maximos_idx) < 2 or len(minimos_idx) < 2:
        return None
    m_sup, b_sup = np.polyfit(maximos_idx, close[maximos_idx], 1)
    m_inf, b_inf = np.polyfit(minimos_idx, close[minimos_idx], 1)
    linea_sup = m_sup * x + b_sup
    linea_inf = m_inf * x + b_inf
    if m_sup > 0.01 and m_inf > 0.01:
        tipo = "Canal Alcista"
        color = "green"
    elif m_sup < -0.01 and m_inf < -0.01:
        tipo = "Canal Bajista"
        color = "red"
    else:
        tipo = "Canal Lateral"
        color = "blue"
    return idx, linea_sup, linea_inf, tipo, color

def detectar_triangulo(df, ventana=15):
    close = df["Close"].squeeze().values
    idx = df.index
    n = len(close)
    if n < ventana * 2:
        return None
    x = np.arange(n)
    maximos_idx = argrelextrema(close, np.greater, order=ventana)[0]
    minimos_idx = argrelextrema(close, np.less, order=ventana)[0]
    if len(maximos_idx) < 2 or len(minimos_idx) < 2:
        return None
    m_sup, b_sup = np.polyfit(maximos_idx, close[maximos_idx], 1)
    m_inf, b_inf = np.polyfit(minimos_idx, close[minimos_idx], 1)
    linea_sup = m_sup * x + b_sup
    linea_inf = m_inf * x + b_inf
    if m_sup < -0.01 and m_inf > 0.01:
        tipo = "Triángulo Simétrico"
        color = "orange"
    elif abs(m_sup) < 0.01 and m_inf > 0.01:
        tipo = "Triángulo Ascendente"
        color = "green"
    elif m_sup < -0.01 and abs(m_inf) < 0.01:
        tipo = "Triángulo Descendente"
        color = "red"
    else:
        return None
    return idx, linea_sup, linea_inf, tipo, color

def detectar_señales(df):
    close = df["Close"].squeeze()
    sma20 = SMAIndicator(close, window=20).sma_indicator()
    sma50 = SMAIndicator(close, window=50).sma_indicator()
    rsi = RSIIndicator(close, window=14).rsi()
    señales_compra = []
    señales_venta = []
    for i in range(1, len(df)):
        cruce_alcista = sma20.iloc[i] > sma50.iloc[i] and sma20.iloc[i-1] <= sma50.iloc[i-1]
        cruce_bajista = sma20.iloc[i] < sma50.iloc[i] and sma20.iloc[i-1] >= sma50.iloc[i-1]
        rsi_sobreventa = rsi.iloc[i] < 35
        rsi_sobrecompra = rsi.iloc[i] > 65
        if cruce_alcista or rsi_sobreventa:
            señales_compra.append((df.index[i], float(close.iloc[i])))
        if cruce_bajista or rsi_sobrecompra:
            señales_venta.append((df.index[i], float(close.iloc[i])))
    return señales_compra, señales_venta

def screener(tickers, periodo="6mo"):
    resultados = []
    for t in tickers:
        try:
            df = yf.download(t, period=periodo, interval="1d", auto_adjust=True, progress=False)
            if df.empty:
                continue
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            close = df["Close"].squeeze()
            rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
            sma20 = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
            sma50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]
            precio = float(close.iloc[-1])
            cambio = ((precio - float(close.iloc[-2])) / float(close.iloc[-2])) * 100
            señal = "🟢 Compra" if sma20 > sma50 and rsi < 60 else ("🔴 Venta" if sma20 < sma50 and rsi > 40 else "⚪ Neutral")
            resultados.append({
                "Ticker": t,
                "Precio": f"${precio:.2f}",
                "Cambio %": f"{cambio:+.2f}%",
                "RSI": f"{rsi:.1f}",
                "SMA20 > SMA50": "✅" if sma20 > sma50 else "❌",
                "Señal": señal
            })
        except:
            pass
    return pd.DataFrame(resultados)

# --- Cargar datos principales ---
df = yf.download(ticker, period=periodo, interval="1d", auto_adjust=True)

with tab1:
 if df is not None and not df.empty:
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    close = df["Close"].squeeze()

    precio_actual = float(close.iloc[-1])
    precio_anterior = float(close.iloc[-2])
    cambio = precio_actual - precio_anterior
    cambio_pct = (cambio / precio_anterior) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precio Actual", f"${precio_actual:.2f}", f"{cambio_pct:+.2f}%")
    col2.metric("Máximo histórico", f"${float(df['High'].max()):.2f}")
    col3.metric("Mínimo histórico", f"${float(df['Low'].min()):.2f}")
    col4.metric("Volumen promedio", f"{int(df['Volume'].mean()):,}")

    # --- Gráfico principal ---
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df["Open"].squeeze(),
        high=df["High"].squeeze(),
        low=df["Low"].squeeze(),
        close=close,
        name="Precio"
    )])

    if mostrar_sma:
        sma20 = SMAIndicator(close, window=20).sma_indicator()
        sma50 = SMAIndicator(close, window=50).sma_indicator()
        fig.add_trace(go.Scatter(x=df.index, y=sma20, name="SMA 20", line=dict(color="blue", width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA 50", line=dict(color="orange", width=1.5)))

    if mostrar_bb:
        bb = BollingerBands(close, window=20)
        fig.add_trace(go.Scatter(x=df.index, y=bb.bollinger_hband(), name="BB Superior", line=dict(color="gray", dash="dash")))
        fig.add_trace(go.Scatter(x=df.index, y=bb.bollinger_lband(), name="BB Inferior", line=dict(color="gray", dash="dash")))
        fig.add_trace(go.Scatter(x=df.index, y=bb.bollinger_mavg(), name="BB Media", line=dict(color="gray", width=1)))

    if mostrar_señales:
        señales_compra, señales_venta = detectar_señales(df)
        ultimas_compras = señales_compra[-5:]
        ultimas_ventas = señales_venta[-5:]

        # Alertas Telegram solo cuando cambia el símbolo
        if "ultimo_ticker_alerta" not in st.session_state:
            st.session_state.ultimo_ticker_alerta = ""

        if ticker != st.session_state.ultimo_ticker_alerta:
            st.session_state.ultimo_ticker_alerta = ticker
            if señales_compra:
                ultima_compra = señales_compra[-1]
                mensaje = f"🟢 <b>SEÑAL DE COMPRA</b>\n📈 Acción: {ticker}\n💰 Precio: ${ultima_compra[1]:.2f}\n📅 Fecha: {ultima_compra[0].strftime('%d/%m/%Y')}"
                enviar_alerta_telegram(mensaje)
            if señales_venta:
                ultima_venta = señales_venta[-1]
                mensaje = f"🔴 <b>SEÑAL DE VENTA</b>\n📉 Acción: {ticker}\n💰 Precio: ${ultima_venta[1]:.2f}\n📅 Fecha: {ultima_venta[0].strftime('%d/%m/%Y')}"
                enviar_alerta_telegram(mensaje)
        if ultimas_compras:
            fig.add_trace(go.Scatter(
                x=[s[0] for s in ultimas_compras],
                y=[s[1] * 0.98 for s in ultimas_compras],
                mode="markers", name="🟢 Compra",
                marker=dict(symbol="triangle-up", size=12, color="lime")
            ))
        if ultimas_ventas:
            fig.add_trace(go.Scatter(
                x=[s[0] for s in ultimas_ventas],
                y=[s[1] * 1.02 for s in ultimas_ventas],
                mode="markers", name="🔴 Venta",
                marker=dict(symbol="triangle-down", size=12, color="red")
            ))

    if mostrar_soportes:
        soportes, resistencias = detectar_soportes_resistencias(df)
        for fecha, precio in (soportes[-3:] if len(soportes) >= 3 else soportes):
            fig.add_hline(y=precio, line_dash="dot", line_color="lime",
                         annotation_text=f"Soporte ${precio:.2f}", annotation_position="right")
        for fecha, precio in (resistencias[-3:] if len(resistencias) >= 3 else resistencias):
            fig.add_hline(y=precio, line_dash="dot", line_color="red",
                         annotation_text=f"Resistencia ${precio:.2f}", annotation_position="right")

    if mostrar_canales:
        resultado_canal = detectar_canal(df)
        if resultado_canal:
            idx, linea_sup, linea_inf, tipo, color = resultado_canal
            fig.add_trace(go.Scatter(x=idx, y=linea_sup, name=f"{tipo} Superior", line=dict(color=color, dash="dash", width=1.5)))
            fig.add_trace(go.Scatter(x=idx, y=linea_inf, name=f"{tipo} Inferior", line=dict(color=color, dash="dash", width=1.5)))

    if mostrar_triangulos:
        resultado_tri = detectar_triangulo(df)
        if resultado_tri:
            idx, linea_sup, linea_inf, tipo, color = resultado_tri
            fig.add_trace(go.Scatter(x=idx, y=linea_sup, name=f"{tipo} Superior", line=dict(color=color, dash="dot", width=2)))
            fig.add_trace(go.Scatter(x=idx, y=linea_inf, name=f"{tipo} Inferior", line=dict(color=color, dash="dot", width=2)))

    fig.update_layout(
        title=f"{ticker} - Análisis Técnico",
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(side="right")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Volumen ---
    if mostrar_volumen:
        colores_volumen = ["green" if float(close.iloc[i]) >= float(close.iloc[i-1]) else "red" for i in range(1, len(df))]
        colores_volumen = ["green"] + colores_volumen
        fig_vol = go.Figure(data=[go.Bar(
            x=df.index, y=df["Volume"].squeeze(),
            marker_color=colores_volumen, name="Volumen"
        )])
        fig_vol.update_layout(title="Volumen", height=200, template="plotly_dark")
        st.plotly_chart(fig_vol, use_container_width=True)

    # --- RSI ---
    if mostrar_rsi:
        rsi = RSIIndicator(close, window=14).rsi()
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="cyan")))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Sobrecompra")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Sobreventa")
        fig_rsi.update_layout(title="RSI (14)", height=250, template="plotly_dark", yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig_rsi, use_container_width=True)

    # --- MACD ---
    if mostrar_macd:
        macd_ind = MACD(close)
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=macd_ind.macd(), name="MACD", line=dict(color="blue")))
        fig_macd.add_trace(go.Scatter(x=df.index, y=macd_ind.macd_signal(), name="Señal", line=dict(color="orange")))
        macd_hist = macd_ind.macd_diff()
        colores_macd = ["green" if v >= 0 else "red" for v in macd_hist]
        fig_macd.add_trace(go.Bar(x=df.index, y=macd_hist, name="Histograma", marker_color=colores_macd))
        fig_macd.update_layout(title="MACD", height=250, template="plotly_dark")
        st.plotly_chart(fig_macd, use_container_width=True)

    else:
        st.info("Introduce un símbolo y espera que carguen los datos.")

# --- Análisis de Sentimiento ---
def obtener_noticias(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    feed = feedparser.parse(url)
    noticias = []
    for entry in feed.entries[:10]:
        titulo = entry.title
        enlace = entry.link
        fecha = entry.get("published", "")
        blob = TextBlob(titulo)
        polaridad = blob.sentiment.polarity
        if polaridad > 0.1:
            sentimiento = "🟢 Positivo"
            color = "green"
        elif polaridad < -0.1:
            sentimiento = "🔴 Negativo"
            color = "red"
        else:
            sentimiento = "⚪ Neutral"
            color = "gray"
        noticias.append({
            "titulo": titulo,
            "enlace": enlace,
            "fecha": fecha,
            "sentimiento": sentimiento,
            "polaridad": polaridad,
            "color": color
        })
    return noticias

# --- Screener ---
if usar_screener:
    st.markdown("---")
    st.subheader("📊 Screener de Acciones")
    lista_tickers = [t.strip().upper() for t in tickers_screener.split(",") if t.strip()]
    with st.spinner("Escaneando acciones..."):
        df_screener = screener(lista_tickers, periodo="6mo")
    if not df_screener.empty:
        st.dataframe(df_screener, use_container_width=True)
    else:
        st.warning("No se pudieron obtener datos para las acciones indicadas.")

# --- Pestaña Sentimiento ---
with tab2:
    st.subheader(f"📰 Análisis de Sentimiento - {ticker}")
    with st.spinner("Cargando noticias..."):
        noticias = obtener_noticias(ticker)

    if not noticias:
        st.warning("No se encontraron noticias para esta acción.")
    else:
        positivas = sum(1 for n in noticias if "Positivo" in n["sentimiento"])
        negativas = sum(1 for n in noticias if "Negativo" in n["sentimiento"])
        neutrales = sum(1 for n in noticias if "Neutral" in n["sentimiento"])
        total = len(noticias)
        sentimiento_general = "🟢 POSITIVO" if positivas > negativas else ("🔴 NEGATIVO" if negativas > positivas else "⚪ NEUTRAL")

        st.markdown(f"### Sentimiento general: {sentimiento_general}")

        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 Positivas", f"{positivas}/{total}")
        col2.metric("🔴 Negativas", f"{negativas}/{total}")
        col3.metric("⚪ Neutrales", f"{neutrales}/{total}")

        fig_sent = go.Figure(data=[go.Pie(
            labels=["Positivo", "Negativo", "Neutral"],
            values=[positivas, negativas, neutrales],
            marker=dict(colors=["green", "red", "gray"]),
            hole=0.4
        )])
        fig_sent.update_layout(title="Distribución de Sentimiento", template="plotly_dark", height=300)
        st.plotly_chart(fig_sent, use_container_width=True)

        st.markdown("### 📋 Noticias recientes")
        for n in noticias:
            with st.expander(f"{n['sentimiento']} — {n['titulo']}"):
                st.write(f"📅 {n['fecha']}")
                st.write(f"🔗 [Ver noticia completa]({n['enlace']})")
                st.progress(min(max((n['polaridad'] + 1) / 2, 0), 1))

# --- Pestaña Backtesting ---
with tab3:
    st.subheader("🔬 Backtesting de Estrategias")

    col_b1, col_b2, col_b3 = st.columns(3)
    ticker_bt = col_b1.text_input("Símbolo", value="AAPL")
    periodo_bt = col_b2.selectbox("Período", ["1y", "2y", "5y", "max"], index=1)
    estrategia_bt = col_b3.selectbox("Estrategia", [
        "Cruce de Medias (SMA20/SMA50)",
        "RSI (Sobreventa/Sobrecompra)",
        "MACD",
        "Ruptura de Canal",
        "Combinada RSI + MACD",
        "Compra en Canal Alcista (Tendencia 1 año)"
    ])

    capital_inicial = st.number_input("Capital inicial ($)", value=10000, step=1000)

    if st.button("▶️ Ejecutar Backtesting"):
        with st.spinner("Ejecutando backtesting..."):

            # Descargar datos
            df_bt = yf.download(ticker_bt, period=periodo_bt, interval="1d", auto_adjust=True, progress=False)
            df_bt.columns = [col[0] if isinstance(col, tuple) else col for col in df_bt.columns]

            if df_bt.empty:
                st.error("No se encontraron datos para este símbolo.")
            else:
                close_bt = df_bt["Close"].squeeze()

                # Calcular señales según estrategia
                df_bt["signal"] = 0

                if estrategia_bt == "Cruce de Medias (SMA20/SMA50)":
                    df_bt["sma20"] = close_bt.rolling(20).mean()
                    df_bt["sma50"] = close_bt.rolling(50).mean()
                    df_bt["signal"] = np.where(df_bt["sma20"] > df_bt["sma50"], 1, 0)

                elif estrategia_bt == "RSI (Sobreventa/Sobrecompra)":
                    rsi_bt = RSIIndicator(close_bt, window=14).rsi()
                    df_bt["signal"] = np.where(rsi_bt < 35, 1, np.where(rsi_bt > 65, 0, np.nan))
                    df_bt["signal"] = df_bt["signal"].ffill().fillna(0)

                elif estrategia_bt == "MACD":
                    macd_bt = MACD(close_bt)
                    df_bt["signal"] = np.where(macd_bt.macd() > macd_bt.macd_signal(), 1, 0)

                elif estrategia_bt == "Ruptura de Canal":
                    df_bt["max20"] = close_bt.rolling(20).max()
                    df_bt["min20"] = close_bt.rolling(20).min()
                    df_bt["signal"] = np.where(
                        close_bt > df_bt["max20"].shift(1), 1,
                        np.where(close_bt < df_bt["min20"].shift(1), 0, np.nan)
                    )
                    df_bt["signal"] = df_bt["signal"].ffill().fillna(0)

                elif estrategia_bt == "Combinada RSI + MACD":
                    rsi_bt = RSIIndicator(close_bt, window=14).rsi()
                    macd_bt = MACD(close_bt)
                    señal_rsi = rsi_bt < 40
                    señal_macd = macd_bt.macd() > macd_bt.macd_signal()
                    señal_venta_rsi = rsi_bt > 60
                    señal_venta_macd = macd_bt.macd() < macd_bt.macd_signal()
                    df_bt["signal"] = np.where(
                        señal_rsi & señal_macd, 1,
                        np.where(señal_venta_rsi & señal_venta_macd, 0, np.nan)
                    )
                    df_bt["signal"] = df_bt["signal"].ffill().fillna(0)

                elif estrategia_bt == "Compra en Canal Alcista (Tendencia 1 año)":
                    # Tendencia alcista si precio actual > SMA200
                    df_bt["sma200"] = close_bt.rolling(200).mean()
                    # Canal: bandas superior e inferior de 20 períodos
                    df_bt["canal_sup"] = close_bt.rolling(20).max()
                    df_bt["canal_inf"] = close_bt.rolling(20).min()
                    # Posición dentro del canal (0=parte baja, 1=parte alta)
                    df_bt["pos_canal"] = (close_bt - df_bt["canal_inf"]) / (df_bt["canal_sup"] - df_bt["canal_inf"])
                    # Compra: tendencia alcista + precio en parte baja del canal (pos < 0.3)
                    # Venta: precio en parte alta del canal (pos > 0.7)
                    tendencia_alcista = close_bt > df_bt["sma200"]
                    en_parte_baja = df_bt["pos_canal"] < 0.3
                    en_parte_alta = df_bt["pos_canal"] > 0.7
                    df_bt["signal"] = np.where(
                        tendencia_alcista & en_parte_baja, 1,
                        np.where(en_parte_alta, 0, np.nan)
                    )
                    df_bt["signal"] = df_bt["signal"].ffill().fillna(0)

                # Calcular rendimiento de la estrategia
                df_bt["retorno"] = close_bt.pct_change()
                df_bt["retorno_estrategia"] = df_bt["signal"].shift(1) * df_bt["retorno"]
                df_bt = df_bt.dropna()

                capital_estrategia = capital_inicial * (1 + df_bt["retorno_estrategia"]).cumprod()
                capital_buyhold = capital_inicial * (1 + df_bt["retorno"]).cumprod()

                # Métricas
                rendimiento_estrategia = ((capital_estrategia.iloc[-1] - capital_inicial) / capital_inicial) * 100
                rendimiento_buyhold = ((capital_buyhold.iloc[-1] - capital_inicial) / capital_inicial) * 100
                max_drawdown = ((capital_estrategia - capital_estrategia.cummax()) / capital_estrategia.cummax()).min() * 100
                operaciones = df_bt["signal"].diff().abs().sum()
                aciertos = (df_bt["retorno_estrategia"] > 0).sum()
                total_ops = (df_bt["retorno_estrategia"] != 0).sum()
                ratio_aciertos = (aciertos / total_ops * 100) if total_ops > 0 else 0

                # Mostrar métricas
                st.markdown("### 📊 Resultados")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Capital Final", f"${capital_estrategia.iloc[-1]:,.0f}", f"{rendimiento_estrategia:+.1f}%")
                m2.metric("Buy & Hold", f"${capital_buyhold.iloc[-1]:,.0f}", f"{rendimiento_buyhold:+.1f}%")
                m3.metric("Max Drawdown", f"{max_drawdown:.1f}%")
                m4.metric("Ratio Aciertos", f"{ratio_aciertos:.1f}%")

                # Gráfico de rendimiento
                fig_bt = go.Figure()
                fig_bt.add_trace(go.Scatter(
                    x=df_bt.index, y=capital_estrategia,
                    name=f"Estrategia: {estrategia_bt}",
                    line=dict(color="cyan", width=2)
                ))
                fig_bt.add_trace(go.Scatter(
                    x=df_bt.index, y=capital_buyhold,
                    name="Buy & Hold",
                    line=dict(color="orange", width=2)
                ))
                fig_bt.update_layout(
                    title=f"Rendimiento: {ticker_bt}",
                    yaxis_title="Capital ($)",
                    height=400,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_bt, use_container_width=True)

                # Gráfico de señales sobre precio
                fig_sig = go.Figure()
                fig_sig.add_trace(go.Scatter(
                    x=df_bt.index, y=close_bt,
                    name="Precio", line=dict(color="white", width=1)
                ))
                compras = df_bt[df_bt["signal"].diff() == 1]
                ventas = df_bt[df_bt["signal"].diff() == -1]
                fig_sig.add_trace(go.Scatter(
                    x=compras.index, y=close_bt[compras.index],
                    mode="markers", name="Compra",
                    marker=dict(symbol="triangle-up", size=10, color="lime")
                ))
                fig_sig.add_trace(go.Scatter(
                    x=ventas.index, y=close_bt[ventas.index],
                    mode="markers", name="Venta",
                    marker=dict(symbol="triangle-down", size=10, color="red")
                ))
                fig_sig.update_layout(
                    title="Señales de Entrada y Salida",
                    height=350,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_sig, use_container_width=True)

                st.success(f"✅ Backtesting completado. {int(operaciones)} operaciones realizadas.")
