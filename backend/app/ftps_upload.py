from __future__ import annotations

import ftplib
import logging
import socket
import ssl
from typing import BinaryIO

log = logging.getLogger(__name__)


class _ImplicitFTP_TLS(ftplib.FTP_TLS):
    """ftplib only supports explicit (AUTH TLS) by default. Bambu uses implicit TLS."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sock: socket.socket | None = None

    @property
    def sock(self) -> socket.socket | None:
        return self._sock

    @sock.setter
    def sock(self, value: socket.socket | None) -> None:
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value, server_hostname=self.host)
        self._sock = value


class FtpsUploadError(RuntimeError):
    pass


def upload_3mf(
    *,
    host: str,
    access_code: str,
    src: BinaryIO,
    remote_name: str,
    port: int = 990,
    timeout_sec: float = 60.0,
) -> None:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    ftp = _ImplicitFTP_TLS(context=context, timeout=timeout_sec)
    try:
        ftp.connect(host=host, port=port, timeout=timeout_sec)
        ftp.login(user="bblp", passwd=access_code)
        ftp.prot_p()
        ftp.set_pasv(True)
        log.info("ftps upload start name=%s", remote_name)
        ftp.storbinary(f"STOR {remote_name}", src, blocksize=64 * 1024)
        log.info("ftps upload done name=%s", remote_name)
    except (ftplib.all_errors, OSError, ssl.SSLError) as exc:
        raise FtpsUploadError(f"FTPS upload failed: {exc}") from exc
    finally:
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass
