"""Průvodce: token ze Spotterry (Nastavení → Účet → Home Assistant).

Token se před uložením OVĚŘÍ jedním dotazem. Integrace, která se uloží
s neplatným tokenem a pak jen tiše ukazuje „nedostupné", je horší než
průvodce, který rovnou řekne, co je špatně.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import api
from .const import CONF_TOKEN, CONF_URL, DEFAULT_URL, DOMAIN


async def _over(hass, token: str, url: str) -> tuple[dict | None, str | None]:
    klient = api.SpotterraApi(async_get_clientsession(hass), token, url)
    try:
        return await klient.stav(), None
    except api.SpotterraAuthError:
        return None, "invalid_auth"
    except api.SpotterraError:
        return None, "cannot_connect"


class SpotterraConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        chyby: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            url = (user_input.get(CONF_URL) or DEFAULT_URL).rstrip("/")
            d, chyba = await _over(self.hass, token, url)
            if chyba:
                chyby["base"] = chyba
            else:
                # Jedno nastavení na token. Týž token dvakrát by vyrobil
                # dvě sady entit a hlásič by každou větu řekl dvakrát.
                await self.async_set_unique_id(token[:8] + "|" + url)
                self._abort_if_unique_id_configured()
                nazev = ((d or {}).get("domov") or {}).get("nazev") or "Spotterra"
                return self.async_create_entry(
                    title=nazev, data={CONF_TOKEN: token, CONF_URL: url})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_TOKEN): str,
                vol.Optional(CONF_URL, default=DEFAULT_URL): str,
            }),
            errors=chyby,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Token zrušený ve Spotterře → nový token, entity zůstanou."""
        chyby: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            url = entry.data.get(CONF_URL) or DEFAULT_URL
            _, chyba = await _over(self.hass, token, url)
            if chyba:
                chyby["base"] = chyba
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=chyby,
        )
