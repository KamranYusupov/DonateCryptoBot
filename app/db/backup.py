from pathlib import Path
from datetime import datetime
import asyncio
import gzip
import shutil
import tempfile
import os

from app.core.config import settings


async def create_backup() -> Path:
    timestamp = datetime.now().strftime("%H-%M_%Y-%m-%d")

    sql_path = Path(tempfile.gettempdir()) / f"backup_{timestamp}.sql"
    gz_path = sql_path.with_suffix(".sql.gz")

    env = os.environ.copy()
    env["PGPASSWORD"] = settings.postgres_password

    process = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h", settings.postgres_host,
        "-p", str(settings.postgres_port),
        "-U", settings.postgres_user,
        "-d", settings.postgres_db,
        "-f", str(sql_path),
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(stderr.decode())

    with open(sql_path, "rb") as src:
        with gzip.open(gz_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    sql_path.unlink()

    return gz_path