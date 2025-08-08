import React from 'react';
import {
  useDataProvider,
  useNotify,
  Loading,
  SaveButton,
  Toolbar,
} from 'react-admin';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Alert,
  Button,
} from '@mui/material';
import { customApi } from '../../providers/dataProvider';
import { JsonField } from '../../fields/JsonField';

const AccountsConfigEdit: React.FC = () => {
  const dataProvider = useDataProvider();
  const notify = useNotify();
  const [configData, setConfigData] = React.useState<string>('');
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const data = await customApi.getConfig('accounts');
      if (data.file_exists) {
        setConfigData(JSON.stringify(data.config, null, 2));
      } else {
        setConfigData(JSON.stringify({ accounts: [], replacement_sets: {} }, null, 2));
      }
    } catch (error) {
      notify(`Failed to load configuration: ${error}`, { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Validate JSON
      const parsedConfig = JSON.parse(configData);
      
      // Save configuration
      await dataProvider.update('config-accounts', {
        id: 'accounts',
        data: parsedConfig,
        previousData: {}
      });
      
      notify('Configuration saved successfully', { type: 'success' });
      
      // Ask about restarting services
      if (window.confirm('Configuration saved. Restart affected services now?')) {
        await customApi.restartServices('accounts');
        notify('Services restarted successfully', { type: 'success' });
      }
    } catch (error) {
      if (error instanceof SyntaxError) {
        notify(`Invalid JSON format: ${error.message}`, { type: 'error' });
      } else {
        notify(`Failed to save configuration: ${error}`, { type: 'error' });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = () => {
    if (window.confirm('Are you sure you want to restore the original configuration?')) {
      fetchConfig();
      notify('Configuration restored', { type: 'info' });
    }
  };

  if (loading) return <Loading />;

  return (
    <Box p={3}>
      <Card>
        <CardHeader 
          title="Accounts Configuration"
          subheader="Edit the accounts.yaml configuration file"
        />
        <CardContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This configuration defines account settings, replacement sets, and notification channels.
            Make sure to maintain valid JSON format.
          </Alert>
          
          <Box sx={{ mb: 2 }}>
            <JsonField
              source="config"
              label="Configuration (JSON)"
              helperText="Edit the configuration in JSON format. Use 'Format JSON' to auto-format."
            />
            
            <textarea
              value={configData}
              onChange={(e) => setConfigData(e.target.value)}
              style={{
                width: '100%',
                minHeight: '400px',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                padding: '12px',
                border: '1px solid rgba(0, 0, 0, 0.23)',
                borderRadius: '4px',
                backgroundColor: '#fafafa',
              }}
            />
          </Box>
          
          <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Box>
              <SaveButton
                label="Save Configuration"
                onClick={handleSave}
                disabled={saving}
                saving={saving}
                sx={{ mr: 2 }}
              />
              <Button
                variant="outlined"
                onClick={handleRestore}
                disabled={saving}
              >
                Restore Original
              </Button>
            </Box>
            
            <Button
              variant="text"
              onClick={() => window.history.back()}
            >
              Cancel
            </Button>
          </Toolbar>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AccountsConfigEdit;