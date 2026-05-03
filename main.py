import sys
import time
import signal
import argparse
import subprocess
from pathlib import Path

from utils.logger import setup_logger
logger = setup_logger()

# ─── Konfigurasi Path ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()

COMPONENTS = {
    "listener":      ROOT / "engine" / "listener.py",
    "api":           ROOT / "api" / "app.py",
    "generator":     ROOT / "engine" / "data_generator.py",
    "dashboard":     ROOT / "dashboard" / "main.py",
}

# Urutan startup (dengan jeda detik antar proses)
STARTUP_ORDER = [
    ("listener",  2.5),   # Tunggu 2.5 detik sebelum lanjut
    ("api",       2.0),   # Tunggu API siap sebelum generator & dashboard
    ("generator", 1.0),
]

# ─── State Global ─────────────────────────────────────────────────────────────
processes: dict[str, subprocess.Popen] = {}

def start_process(name: str, script: Path) -> subprocess.Popen:
    """Jalankan script Python sebagai subprocess."""
    if not script.exists():
        logger.warning(f"⚠️  File tidak ditemukan: {script}. Lewati.")
        return None

    logger.info(f"🚀 Memulai  → {name}  ({script.relative_to(ROOT)})")
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(ROOT),      # CWD = root project agar import utils.logger bekerja
        text=True,
    )
    return proc


def stop_all():
    """Kirim SIGTERM ke semua proses, tunggu hingga berhenti."""
    logger.info("🛑 Menghentikan semua proses...")
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            logger.info(f"   ↳ Menghentikan {name} (PID {proc.pid})")
            proc.terminate()

    # Beri waktu 5 detik untuk graceful shutdown
    deadline = time.time() + 5
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            remaining = max(0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                logger.error(f"   ↳ Force-kill {name} (PID {proc.pid})")
                proc.kill()

    logger.info("✅ Semua proses dihentikan.")


def signal_handler():
    logger.info("\n⚡ Sinyal interrupt diterima.")
    stop_all()
    sys.exit(0)


def check_crashed() -> list[str]:
    """Kembalikan daftar nama proses yang sudah crash."""
    return [
        name for name, proc in processes.items()
        if proc and proc.poll() is not None
    ]


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Streaming API — Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh:
  python main.py                  # Jalankan tanpa dashboard
  python main.py --dashboard      # Jalankan semua termasuk Gradio
  python main.py --no-generator   # Jalankan tanpa data generator (data manual)
        """
    )
    parser.add_argument("--dashboard",    action="store_true", help="Jalankan Gradio dashboard")
    parser.add_argument("--no-generator", action="store_true", help="Lewati data_generator.py")
    args = parser.parse_args()

    # Tangani Ctrl+C
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ── Tentukan komponen yang akan dijalankan ────────────────
    order = list(STARTUP_ORDER)  # copy
    if args.no_generator:
        order = [(n, d) for n, d in order if n != "generator"]
        logger.info("ℹ️  Mode --no-generator: data_generator dilewati.")
    if args.dashboard:
        order.append(("dashboard", 1.0))

    # ── Startup berurutan ─────────────────────────────────────
    for name, delay in order:
        proc = start_process(name, COMPONENTS[name])
        if proc:
            processes[name] = proc
        if delay > 0:
            logger.info(f"   ⏳ Jeda {delay}s sebelum komponen berikutnya...")
            time.sleep(delay)

    logger.info("✅ Semua komponen berjalan. Tekan Ctrl+C untuk berhenti.")

    # ── Monitor — restart jika crash ──────────────────────────
    try:
        while True:
            time.sleep(3)
            crashed = check_crashed()
            for name in crashed:
                logger.warning(f"⚠️  Proses '{name}' berhenti tak terduga. Merestart...")
                proc = start_process(name, COMPONENTS[name])
                if proc:
                    processes[name] = proc
    except KeyboardInterrupt:
        pass
    finally:
        stop_all()


if __name__ == "__main__":
    main()