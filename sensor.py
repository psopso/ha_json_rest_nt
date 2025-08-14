from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import PLATFORM_SCHEMA

import requests
import json
import voluptuous as vol
import logging
import datetime

import homeassistant.helpers.config_validation as cv

from .functions import check_time_in_intervals_by_weekday, get_nttarifftable

CONF_METER_NO = "MeterNo"
CONF_CEZ_URL = "CEZ URL"

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_METER_NO): cv.string,
        vol.Required(CONF_CEZ_URL): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    sensor = NTTariffSensor(config.get(CONF_METER_NO), config.get(CONF_CEZ_URL))
    async_add_entities([sensor])

    async def handle_update_service(call):
        """Načte JSON ze souboru a aktualizuje senzor."""
        try:
            """
            if not os.path.exists(FILE_PATH):
                sensor.update_from_data({"low_tariff": "Soubor nenalezen"})
                return

            with open(FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            """

            statuscode,responsetext = await get_nttarifftable(hass, sensor._cez_url, sensor._meter_no)
            sensor.update_from_data(responsetext)

        except Exception as e:
            _LOGGER.info(f"Chyba: {e}")
            sensor._attr_native_value = "Chyba"

        # Oznámíme HA, že se hodnota senzoru změnila
        sensor.async_write_ha_state()

    # Registrace služby
    hass.services.async_register(
        domain="ha_json_rest_nt",
        service="nttariff_update",
        service_func=handle_update_service
    )

    # Volání služby z integrace
    await sensor.hass.services.async_call(
        "ha_json_rest_nt",         # doména integrace
        "nttariff_update",      # název služby
        {
        }
    )    

    async def hourly_callback(now):
        """Funkce, která se spustí každou hodinu."""
        _LOGGER.info("Hodinová úloha běží! Čas: %s", now)
        # Zde můžeš udělat libovolnou akci:
        # např. čtení API, aktualizace entity, zápis do souboru atd.

    # Spustí hourly_callback každých 60 minut
    async_track_time_interval(hass, hourly_callback, timedelta(minutes=1))


class NTTariffSensor(SensorEntity):
    def __init__(self, meter_no, cez_url):
        self._attr_name = "Sensor nizkeho tarifu"
        self._attr_unique_id = "ha_json_rest_nt"
        self._data = {}
        self._attr_native_value = None
        self._meter_no = meter_no
        self._cez_url = cez_url
        self._custom_attributes = { "NTInterval": "", "TimeString": "" }
    
    @property
    def extra_state_attributes(self):
        return self._custom_attributes

    @property
    def native_value(self):
        return self._attr_native_value

    def update_from_data(self, data):
        """Aktualizace dat uložených v senzoru."""
        self._data = data

    def update(self):
        try:
            now = datetime.datetime.now()
            padne, NTInterval = check_time_in_intervals_by_weekday(self._data, now)
            if padne:
                self._attr_native_value = "+"
                self._custom_attributes["NTInterval"] = NTInterval
            else:
                self._attr_native_value = "-"
                self._custom_attributes["NTInterval"] = NTInterval
            formatted_string = now.strftime("%H:%M")
            self._custom_attributes["TimeString"] = formatted_string

        except Exception as e:
            self._attr_native_value = "Chyba"

