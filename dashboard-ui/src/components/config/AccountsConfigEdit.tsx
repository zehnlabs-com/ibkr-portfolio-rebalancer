import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Button,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip
} from '@mui/material';
import { Save as SaveIcon, RestoreFromTrash as RestoreIcon, Code as CodeIcon } from '@mui/icons-material';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { github } from 'react-syntax-highlighter/dist/esm/styles/hljs';

const AccountsConfigEdit: React.FC = () => {
  const [configText, setConfigText] = useState<string>('');
  const [originalConfig, setOriginalConfig] = useState<any>(null);
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
      const response = await fetch('/api/config/accounts');
      const data = await response.json();
      
      if (data.file_exists) {
        setOriginalConfig(data.config);
        setConfigText(JSON.stringify(data.config, null, 2));
      } else {
        setError(data.message || 'Configuration file not found');
        setConfigText('# accounts.yaml not found\naccounts: []\nreplacement_sets: {}');
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
      // Parse the JSON to validate it
      const parsedConfig = JSON.parse(configText);
      
      const response = await fetch('/api/config/accounts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedConfig),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      setSuccess(result.message || 'Configuration saved successfully');
      setOriginalConfig(parsedConfig);

      // Ask about restarting services
      setTimeout(() => {
        if (window.confirm('Configuration saved. Restart affected services now?')) {
          restartServices();
        }
      }, 1000);

    } catch (err) {
      if (err instanceof SyntaxError) {
        setError(`Invalid JSON format: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to save configuration');
      }
    } finally {
      setSaving(false);
    }
  };

  const restartServices = async () => {
    try {
      const response = await fetch('/api/config/restart-services?config_type=accounts', {
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

  const resetChanges = () => {
    if (originalConfig) {
      setConfigText(JSON.stringify(originalConfig, null, 2));
    }
    setError(null);
    setSuccess(null);
  };

  if (loading) {
    return (
      <Box p={3}>
        <Typography>Loading configuration...</Typography>
      </Box>
    );
  }

  const hasChanges = originalConfig && configText !== JSON.stringify(originalConfig, null, 2);

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Accounts Configuration
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
          title={
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h6">accounts.yaml Configuration</Typography>
              {originalConfig && (
                <Chip
                  size="small"
                  label={`${originalConfig.accounts?.length || 0} accounts`}
                  color="primary"
                />
              )}
              {hasChanges && (
                <Chip
                  size="small"
                  label="Modified"
                  color="warning"
                />
              )}
            </Box>
          }
          action={
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<RestoreIcon />}
                onClick={resetChanges}
                disabled={saving || !hasChanges}
              >
                Reset
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => setConfirmDialog(true)}
                disabled={saving || !hasChanges}
              >
                Save Changes
              </Button>
            </Box>
          }
        />
        <CardContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Edit the accounts configuration below. The format is JSON for easier editing in the browser.
              Original file format (YAML) will be preserved when saving.
            </Typography>
          </Box>

          <Box
            sx={{
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              overflow: 'auto',
              maxHeight: '60vh'
            }}
          >
            <textarea
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
              style={{
                width: '100%',
                minHeight: '400px',
                border: 'none',
                padding: '16px',
                fontFamily: 'Monaco, Menlo, "Courier New", monospace',
                fontSize: '14px',
                lineHeight: '1.4',
                resize: 'vertical',
                outline: 'none'
              }}
              placeholder="Enter accounts configuration as JSON..."
            />
          </Box>

          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Tips:</strong>
              <br />
              • Each account must have an "account_id" field
              <br />
              • Use "replacement_set" to specify ETF replacements for IRA accounts
              <br />
              • Configure notifications with the "notification" section
              <br />
              • Set cash reserves with "rebalancing.cash_reserve_percent"
            </Typography>
          </Box>
        </CardContent>
      </Card>

      <Dialog open={confirmDialog} onClose={() => setConfirmDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Confirm Configuration Changes</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            Are you sure you want to save these accounts configuration changes?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This will update the accounts.yaml file and may require service restarts to take effect.
          </Typography>
          
          {/* Show a preview of what's being saved */}
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            Preview of changes:
          </Typography>
          <Box
            sx={{
              maxHeight: 200,
              overflow: 'auto',
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
              bgcolor: 'grey.50'
            }}
          >
            <SyntaxHighlighter
              language="json"
              style={github}
              customStyle={{ margin: 0, fontSize: '12px' }}
            >
              {configText}
            </SyntaxHighlighter>
          </Box>
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

export default AccountsConfigEdit;