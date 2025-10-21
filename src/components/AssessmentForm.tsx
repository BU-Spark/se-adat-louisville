import React, { useState, useEffect, useRef } from 'react';
import styles from '../styles/AssessmentForm.module.css';
import LocationMap from './LocationMap';

export default function AssessmentForm() {
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [zipcode, setZipcode] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [marker, setMarker] = useState<{ lat: number; lng: number } | null>(null);

  // Step 2 field
  const [numUnits, setNumUnits] = useState('');
  const [step2Confirmed, setStep2Confirmed] = useState(false);

  // Step 3 fields: AMI breakdowns
  const [units80AMI, setUnits80AMI] = useState('');
  const [units50AMI, setUnits50AMI] = useState('');
  const [units30AMI, setUnits30AMI] = useState('');

  // Ref for Step 2 section to scroll to
  const step2Ref = useRef<HTMLDivElement>(null);
  const step3Ref = useRef<HTMLDivElement>(null);

  // Handle location selection from map
  const handleLocationSelect = (location: { lat: number; lng: number }) => {
    setMarker(location);
  };

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setConfirmed(true);
  }

  // Auto-scroll to Step 2 when it appears
  useEffect(() => {
    if (confirmed && step2Ref.current) {
      step2Ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [confirmed]);

  // Auto-scroll to Step 3 when it appears
  useEffect(() => {
    if (step2Confirmed && step3Ref.current) {
      step3Ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [step2Confirmed]);

  function handleStep2Confirm(e: React.FormEvent) {
    e.preventDefault();
    setStep2Confirmed(true);
  }

  return (
    <div style={{ fontFamily: 'Instrument Sans, sans-serif' }}>
      {/* Google Map - now a separate component */}
      <LocationMap marker={marker} onLocationSelect={handleLocationSelect} />

      {/* Form */}
      <main className={styles.formMain}>
        {/* Header section - spans full width above both columns */}
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

        {/* Two column layout: Step 1 on left, Step 3 on right (when visible) */}
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
          {/* Left column: Step 1 - fixed width */}
          <div style={{ width: '50%', maxWidth: '50%', minWidth: '50%' }}>
            <h2 className={styles.sectionHeader}>Step 1: Select development location</h2>
            <form
              onSubmit={handleSubmit}
              style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '1rem' }}
            >
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

            {/* Step 2: Number of units - shown after Step 1 is confirmed, directly under Step 1 */}
            {confirmed && (
              <div ref={step2Ref} style={{ marginTop: '2rem' }}>
                <h2 className={styles.sectionHeader}>Step 2: Input Expected Housing Units</h2>
                <form
                  onSubmit={handleStep2Confirm}
                  style={{ display: 'flex', flexDirection: 'column', width: '100%', maxWidth: '100%', gap: '1rem' }}
                >
                  <label className={styles.label}>Units </label>
                  <div style={{ width: '100%', display: 'block' }}>
                    <label className={styles.hintText} htmlFor="numUnitsInput">
                      Type the number of units in proposed project
                    </label>
                    <input
                      id="numUnitsInput"
                      className={`${styles.input} focus:border-blue-700 focus:outline-none`}
                      type="number"
                      value={numUnits}
                      onChange={(e) => setNumUnits(e.target.value)}
                      min="1"
                    />
                  </div>
                  <button type="submit" className={`${styles.confirmButton}`}>
                    Confirm
                  </button>
                </form>
              </div>
            )}
          </div>

          {/* Right column: Step 3 - shown after Step 2 is confirmed, fixed width */}
          {step2Confirmed && (
            <div ref={step3Ref} style={{ width: '50%', maxWidth: '50%', minWidth: '50%' }}>
              <h2 className={styles.sectionHeader}>Step 3: Input Unit Affordability Levels</h2>
              <form style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '1rem' }}>
                <label className={styles.hintText}>
                  The affordability of housing affects local rent prices and who can move into a given neighborhood.
                  Below, please enter the number of units in the proposed development reserved for each Area Median
                  Income (AMI) tier.
                </label>

                <label className={styles.label}>Rental Price - 80% AMI</label>
                <div style={{ width: '100%', display: 'block' }}>
                  <label className={styles.hintText} htmlFor="units80AMI">
                    Type the number of affordable units
                  </label>
                  <input
                    id="units80AMI"
                    className={`${styles.input} focus:border-blue-700 focus:outline-none`}
                    type="number"
                    min="0"
                    value={units80AMI}
                    onChange={(e) => setUnits80AMI(e.target.value)}
                  />
                </div>

                <label className={styles.label}>Rental Price - 50% AMI</label>
                <div style={{ width: '100%', display: 'block' }}>
                  <label className={styles.hintText} htmlFor="units50AMI">
                    Type the number of affordable units
                  </label>
                  <input
                    id="units50AMI"
                    className={`${styles.input} focus:border-blue-700 focus:outline-none`}
                    type="number"
                    min="0"
                    value={units50AMI}
                    onChange={(e) => setUnits50AMI(e.target.value)}
                  />
                </div>

                <label className={styles.label}>Rental Price - 30% AMI</label>
                <div style={{ width: '100%', display: 'block' }}>
                  <label className={styles.hintText} htmlFor="units30AMI">
                    Type the number of affordable units
                  </label>
                  <input
                    id="units30AMI"
                    className={`${styles.input} focus:border-blue-700 focus:outline-none`}
                    type="number"
                    min="0"
                    value={units30AMI}
                    onChange={(e) => setUnits30AMI(e.target.value)}
                  />
                </div>

                <button type="button" className={`${styles.confirmButton}`}>
                  Confirm
                </button>
              </form>
            </div>
          )}
        </div>

        {/* Step 2 moved above inside the left column */}
      </main>
    </div>
  );
}
