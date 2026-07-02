import os
import tempfile
import shutil


def atomic_write(filepath, content, mode="w", encoding="utf-8"):
    dirpath = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".tmp_", suffix=".tmp")
    try:
        if "b" in mode:
            with os.fdopen(fd, mode) as f:
                f.write(content)
        else:
            with os.fdopen(fd, mode, encoding=encoding) as f:
                f.write(content)
        shutil.move(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def backup_file(filepath):
    bak_path = filepath + ".bak"
    shutil.copy2(filepath, bak_path)
    return bak_path
