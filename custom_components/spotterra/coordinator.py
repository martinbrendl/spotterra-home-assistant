"""Jeden dotaz co 30 s: stav i nové události.

Nové události se vystřelí dvakrát: jako entita `event.spotterra_*`
(pro kartu a historii) a jako událost na sběrnici `spotterra_udalost`
(pro blueprint hlásiče — šablony nad `trigger.event.data` jsou čitelnější
než nad atributy entity).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import api
from .const import BUS_UDALOST, CONF_TOKEN, CONF_URL, DEFAULT_URL, DOMAIN, SCAN_INTERVAL_S

_LOGGER = logging.getLogger(__name__)


class SpotterraCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_S),
        )
        self.api = api.SpotterraApi(
            async_get_clientsession(hass),
            entry.data[CONF_TOKEN],
            entry.data.get(CONF_URL) or DEFAULT_URL,
        )
        # Posluchači z event platformy; plní je `event.py`.
        self.posluchaci_udalosti: list = []

    async def _async_update_data(self) -> dict:
        try:
            d = await self.api.stav()
        except api.SpotterraAuthError as exc:
            # Token zrušený v nastavení Spotterry → HA nabídne nový.
            raise ConfigEntryAuthFailed("token") from exc
        except api.SpotterraError as exc:
            raise UpdateFailed(str(exc)) from exc

        for u in api.udalosti(d):
            self.hass.bus.async_fire(BUS_UDALOST, {
                "druh": u.get("druh"),
                "nadpis": u.get("nadpis"),
                "text": u.get("text"),
                "tts_text": u.get("tts_text"),
                "hex": u.get("hex"),
                "url": u.get("url"),
                "id": u.get("id"),
            })
            for posluchac in self.posluchaci_udalosti:
                posluchac(u)
        return d
