"""Senzory. Hodnotu i atributy bere JEN přes `api.hodnota`/`api.atributy`,
aby tvar odpovědi znalo jedno místo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import DEGREE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import api
from .entita import SpotterraEntita


@dataclass(frozen=True, kw_only=True)
class Popis(SensorEntityDescription):
    cas: bool = False          # hodnota je unix ts → datetime


POPISY: tuple[Popis, ...] = (
    Popis(key="nad_domem", icon="mdi:airplane",
          state_class=SensorStateClass.MEASUREMENT),
    Popis(key="zajimave", icon="mdi:star-circle-outline",
          state_class=SensorStateClass.MEASUREMENT),
    Popis(key="dalsi_prulet_min", icon="mdi:airplane-clock",
          device_class=SensorDeviceClass.DURATION,
          native_unit_of_measurement=UnitOfTime.MINUTES),
    Popis(key="dalsi_prulet_typ", icon="mdi:airplane-search"),
    Popis(key="nejblizsi_zajimave", icon="mdi:star-shooting-outline"),
    Popis(key="iss_zacatek", icon="mdi:space-station",
          device_class=SensorDeviceClass.TIMESTAMP, cas=True),
    Popis(key="iss_elevace", icon="mdi:angle-acute",
          native_unit_of_measurement=DEGREE),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities(SpotterraSenzor(c, p) for p in POPISY)


class SpotterraSenzor(SpotterraEntita, SensorEntity):
    entity_description: Popis

    def __init__(self, coordinator, popis: Popis) -> None:
        super().__init__(coordinator, popis.key)
        self.entity_description = popis

    @property
    def native_value(self):
        v = api.hodnota(self.coordinator.data, self._klic)
        if v is not None and self.entity_description.cas:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        return v

    @property
    def extra_state_attributes(self):
        return api.atributy(self.coordinator.data, self._klic)
