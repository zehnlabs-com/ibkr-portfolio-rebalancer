import React from 'react';
import { AppBar, TitlePortal } from 'react-admin';
import { Box } from '@mui/material';
import { ThemeToggle } from './ThemeToggle';

export const CustomAppBar: React.FC = () => (
  <AppBar>
    <TitlePortal />
    <Box sx={{ flexGrow: 1 }} />
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
      <ThemeToggle />
    </Box>
  </AppBar>
);