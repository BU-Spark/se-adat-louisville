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
  ami60: 0;
  ami70: 0;
}

interface ApiResponse {
  status: string;
  message: string;
  task_id: string;
  session_id: string;
}

interface TaskResult {
  status: string;
  task_id: string;
  session_id?: string;
  results?: {
    eligible?: boolean;
    total_affordable?: number;
    total_units?: number;
    processed_at?: string;
    [key: string]: unknown;
  };
}

interface TaskStatusResponse {
  task_id: string;
  status: string;
  message?: string;
  result?: TaskResult;
  error?: string;
}

export default function AssessmentAPIHandler() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const step3Form = document.querySelector('#step3 form') as HTMLFormElement;

    if (step3Form) {
      const handleFinalSubmit = async (e: Event) => {
        e.preventDefault();

        const addressInput = document.getElementById('addressInput') as HTMLInputElement;
        const cityInput = document.getElementById('cityInput') as HTMLInputElement;
        const zipcodeInput = document.getElementById('zipcodeInput') as HTMLInputElement;
        const numUnitsInput = document.getElementById('numUnitsInput') as HTMLInputElement;
        const units80Input = document.getElementById('units80AMI') as HTMLInputElement;
        const units50Input = document.getElementById('units50AMI') as HTMLInputElement;
        const units30Input = document.getElementById('units30AMI') as HTMLInputElement;
        const units60Input = document.getElementById('units60AMI') as HTMLInputElement;
        const units70Input = document.getElementById('units70AMI') as HTMLInputElement;

        // Remove state from validation since we're hardcoding it
        if (!addressInput?.value || !cityInput?.value || !zipcodeInput?.value) {
          alert('Please complete Step 1: Enter address, city, and zipcode');
          return;
        }

        if (!numUnitsInput?.value || parseInt(numUnitsInput.value) < 1) {
          alert('Please complete Step 2: Enter a valid number of units');
          return;
        }

        const formData: FormData = {
          address: addressInput.value,
          city: cityInput.value,
          zip: zipcodeInput.value,
          state: 'KY', // Hardcoded for Louisville, Kentucky
          project_units_total: parseInt(numUnitsInput.value),
          ami80: parseInt(units80Input?.value || '0'),
          ami50: parseInt(units50Input?.value || '0'),
          ami30: parseInt(units30Input?.value || '0'),
          ami60: parseInt(units60Input?.value || '0'),
          ami70: parseInt(units70Input?.value || '0'),
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
      const payload = {
        session_id: null,
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

      const response = await fetch(`${API_BASE_URL}/api/assess`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const data: ApiResponse = await response.json();
      console.log('API Response:', data);

      setSessionId(data.session_id);
      setTaskStatus('queued');

      alert(
        `✅ Assessment submitted successfully!\n\n` +
          `Task ID: ${data.task_id}\n` +
          `Session ID: ${data.session_id}\n\n` +
          `Processing your assessment... This will take about 3-5 seconds.`
      );

      pollTaskStatus(data.task_id);
    } catch (err) {
      console.error('Submission error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      alert(
        `❌ Error submitting assessment\n\n` +
          `${err instanceof Error ? err.message : 'Unknown error'}\n\n` +
          `Please check:\n` +
          `1. Backend is running (${API_BASE_URL}/health)\n` +
          `2. Redis is running\n` +
          `3. Celery worker is running`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const maxAttempts = 20;
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

          // Get the session ID from task result or stored state
          const resultSessionId = status.result?.session_id || sessionId;

          // Show brief alert then redirect
          alert(
            `🎉 Assessment Complete!\n\n` +
              `Eligible for Development: ${eligible}\n\n` +
              `Redirecting to results page...`
          );

          // Redirect to results page with session ID
          window.location.href = `/results?session_id=${resultSessionId}`;
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
          setTimeout(poll, 3000);
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

    setTimeout(poll, 2000);
  };

  return (
    <div style={{ display: 'none' }} id="assessment-api-status">
      {isSubmitting && <div>Submitting assessment...</div>}
      {taskStatus && <div>Task Status: {taskStatus}</div>}
      {error && <div>Error: {error}</div>}
      {sessionId && <div>Session ID: {sessionId}</div>}
    </div>
  );
}
