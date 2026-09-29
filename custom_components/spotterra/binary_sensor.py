"""Binární senzory: je nad domem něco zajímavého, běží tiché hodiny."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import api
from .entita import SpotterraEntita

KLICE = {"je_zajimave": "mdi:star", "tiche_hodiny": "mdi:bell-sleep"}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities(SpotterraBinarni(c, k, i) for k, i in KLICE.items())


class SpotterraBinarni(SpotterraEntita, BinarySensorEntity):
    def __init__(self, coordinator, klic: str, ikona: str) -> None:
        super().__init__(coordinator, klic)
        self._attr_icon = ikona

    @property
    def is_on(self) -> bool | None:
        return api.hodnota(self.coordinator.data, self._klic)
