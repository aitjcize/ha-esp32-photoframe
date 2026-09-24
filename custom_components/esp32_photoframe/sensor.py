"""Sensor platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PhotoFrameCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameBatterySensor(coordinator, entry),
        PhotoFrameBatteryVoltageSensor(coordinator, entry),
        PhotoFrameChargingSensor(coordinator, entry),
        PhotoFrameUSBConnectedSensor(coordinator, entry),
        PhotoFrameBatteryConnectedSensor(coordinator, entry),
        PhotoFrameOnlineSensor(coordinator, entry),
        PhotoFrameTemperatureSensor(coordinator, entry),
        PhotoFrameHumiditySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameBatterySensor(CoordinatorEntity, SensorEntity):
    """Battery level sensor for PhotoFrame."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery_level"
        self._attr_name = "Battery level"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Battery sensor always available to show last known value."""
        return True

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        battery_data = self.coordinator.data.get("battery", {})
        return battery_data.get("battery_level")


class PhotoFrameBatteryVoltageSensor(CoordinatorEntity, SensorEntity):
    """Battery voltage sensor for PhotoFrame."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery_voltage"
        self._attr_name = "Battery voltage"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Battery voltage sensor always available to show last known value."""
        return True

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        battery_data = self.coordinator.data.get("battery", {})
        voltage = battery_data.get("battery_voltage")
        if voltage is not None:
            return voltage / 1000.0  # Convert mV to V
        return None


class PhotoFrameChargingSensor(CoordinatorEntity, BinarySensorEntity):
    """Battery charging sensor for PhotoFrame."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_has_entity_name = True

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_charging"
        self._attr_name = "Charging"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Charging sensor always available to show last known value."""
        return True

    @property
    def is_on(self) -> bool | None:
        """Return true if battery is charging."""
        battery_data = self.coordinator.data.get("battery", {})
        return battery_data.get("charging")


class PhotoFrameUSBConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    """USB connection sensor for PhotoFrame."""

    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_has_entity_name = True

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_usb_connected"
        self._attr_name = "USB connected"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """USB connected sensor always available to show last known value."""
        return True

    @property
    def is_on(self) -> bool | None:
        """Return true if USB is connected."""
        battery_data = self.coordinator.data.get("battery", {})
        return battery_data.get("usb_connected")


class PhotoFrameBatteryConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    """Battery connection sensor for PhotoFrame."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery_connected"
        self._attr_name = "Battery connected"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Battery connected sensor always available to show last known value."""
        return True

    @property
    def is_on(self) -> bool | None:
        """Return true if battery is connected."""
        battery_data = self.coordinator.data.get("battery", {})
        return battery_data.get("battery_connected")


class PhotoFrameOnlineSensor(CoordinatorEntity, BinarySensorEntity):
    """Device online status sensor for PhotoFrame."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_online"
        self._attr_name = "Online"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if device is online.

        Device is considered online if:
        1. Explicit _device_online flag is True (set by online/offline notifications), AND
        2. Either last_update_success is True OR last update was within timeout period
        """
        from datetime import datetime, timedelta

        # If device explicitly notified offline, it's offline
        if not self.coordinator._device_online:
            return False

        # Check if we have recent successful update
        if self.coordinator.last_update_success:
            return True

        # Check timeout-based offline detection
        if self.coordinator._last_update_time:
            time_since_update = datetime.now() - self.coordinator._last_update_time
            # Consider online if updated within the last 2 minutes
            return time_since_update < timedelta(minutes=2)

        # No update time recorded, assume offline
        return False

    @property
    def available(self) -> bool:
        """This sensor is always available to show online/offline state."""
        return True


class PhotoFrameTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Temperature sensor for PhotoFrame."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_temperature"
        self._attr_name = "Temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Temperature sensor always available to show last known value."""
        return True

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        sensor_data = self.coordinator.data.get("sensor", {})
        return sensor_data.get("temperature")


class PhotoFrameHumiditySensor(CoordinatorEntity, SensorEntity):
    """Humidity sensor for PhotoFrame."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_humidity"
        self._attr_name = "Humidity"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Humidity sensor always available to show last known value."""
        return True

    @property
    def native_value(self) -> float | None:
        """Return the humidity value."""
        sensor_data = self.coordinator.data.get("sensor", {})
        return sensor_data.get("humidity")
