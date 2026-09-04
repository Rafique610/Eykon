import subprocess
import sys


def main():
    """Launch the Streamlit app as a subprocess."""
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "src/ui/app.py"],
            check=True,
        )
    except KeyboardInterrupt:
        print("\nApp stopped by user.")


if __name__ == "__main__":
    main()
