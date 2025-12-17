import React, { useState, useRef, useEffect } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapLibreSearchControl } from '@stadiamaps/maplibre-search-box';
import '@stadiamaps/maplibre-search-box/dist/maplibre-search-box.css';
import styles from '../styles/LocationMapLibre.module.css';
import mapPinIcon from '../../public/assets/assessment/mapPin.svg';

const defaultCenter = { lat: 38.2527, lng: -85.7585 }; // Louisville, KY

const PinIcon = () => <img src={mapPinIcon.src} alt="Pin" width="20" height="20" />;

export type LocationMapLibreProps = {
  marker: { lat: number; lng: number } | null;
  onLocationSelect?: (location: {
    lat: number;
    lng: number;
    address?: string;
    city?: string;
    zipcode?: string;
  }) => void;
};

export default function LocationMapLibre({ marker, onLocationSelect }: LocationMapLibreProps) {
  const [pinDropMode, setPinDropMode] = useState(false);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const searchControlRef = useRef<MapLibreSearchControl | null>(null);
  const expandedIconRef = useRef<HTMLElement | null>(null);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [marker?.lng || defaultCenter.lng, marker?.lat || defaultCenter.lat],
      zoom: 15,
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Add Stadia Maps search control with proximity bias
    // useMapFocusPoint: true automatically biases results to map center
    const searchControl = new MapLibreSearchControl({
      useMapFocusPoint: true,
      onResultSelected: (feature) => {
        try {
          if (feature && feature.geometry?.coordinates) {
            const [lng, lat] = feature.geometry.coordinates;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const props = feature.properties as any;
            const addressComponents = props.addressComponents || {};

            // Extract address components
            const streetNumber = addressComponents.number || '';
            const streetName = addressComponents.street || '';
            const address =
              streetNumber && streetName ? `${streetNumber} ${streetName}`.trim() : streetName || props.name || '';

            // Extract city from coarseLocation (format: "City, State, Country")
            const coarseLocation = props.coarseLocation || '';
            const city = coarseLocation ? coarseLocation.split(',')[0].trim() : '';

            // Extract zipcode (note: capital C in postalCode)
            const zipcode = addressComponents.postalCode || addressComponents.postalcode || '';

            // Notify via callback if provided
            onLocationSelect?.({
              lat,
              lng,
              address,
              city,
              zipcode,
            });

            // Also dispatch a CustomEvent for non-React listeners (Astro page)
            try {
              window.dispatchEvent(
                new CustomEvent('location-selected', {
                  detail: { lat, lng, address, city, zipcode },
                })
              );
            } catch {
              // no-op on server or if window not available
            }

            // Update or create marker
            if (markerRef.current) {
              markerRef.current.setLngLat([lng, lat]);
            } else {
              markerRef.current = new maplibregl.Marker({ color: '#FFBA37' }).setLngLat([lng, lat]).addTo(map);
            }
          }
        } catch (error) {
          console.error('Error in onResultSelected:', error);
        }
      },
    });

    map.addControl(searchControl, 'top-left');
    searchControlRef.current = searchControl;
    mapRef.current = map;

    // Wait for map to load before adding any initial markers
    map.on('load', () => {
      if (marker) {
        markerRef.current = new maplibregl.Marker({ color: '#FFBA37' }).setLngLat([marker.lng, marker.lat]).addTo(map);
      }
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []); // Empty dependency array - only initialize once

  // Handle map clicks for pin drop mode - separate effect so it updates with pinDropMode
  useEffect(() => {
    if (!mapRef.current) return;

    const handleMapClick = async (e: maplibregl.MapMouseEvent) => {
      if (pinDropMode) {
        const { lng, lat } = e.lngLat;
        const geocodeData = { address: '', city: '', zipcode: '' };

        // Notify via callback if provided
        onLocationSelect?.({
          lat,
          lng,
          ...geocodeData,
        });

        // Dispatch event for listeners
        try {
          window.dispatchEvent(
            new CustomEvent('location-selected', {
              detail: { lat, lng, ...geocodeData },
            })
          );
        } catch {
          // ignore if not in browser
        }

        // Update marker
        if (markerRef.current) {
          markerRef.current.setLngLat([lng, lat]);
        } else {
          markerRef.current = new maplibregl.Marker({ color: '#FFBA37' }).setLngLat([lng, lat]).addTo(mapRef.current!);
        }

        setPinDropMode(false);
      }
    };

    mapRef.current.on('click', handleMapClick);

    return () => {
      mapRef.current?.off('click', handleMapClick);
    };
  }, [pinDropMode, onLocationSelect]);

  // Update marker when prop changes
  useEffect(() => {
    if (!mapRef.current) return;

    if (marker) {
      if (markerRef.current) {
        markerRef.current.setLngLat([marker.lng, marker.lat]);
      } else {
        markerRef.current = new maplibregl.Marker({ color: '#FFBA37' })
          .setLngLat([marker.lng, marker.lat])
          .addTo(mapRef.current);
      }
      mapRef.current.flyTo({ center: [marker.lng, marker.lat], zoom: 15 });
    }
  }, [marker]);

  // Update cursor style when pin drop mode changes
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getCanvas().style.cursor = pinDropMode ? 'crosshair' : '';
    }
  }, [pinDropMode]);

  // Handle search box expand/collapse
  useEffect(() => {
    if (!searchControlRef.current) return;

    const searchContainer = searchControlRef.current.getContainer();
    if (searchContainer) {
      if (searchExpanded) {
        searchContainer.classList.add('expanded');
      } else {
        searchContainer.classList.remove('expanded');
      }
    }
  }, [searchExpanded]);

  // Mount a non-interactive icon inside the search container when expanded
  useEffect(() => {
    const container = searchControlRef.current?.getContainer();
    if (!container) return;

    if (searchExpanded) {
      // Create the button if it doesn't exist
      if (!expandedIconRef.current) {
        const icon = document.createElement('div');
        icon.className = styles.mapSearchIconExpanded;
        icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
        `;
        container.appendChild(icon);
        expandedIconRef.current = icon;
      } else {
        expandedIconRef.current.style.display = '';
      }
    } else if (expandedIconRef.current) {
      // Hide when not expanded
      expandedIconRef.current.style.display = 'none';
    }

    return () => {
      // no-op cleanup (no listeners attached)
    };
  }, [searchExpanded]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '315px' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '315px' }} />

      {/* Search Toggle Button (collapsed only) */}
      {!searchExpanded && (
        <button
          className={styles.mapSearchIcon}
          aria-label={'Open search'}
          onClick={() => setSearchExpanded(true)}
          title={'Search for address'}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
        </button>
      )}

      {/* Pin Drop Control */}
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
  );
}
