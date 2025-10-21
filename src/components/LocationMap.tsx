import React, { useCallback } from 'react';
import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';

const defaultCenter = { lat: 42.3505, lng: -71.1054 };

const containerStyle = {
  width: '100%',
  height: '315px',
};

type LocationMapProps = {
  marker: { lat: number; lng: number } | null;
  onLocationSelect: (location: { lat: number; lng: number }) => void;
};

export default function LocationMap({ marker, onLocationSelect }: LocationMapProps) {
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: 'YOUR_GOOGLE_MAPS_API_KEY', // <-- Replace with your API key
  });

  const onMapClick = useCallback(
    (e: google.maps.MapMouseEvent) => {
      if (e.latLng) {
        onLocationSelect({
          lat: e.latLng.lat(),
          lng: e.latLng.lng(),
        });
      }
    },
    [onLocationSelect]
  );

  return (
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
  );
}
