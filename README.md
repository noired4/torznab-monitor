# Torznab Monitor

Torznab Monitor is a Python application that monitors Torznab feeds and sends notifications via Notifiarr when new items matching specific categories are found.

## Features

- Monitors multiple Torznab endpoints
- Configurable category filtering
- Notifications via Notifiarr (Discord)
- Configurable polling intervals
- Flexible notification mapping system
- Debug logging support
- Skip initialization option for testing

## Configuration

### Main Configuration (config.json)

```json
{
    "torznab": {
        "endpoints": {
            "endpoint1": {
                "url": "http://your-prowlarr-host:9696/11/api?apikey=YOUR_API_KEY&extended=1&t=search",
                "categories": ["100069"],
                "poll_interval": 1800
            }
        }
    },
    "notifiarr": {
        "url": "https://notifiarr.com/api/v1/notification/passthrough",
        "api_key": "YOUR_NOTIFIARR_API_KEY",
        "discord": {
            "channel_id": YOUR_DISCORD_CHANNEL_ID
        }
    }
}
```

### Notification Mapping (notification_mapping.json)

```json
{
    "mappings": {
        "endpoint1-notifiarr": {
            "title": {
                "type": "xml_tag",
                "path": "title"
            },
            "name": {
                "type": "static",
                "value": "New torrent available"
            },
            "description": {
                "type": "xml_tag",
                "path": "comments"
            },
            "image": {
                "type": "torznab_attr",
                "name": "coverurl",
                "select": "first"
            },
            "thumbnail": {
                "type": "static",
                "value": "https://example.com/thumbnail.png"
            },
            "icon": {
                "type": "static",
                "value": "https://example.com/favicon.ico"
            }
        }
    }
}
```

## Installation

### Local Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `config.json.example` to `config.json` and update with your settings
4. Copy `notification_mapping.json.example` to `notification_mapping.json` and update with your settings

### Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t torznab-monitor .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name torznab-monitor \
     -v $(pwd)/config:/config \
     -v $(pwd)/data:/app/data \
     torznab-monitor
   ```

## Usage

### Basic Usage

```bash
python main.py
```

### Command Line Options

- `--skip-init`: Skip initializing seen items (useful for testing)
- `--config`: Specify a custom config file path (default: config.json)
- `--mapping`: Specify a custom mapping file path (default: notification_mapping.json)
- `--debug`: Enable debug logging


Examples:
```bash
# Run with debug logging
python main.py --debug

# Skip initialization
python main.py --skip-init

# Use custom config
python main.py --config custom_config.json --mapping custom_mapping.json

# Combine options
python main.py --debug --skip-init
```

## Notification Mapping Types

The notification mapping system supports three types of mappings:

1. `xml_tag`: Extract values from XML tags
   ```json
   {
       "type": "xml_tag",
       "path": "title"
   }
   ```

2. `torznab_attr`: Extract values from Torznab attributes
   ```json
   {
       "type": "torznab_attr",
       "name": "coverurl",
       "select": "first"
   }
   ```

3. `static`: Use static string values
   ```json
   {
       "type": "static",
       "value": "New torrent available"
   }
   ```

## License

[MIT](LICENSE)