import React, { useState, useCallback } from 'react';
import styles from '../styles/AssessmentForm.module.css';
import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';

// Default map center (Boston)
const defaultCenter = { lat: 42.3505, lng: -71.1054 };

const containerStyle = {
  width: '100%',
  height: '315px',
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
      <div className="w-full h-56 p-0" style={{ paddingLeft: 0, paddingRight: 0 }}>
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
      <main className={styles.formMain}>
        <h1 className={styles.header}>How to Start The Assessment</h1>
        <p className={styles.paragraph}>
          Select the location of the proposed project to begin the assessment. This should be the address at which the
          project will be built. You can enter the address in the search bar or directly enter the address in the field
          below*.
        </p>
        <p className={styles.paragraphBottom}>
          <em style={{ fontWeight: 400 }}>
            *If the address is not recognized, place a location pin directly on the map where the development is to
            occur.
          </em>
        </p>
        <hr className={styles.divider} />
        <h2 className={styles.sectionHeader}>Step 1: Select development location</h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', width: '50%', gap: '1rem' }}>
          <label className={styles.label}>
            Address{' '}
            <span className={styles.hintText} style={{ marginLeft: '0.5rem' }}>
              Type here or select on map
            </span>
          </label>
          <div style={{ width: '100%', display: 'block' }}>
            <label className={styles.hintText} htmlFor="addressInput">
              Address
            </label>
            <input
              id="addressInput"
              className={`${styles.input} focus:border-blue-700 focus:outline-none`}
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </div>
          <div style={{ width: '100%', display: 'block' }}>
            <label className={styles.hintText} htmlFor="cityInput">
              City
            </label>
            <input
              id="cityInput"
              className={`${styles.input} focus:border-blue-700 focus:outline-none`}
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div style={{ width: '100%', display: 'block' }}>
            <label className={styles.hintText} htmlFor="zipcodeInput">
              Zipcode
            </label>
            <input
              id="zipcodeInput"
              className={`${styles.input} focus:border-blue-700 focus:outline-none`}
              type="text"
              value={zipcode}
              onChange={(e) => setZipcode(e.target.value)}
            />
          </div>
          <button type="submit" className={`${styles.confirmButton}`}>
            Confirm
          </button>
        </form>
        {confirmed && <div className="mt-6 text-blue-900 text-lg font-semibold">Location confirmed!</div>}
      </main>
    </div>
  );
}
