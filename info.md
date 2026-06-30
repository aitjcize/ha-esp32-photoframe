# ESP32 PhotoFrame Integration

Home Assistant companion integration for the [ESP32 PhotoFrame](https://github.com/aitjcize/esp32-photoframe) firmware.

This integration provides Home Assistant control and monitoring for e-ink photoframes running the ESP32 PhotoFrame firmware. It is panel-agnostic — both 6-color (Spectra) and 16-level grayscale (GC16) boards are supported (Waveshare PhotoPainter, Seeed Studio XIAO EE02/EE04, reTerminal E1002/E1003/E1004).

## Features

- **Battery Monitoring**: Track battery level and voltage
- **Auto-Rotate**: Automatically rotate images from SD card or URL
- **Deep Sleep**: Battery-saving deep sleep mode
- **URL Rotation**: Fetch images from any URL or Home Assistant camera/image entities
- **Manual Control**: Rotate images on demand via button or service
- **Display Service**: Send images from HA cameras directly to the photoframe

## Device Controls

- **Auto rotate** - Enable/disable automatic image rotation
- **Deep sleep** - Enable/disable deep sleep for battery saving
- **Use HA images** - Toggle Home Assistant image serving
- **Rotation mode** - Choose between SD card or URL rotation
- **Media source** - Select which camera/image entity to display
- **Rotate interval** - Set rotation interval in seconds
- **Image URL** - Configure custom image URL

## Services

### `esp32_photoframe.rotate`
Manually trigger image rotation (same as pressing the KEY button).

### `esp32_photoframe.display_image`
Display an image from a camera or image entity on the PhotoFrame.

**Parameters:**
- `entity_id` (required): Camera or image entity to display

**Example:**
```yaml
service: esp32_photoframe.display_image
data:
  entity_id: camera.front_door
target:
  device_id: <your_photoframe_device_id>
```

## Setup

1. Install via HACS or manually copy to `custom_components/esp32_photoframe`
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "ESP32 PhotoFrame"
5. Enter your PhotoFrame hostname (default: `photoframe.local`)
6. If battery-powered and device appears offline, press the BOOT button to wake it up

## Configuration

After adding the device, you can configure:

- **Use HA Images**: Enable to serve images from Home Assistant
- **Media Source**: Select which camera/image entity to serve
- All other settings are available as device controls

## Requirements

- ESP32-S3 PhotoPainter device with the photoframe firmware
- Home Assistant 2024.1.0 or newer
- Device must be on the same network as Home Assistant

## Support

For issues and feature requests, please visit:
https://github.com/aitjcize/esp32-photoframe
