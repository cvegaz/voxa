/**
 * Translation catalog for the Voxa landing page (Spanish + English).
 *
 * Same conventions as the app (frontend/src/i18n/translations.ts): flat,
 * dot-namespaced keys; `{placeholder}` tokens substituted by `t()`. Spanish is
 * the default/source language; every key must exist in both maps.
 */

export type Language = 'es' | 'en';

export const SUPPORTED_LANGUAGES: Language[] = ['es', 'en'];
export const DEFAULT_LANGUAGE: Language = 'es';

export type TranslationKey = keyof typeof messages.es;

export const messages = {
  es: {
    // Language switcher
    'lang.switchToEs': 'Ver Voxa en español',
    'lang.switchToEn': 'View Voxa in English',
    'lang.groupLabel': 'Idioma de la página',

    // Nav
    'nav.how': 'Cómo funciona',
    'nav.features': 'Características',
    'nav.cases': 'Casos de uso',
    'nav.tech': 'Tecnología',
    'nav.contact': 'Contacto',

    // Hero
    'hero.badge': 'Captura de datos por voz · IA',
    'hero.title': 'Habla, y Voxa llena tu Excel.',
    'hero.subtitle':
      'Sube una plantilla, narra la información en voz alta y la IA transcribe tu voz y extrae cada dato en su columna. Sin teclear, sin formularios.',
    'hero.ctaPrimary': 'Hablemos de tu caso',
    'hero.ctaGithub': 'Ver en GitHub',
    'hero.ctaApp': 'Probar la app',

    // Hero mockup (animated)
    'mockup.spoken': '«Estadio Azteca, aforo 87 000, partido el 17 de septiembre»',
    'mockup.recording': 'Grabando',
    'mockup.transcribing': 'Transcribiendo',
    'mockup.extracting': 'Extrayendo campos',
    'mockup.done': 'Fila añadida',
    'mockup.colVenue': 'Sede',
    'mockup.colCapacity': 'Aforo',
    'mockup.colDate': 'Fecha',
    'mockup.ariaLabel':
      'Demostración animada: la voz se convierte en texto y luego en una fila de Excel.',

    // How it works
    'how.title': 'De la voz a la celda, en seis pasos',
    'how.subtitle':
      'El mismo flujo que ves en la app, sin fricción: cargas, narras y descargas.',
    'how.step1.title': 'Sube tu plantilla',
    'how.step1.desc': 'Cargas un archivo .xlsx y Voxa detecta columnas y tipos de dato.',
    'how.step2.title': 'Confirma el esquema',
    'how.step2.desc': 'Revisas las columnas detectadas y confirmas antes de empezar.',
    'how.step3.title': 'Narra',
    'how.step3.desc': 'Grabas o subes un audio describiendo el registro a capturar.',
    'how.step4.title': 'Transcribe (Whisper)',
    'how.step4.desc': 'OpenAI Whisper convierte tu voz en texto y lo confirmas.',
    'how.step5.title': 'Extrae los campos (LLM)',
    'how.step5.desc': 'gpt-4o-mini mapea el texto a cada columna y añade la fila.',
    'how.step6.title': 'Descarga el Excel',
    'how.step6.desc': 'El archivo se reconstruye en memoria y lo descargas listo.',

    // Features
    'features.title': 'Pensado con criterio de producto',
    'features.subtitle':
      'No es solo «audio a Excel»: cada decisión cuida la calidad del dato y la experiencia.',
    'features.bilingual.title': 'Bilingüe ES / EN',
    'features.bilingual.desc':
      'Interfaz y transcripción en español o inglés, con selector y persistencia.',
    'features.stateless.title': 'Exportación en memoria',
    'features.stateless.desc':
      'Las filas viven en la base de datos; el .xlsx se reconstruye al descargar.',
    'features.cap.title': 'Grabación acotada (20 s)',
    'features.cap.desc':
      'Límite configurable, validado en cliente y servidor, listo para planes de pago.',
    'features.mic.title': 'Aviso de micrófono',
    'features.mic.desc':
      'Si detecta un micrófono Bluetooth, avisa: su baja fidelidad afecta la precisión.',
    'features.absent.title': 'Ausente vs. no mencionado',
    'features.absent.desc':
      'Decir «sin estacionamiento» guarda un 0 explícito, distinto de una columna en blanco.',
    'features.dates.title': 'Fechas normalizadas',
    'features.dates.desc':
      'Cualquier forma narrada se normaliza a un formato consistente (17-sep-2026).',

    // Use cases
    'cases.title': 'Un núcleo, muchos dominios',
    'cases.subtitle':
      'Voxa es el motor; tu caso de uso es la configuración. Así nació playPro Stats.',
    'cases.playpro.tag': 'Caso real',
    'cases.playpro.title': 'playPro Stats',
    'cases.playpro.desc':
      'Captura por voz de estadísticas de fútbol americano. Se construyó como una configuración sobre el núcleo de Voxa —no un fork—: mismas tuberías, distinto vocabulario y columnas.',
    'cases.yours.tag': 'Tu proyecto',
    'cases.yours.title': '¿Tu dominio?',
    'cases.yours.desc':
      'Inventario, visitas médicas, inspecciones, encuestas de campo… Adapto Voxa a tus columnas, tu jerga y tu idioma, y lo integro donde lo necesites.',
    'cases.yours.cta': 'Cuéntame tu caso',

    // Tech
    'tech.title': 'Ingeniería seria por debajo',
    'tech.subtitle':
      'Arquitectura por capas, decisiones documentadas (ADRs) y una amplia suite de pruebas.',
    'tech.layer.frontend': 'Frontend',
    'tech.layer.backend': 'Backend',
    'tech.layer.db': 'Base de datos',
    'tech.layer.ai': 'IA',
    'tech.layer.infra': 'Infra',
    'tech.val.frontend': 'React 18 · TypeScript · Vite · CSS Modules · Vitest',
    'tech.val.backend': 'Python · FastAPI · asyncpg · openpyxl / pandas',
    'tech.val.db': 'PostgreSQL 16',
    'tech.val.ai': 'OpenAI Whisper (whisper-1) + gpt-4o-mini',
    'tech.val.infra': 'Docker Compose · Nginx (sirve y proxea /api)',
    'tech.quality.tests': 'Desarrollo guiado por pruebas (pytest + Vitest).',
    'tech.quality.adr': 'Decisiones registradas como ADRs.',
    'tech.quality.layers': 'Capas estrictas: routes → services → repositories → models.',
    'tech.repoCta': 'Explorar el código',

    // Contact
    'contact.title': 'Hablemos de tu caso',
    'contact.subtitle':
      'Cuéntame qué datos capturas hoy y cómo te gustaría hacerlo por voz. Te respondo personalmente.',
    'contact.name': 'Nombre',
    'contact.email': 'Correo',
    'contact.company': 'Empresa',
    'contact.optional': 'opcional',
    'contact.message': 'Mensaje',
    'contact.namePlaceholder': 'Tu nombre',
    'contact.emailPlaceholder': 'tucorreo@ejemplo.com',
    'contact.companyPlaceholder': 'Tu empresa u organización',
    'contact.messagePlaceholder': '¿Qué te gustaría capturar por voz?',
    'contact.submit': 'Enviar mensaje',
    'contact.submitting': 'Enviando…',
    'contact.success': '¡Gracias! Mensaje recibido. Te responderé pronto.',
    'contact.error': 'No se pudo enviar el mensaje. Inténtalo de nuevo en un momento.',
    'contact.validation.name': 'Escribe tu nombre.',
    'contact.validation.email': 'Escribe un correo válido.',
    'contact.validation.message': 'Escribe un mensaje.',
    'contact.altEmail': 'O escríbeme directamente',
    'contact.altCalendly': 'Agenda una llamada',

    // Footer
    'footer.tagline': 'Captura de datos por voz, potenciada por IA.',
    'footer.github': 'GitHub',
    'footer.app': 'Probar la app',
    'footer.linkedin': 'LinkedIn',
    'footer.rights': 'Voxa · Proyecto de portafolio. Disponible para adaptaciones a medida.',

    // Privacy notice (ADR-0019 §8) — the contact form collects personal data
    'privacy.link': 'Aviso de privacidad',
    'privacy.title': 'Aviso de privacidad',
    'privacy.contactTitle': 'El formulario de contacto',
    'privacy.contactBody':
      'Si nos escribes, guardamos tu nombre, correo, empresa (si la pones) y tu mensaje, únicamente para responderte. No los compartimos ni los vendemos.',
    'privacy.demoTitle': 'La demostración de Voxa',
    'privacy.demoBody':
      'La aplicación procesa voz y tiene su propio aviso de privacidad, disponible en su pie de página. Ahí se explica a dónde va el audio, qué se conserva y por cuánto tiempo.',
    'privacy.rightsTitle': 'Tus derechos',
    'privacy.rightsBody':
      'Puedes pedir el acceso, la rectificación, la cancelación o la oposición al tratamiento de tus datos (derechos ARCO) escribiendo al correo de contacto. Responsable: Carlos Vega.',
    'privacy.close': 'Cerrar',
  },
  en: {
    // Language switcher
    'lang.switchToEs': 'Ver Voxa en español',
    'lang.switchToEn': 'View Voxa in English',
    'lang.groupLabel': 'Page language',

    // Nav
    'nav.how': 'How it works',
    'nav.features': 'Features',
    'nav.cases': 'Use cases',
    'nav.tech': 'Tech',
    'nav.contact': 'Contact',

    // Hero
    'hero.badge': 'Voice data capture · AI',
    'hero.title': 'Talk, and Voxa fills your Excel.',
    'hero.subtitle':
      'Upload a template, narrate the information out loud, and AI transcribes your speech and extracts each value into its column. No typing, no forms.',
    'hero.ctaPrimary': "Let's talk about your use case",
    'hero.ctaGithub': 'View on GitHub',
    'hero.ctaApp': 'Try the app',

    // Hero mockup (animated)
    'mockup.spoken': '“Azteca Stadium, capacity 87,000, match on September 17th”',
    'mockup.recording': 'Recording',
    'mockup.transcribing': 'Transcribing',
    'mockup.extracting': 'Extracting fields',
    'mockup.done': 'Row added',
    'mockup.colVenue': 'Venue',
    'mockup.colCapacity': 'Capacity',
    'mockup.colDate': 'Date',
    'mockup.ariaLabel':
      'Animated demo: speech becomes text and then a row in Excel.',

    // How it works
    'how.title': 'From voice to cell, in six steps',
    'how.subtitle':
      'The same flow you see in the app, friction-free: upload, narrate, download.',
    'how.step1.title': 'Upload your template',
    'how.step1.desc': 'Load an .xlsx file and Voxa detects columns and data types.',
    'how.step2.title': 'Confirm the schema',
    'how.step2.desc': 'Review the detected columns and confirm before you start.',
    'how.step3.title': 'Narrate',
    'how.step3.desc': 'Record or upload audio describing the record to capture.',
    'how.step4.title': 'Transcribe (Whisper)',
    'how.step4.desc': 'OpenAI Whisper turns your speech into text and you confirm it.',
    'how.step5.title': 'Extract fields (LLM)',
    'how.step5.desc': 'gpt-4o-mini maps the text to each column and appends the row.',
    'how.step6.title': 'Download the Excel',
    'how.step6.desc': 'The file is rebuilt in memory and you download it ready to use.',

    // Features
    'features.title': 'Built with product judgment',
    'features.subtitle':
      "It's not just “audio to Excel”: every decision protects data quality and the experience.",
    'features.bilingual.title': 'Bilingual ES / EN',
    'features.bilingual.desc':
      'UI and transcription in Spanish or English, with a switcher and persistence.',
    'features.stateless.title': 'In-memory export',
    'features.stateless.desc':
      'Rows live in the database; the .xlsx is rebuilt on download.',
    'features.cap.title': 'Bounded recording (20s)',
    'features.cap.desc':
      'Configurable limit, validated on client and server, ready for paid tiers.',
    'features.mic.title': 'Microphone warning',
    'features.mic.desc':
      'If it detects a Bluetooth mic, it warns you: low fidelity hurts accuracy.',
    'features.absent.title': 'Absent vs. unmentioned',
    'features.absent.desc':
      'Saying “no parking” stores an explicit 0, distinct from a column left blank.',
    'features.dates.title': 'Normalized dates',
    'features.dates.desc':
      'Any narrated form is normalized to a consistent format (17-sep-2026).',

    // Use cases
    'cases.title': 'One core, many domains',
    'cases.subtitle':
      'Voxa is the engine; your use case is the configuration. That is how playPro Stats was born.',
    'cases.playpro.tag': 'Real case',
    'cases.playpro.title': 'playPro Stats',
    'cases.playpro.desc':
      'Voice capture of American-football statistics. Built as a configuration on top of the Voxa core —not a fork—: same pipelines, different vocabulary and columns.',
    'cases.yours.tag': 'Your project',
    'cases.yours.title': 'Your domain?',
    'cases.yours.desc':
      'Inventory, medical visits, inspections, field surveys… I adapt Voxa to your columns, your jargon and your language, and integrate it wherever you need.',
    'cases.yours.cta': 'Tell me about your case',

    // Tech
    'tech.title': 'Serious engineering underneath',
    'tech.subtitle':
      'Layered architecture, documented decisions (ADRs) and a broad test suite.',
    'tech.layer.frontend': 'Frontend',
    'tech.layer.backend': 'Backend',
    'tech.layer.db': 'Database',
    'tech.layer.ai': 'AI',
    'tech.layer.infra': 'Infra',
    'tech.val.frontend': 'React 18 · TypeScript · Vite · CSS Modules · Vitest',
    'tech.val.backend': 'Python · FastAPI · asyncpg · openpyxl / pandas',
    'tech.val.db': 'PostgreSQL 16',
    'tech.val.ai': 'OpenAI Whisper (whisper-1) + gpt-4o-mini',
    'tech.val.infra': 'Docker Compose · Nginx (serves & proxies /api)',
    'tech.quality.tests': 'Test-driven development (pytest + Vitest).',
    'tech.quality.adr': 'Decisions recorded as ADRs.',
    'tech.quality.layers': 'Strict layers: routes → services → repositories → models.',
    'tech.repoCta': 'Explore the code',

    // Contact
    'contact.title': "Let's talk about your case",
    'contact.subtitle':
      'Tell me what data you capture today and how you would like to do it by voice. I reply personally.',
    'contact.name': 'Name',
    'contact.email': 'Email',
    'contact.company': 'Company',
    'contact.optional': 'optional',
    'contact.message': 'Message',
    'contact.namePlaceholder': 'Your name',
    'contact.emailPlaceholder': 'you@example.com',
    'contact.companyPlaceholder': 'Your company or organization',
    'contact.messagePlaceholder': 'What would you like to capture by voice?',
    'contact.submit': 'Send message',
    'contact.submitting': 'Sending…',
    'contact.success': 'Thanks! Message received. I will get back to you soon.',
    'contact.error': 'The message could not be sent. Please try again in a moment.',
    'contact.validation.name': 'Enter your name.',
    'contact.validation.email': 'Enter a valid email.',
    'contact.validation.message': 'Enter a message.',
    'contact.altEmail': 'Or email me directly',
    'contact.altCalendly': 'Book a call',

    // Footer
    'footer.tagline': 'Voice-powered data capture, driven by AI.',
    'footer.github': 'GitHub',
    'footer.app': 'Try the app',
    'footer.linkedin': 'LinkedIn',
    'footer.rights': 'Voxa · Portfolio project. Available for custom adaptations.',

    // Privacy notice (ADR-0019 §8) — the contact form collects personal data
    'privacy.link': 'Privacy notice',
    'privacy.title': 'Privacy notice',
    'privacy.contactTitle': 'The contact form',
    'privacy.contactBody':
      'If you write to us we store your name, email, company (if given) and your message, solely to reply to you. We do not share or sell them.',
    'privacy.demoTitle': 'The Voxa demo',
    'privacy.demoBody':
      'The application processes voice and carries its own privacy notice, linked from its footer. It explains where the audio goes, what is kept, and for how long.',
    'privacy.rightsTitle': 'Your rights',
    'privacy.rightsBody':
      'You may request access, rectification, cancellation, or object to the processing of your data by writing to the contact address. Data controller: Carlos Vega.',
    'privacy.close': 'Close',
  },
} satisfies Record<Language, Record<string, string>>;
