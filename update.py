# -*- encoding: utf-8 -*-

import hashlib
import sys
import time
from pathlib import Path
from typing import Tuple, List, Dict, Final
from zipfile import ZipFile

import requests
from requests.exceptions import ReadTimeout, RequestException, SSLError

P: Final[Path] = Path(__file__).resolve().parent

LANG_DIR: Final[Path] = P / "sources"
LANG_DIR.mkdir(exist_ok=True)

MAX_RETRIES: Final[int] = 3

def get_response(url: str) -> requests.Response | None:
    """Get HTTP response and handle exceptions and retry logic.

    Args:
        url (str): URL to request

    Returns:
        requests.Response | None: Response object, or None if request fails
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            return resp
        except SSLError as e:
            if retries < MAX_RETRIES - 1:
                print(f"SSL Error encountered: {e}")
                print("Server access restricted, retrying in 10 seconds...")
                time.sleep(10)
            else:
                print(f"SSL Error encountered: {e}")
                print("Maximum retry attempts reached. Operation terminated.")
        except ReadTimeout as e:
            if retries < MAX_RETRIES - 1:
                print(f"Request timeout: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"Request timeout: {e}")
                print("Maximum retry attempts reached. Operation terminated.")
        except RequestException as ex:
            print(f"Request error occurred: {ex}")
            break
        retries = retries + 1


def get_file(url: str, filename: str, filepath: Path, sha1: str) -> None:
    """Download file and verify SHA1 value.

    Args:
        url (str): File download URL
        filename (str): File name
        filepath (Path): File save path
        sha1 (str): Expected SHA1 checksum
    """
    success = False
    for _ in range(MAX_RETRIES):
        resp = get_response(url)
        if resp is None:
            print(f"Failed to download {filename}: No response received.")
            continue
        try:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            with filepath.open("rb") as f:
                if hashlib.file_digest(f, "sha1").hexdigest() == sha1:
                    success = True
                    break
            print("File SHA1 checksum mismatch, retrying download.")
        except RequestException as e:
            print(f"Request error: {e}")
            sys.exit(1)
    if not success:
        print(f'Unable to download file "{filename}".')


def get_client(info: dict) -> Path:
    """Get client.jar file.

    Args:
        info (dict): Version info

    Returns:
        Path: Path to client.jar
    """
    client_manifest_url = info["url"]
    client_path = P / f"Java_Edition_{info['id']}.jar"
    if client_path.exists():
        return client_path
    print(
        f'Fetching client manifest file "{Path(client_manifest_url).name.replace("%20", " ")}"...'
    )
    client_manifest_resp = get_response(client_manifest_url)
    if client_manifest_resp is None:
        print("Failed to retrieve client manifest.")
        sys.exit(1)
    client_manifest = client_manifest_resp.json()

    client_url = client_manifest["downloads"]["client"]["url"]
    client_sha1 = client_manifest["downloads"]["client"]["sha1"]
    print(f'Downloading "{client_path.name}" ({client_sha1})...')
    get_file(client_url, client_path.name, client_path, client_sha1)
    print()
    return client_path


def main():
    version_manifest_json: Dict = get_response(
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
).json()
    
    V: str = version_manifest_json["latest"]["snapshot"]
    version_info: Dict = next(
    (_ for _ in version_manifest_json["versions"] if _["id"] == V), {}
)
    client_path = get_client(version_info)
    with ZipFile(client_path) as client:
        with client.open("assets/minecraft/lang/en_us.json") as content:
            with open(LANG_DIR / "en_us.json", "wb") as en:
                en.write(content.read())

if __name__ == "__main__":
    main()