import React, { useState, useCallback } from 'react';
import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';

// Default map center (Boston)
const defaultCenter = { lat: 42.3505, lng: -71.1054 };

const containerStyle = {
  width: '100%',
  height: '300px',
};

export default function AssessmentForm() {
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [zipcode, setZipcode] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [marker, setMarker] = useState<{ lat: number; lng: number } | null>(null);

  // Load Google Maps JS API
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: 'YOUR_GOOGLE_MAPS_API_KEY', // <-- Replace with your API key
  });

  // Handle map click: place marker
  const onMapClick = useCallback((e: google.maps.MapMouseEvent) => {
    if (e.latLng) {
      setMarker({
        lat: e.latLng.lat(),
        lng: e.latLng.lng(),
      });
    }
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setConfirmed(true);
  }

  return (
    <div style={{ fontFamily: 'Instrument Sans, sans-serif' }}>
      {/* Google Map */}
      <div className="w-full h-64 p-0" style={{ paddingLeft: 0, paddingRight: 0 }}>
        {isLoaded ? (
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={defaultCenter}
            zoom={15}
            onClick={onMapClick}
            options={{
              streetViewControl: false,
              mapTypeControl: false,
              fullscreenControl: false,
            }}
          >
            {marker && <Marker position={marker} />}
          </GoogleMap>
        ) : (
          <div className="flex items-center justify-center h-full text-blue-900">Loading map…</div>
        )}
      </div>
      {/* Form */}
      <main
        className="bg-white rounded-xl shadow-lg p-8 relative z-10"
        style={{
          display: 'block',
          maxWidth: '50rem',
          marginLeft: '2rem',
          marginRight: '2rem',
          marginTop: '2.5rem',
          lineHeight: '1.5',
        }}
      >
        <h1
          style={{
            fontSize: '1.25rem',
            color: '#004597',
            fontFamily: 'Instrument Sans, sans-serif',
            fontWeight: 700,
            marginBottom: '1.5rem',
            lineHeight: '1.5',
          }}
        >
          How to Start The Assessment
        </h1>
        <p
          className="mb-1 leading-relaxed"
          style={{ fontSize: '0.70rem', color: '#0B488F', fontWeight: 400, lineHeight: '1.5' }}
        >
          Select the location of the proposed project to begin the assessment. This should be the address at which the
          project will be built.
          <br />
          You can enter the address in the search bar or directly enter the address in the field below*.
        </p>
        <p className="mb-6 leading-relaxed" style={{ fontSize: '0.70rem', color: '#0B488F', lineHeight: '1.5' }}>
          <em style={{ fontWeight: 400 }}>
            *If the address is not recognized, place a location pin directly on the map where the development is to
            occur.
          </em>
        </p>
        <hr style={{ border: 'none', borderTop: '1px solid rgba(0,0,0,0.15)', margin: '1.5rem 0' }} />
        <h2
          className="mb-4"
          style={{
            fontSize: '1rem',
            color: '#004597',
            fontFamily: 'Instrument Sans, sans-serif',
            fontWeight: 500,
          }}
        >
          Step 1: Select development location
        </h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', width: '50%', gap: '1rem' }}>
          <label
            className="block"
            style={{
              fontSize: '1rem',
              fontFamily: 'Instrument Sans, sans-serif',
              fontWeight: 400,
              color: 'rgba(0, 0, 0, 1)',
            }}
          >
            Address{' '}
            <span style={{ color: 'rgba(0, 0, 0, 0.4)', fontWeight: 400, fontSize: '0.75em', marginLeft: '0.5rem' }}>
              Type here or select on map
            </span>
          </label>
          <div style={{ width: '100%', display: 'block' }}>
            <input
              style={{ width: '100%', display: 'block' }}
              className="rounded-md border border-gray-300 bg-gray-100 px-3 py-2 focus:border-blue-700 focus:outline-none"
              type="text"
              placeholder="Address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </div>
          <div style={{ width: '100%', display: 'block' }}>
            <input
              style={{ width: '100%', display: 'block' }}
              className="rounded-md border border-gray-300 bg-gray-100 px-3 py-2 focus:border-blue-700 focus:outline-none"
              type="text"
              placeholder="City"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div style={{ width: '100%', display: 'block' }}>
            <input
              style={{ width: '100%', display: 'block' }}
              className="rounded-md border border-gray-300 bg-gray-100 px-3 py-2 focus:border-blue-700 focus:outline-none"
              type="text"
              placeholder="Zipcode"
              value={zipcode}
              onChange={(e) => setZipcode(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="bg-yellow-400 text-blue-900 font-semibold rounded-md px-6 py-2 mt-2 shadow hover:bg-yellow-300 transition"
          >
            Confirm
          </button>
        </form>
        {confirmed && <div className="mt-6 text-blue-900 text-lg font-semibold">Location confirmed!</div>}
      </main>
    </div>
  );
}
