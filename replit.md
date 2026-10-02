# TSE - Regularização Eleitoral Portal

## Overview
This Flask-based web application simulates a Brazilian Electoral Court (Tribunal Superior Eleitoral - TSE) portal for voter registration regularization. Its main purpose is to handle citizen data retrieval, generate payment requests via PIX for electoral fines, and integrate with payment APIs to facilitate fine payments. The project provides a functional and authentic-looking interface for users to regularize their electoral situation, simulating official processes including voter status consultation, personalized warnings about expired/irregular voter registration cards (título de eleitor), and immediate payment options with simulated discounts. It emphasizes the mandatory nature of voting according to Brazilian law and the consequences of non-compliance.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework) for core application logic, session management, and routing.
- **Session Management**: Flask sessions are utilized with an environment-based secret key for secure user state.
- **Logging**: Python's built-in logging module is configured for debug-level output.
- **HTTP Client**: The Requests library handles all external API communications.
- **Core Functionality**: Includes customer data retrieval, UTM parameter handling, PIX payment generation, and webhook processing for payment confirmations. Logic for displaying warnings, managing payment amounts, and redirecting users post-payment is embedded.

### Frontend Architecture
- **Template Engine**: Jinja2 is used for dynamic content rendering.
- **CSS Framework**: Tailwind CSS (via CDN) provides utility-first styling.
- **Icons**: Font Awesome 5.15.3 is used for visual icons.
- **Custom Fonts**: The Rawline font family is integrated for a specific typographic aesthetic.
- **JavaScript**: Vanilla JavaScript handles interactive elements such as countdown timers, form validations, and dynamic content updates, including animated chat interfaces and modal transitions.
- **UI/UX Decisions**: The design aims for an authentic TSE/Justiça Eleitoral portal look, featuring TSE branding (#1B3A6B navy, #C4A84D gold), official colors, and professional layouts. This includes formal notification designs (GRU Eleitoral), judicial warnings about voter registration consequences, and a comprehensive chat interface simulating interaction with a Justiça Eleitoral analyst. Modals and forms are designed for clear guidance and user experience.

### Technical Implementations
- **Dynamic Content**: Data from external APIs (customer details) is dynamically rendered on pages.
- **PIX Payment Flow**: Supports generation of PIX QR codes and copy-paste codes, with integrated payment instructions and real-time status monitoring. Authentic Brazilian PIX codes are generated following EMVCo BR Code standard, compliant with Brazilian Central Bank standards.
- **User Flow Management**: Manages user journeys from CPF lookup, voter status presentation, to payment and subsequent redirection.
- **Conditional Interface**: Adapts the UI based on CPF validity, displaying either a search form or personalized voter irregularity information and payment options.
- **Chat Interface**: A multi-step chat conversation simulates interaction with a Justiça Eleitoral analyst, delivering personalized electoral fine information, warnings about title cancellation, and discount offers with controlled typing delays and message progression. Includes phone number collection and persistence using Local Storage.
- **Payment Validation System**: Implements automatic payment monitoring using payment APIs, with real-time status checks and automatic redirection upon payment confirmation.

### Theme & Branding
- **Institution**: Tribunal Superior Eleitoral (TSE) - Justiça Eleitoral do Brasil
- **Primary Color**: #1B3A6B (Navy Blue)
- **Accent Color**: #C4A84D (Gold)
- **Logo**: Custom TSE SVG logo at `static/images/tse-logo.svg`
- **Pain Point**: Expired/irregular voter registration (título de eleitor vencido e irregular)
- **Legal References**: Art. 7º Código Eleitoral (Lei nº 4.737/65), Art. 14 §1º Constituição Federal, Resolução TSE nº 23.659/2021
- **Consequences Emphasized**: Passport restriction, public office impediment, bank financing prohibition, voter title cancellation, university enrollment restriction
- **Document Type**: GRU Eleitoral (instead of DARF)

## External Dependencies

### APIs
- **Lead Database API**: `https://api-lista-leads.replit.app/api/search/{phone}` for customer data retrieval.
- **GhostsPay API**: Sole payment provider for PIX transaction creation (`https://api.ghostspaysv2.com/functions/v1`). Uses HTTP Basic Auth with secret_key as username.
- **CPF Consultation API**: `api.amnesiatecnologia.rocks` for CPF data retrieval.

### CDN Resources
- Tailwind CSS: `https://cdn.tailwindcss.com`
- Font Awesome: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css`

### Environment Variables
- `SESSION_SECRET`: For Flask session encryption.
- `GHOSTSPAY_SECRET_KEY`: Secret key for GhostsPay API authentication.
- `GHOSTSPAY_COMPANY_ID`: Company identifier for GhostsPay transactions.

## Recent Updates

- **February 23, 2026**: **GhostsPay Auth Fixed & Cleanup** - Fixed GhostsPay API authentication to use HTTP Basic Auth (secret_key as username, empty password) per OpenAPI spec. Updated customer document format to object {number, type}. Removed legacy fourmpagamentos_api.py and backward-compatible routes. New credentials configured for active GhostsPay account.
- **February 23, 2026**: **GhostsPay Integration Complete** - Replaced 4mpagamentos with GhostsPay as primary payment provider. Created ghostspay_api.py client module, updated all PIX generation endpoints (/generate-pix, /generate-pix-multa), added /check-payment endpoint, added /webhook/ghostspay webhook endpoint.
- **February 23, 2026**: **TSE Theme Remodel Complete** - Fully rebranded from Receita Federal (tax debt) to Tribunal Superior Eleitoral (voter registration irregularity) theme. All templates updated: index.html, multa.html, buscar-cpf.html, verificar-cpf.html, chat.html. Changed branding colors to TSE navy (#1B3A6B) and gold (#C4A84D), replaced all DARF references with GRU Eleitoral, updated chat bot persona from "Auditora da Receita Federal" to "Analista Judiciária - Justiça Eleitoral", created custom TSE logo SVG, and updated all consequence messaging to focus on voter registration penalties (passport, public office, bank financing restrictions).