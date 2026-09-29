"""Entita události: poslední hlášení ze Spotterry (karta, historie).

Pro automatizace je pohodlnější událost na sběrnici `spotterra_udalost`
(vystřeluje ji koordinátor); tahle entita je tu kvůli kartě a logbooku.
"""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DRUHY_UDALOSTI
from .entita import SpotterraEntita


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SpotterraUdalost(entry.runtime_data)])


class SpotterraUdalost(SpotterraEntita, EventEntity):
    _attr_event_types = DRUHY_UDALOSTI
    _attr_icon = "mdi:airplane-alert"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "udalost")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.posluchaci_udalosti.append(self._prisla)
        self.async_on_remove(
            lambda: self.coordinator.posluchaci_udalosti.remove(self._prisla))

    @callback
    def _prisla(self, u: dict) -> None:
        druh = u.get("druh") if u.get("druh") in DRUHY_UDALOSTI else "alert"
        self._trigger_event(druh, {
            "nadpis": u.get("nadpis"),
            "text": u.get("text"),
            "tts_text": u.get("tts_text"),
            "hex": u.get("hex"),
            "url": u.get("url"),
        })
        self.async_write_ha_state()
