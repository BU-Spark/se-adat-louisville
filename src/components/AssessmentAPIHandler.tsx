import { useEffect, useState } from 'react';

interface FormData {
  address: string;
  city: string;
  zip: string;
  state: string;
  project_units_total: number;
  ami80: number;
  ami50: number;
  ami30: number;
  ami60: number;
  ami70: number;
}

interface ApiResponse {
  status: string;
  message: string;
  task_id: string;
  session_id: string;
}

interface TaskStatusResponse {
  task_id: string;
  status: string;
  message?: string;
  result?: any;
  error?: string;
}

/**
 * This component works ALONGSIDE your existing AssessmentForm.tsx
 * AssessmentForm.tsx handles form progression (steps 1-3)
 * This component handles final submission and API communication
 */
export default function AssessmentAPIHandler() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Backend API URL - should be configured via environment variable
  const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    // Find the final submit button in step 3
    const step3Form = document.querySelector('#step3 form') as HTMLFormElement;
    
    if (step3Form) {
      const handleFinalSubmit = async (e: Event) => {
        e.preventDefault();
        
        // Collect all form data from the page
        const addressInput = document.getElementById('addressInput') as HTMLInputElement;
        const cityInput = document.getElementById('cityInput') as HTMLInputElement;
        const zipcodeInput = document.getElementById('zipcodeInput') as HTMLInputElement;
        const numUnitsInput = document.getElementById('numUnitsInput') as HTMLInputElement;
        const units80Input = document.getElementById('units80AMI') as HTMLInputElement;
        const units50Input = document.getElementById('units50AMI') as HTMLInputElement;
        const units30Input = document.getElementById('units30AMI') as HTMLInputElement;
        
        // Validate all inputs are filled
        if (!addressInput?.value || !cityInput?.value || !zipcodeInput?.value) {
          alert('Please complete Step 1: Enter address, city, and zipcode');
          return;
        }
        
        if (!numUnitsInput?.value || parseInt(numUnitsInput.value) < 1) {
          alert('Please complete Step 2: Enter a valid number of units');
          return;
        }
        
        // Build the form data object
        const formData: FormData = {
          address: addressInput.value,
          city: cityInput.value,
          zip: zipcodeInput.value,
          state: 'MA', // Default to Massachusetts, you can make this dynamic
          project_units_total: parseInt(numUnitsInput.value),
          ami80: parseInt(units80Input?.value || '0'),
          ami50: parseInt(units50Input?.value || '0'),
          ami30: parseInt(units30Input?.value || '0'),
          ami60: 0, // Not in your form, but required by API
          ami70: 0, // Not in your form, but required by API
        };
        
        console.log('Submitting assessment:', formData);
        await submitAssessment(formData);
      };
      
      step3Form.addEventListener('submit', handleFinalSubmit);
      
      return () => {
        step3Form.removeEventListener('submit', handleFinalSubmit);
      };
    }
  }, []);

  const submitAssessment = async (formData: FormData) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      // Prepare payload for API
      const payload = {
        project_name: `${formData.address}, ${formData.city}`,
        project_units_total: formData.project_units_total,
        address: formData.address,
        city: formData.city,
        state: formData.state,
        zip: formData.zip,
        affordability: {
          ami30: formData.ami30,
          ami50: formData.ami50,
          ami60: formData.ami60,
          ami70: formData.ami70,
          ami80: formData.ami80,
        },
        build_type: null,
        scatter: null,
      };

      console.log('Sending to API:', payload);

      // Submit to FastAPI backend
      const response = await fetch(`${API_BASE_URL}/api/assess`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data: ApiResponse = await response.json();
      console.log('API Response:', data);

      setTaskId(data.task_id);
      setSessionId(data.session_id);
      setTaskStatus('queued');

      // Show initial success message
      alert(
        `✅ Assessment submitted successfully!\n\n` +
        `Task ID: ${data.task_id}\n` +
        `Session ID: ${data.session_id}\n\n` +
        `Processing your assessment... This will take about 3-5 seconds.`
      );

      // Start polling for task status
      pollTaskStatus(data.task_id);

    } catch (err) {
      console.error('Submission error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      alert(
        `❌ Error submitting assessment\n\n` +
        `${err instanceof Error ? err.message : 'Unknown error'}\n\n` +
        `Please check:\n` +
        `1. Backend is running (http://localhost:8000)\n` +
        `2. Redis is running\n` +
        `3. Celery worker is running`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const maxAttempts = 20; // Poll for up to ~60 seconds
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setTaskStatus('timeout');
        alert(
          `⏱️ Polling timeout\n\n` +
          `The task is still processing after 60 seconds.\n` +
          `This might be normal for complex assessments.\n\n` +
          `Check the Celery worker logs for progress.\n` +
          `Session ID: ${sessionId}`
        );
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/task/${taskId}`);
        
        if (!response.ok) {
          throw new Error(`Status check failed: ${response.status}`);
        }

        const status: TaskStatusResponse = await response.json();
        console.log(`[Poll ${attempts + 1}/${maxAttempts}] Task status:`, status);

        setTaskStatus(status.status);

        if (status.status === 'completed') {
          console.log('Task completed!', status.result);
          
          const results = status.result?.results;
          const eligible = results?.eligible ? 'YES ✅' : 'NO ❌';
          
          alert(
            `🎉 Assessment Complete!\n\n` +
            `Eligible for Development: ${eligible}\n\n` +
            `Affordable Units: ${results?.total_affordable || 'N/A'}\n` +
            `Total Units: ${results?.total_units || 'N/A'}\n` +
            `Processed At: ${results?.processed_at || 'N/A'}\n\n` +
            `Session ID: ${sessionId}\n` +
            `Check your Supabase database for full details.`
          );
          return;
          
        } else if (status.status === 'failed') {
          setError(status.error || 'Task failed');
          alert(
            `❌ Assessment Failed\n\n` +
            `Error: ${status.error || 'Unknown error'}\n\n` +
            `Task ID: ${taskId}\n` +
            `Check the Celery worker logs for details.`
          );
          return;
          
        } else {
          // Still processing, poll again
          attempts++;
          setTimeout(poll, 3000); // Poll every 3 seconds
        }
      } catch (err) {
        console.error('Error polling task status:', err);
        setError(err instanceof Error ? err.message : 'Error checking status');
        alert(
          `❌ Error checking task status\n\n` +
          `${err instanceof Error ? err.message : 'Unknown error'}\n\n` +
          `The task may still be processing. Check:\n` +
          `1. Backend is still running\n` +
          `2. Task ID: ${taskId}`
        );
        return;
      }
    };

    // Start polling after a short delay
    setTimeout(poll, 2000);
  };

  // This component renders a hidden status indicator
  // You can optionally show this to the user
  return (
    <div style={{ display: 'none' }} id="assessment-api-status">
      {isSubmitting && <div>Submitting assessment...</div>}
      {taskStatus && <div>Task Status: {taskStatus}</div>}
      {error && <div>Error: {error}</div>}
      {sessionId && <div>Session ID: {sessionId}</div>}
    </div>
  );
}
