import '@testing-library/jest-dom/vitest';

// Mock window.matchMedia for all tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock window.open for tests that need it
Object.defineProperty(window, 'open', {
  writable: true,
  value: vi.fn(),
});
