import React from 'react';
import { IconButton, Tooltip, Box } from '@mui/material';
import { DarkMode, LightMode } from '@mui/icons-material';
import { useTheme } from '../theme/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { mode, toggleTheme } = useTheme();

  return (
    <Tooltip title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
      <IconButton
        onClick={toggleTheme}
        sx={{
          color: 'inherit',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'rotate(180deg)',
            backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.04)',
          },
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            transform: mode === 'dark' ? 'scale(1)' : 'scale(1.1)',
          }}
        >
          {mode === 'dark' ? (
            <LightMode 
              sx={{ 
                fontSize: 20,
                color: '#fbbf24',
              }} 
            />
          ) : (
            <DarkMode 
              sx={{ 
                fontSize: 20,
                color: '#6366f1',
              }} 
            />
          )}
        </Box>
      </IconButton>
    </Tooltip>
  );
};