# Grabby Web Frontend

React/TypeScript web interface for Grabby video downloader.

## Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Backend API running on port 8000

### Installation

1. **Install Node.js dependencies:**
```bash
npm install
```

2. **Start development server:**
```bash
npm start
```

3. **Build for production:**
```bash
npm run build
```

### Dependencies Installation

If you encounter module resolution errors, install the required dependencies:

```bash
# Core React dependencies
npm install react@^18.2.0 react-dom@^18.2.0

# TypeScript support
npm install -D typescript@^4.9.5 @types/react@^18.2.0 @types/react-dom@^18.2.0

# Material-UI components
npm install @mui/material@^5.14.0 @emotion/react@^11.11.0 @emotion/styled@^11.11.0
npm install @mui/icons-material@^5.14.0

# React Query for data fetching
npm install @tanstack/react-query@^4.32.0

# Routing
npm install react-router-dom@^6.15.0 @types/react-router-dom@^5.3.0

# WebSocket client
npm install socket.io-client@^4.7.0

# HTTP client
npm install axios@^1.5.0

# Date utilities
npm install date-fns@^2.30.0

# React scripts for development
npm install -D react-scripts@^5.0.1
```

### Environment Variables

Create a `.env` file in the web directory:
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Features

- **Dashboard** - Overview of downloads and statistics
- **Downloads** - Browse and manage downloads
- **Queue** - Real-time queue management
- **History** - Download history with search
- **Settings** - Application configuration
- **Real-time Updates** - WebSocket integration for live updates

### Troubleshooting

**Module not found errors:**
- Run `npm install` to install all dependencies
- Check that Node.js 18+ is installed
- Clear npm cache: `npm cache clean --force`

**Build errors:**
- Ensure TypeScript is properly configured
- Check `tsconfig.json` is present
- Verify all import paths are correct
