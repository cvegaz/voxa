import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Self-hosted Inter (variable), same as the app, so the brand font matches.
import '@fontsource-variable/inter';
import { App } from './App';
import { LanguageProvider } from './i18n/LanguageContext';
import './styles/tokens.css';
import './styles/base.css';
import './styles/buttons.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('No se encontró el elemento #root en index.html');
}

createRoot(container).render(
  <StrictMode>
    <LanguageProvider>
      <App />
    </LanguageProvider>
  </StrictMode>
);
