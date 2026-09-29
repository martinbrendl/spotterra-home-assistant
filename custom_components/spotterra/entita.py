"""Společný základ entit: jedno zařízení „Spotterra" na nastavení."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SpotterraCoordinator


class SpotterraEntita(CoordinatorEntity[SpotterraCoordinator]):
    _attr_has_entity_name = True
    _attr_attribution = "Data: Spotterra · adsb.lol (ODbL) · CelesTrak"

    def __init__(self, coordinator: SpotterraCoordinator, klic: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._klic = klic
        self._attr_unique_id = f"{entry.entry_id}_{klic}"
        self._attr_translation_key = klic
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Spotterra",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://spotterra.com/settings?tab=account#home-assistant-integrace",
        )
