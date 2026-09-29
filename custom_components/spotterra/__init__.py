"""Spotterra pro Home Assistant.

Co je nad tebou, příští přelet, příští průlet ISS — a události
s hotovou větou pro reproduktor. Stav i události přichází jedním
dotazem co 30 s (`coordinator.py`); veškerá logika je v `api.py`,
aby šla testovat bez Home Assistantu.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SpotterraCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.EVENT]

type SpotterraConfigEntry = ConfigEntry[SpotterraCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SpotterraConfigEntry) -> bool:
    coordinator = SpotterraCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpotterraConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
