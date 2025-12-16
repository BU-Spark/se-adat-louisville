# Frontend Setup

Frontend built with **Astro + React + Tailwind CSS**, connecting to the ADAT backend.

---

## Prerequisites
- Node.js 20+ & npm  
- Google Maps API key (Maps, Autocomplete, Geocoding)  
- Backend running  

---

## Google Maps API Key
Add your key to `.env`:
```env
PUBLIC_GOOGLE_MAPS_API_KEY=your_key_here
```
## Running Locally
### With Docker Compose
```
docker-compose up frontend
```
### Manually
```
cd src
npm install
npm run dev
```
Dev server runs at http://localhost:1234

## Build for Production
```
npm run build
npm run preview
```
Adjust backend URLs in .env if needed.

## Tips
- Ensure backend and ETL pipeline are running.

- Keep .env secure; do not commit API keys.
