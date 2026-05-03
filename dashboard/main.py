import sys
import os
import gradio as gr

sys.path.insert(0, os.path.dirname(__file__))               # tambah folder dashboard (untuk transform)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # tambah root project (untuk utils)

from transform import DataTransformer
transformer = DataTransformer()

from utils.logger import setup_logger
logger = setup_logger()

# ---- KPI CARD UI ----
def create_kpi_card(label, value, icon=""):
    return f"""
    <div style="background-color: #FF7043; padding: 20px; border-radius: 20px; 
                color: white; font-family: sans-serif; min-width: 200px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px;">
        <div style="font-size: 1.1em; opacity: 0.9;">{label}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 2.2em; font-weight: bold;">{value}</span>
            <span style="font-size: 1.8em;">{icon}</span>
        </div>
    </div>
    """

# ---- DASHBOARD LOGIC ----
def update_dashboard():
    """Mengambil data dari generator transform.py dan menghitung metrik"""
    for df in transformer.get_stream_data():
        # Hitung Metrik
        total_orders = len(df)
        revenue = df[df["status"] == "complete"]["price"].sum()
        pending = len(df[df["status"] == "pending"])
        cancelled = len(df[df["status"] == "cancelled"])

        # Format DataFrame untuk tampilan tabel (Urutkan yang terbaru di atas)
        latest_df = df.sort_values("timestamp", ascending=False).head(10)

        # Yield ke UI
        yield (
            create_kpi_card("Total Orders", total_orders, "📦"),
            create_kpi_card("Revenue", f"Rp {revenue:,}", "💰"),
            create_kpi_card("Pending", pending, "⏳"),
            create_kpi_card("Cancelled", cancelled, "❌"),
            latest_df
        )

# ---- UI LAYOUT ----
with gr.Blocks(title="Real-time Coffee Monitor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Real-time Orders Monitoring")

    with gr.Row():
        kpi_total = gr.HTML()
        kpi_revenue = gr.HTML()
        kpi_pending = gr.HTML()
        kpi_cancelled = gr.HTML()

    latest_table = gr.Dataframe(label="Latest Orders Stream")

    # Otomatis jalankan saat dashboard dibuka
    demo.load(
        fn=update_dashboard,
        outputs=[kpi_total, kpi_revenue, kpi_pending, kpi_cancelled, latest_table]
    )

if __name__ == "__main__":
    logger.info("Launching Gradio Dashboard on port 7860...")
    try:
        demo.launch(share=True, server_port=7860)
    except Exception as e:
        logger.critical(f"Failed to launch Gradio: {e}")