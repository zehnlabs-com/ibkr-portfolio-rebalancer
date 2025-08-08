import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Button,
  TextField,
  Grid,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip
} from '@mui/material';
import { Save as SaveIcon, RestoreFromTrash as RestoreIcon } from '@mui/icons-material';

const EnvConfigEdit: React.FC = () => {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config/env');
      const data = await response.json();
      
      if (data.file_exists) {
        setConfig(data.config || {});
      } else {
        setError(data.message || 'Configuration file not found');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    setConfirmDialog(false);

    try {
      const response = await fetch('/api/config/env', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setSuccess(result.message || 'Configuration saved successfully');

      // Ask about restarting services
      setConfirmDialog(false);
      setTimeout(() => {
        if (window.confirm('Configuration saved. Restart affected services now?')) {
          restartServices();
        }
      }, 1000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const restartServices = async () => {
    try {
      const response = await fetch('/api/config/restart-services?config_type=env', {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        setSuccess(`Services restarted: ${result.services_restarted}/${result.total_services} successful`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart services');
    }
  };

  const handleConfigChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const isSensitive = (key: string): boolean => {
    return ['PASSWORD', 'TOKEN', 'SECRET', 'KEY'].some(sensitive => 
      key.toUpperCase().includes(sensitive)
    );
  };

  if (loading) {
    return (
      <Box p={3}>
        <Typography>Loading configuration...</Typography>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Environment Configuration
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Card>
        <CardHeader
          title="Environment Variables"
          action={
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<RestoreIcon />}
                onClick={fetchConfig}
                disabled={saving}
              >
                Reset
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => setConfirmDialog(true)}
                disabled={saving}
              >
                Save Changes
              </Button>
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={3}>
            {Object.entries(config).map(([key, value]) => (
              <Grid item xs={12} sm={6} key={key}>
                <TextField
                  fullWidth
                  label={key}
                  value={value}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  type={isSensitive(key) ? 'password' : 'text'}
                  InputProps={{
                    endAdornment: isSensitive(key) ? (
                      <Chip size="small" label="Sensitive" color="warning" />
                    ) : null
                  }}
                  helperText={isSensitive(key) ? 'Sensitive value - masked for security' : undefined}
                />
              </Grid>
            ))}
          </Grid>

          {Object.keys(config).length === 0 && (
            <Box className="empty-state">
              <Typography className="empty-message">
                No configuration found
              </Typography>
              <Typography className="empty-description">
                The environment configuration file is empty or doesn't exist.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      <Dialog open={confirmDialog} onClose={() => setConfirmDialog(false)}>
        <DialogTitle>Confirm Configuration Changes</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to save these environment configuration changes?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This will update the .env file and may require service restarts to take effect.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EnvConfigEdit;