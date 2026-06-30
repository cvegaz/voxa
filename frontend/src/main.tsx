import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Self-hosted Inter (variable). Loaded once here so the whole app inherits it
// via the --font-sans token in index.css.
import '@fontsource-variable/inter';
import { App } from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LanguageProvider } from './i18n/LanguageContext';
import './index.css';

// Find the node where React will "live" (the <div id="root"> in index.html).
const container = document.getElementById('root');
if (!container) {
  throw new Error('No se encontró el elemento #root en index.html');
}

// createRoot is the React 18 API: it enables concurrent rendering.
createRoot(container).render(
  <StrictMode>
    <ErrorBoundary>
      <LanguageProvider>
        <App />
      </LanguageProvider>
    </ErrorBoundary>
  </StrictMode>
);
