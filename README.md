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
  - Rating, Reviews, Category  
- **Batch mode**: if you supply `search_terms`, it will run exactly those searches and return immediately (no “Keep going?” prompt)  
- **Manual mode**: if you omit `search_terms`, after each scrape you’re asked “Keep going?”  
- **Custom fields**: define required `*` or optional fields in your dialog  
- **Confirmation modes**:
  - `always`: always prompt after each scrape
  - `on_missing`: prompt only if *any* field (required or optional) is blank
  - `on_required_missing`: prompt only if a *required* field is blank  
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
# => {("40.785091","-73.968285"): {"name": "Central Park", "latitude": "...", ...}}
```

### With search term (batch mode; no “Keep going?”)

```python
from gmaps_scraper import get_google_map_details

data = get_google_map_details(search_terms=["Empire State Building", "Central Park"])
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

### With confirmation modes

```python
from gmaps_scraper import get_google_map_details

# Only prompt if any field is missing
data = get_google_map_details(confirmation_mode="on_missing")
print(data)

# Only prompt if a required field is missing
data = get_google_map_details(confirmation_mode="on_required_missing")
print(data)
```

In the confirmation dialog box:
- Fields ending with `*` are **required**—the dialog won’t proceed until you fill them when prompting.
- Optional fields can be left blank.
- Control prompts using `confirmation_mode`.

## API Reference

```python
get_google_map_details(
    additional_required: List[str] = None,
    additional_optional: List[str] = None,
    search_terms: List[str] | str = None,
    confirmation_mode: Literal["always", "on_missing", "on_required_missing"] = "always",
    debug: bool = False
) -> Dict[Tuple[str, str], Dict[str, str]]
```

- **additional_required**: list of field names that must be filled before proceeding  
- **additional_optional**: list of field names that may be left blank  
- **search_terms**: term or list of terms to enter into Google Maps search bar  
- **confirmation_mode**: when to show the confirmation dialog; one of:
  - `"always"`: always prompt (default)
  - `"on_missing"`: prompt only if any field (required or optional) is blank  
  - `"on_required_missing"`: prompt only if a required field is blank  
- **debug**: if `True`, prints debug logs for URL changes and scraped values  

## License

MIT © Kanad Rishiraj (RoamingSaint)
