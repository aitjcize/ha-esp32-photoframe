"""Constants for the ESP32 PhotoFrame integration."""

DOMAIN = "esp32_photoframe"

# Configuration
CONF_HOST = "host"
CONF_HA_URL = "ha_url"

# Default values
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_PORT = 80

# API endpoints
API_CONFIG = "/api/config"
API_BATTERY = "/api/battery"
API_SENSOR = "/api/sensor"
API_SYSTEM_INFO = "/api/system-info"
API_DISPLAY_IMAGE = "/api/display-image"
API_ROTATE = "/api/rotate"
API_OTA_STATUS = "/api/ota/status"
API_CURRENT_IMAGE = "/api/current_image"
API_PROCESSING_SETTINGS = "/api/settings/processing"

# Services
SERVICE_ROTATE = "rotate"
SERVICE_DISPLAY_IMAGE = "display_image"

# Image serving. Each frame fetches IMAGE_ENDPOINT_PATH/<its image token>; the
# bare path (what older releases configured) serves nothing.
IMAGE_ENDPOINT_PATH = "/api/esp32_photoframe/image"
CONF_IMAGE_TOKEN = "image_token"
# Options: refuse image requests from outside the local network (default on),
# and the frame's own image URL from before "Use HA images" was turned on
CONF_IMAGE_LOCAL_ONLY = "image_local_only"
CONF_PREVIOUS_IMAGE_URL = "previous_image_url"
