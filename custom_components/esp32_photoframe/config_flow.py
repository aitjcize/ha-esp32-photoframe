"""Config flow for ESP32 PhotoFrame integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .const import CONF_HA_URL, DOMAIN, IMAGE_ENDPOINT_PATH

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    # Auto-detect HA URL if not provided
    ha_url = data.get(CONF_HA_URL) or get_url(hass)

    # Ensure host has http:// prefix
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"

    # Test connection to photoframe and fetch device name
    session = async_get_clientsession(hass)
    device_name = None
    try:
        async with session.get(
            f"{host}/api/config", timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                raise CannotConnect(f"HTTP {response.status}")
            config_data = await response.json()
            device_name = config_data.get("device_name", "ESP32-PhotoFrame")
            device_id = config_data.get("device_id")
    except aiohttp.ClientError as err:
        raise CannotConnect(f"Connection failed: {err}")
    except Exception as err:
        raise CannotConnect(f"Unexpected error: {err}")

    # Check if another device with the same name already exists
    if device_name:
        for entry in hass.config_entries.async_entries(DOMAIN):
            existing_device_name = entry.data.get("device_name")
            if existing_device_name == device_name:
                raise DuplicateDeviceName(
                    f"A device with name '{device_name}' is already configured. "
                    "Please change the device name on the PhotoFrame and try again."
                )

    # Configure the photoframe with HA URL
    try:
        async with session.post(
            f"{host}/api/config",
            json={"ha_url": ha_url},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status != 200:
                _LOGGER.warning(
                    "Failed to set HA URL on photoframe: HTTP %s", response.status
                )
    except Exception as err:
        _LOGGER.warning("Failed to set HA URL on photoframe: %s", err)

    # Return info that you want to store in the config entry.
    return {
        "title": (
            f"PhotoFrame ({device_name})" if device_name else f"PhotoFrame ({host})"
        ),
        "host": host,
        "ha_url": ha_url,
        "device_name": device_name,
        "device_id": device_id,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ESP32 PhotoFrame."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_info: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except DuplicateDeviceName as err:
                errors["base"] = "duplicate_device_name"
                _LOGGER.warning("Duplicate device name detected: %s", err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Store device info and show confirmation step
                self._device_info = info
                return await self.async_step_confirm()

        # Prefill host with photoframe.local or preserve user input
        if user_input is not None:
            # Preserve user input when showing errors
            suggested_values = user_input
        else:
            # Initial form, suggest photoframe.local
            suggested_values = {
                CONF_HOST: "photoframe.local",
            }

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, suggested_values
            ),
            errors=errors,
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the confirmation step."""
        if user_input is not None:
            # User confirmed, create the entry
            info = self._device_info
            await self.async_set_unique_id(info["host"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=info["title"],
                data={
                    CONF_HOST: info["host"],
                    CONF_HA_URL: info["ha_url"],
                    "device_name": info.get("device_name"),
                    "device_id": info.get("device_id"),
                },
            )

        # Show confirmation with device name
        device_name = self._device_info.get("device_name", "Unknown")
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {}
            ),  # Empty schema - no input fields, just submit button
            description_placeholders={"device_name": device_name},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow.

        HA >= 2024.12 populates `self.config_entry` on the OptionsFlow
        instance automatically; passing it to the constructor raises
        `TypeError: OptionsFlowHandler() takes no arguments`.
        """
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update HA URL and optionally image URL on the photoframe
            host = self.config_entry.data[CONF_HOST]
            ha_url = user_input[CONF_HA_URL]
            use_ha_images = user_input.get("use_ha_images", False)

            session = async_get_clientsession(self.hass)

            # Build config to send to photoframe
            config_data = {"ha_url": ha_url}

            # Only set image_url if user wants to use HA image serving
            if use_ha_images:
                image_url = f"{ha_url}{IMAGE_ENDPOINT_PATH}"
                config_data["image_url"] = image_url
                _LOGGER.info(
                    "Configuring photoframe to fetch images from HA: %s", image_url
                )

            try:
                async with session.post(
                    f"{host}/api/config",
                    json=config_data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        _LOGGER.warning("Failed to update config on photoframe")
            except Exception as err:
                _LOGGER.warning("Failed to update config: %s", err)

            return self.async_create_entry(title="", data=user_input)

        # Get list of camera and image entities for selection
        from homeassistant.helpers import entity_registry as er

        entity_reg = er.async_get(self.hass)
        camera_entities = [
            entity.entity_id
            for entity in entity_reg.entities.values()
            if entity.domain in ("camera", "image")
        ]

        # Add state-based entities as well
        for state in self.hass.states.async_all():
            if (
                state.domain in ("camera", "image")
                and state.entity_id not in camera_entities
            ):
                camera_entities.append(state.entity_id)

        camera_entities.sort()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HA_URL,
                        default=self.config_entry.data.get(CONF_HA_URL, ""),
                    ): str,
                    vol.Optional(
                        "use_ha_images",
                        default=self.config_entry.options.get("use_ha_images", False),
                    ): bool,
                    vol.Optional(
                        "media_entity_id",
                        default=self.config_entry.options.get("media_entity_id", ""),
                    ): vol.In([""] + camera_entities),
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class DuplicateDeviceName(Exception):
    """Error to indicate device name is already in use."""
