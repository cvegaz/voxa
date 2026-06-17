import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './index.css';

// Buscamos el nodo donde React va a "vivir" (el <div id="root"> del index.html).
const container = document.getElementById('root');
if (!container) {
  throw new Error('No se encontró el elemento #root en index.html');
}

// createRoot es la API de React 18: habilita el renderizado concurrente.
createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>
);
