# ESP32 PhotoFrame Home Assistant Integration

Home Assistant companion integration for the [ESP32 PhotoFrame](https://github.com/aitjcize/esp32-photoframe) firmware.

This custom integration provides comprehensive control and monitoring for e-ink photoframes running the ESP32 PhotoFrame firmware. It is panel-agnostic — it works with both **6-color (Spectra)** and **16-level grayscale (GC16)** boards (Waveshare PhotoPainter, Seeed Studio XIAO EE02/EE04, and reTerminal E1002/E1003/E1004), since image conversion is handled on-device.

## Features

- **Device Configuration**: Control auto-rotate, rotation mode, deep sleep, and image URL settings
- **Battery Monitoring**: Track battery level and voltage when device is always-on (USB powered or deep sleep disabled)
- **Image Serving**: Serve images from Home Assistant camera/image entities to the photoframe
- **Services**: Control photoframe settings and display images via Home Assistant automations

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "ESP32 PhotoFrame" in HACS integrations
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/esp32_photoframe` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "ESP32 PhotoFrame"
4. Enter your PhotoFrame hostname (default: `photoframe.local`)
   - 💡 **Tip**: If battery-powered and device appears offline, press the BOOT button to wake it up

The integration will automatically detect your Home Assistant URL and configure the photoframe.

### Device Controls

All settings are available as device controls - no need to dig into configuration options!

- **Use HA Images** switch - Enable to serve images from Home Assistant
- **Media Source** select - Choose which camera/image entity to display
- **Rotation Mode** select - Switch between storage or URL rotation
- **Auto Rotate** switch - Enable/disable automatic rotation
- **Auto Rotate Enabled Sensor** select - Only rotate while a chosen binary sensor is on
- **Deep Sleep** switch - Enable/disable deep sleep for battery saving
- **Rotation Schedule** text - Set when images rotate, using cron rules

## Usage

### Entities
The integration creates the following entities for easy control:

#### Switches
- `switch.esp32_photoframe_auto_rotate` - Toggle automatic image rotation
- `switch.esp32_photoframe_deep_sleep` - Enable/disable deep sleep mode
- `switch.esp32_photoframe_use_ha_images` - Enable/disable Home Assistant image serving

#### Numbers
- `number.esp32_photoframe_timezone_offset` - Set the timezone UTC offset

#### Selects
- `select.esp32_photoframe_rotation_mode` - Choose between "storage" or "url" rotation
- `select.esp32_photoframe_media_source` - Select which camera/image entity to serve
- `select.esp32_photoframe_auto_rotate_enabled_sensor` - Gate rotation on a `binary_sensor`: the frame only rotates while it is `on` ("None" = always). For complex conditions, point it at a Template binary-sensor helper.

#### Text Inputs
- `text.esp32_photoframe_rotation_schedule` - Set the rotation schedule as cron rules (`minute hour day-of-week`; separate multiple rules with `;`, e.g. `0 9 1-5; 0 18 0,6`)
- `text.esp32_photoframe_image_url` - Set the image URL for URL rotation mode
- `text.esp32_photoframe_home_assistant_url` - Configure Home Assistant URL

#### Buttons
- `button.esp32_photoframe_rotate_image` - Manually trigger image rotation (like pressing KEY button)

#### Sensors
- `sensor.esp32_photoframe_battery_level` - Battery percentage (shows last known value)
- `sensor.esp32_photoframe_battery_voltage` - Battery voltage in volts (shows last known value)

### Services

#### `esp32_photoframe.rotate`

Manually trigger image rotation (same as pressing the KEY button):

```yaml
service: esp32_photoframe.rotate
```

#### `esp32_photoframe.display_image`

Display an image from a camera or image entity:

```yaml
service: esp32_photoframe.display_image
data:
  entity_id: camera.front_door
```

### Image Serving for URL Rotation

When you configure a media entity in the integration options, the photoframe can fetch images from:

```
http://YOUR_HA_URL:8123/api/esp32_photoframe/image
```

**Setup for URL Rotation:**

1. Configure a camera or image entity in the integration options
2. Set the photoframe to URL rotation mode
3. The photoframe's image URL will be automatically set to the HA endpoint
4. Images from the selected entity will be served to the photoframe

## How It Works

### URL-Based Rotation with Home Assistant

1. **Setup**: During integration setup, the HA URL is sent to the photoframe via its `/api/config` endpoint
2. **Image Serving**: The integration registers an HTTP endpoint at `/api/esp32_photoframe/image`
3. **Photoframe Fetches**: When in URL rotation mode, the photoframe fetches images from this endpoint
4. **Dynamic Content**: The endpoint serves images from the configured camera/image entity
5. **Battery Reporting**: When the photoframe wakes up and has the HA URL configured, it posts battery data back to HA

### Deep Sleep vs Always-On

- **Deep Sleep Enabled**: Battery sensors are unavailable. Photoframe wakes periodically to rotate images.
- **Deep Sleep Disabled**: Battery sensors update every 60 seconds. Photoframe stays connected to WiFi.


## License

MIT License - See main photoframe repository for details
