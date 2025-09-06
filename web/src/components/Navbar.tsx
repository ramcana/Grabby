import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Badge,
} from '@mui/material';
import {
  Dashboard,
  Download,
  Queue,
  History,
  Settings,
  Notifications,
} from '@mui/icons-material';
import { useWebSocket } from '../contexts/WebSocketContext';

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { connectionStatus, activeDownloads } = useWebSocket();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Dashboard /> },
    { path: '/downloads', label: 'Downloads', icon: <Download /> },
    { path: '/queue', label: 'Queue', icon: <Queue /> },
    { path: '/history', label: 'History', icon: <History /> },
    { path: '/settings', label: 'Settings', icon: <Settings /> },
  ];

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ mr: 4 }}>
          Grabby
        </Typography>
        
        <Box sx={{ flexGrow: 1, display: 'flex', gap: 1 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              sx={{
                backgroundColor: location.pathname === item.path ? 'rgba(255,255,255,0.1)' : 'transparent',
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton color="inherit">
            <Badge badgeContent={activeDownloads} color="secondary">
              <Notifications />
            </Badge>
          </IconButton>
          
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: connectionStatus === 'connected' ? 'success.main' : 'error.main',
              ml: 1,
            }}
            title={`WebSocket: ${connectionStatus}`}
          />
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
