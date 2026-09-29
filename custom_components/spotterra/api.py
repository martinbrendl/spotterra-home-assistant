"""Klient serveru Spotterra — BEZ importu Home Assistantu.

Veškerá logika integrace, kterou jde zkazit tiše, je tady: HTTP, kurzor
událostí, výběr hodnot pro senzory. Napojení na Home Assistant
(`coordinator.py`, `sensor.py`…) je tenké a jen tohle volá. Důvod je
praktický: tenhle modul jde testovat obyčejným pytestem bez instalace
Home Assistantu (`tests/test_api.py`).

JEDEN DOTAZ CO 30 S. `GET /api/ha/v1/stav?od=<kurzor>` vrátí stav
i nové události najednou. Žádné trvalé spojení — krátký dotaz je
šetrnější k serveru i k Home Assistantu.
"""
from __future__ import annotations

from typing import Any


class SpotterraError(Exception):
    """Server nedostupný nebo odpověď nedává smysl — zkusí se znovu."""


class SpotterraAuthError(SpotterraError):
    """Token neplatí (zrušený v nastavení Spotterry) — potřeba nový."""


# Verze tvaru odpovědi, kterou tahle integrace umí číst. Vyšší verze
# se nečte naslepo: senzor, který ukazuje špatné číslo, je horší než
# senzor, který přizná, že nerozumí.
PODPOROVANE_VERZE = {1}


class SpotterraApi:
    """Tenký klient. `session` je aiohttp ClientSession z Home Assistantu."""

    def __init__(self, session, token: str, url: str):
        self._session = session
        self._token = (token or "").strip()
        self._url = (url or "").rstrip("/")
        # Kurzor událostí drží klient, ne server: server si nepamatuje,
        # kolik Home Assistantů se ptá. None = ještě jsme se nesrovnali
        # a server vydá prázdný seznam + aktuální kurzor.
        self.kurzor: int | None = None

    async def stav(self) -> dict[str, Any]:
        """Stav + nové události. Posune kurzor až PO úspěšném přečtení."""
        params = {} if self.kurzor is None else {"od": str(self.kurzor)}
        try:
            async with self._session.get(
                f"{self._url}/api/ha/v1/stav",
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=_timeout(15),
            ) as r:
                if r.status == 401:
                    raise SpotterraAuthError("token")
                if r.status == 429:
                    raise SpotterraError("rate_limit")
                if r.status != 200:
                    raise SpotterraError(f"http_{r.status}")
                d = await r.json()
        except SpotterraError:
            raise
        except Exception as exc:  # síť, timeout, rozbitý JSON
            raise SpotterraError(type(exc).__name__) from exc
        d = over_tvar(d)
        # Kurzor až po ověření tvaru: rozbitá odpověď nesmí posunout
        # kurzor přes události, které jsme nikdy neviděli.
        self.kurzor = int(d.get("kurzor") or 0)
        return d


def _timeout(s: float):
    try:
        import aiohttp
        return aiohttp.ClientTimeout(total=s)
    except ImportError:  # testy bez aiohttp
        return s


def over_tvar(d: Any) -> dict[str, Any]:
    """Odpověď serveru, nebo SpotterraError, když jí nerozumíme."""
    if not isinstance(d, dict):
        raise SpotterraError("tvar")
    if d.get("verze") not in PODPOROVANE_VERZE:
        raise SpotterraError(f"verze_{d.get('verze')}")
    d.setdefault("udalosti", [])
    if not isinstance(d["udalosti"], list):
        raise SpotterraError("udalosti")
    return d


# ---------------------------------------------------------------- hodnoty

def nazev_stroje(p: dict | None) -> str | None:
    """Čím stroj pojmenovat: typ → volací znak → registrace → hex.

    ADS-B často nenese typ (hlavně malá letadla a vrtulníky). „Neznámý"
    u letadla, které právě letí nad domem, zní jako porucha; volací znak
    je pravdivá odpověď.
    """
    if not p:
        return None
    return (p.get("typ_nazev") or p.get("typ") or p.get("volaci_znak")
            or p.get("registrace") or p.get("hex") or None)


def hodnota(d: dict | None, klic: str):
    """Hodnota pro senzor podle klíče. Jediné místo, které zná tvar stavu.

    Senzory i binární senzory se ptají JEN přes tuhle funkci. Kdyby si
    každý sahal do slovníku po svém, rozešly by se při první změně tvaru
    na serveru.
    """
    if not d:
        return None
    if klic == "nad_domem":
        return d.get("nad_domem")
    if klic == "zajimave":
        return d.get("zajimave")
    if klic == "dalsi_prulet_min":
        p = d.get("dalsi_prulet") or {}
        return p.get("za_min")
    if klic == "dalsi_prulet_typ":
        return nazev_stroje(d.get("dalsi_prulet"))
    if klic == "nejblizsi_zajimave":
        return nazev_stroje(d.get("nejzajimavejsi"))
    if klic == "iss_zacatek":
        i = d.get("iss") or {}
        return i.get("zacatek")
    if klic == "iss_elevace":
        i = d.get("iss") or {}
        return i.get("max_elev")
    if klic == "tiche_hodiny":
        return bool(d.get("tiche_hodiny"))
    if klic == "je_zajimave":
        return int(d.get("zajimave") or 0) > 0
    raise KeyError(klic)


def atributy(d: dict | None, klic: str) -> dict:
    """Doplňkové atributy senzoru — detail stroje, věta pro reproduktor."""
    if not d:
        return {}
    if klic in ("dalsi_prulet_min", "dalsi_prulet_typ"):
        return dict(d.get("dalsi_prulet") or {})
    if klic == "nejblizsi_zajimave":
        return dict(d.get("nejzajimavejsi") or {})
    if klic in ("iss_zacatek", "iss_elevace"):
        return dict(d.get("iss") or {})
    if klic == "nad_domem":
        return {"letadla": list(d.get("letadla") or [])[:10]}
    return {}


def udalosti(d: dict | None) -> list[dict]:
    """Nové události k vystřelení — vzestupně podle id, bez duplicit.

    Server je vydává seřazené a jen jednou, ale integrace to nebere za
    dané: dvakrát přečtená věta z reproduktoru je chyba, kterou uživatel
    slyší, ne jen vidí.
    """
    videno = set()
    ven = []
    for u in sorted((d or {}).get("udalosti") or [], key=lambda u: u.get("id") or 0):
        uid = u.get("id")
        if uid in videno:
            continue
        videno.add(uid)
        ven.append(u)
    return ven
