import { useEffect } from 'react';

export default function AssessmentFormHandler() {
  useEffect(() => {
    const addressInput = document.getElementById('addressInput') as HTMLInputElement;
    const cityInput = document.getElementById('cityInput') as HTMLInputElement;
    const zipcodeInput = document.getElementById('zipcodeInput') as HTMLInputElement;

    // Ensure inputs are cleared on full page load/refresh
    const clearIfPresent = (el: HTMLInputElement | null) => {
      if (el) {
        el.value = '';
        // Trigger input event for any listeners
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
    };

    clearIfPresent(addressInput);
    clearIfPresent(cityInput);
    clearIfPresent(zipcodeInput);

    const numUnitsInput = document.getElementById('numUnitsInput') as HTMLInputElement | null;
    const units80AMI = document.getElementById('units80AMI') as HTMLInputElement | null;
    const units50AMI = document.getElementById('units50AMI') as HTMLInputElement | null;
    const units30AMI = document.getElementById('units30AMI') as HTMLInputElement | null;

    clearIfPresent(numUnitsInput);
    clearIfPresent(units80AMI);
    clearIfPresent(units50AMI);
    clearIfPresent(units30AMI);

    // Listen for map location selections
    const handleLocationSelected = (event: CustomEvent) => {
      const detail = event.detail || {};
      if (detail.address && addressInput) addressInput.value = detail.address;
      if (detail.city && cityInput) cityInput.value = detail.city;
      if (detail.zipcode && zipcodeInput) zipcodeInput.value = detail.zipcode;
    };

    window.addEventListener('location-selected', handleLocationSelected as EventListener);

    // Step progression handlers
    const step1Form = document.getElementById('step1Form');
    const step2 = document.getElementById('step2');
    const step2Form = document.getElementById('step2Form');
    const step3 = document.getElementById('step3');

    const handleStep1Submit = (e: Event) => {
      e.preventDefault();
      if (step2) {
        step2.style.display = '';
        step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    const handleStep2Submit = (e: Event) => {
      e.preventDefault();
      if (step3) {
        step3.style.display = '';
        step3.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    if (step1Form) {
      step1Form.addEventListener('submit', handleStep1Submit);
    }

    if (step2Form) {
      step2Form.addEventListener('submit', handleStep2Submit);
    }

    // Cleanup
    return () => {
      window.removeEventListener('location-selected', handleLocationSelected as EventListener);
      if (step1Form) {
        step1Form.removeEventListener('submit', handleStep1Submit);
      }
      if (step2Form) {
        step2Form.removeEventListener('submit', handleStep2Submit);
      }
    };
  }, []);

  // This component renders nothing, it just manages side effects
  return null;
}
