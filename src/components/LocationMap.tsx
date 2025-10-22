import React, { useCallback, useState, useRef } from 'react';
import { GoogleMap, Marker, useJsApiLoader, Autocomplete } from '@react-google-maps/api';
import styles from '../styles/LocationMap.module.css';
import mapPinIcon from '../assets/mapPin.svg';

const defaultCenter = { lat: 42.3505, lng: -71.1054 };

const SearchIcon = () => (
  <svg
    width="15"
    height="15"
    viewBox="0 0 24 24"
    fill="none"
    stroke="#000000ff"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const PinIcon = () => <img src={mapPinIcon.src} alt="Pin" width="20" height="20" />;

export type LocationMapProps = {
  marker: { lat: number; lng: number } | null;
  onLocationSelect?: (location: {
    lat: number;
    lng: number;
    address?: string;
    city?: string;
    zipcode?: string;
  }) => void;
};

export default function LocationMap({ marker, onLocationSelect }: LocationMapProps) {
  const [center, setCenter] = useState(marker || defaultCenter);
  const [localMarker, setLocalMarker] = useState<{ lat: number; lng: number } | null>(marker || null);
  const [autocomplete, setAutocomplete] = useState<google.maps.places.Autocomplete | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [pinDropMode, setPinDropMode] = useState(false);

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: import.meta.env.PUBLIC_GOOGLE_MAPS_API_KEY,
    libraries: ['places'],
  });

  // keep map centered with marker updates from parent
  React.useEffect(() => {
    if (marker) {
      setCenter(marker);
      setLocalMarker(marker);
    }
  }, [marker]);

  // Helper function to parse address components
  const parseAddressComponents = (addressComponents?: google.maps.GeocoderAddressComponent[]) => {
    let streetNumber = '';
    let route = '';
    let city = '';
    let zipcode = '';

    addressComponents?.forEach((component) => {
      const types = component.types;
      if (types.includes('street_number')) {
        streetNumber = component.long_name;
      } else if (types.includes('route')) {
        route = component.long_name;
      } else if (types.includes('locality')) {
        city = component.long_name;
      } else if (types.includes('postal_code')) {
        zipcode = component.long_name;
      }
    });

    return {
      address: `${streetNumber} ${route}`.trim(),
      city,
      zipcode,
    };
  };

  const onPlaceChanged = () => {
    if (autocomplete) {
      const place = autocomplete.getPlace();
      if (place.geometry && place.geometry.location) {
        const lat = place.geometry.location.lat();
        const lng = place.geometry.location.lng();
        const newCenter = { lat, lng };
        setCenter(newCenter);
        setLocalMarker(newCenter);

        const { address, city, zipcode } = parseAddressComponents(place.address_components);
        const payload = { lat, lng, address, city, zipcode } as const;
        // Emit CustomEvent so the form handler (Astro island) can auto-fill fields
        window.dispatchEvent(new CustomEvent('location-selected', { detail: payload }));
        // Still support optional callback for parent React usage
        onLocationSelect?.(payload);

        // Pan the map to the new location
        if (mapRef.current) {
          mapRef.current.panTo(newCenter);
        }

        // Close the search bar after selection
        // setSearchOpen(false);
      }
    }
  };

  const handleMapClick = useCallback(
    (e: google.maps.MapMouseEvent) => {
      if (e.latLng && pinDropMode) {
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        const newCenter = { lat, lng };
        setCenter(newCenter);
        setLocalMarker(newCenter);

        // Perform reverse geocoding to get address
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ location: { lat, lng } }, (results, status) => {
          if (status === 'OK' && results?.[0]) {
            const { address, city, zipcode } = parseAddressComponents(results[0].address_components);
            const payload = { lat, lng, address, city, zipcode } as const;
            window.dispatchEvent(new CustomEvent('location-selected', { detail: payload }));
            onLocationSelect?.(payload);
          } else {
            // If geocoding fails, just send coordinates
            const payload = { lat, lng } as const;
            window.dispatchEvent(new CustomEvent('location-selected', { detail: payload }));
            onLocationSelect?.(payload);
          }
        });

        // Exit pin drop mode after placing pin
        setPinDropMode(false);
      }
    },
    [onLocationSelect, pinDropMode]
  );

  // Store map instance to use for bounds
  const mapRef = useRef<google.maps.Map | null>(null);
  const handleMapLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
  }, []);

  // Update autocomplete bounds when map moves
  const handleMapIdle = useCallback(() => {
    if (autocomplete && mapRef.current) {
      autocomplete.setBounds(mapRef.current.getBounds() ?? undefined);
    }
  }, [autocomplete]);

  return isLoaded ? (
    <div style={{ position: 'relative', width: '100%', height: '315px' }}>
      <GoogleMap
        mapContainerStyle={{ width: '100%', height: '315px' }}
        center={center}
        zoom={15}
        onClick={handleMapClick}
        onLoad={handleMapLoad}
        onIdle={handleMapIdle}
        options={{
          streetViewControl: false,
          mapTypeControl: false,
          fullscreenControl: false,
          draggableCursor: pinDropMode ? 'crosshair' : 'default',
        }}
      >
        {(marker || localMarker) && <Marker position={marker || localMarker!} />}
      </GoogleMap>
      <div>
        {!searchOpen && (
          <button className={styles.mapSearchIcon} aria-label="Open search" onClick={() => setSearchOpen(true)}>
            <SearchIcon />
          </button>
        )}
        {searchOpen && (
          <div className={styles.mapSearchBarContainer}>
            <Autocomplete onLoad={setAutocomplete} onPlaceChanged={onPlaceChanged}>
              <input ref={inputRef} type="text" autoComplete="on" className={styles.mapSearchBar} autoFocus />
            </Autocomplete>
            <div className={styles.mapSearchBarIcon}>
              <SearchIcon />
            </div>
          </div>
        )}
        <button
          className={styles.mapPinIcon}
          aria-label={pinDropMode ? 'Cancel pin drop' : 'Drop pin on map'}
          onClick={() => setPinDropMode(!pinDropMode)}
          title={pinDropMode ? 'Click to cancel' : 'Click to drop pin on map'}
          style={{ opacity: pinDropMode ? 1 : 0.7 }}
        >
          <PinIcon />
        </button>
      </div>
    </div>
  ) : null;
}
