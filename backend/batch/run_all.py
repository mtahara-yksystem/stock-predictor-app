import subprocess
import sys


def run_task(command):
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"Error occurred in: {command}")
        sys.exit(1)


if __name__ == "__main__":
    tasks = [
        ["python", "-m", "batch.sync_sector"],
        ["python", "-m", "batch.sync_macro"],
        ["python", "-m", "batch.train_model"],
        ["python", "-m", "batch.predict_all"],
        ["python", "-m", "batch.generate_signals"],
    ]

    for task in tasks:
        run_task(task)
