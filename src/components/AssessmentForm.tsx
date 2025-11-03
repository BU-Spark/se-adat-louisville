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

    // Step 3 confirm: create a session via API when the final confirm button is clicked
    const genUUID = (): string => {
      // Prefer the native crypto.randomUUID when available
      const webCrypto =
        typeof crypto !== 'undefined' ? (crypto as unknown as { randomUUID?: () => string }) : undefined;
      if (webCrypto && typeof webCrypto.randomUUID === 'function') {
        return webCrypto.randomUUID();
      }
      // fallback simple UUID generator
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
    };

    const handleFinalSubmit = async (e: Event) => {
      e.preventDefault();
      try {
        const sessionID = genUUID();
        const created = new Date();
        const expires = new Date(created.getTime() + 12 * 60 * 60 * 1000); // +12 hours

        const payload = {
          session_id: sessionID,
          created_at: created.toISOString(),
          expires_by: expires.toISOString(),
          is_active: true,
        };

        // Determine backend API base. Prefer a build-time env var (PUBLIC_API_BASE).
        // Fallback to localhost:8000 which is where the FastAPI app runs in dev.
        const apiBase =
          typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.PUBLIC_API_BASE
            ? import.meta.env.PUBLIC_API_BASE
            : '';

        console.log('Using API base:', apiBase);
        const url = apiBase.replace(/\/$/, '') + '/api/sessions';
        console.log('URL for session creation:', url);

        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const text = await resp.text();
          console.error('Failed to create session', resp.status, text);
          alert('Failed to create session: ' + resp.status + '\n' + text);
          return;
        }

        const data = await resp.json();
        console.log('Session created', data);

        if (step3) {
          let statusEl = document.getElementById('sessionStatus');
          if (!statusEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'sessionStatus';
            statusEl.style.marginTop = '1rem';
            statusEl.style.fontSize = '0.9rem';
            statusEl.style.color = '#064e3b';
            step3.appendChild(statusEl);
          }
          statusEl.textContent = `Session created: ${payload.session_id}`;
        }
      } catch (err) {
        console.error('Error creating session', err);
        alert('Error creating session: ' + String(err));
      }
    };

    let finalButton: HTMLButtonElement | null = null;
    if (step3) {
      finalButton = step3.querySelector('button[type="finalSubmit"]') as HTMLButtonElement | null;
      if (finalButton) finalButton.addEventListener('click', handleFinalSubmit);
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
      if (finalButton) finalButton.removeEventListener('click', handleFinalSubmit);
    };
  }, []);

  // This component renders nothing, it just manages side effects
  return null;
}
