# Frontend – Car Marketplace

This frontend is a React-based single-page application (SPA) for browsing and filtering car advertisements.

## 🔧 Technologies Used

- **React** (`create-react-app`)
- **Node.js** – used during Docker build for dependency installation and building React
- **Nginx** – serves the static React build in production
- **Docker** – containerizes the frontend for portability and deployment

## 🧩 Integration

This React app is connected to a **Django REST Framework backend**, which exposes several API endpoints under `/api/cars/`.

Examples of API routes:
- `GET /api/cars/filtered-list/` — get cars with optional filters
- `GET /api/cars/filters-summary/` — fetch available filter options

## 🚀 Development Workflow

```bash
# Start development server (hot reload)
npm start