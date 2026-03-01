from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class VintedProxy:
    ip: str
    port: str
    username: Optional[str]
    password: Optional[str]
    is_https: bool

    @property
    def scheme(self) -> str:
        return "https" if self.is_https else "http"

    def to_str_proxy(self) -> str:
        if self.username and self.password:
            return f"{self.scheme}://{self.username}:{self.password}@{self.ip}:{self.port}"
        else:
            return f"{self.scheme}://{self.ip}:{self.port}"

    def __str__(self) -> str:
        if self.username and self.password:
            return f"{self.scheme}://{self.username}:{self.password}@{self.ip}:{self.port} (HTTPS: {self.is_https})"
        else:
            return f"{self.scheme}://{self.ip}:{self.port} (HTTPS: {self.is_https})"

    def __repr__(self) -> str:
        return f"VintedProxy(ip={self.ip}, port={self.port}, username={self.username}, password={self.password}, is_https={self.is_https})"
