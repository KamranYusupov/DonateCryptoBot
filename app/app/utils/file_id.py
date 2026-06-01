import os


def load_file_id(
    file_id_path: str,
) -> str | None:
    if os.path.exists(file_id_path):
        with open(file_id_path, "r") as f:
            return f.read().strip()

    return None

def save_file_id(file_id_path: str, file_id: str):
    with open(file_id_path, "w") as f:
        f.write(file_id)