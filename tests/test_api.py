"""Klient integrace Spotterra — testy bez Home Assistantu.

Home Assistant 2026.9 potřebuje Python >= 3.14.2; tyhle testy běží bez něj,
protože veškerá logika, kterou jde zkazit tiše, je v `api.py`. Napojení
na HA (`coordinator.py`, entity) je tenké a tady se NETESTUJE — to je
známá mez, ne opomenutí.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "custom_components", "spotterra"))

import api  # noqa: E402


class _Odpoved:
    def __init__(self, status, telo):
        self.status = status
        self._telo = telo

    async def json(self):
        if isinstance(self._telo, Exception):
            raise self._telo
        return self._telo

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _Session:
    def __init__(self, odpovedi):
        self.odpovedi = list(odpovedi)
        self.volani = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.volani.append({"url": url, "params": dict(params or {}),
                            "headers": dict(headers or {})})
        o = self.odpovedi.pop(0)
        if isinstance(o, Exception):
            raise o
        return o


def _stav(**kw):
    d = {"verze": 1, "nad_domem": 7, "zajimave": 1, "kurzor": 12,
         "udalosti": [], "tiche_hodiny": False}
    d.update(kw)
    return d


def _run(c):
    return asyncio.run(c)


class TestKurzor:
    def test_JADRO_prvni_dotaz_bez_kurzoru(self):
        """Bez `od` server nic nevydá a jen srovná kurzor. Kdyby integrace
        poslala od=0, reproduktor by po restartu HA přečetl celou frontu."""
        s = _Session([_Odpoved(200, _stav(kurzor=12))])
        a = api.SpotterraApi(s, "sp_x", "https://spotterra.com")
        _run(a.stav())
        assert "od" not in s.volani[0]["params"]
        assert a.kurzor == 12

    def test_dalsi_dotaz_s_kurzorem(self):
        s = _Session([_Odpoved(200, _stav(kurzor=12)), _Odpoved(200, _stav(kurzor=14))])
        a = api.SpotterraApi(s, "sp_x", "https://spotterra.com")
        _run(a.stav())
        _run(a.stav())
        assert s.volani[1]["params"] == {"od": "12"}
        assert a.kurzor == 14

    def test_JADRO_chyba_kurzor_neposune(self):
        """Rozbitá odpověď nesmí posunout kurzor přes události, které
        integrace nikdy neviděla."""
        s = _Session([_Odpoved(200, _stav(kurzor=12)),
                      _Odpoved(200, {"verze": 99, "kurzor": 50})])
        a = api.SpotterraApi(s, "sp_x", "https://spotterra.com")
        _run(a.stav())
        with pytest.raises(api.SpotterraError):
            _run(a.stav())
        assert a.kurzor == 12


class TestChyby:
    def test_JADRO_401_je_auth_chyba(self):
        """Zrušený token v nastavení Spotterry → HA musí nabídnout nový
        (reauth), ne donekonečna zkoušet."""
        a = api.SpotterraApi(_Session([_Odpoved(401, {})]), "sp_x", "https://s")
        with pytest.raises(api.SpotterraAuthError):
            _run(a.stav())

    @pytest.mark.parametrize("status", [429, 500, 502, 503])
    def test_ostatni_http_chyby_jsou_docasne(self, status):
        a = api.SpotterraApi(_Session([_Odpoved(status, {})]), "sp_x", "https://s")
        with pytest.raises(api.SpotterraError) as e:
            _run(a.stav())
        assert not isinstance(e.value, api.SpotterraAuthError)

    def test_sit_je_docasna_chyba(self):
        a = api.SpotterraApi(_Session([OSError("dns")]), "sp_x", "https://s")
        with pytest.raises(api.SpotterraError):
            _run(a.stav())

    def test_JADRO_neznama_verze_se_necte_naslepo(self):
        """Senzor se špatným číslem je horší než senzor, který přizná,
        že nerozumí."""
        with pytest.raises(api.SpotterraError):
            api.over_tvar({"verze": 2})

    def test_token_jde_v_hlavicce_ne_v_url(self):
        """Token v URL by skončil v access logu i v historii."""
        s = _Session([_Odpoved(200, _stav())])
        _run(api.SpotterraApi(s, "sp_tajne", "https://s/").stav())
        assert s.volani[0]["headers"]["Authorization"] == "Bearer sp_tajne"
        assert "sp_tajne" not in s.volani[0]["url"]
        assert s.volani[0]["url"] == "https://s/api/ha/v1/stav"


class TestHodnoty:
    def test_dalsi_prulet(self):
        d = _stav(dalsi_prulet={"za_min": 6, "typ": "A388", "typ_nazev": "Airbus A380"})
        assert api.hodnota(d, "dalsi_prulet_min") == 6
        assert api.hodnota(d, "dalsi_prulet_typ") == "Airbus A380"
        assert api.atributy(d, "dalsi_prulet_min")["typ"] == "A388"

    def test_stroj_bez_typu_se_jmenuje_volacim_znakem(self):
        """ADS-B bez typu: místo „Neznámý" volací znak, pak registrace."""
        d = _stav(dalsi_prulet={"za_min": 0, "typ": None, "typ_nazev": None,
                                "volaci_znak": "WZZ84", "hex": "471f6a"},
                  nejzajimavejsi={"typ": None, "registrace": "OK-WIA", "hex": "49d3a1"})
        assert api.hodnota(d, "dalsi_prulet_typ") == "WZZ84"
        assert api.hodnota(d, "nejblizsi_zajimave") == "OK-WIA"
        assert api.hodnota(_stav(dalsi_prulet=None), "dalsi_prulet_typ") is None

    def test_bez_pruletu_neni_nula(self):
        """Žádný přelet = neznámo, ne „za 0 minut"."""
        assert api.hodnota(_stav(dalsi_prulet=None), "dalsi_prulet_min") is None

    def test_iss(self):
        d = _stav(iss={"zacatek": 1_800_000_000, "max_elev": 61, "tts_text": "ISS za 10 min."})
        assert api.hodnota(d, "iss_zacatek") == 1_800_000_000
        assert api.atributy(d, "iss_zacatek")["tts_text"] == "ISS za 10 min."

    def test_zajimave_jako_binarni(self):
        assert api.hodnota(_stav(zajimave=2), "je_zajimave") is True
        assert api.hodnota(_stav(zajimave=0), "je_zajimave") is False

    def test_neznamy_klic_je_chyba_ne_none(self):
        """Překlep v klíči senzoru by jinak tiše ukazoval „neznámo" navždy."""
        with pytest.raises(KeyError):
            api.hodnota(_stav(), "preklep")

    def test_prazdny_stav(self):
        assert api.hodnota(None, "nad_domem") is None
        assert api.atributy(None, "nad_domem") == {}


class TestUdalosti:
    def test_JADRO_zadna_udalost_dvakrat(self):
        """Dvakrát přečtená věta z reproduktoru je chyba, kterou člověk slyší."""
        d = _stav(udalosti=[{"id": 3, "text": "c"}, {"id": 2, "text": "b"},
                            {"id": 3, "text": "c"}])
        assert [u["id"] for u in api.udalosti(d)] == [2, 3]

    def test_prazdne(self):
        assert api.udalosti(None) == []
        assert api.udalosti(_stav()) == []
