# -*- coding: utf-8 -*-
"""Перевірка «сервер перегляду живий?» — викликається з start_viewer.bat.

Використання: python viewer_probe.py <порт>
Код виходу 0 — сервер відповідає, 1 — ні.

Окремий файл потрібен тому, що дужки в командах усередині блоків `if ( ... )`
у batch-файлах передчасно закривають блок.
"""
import socket
import sys


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip().isdigit():
        return 1
    port = int(sys.argv[1])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.5)
        return 0 if s.connect_ex(("127.0.0.1", port)) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
