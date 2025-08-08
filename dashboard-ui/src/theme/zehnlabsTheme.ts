import { createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    zehnlabs: {
      primary: string;
      primaryLight: string;
      primaryDark: string;
      accent: string;
      accentLight: string;
    };
  }
  
  interface PaletteOptions {
    zehnlabs?: {
      primary?: string;
      primaryLight?: string;
      primaryDark?: string;
      accent?: string;
      accentLight?: string;
    };
  }
}

export const zehnlabsTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2975ba',        // ZehnLabs blue
      light: '#4a8cd4',
      dark: '#1e5a94',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#1fc5d1',        // ZehnLabs cyan
      light: 'rgba(31, 197, 209, 0.45)',
      contrastText: '#ffffff',
    },
    success: { 
      main: '#52c41a',
      contrastText: '#ffffff',
    },
    error: { 
      main: '#ff4d4f',
      contrastText: '#ffffff',
    },
    warning: { 
      main: '#faad14',
      contrastText: '#000000',
    },
    background: {
      default: '#ffffff',
      paper: '#fafafa',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
    },
    zehnlabs: {
      primary: '#2975ba',
      primaryLight: '#4a8cd4',
      primaryDark: '#1e5a94',
      accent: '#1fc5d1',
      accentLight: 'rgba(31, 197, 209, 0.45)',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    fontSize: 16,
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          border: '1px solid rgba(0,0,0,0.08)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          textTransform: 'none',
          fontWeight: 500,
        },
        contained: {
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          '&:hover': {
            boxShadow: '0 4px 8px rgba(0,0,0,0.15)',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(135deg, #2975ba 0%, #1fc5d1 100%)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid rgba(31, 197, 209, 0.2)',
          background: '#fafafa',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          margin: '2px 8px',
          '&.Mui-selected': {
            backgroundColor: 'rgba(31, 197, 209, 0.1)',
            borderLeft: '4px solid #2975ba',
            '&:hover': {
              backgroundColor: 'rgba(31, 197, 209, 0.15)',
            },
          },
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: '#fafafa',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
        colorSuccess: {
          backgroundColor: '#f6ffed',
          color: '#52c41a',
          border: '1px solid #b7eb8f',
        },
        colorError: {
          backgroundColor: '#fff2f0',
          color: '#ff4d4f',
          border: '1px solid #ffccc7',
        },
      },
    },
  },
});

export default zehnlabsTheme;