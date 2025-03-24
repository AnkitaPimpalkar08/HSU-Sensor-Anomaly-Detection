import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json
import joblib
from sklearn.preprocessing import StandardScaler

# Load config file
with open("config.json") as f:
    config = json.load(f)

data_file = config["LOGGING"]["anomaly_log_file"]
model_path = config["MODEL"]["model_path"]

# Load trained model and scaler using joblib
with open(model_path, 'rb') as f:
    model_data = joblib.load(f)

model = model_data["model"]
scaler = model_data["scaler"]

# Load data function
def load_data():
    df = pd.read_csv(data_file)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    return df

# Streamlit layout enhancements
st.set_page_config(page_title="Real-Time Sensor Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center; color: #FF5733;'>📊 Real-Time Sensor Dashboard</h1>", unsafe_allow_html=True)

# Sidebar Styling and Controls
st.sidebar.title("Dashboard Controls")
st.sidebar.markdown("Explore real-time sensor data and anomalies.")
time_range = st.sidebar.slider("Select time range", 1, 24, 2, 1)  # hours
anomaly_toggle = st.sidebar.checkbox("Show Anomalies", True)

# Plot function with improved styling
def plot_graph(df):
    # Convert Timestamp to a more readable format: HH:MM (hours:minutes)
    df['Time'] = df['Timestamp'].dt.strftime('%H:%M')  # This will show time in Hours:Minutes

    # Scale the data for prediction
    scaled_data = scaler.transform(df[['Temperature', 'Humidity', 'Motion']])

    # Predict anomalies using the Isolation Forest model
    df['is_anomaly'] = model.predict(scaled_data)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "🌡️ Temperature Over Time",
            "💧 Humidity Over Time",
            "🚶 Motion Over Time"
        ),
        vertical_spacing=0.12
    )

    # Temperature Plot
    fig.add_trace(go.Scatter(
        x=df['Time'], y=df['Temperature'],
        mode='lines+markers', name='Temperature',
        line=dict(color='orange', width=2, dash='solid'),
        marker=dict(size=8, color='orange', opacity=0.6)
    ), row=1, col=1)

    # Humidity Plot
    fig.add_trace(go.Scatter(
        x=df['Time'], y=df['Humidity'],
        mode='lines+markers', name='Humidity',
        line=dict(color='blue', width=2, dash='solid'),
        marker=dict(size=8, color='blue', opacity=0.6)
    ), row=2, col=1)

    # Motion Plot
    fig.add_trace(go.Scatter(
        x=df['Time'], y=df['Motion'],
        mode='lines+markers', name='Motion',
        line=dict(color='green', width=2, dash='solid'),
        marker=dict(size=8, color='green', opacity=0.6)
    ), row=3, col=1)

    # Highlight Anomalies if toggle is checked
    if anomaly_toggle:
        anomalies = df[df['is_anomaly'] == -1]  # Isolation Forest uses -1 for anomalies
        fig.add_trace(go.Scatter(
            x=anomalies['Time'], y=anomalies['Temperature'],
            mode='markers', name='Anomalies',
            marker=dict(size=12, color='red', symbol='x', opacity=0.9)
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=anomalies['Time'], y=anomalies['Humidity'],
            mode='markers', name='Anomalies',
            marker=dict(size=12, color='red', symbol='x', opacity=0.9)
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=anomalies['Time'], y=anomalies['Motion'],
            mode='markers', name='Anomalies',
            marker=dict(size=12, color='red', symbol='x', opacity=0.9)
        ), row=3, col=1)

    # Update Layout
    fig.update_layout(
        height=800,
        width=1000,
        title="📊 Live Sensor Monitoring (Temperature, Humidity, Motion)",
        xaxis_title="Time (HH:MM)",  # X-axis title updated
        template="plotly_dark",  # Dark background for contrast
        showlegend=True
    )

    # Pass a unique key to each chart to avoid duplicate element ID error
    st.plotly_chart(fig, use_container_width=True, key=str(time.time()))  # Unique key using timestamp

# Streamlit real-time loop
st.markdown("### 📈 Live Data and Anomalies")
while True:
    df = load_data()
    if not df.empty:
        plot_graph(df)
    time.sleep(config["LOGGING"]["interval_sec"])
