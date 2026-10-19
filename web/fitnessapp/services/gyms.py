"""Búsqueda de gimnasios con Nominatim (OpenStreetMap).

Cambios respecto a la versión original:
- Parámetros con `params=` (requests los codifica). Antes se concatenaba el texto del
  usuario en la URL, así que 'Las Palmas' o '&' rompían la búsqueda.
- User-Agent identificativo y timeout, como exige la política de uso de Nominatim.
- Caché en memoria: la política pide como máximo 1 petición por segundo y evitar repetir
  búsquedas idénticas.
- Endpoint `/search` (el antiguo `/search.php` está obsoleto).
- Se busca por categoría de OpenStreetMap (`[leisure=fitness_centre]`) en lugar de la palabra
  "gimnasio": antes solo salían los sitios con "gimnasio" en el nombre (1 en Las Palmas),
  ahora salen todos los centros deportivos etiquetados (29 en Las Palmas, 40+ en Madrid).
"""

import time
from dataclasses import dataclass

import requests


class GymSearchError(Exception):
    pass


@dataclass
class Gym:
    name: str
    address: str
    lat: float
    lon: float


_CACHE: dict[str, tuple[float, list[Gym]]] = {}
_CACHE_SECONDS = 60 * 60


def _parse(item: dict) -> Gym:
    display = item.get("display_name", "")
    name = item.get("name") or ""
    address = display.removeprefix(name).lstrip(", ") if name else display
    name = name or "Gym (no name)"
    return Gym(name=name, address=address, lat=float(item["lat"]), lon=float(item["lon"]))


def search(city: str, *, url: str, user_agent: str, limit: int = 40) -> list[Gym]:
    key = city.strip().lower()
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_SECONDS:
        return cached[1]

    try:
        response = requests.get(
            url,
            params={
                "q": f"[leisure=fitness_centre] {city.strip()}",
                "format": "jsonv2",
                "countrycodes": "es",
                "limit": limit,
            },
            headers={"User-Agent": user_agent, "Accept-Language": "es"},
            timeout=10,
        )
        response.raise_for_status()
        gyms = [_parse(item) for item in response.json()]
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise GymSearchError("The gym search service is not available right now.") from exc

    _CACHE[key] = (time.monotonic(), gyms)
    return gyms
