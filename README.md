# gmaps-scraper

**Interactive Google Maps scraper with Tkinter confirmation**

`gmaps-scraper` lets you visually pick locations in Google Maps and captures the place name, coordinates, address, city, state, country, plus any custom fields you specify. Each pick pops up a dialog so you can review or add extra info before recording.

## Features

- **Live map interaction** via Selenium & Chrome
- Automatic extraction of:
  - Place name
  - Latitude & longitude
  - Full address
  - City, state, country (via Plus code)
- **Custom fields**: define required `*` or optional fields in your dialog
- **Repeatable picks**: after each capture, you’re asked “Keep going?” 
- Clean teardown of browser sessions

## Installation

```bash
pip install gmaps-scraper
```

## Usage

### Basic pick

```python
from gmaps_scraper import get_google_map_details

# Launch the map picker; no extra fields
data = get_google_map_details()
print(data)
# => { "Central Park": { "latitude": "...", "longitude": "...", ... } }
```

### With search term

```python
from gmaps_scraper import get_google_map_details

data = get_google_map_details(search_term="Empire State Building")
print(data)
```

### With custom fields

```python
from gmaps_scraper import get_google_map_details

data = get_google_map_details(
    additional_required=['Contact', 'Phone'],
    additional_optional=['Notes']
)
print(data)
```
In the confirmation dialog box:
- Fields ending with `*` are **required**—the dialog won’t proceed until you fill them.
- Optional fields can be left blank.

## API Reference

- **`get_google_map_details(additional_required=None, additional_optional=None)`**  
  Starts a headful Chrome session, opens maps.google.com, and watches for your place selections. Returns a dict keyed by place name, with all fields you confirmed.

## License

MIT © Kanad Rishiraj (RoamingSaint)
