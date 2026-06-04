# Email Lead Generator

A small, compliant lead generation tool for finding businesses with Google Places data and enriching each result with public contact details from the business website.

This project intentionally does **not** scrape Google Maps pages. Google Places data is fetched through the official Places API, and email discovery only checks public pages on each business' own website.

## What It Collects

- Business name
- Address
- Phone number
- Website
- Google Maps URL
- Rating and review count
- Public email addresses found on the business website
- `email_ids`, a semicolon-separated list of all email IDs found for the business
- Source page where each email was found
- Extra phone numbers found on the business website
- Public social/profile links found on the business website

## Setup

1. Create a Google Maps Platform API key with Places API enabled.
2. Set the key in your terminal:

```powershell
$env:GOOGLE_MAPS_API_KEY="your_api_key_here"
```

3. Run a search:

```powershell
python lead_generator.py "dentists in Austin TX" --limit 25 --output leads.csv
```

## Browser App

You can also run the lead generator from a local browser screen:

```powershell
cd "C:\Users\User\OneDrive\Documents\New project"
$env:GOOGLE_MAPS_API_KEY="your_api_key_here"
.\run_web_app.bat
```

Then open:

```text
http://127.0.0.1:8765
```

### Save Your API Key

The browser app can save your Google Maps API key locally in this project. Paste the key in the app, select **Save API key on this computer**, then run a search once.

After that, you can leave the API key box blank. The saved key is stored in:

```text
C:\Users\User\OneDrive\Documents\New project\app_settings.json
```

Do not share this file publicly.

### Keep The App Running

To run the website in the background without a visible terminal window, double-click:

```text
run_web_app_hidden.vbs
```

Then open:

```text
http://127.0.0.1:8765
```

Closing the browser tab will not stop the app. It keeps running in the background.

To stop it, double-click:

```text
stop_web_app.bat
```

### Start Automatically With Windows

To make the app start when Windows starts, double-click:

```text
install_startup.bat
```

After that, the website should be available at `http://127.0.0.1:8765` after you log in to Windows.

Every browser search automatically saves a CSV inside:

```text
C:\Users\User\OneDrive\Documents\New project\exports
```

The app also shows the latest saved CSV path after each completed run.

The browser app uses the AIM workflow:

- Acquire: send your query to Google Places API and collect matching businesses.
- Identify: visit each business website and find public emails, phone numbers, and social links.
- Manage: show the lead table and save a CSV file in the `exports` folder.
- Outreach: use per-lead email draft buttons, copy drafts, open Gmail, and create a calendar reminder file for follow-up.

To target 100 leads, add multiple search lines in the browser app:

```text
Doctors in Delhi
Doctors in South Delhi
Doctors in Noida
Doctors in Gurugram
Doctors in Ghaziabad
```

Google Places may return up to about 60 results from one Text Search query, so the app combines multiple queries and removes duplicate businesses until it reaches the target lead count or runs out of results.

## Examples

```powershell
python lead_generator.py "restaurants in Chicago" --limit 40
python lead_generator.py "roofing companies near Phoenix AZ" --limit 20 --max-pages 5
python lead_generator.py "accountants in Miami FL" --no-robots-check
```

The CSV includes one row per business email found. Businesses without a discovered email are still included once, with the email columns left blank.

## Notes

- The Places API Text Search endpoint can return up to 60 results across pages.
- The browser app can target 100 leads by combining multiple queries, but Google API quotas and billing are controlled by Google. This project cannot guarantee that API usage will always be free.
- Google Places fields can affect billing. This tool requests only a focused set of business/contact fields.
- Some businesses do not publish emails. The output will still include the business row with an empty email field.
- Always follow applicable privacy, anti-spam, and marketing laws before contacting leads.
- The app creates individual email drafts inside the browser. You can copy the draft, open Gmail, or try your default email app. It does not send bulk email automatically.
- Calendar reminders are downloaded as `.ics` files. Open the file to add it to Outlook, Google Calendar, Apple Calendar, or another calendar app.

## Useful Official Docs

- [Places API Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search)
- [Places API Place resource fields](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)
