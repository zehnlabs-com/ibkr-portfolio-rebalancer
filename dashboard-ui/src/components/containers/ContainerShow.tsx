import React, { useState, useEffect } from 'react';
import {
  Show,
  SimpleShowLayout,
  TextField,
  DateField,
  useGetOne,
  useRefresh,
  Loading,
  Error,
  useNotify
} from 'react-admin';
import {
  Card,
  CardContent,
  CardHeader,
  Grid,
  Typography,
  Box,
  Chip,
  Button,
  ButtonGroup,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon,
  Description as LogsIcon,
  Autorenew as AutoRefreshIcon
} from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import { dashboardApi } from '../../providers/dataProvider';
import { useRealTimeData } from '../../providers/websocketProvider';

const ContainerShow: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const refresh = useRefresh();
  const notify = useNotify();
  
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsDialog, setLogsDialog] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; action: string | null; }>({ open: false, action: null });
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  const { data, isLoading, error } = useGetOne('containers', { id: id! });
  
  // Set up real-time updates
  useRealTimeData('containers', (updateData) => {
    if (updateData.name === id) {
      refresh();
    }
  });

  // Auto refresh every 10 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      refresh();
    }, 10000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, refresh]);

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    if (action === 'stop' || action === 'restart') {
      setConfirmDialog({ open: true, action });
      return;
    }
    
    await executeAction(action);
  };
  
  const executeAction = async (action: 'start' | 'stop' | 'restart') => {
    setActionLoading(action);
    setConfirmDialog({ open: false, action: null });
    
    try {
      const result = await dashboardApi.controlContainer(id!, action);
      notify(`Container ${action} successful: ${result.message}`, { type: 'success' });
      setTimeout(refresh, 1000); // Refresh after a delay to see the status change
    } catch (error) {
      notify(`Failed to ${action} container: ${error}`, { type: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const logData = await dashboardApi.getContainerLogs(id!, 200);
      setLogs(logData);
      setLogsDialog(true);
    } catch (error) {
      notify(`Failed to fetch logs: ${error}`, { type: 'error' });
    } finally {
      setLogsLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const getLogLineClass = (line: string): string => {
    const lowerLine = line.toLowerCase();
    if (lowerLine.includes('error') || lowerLine.includes('fatal')) return 'error';
    if (lowerLine.includes('warn')) return 'warning';
    if (lowerLine.includes('info')) return 'info';
    if (lowerLine.includes('debug')) return 'debug';
    return '';
  };

  if (isLoading) return <Loading />;
  if (error) return <Error />;
  if (!data) return null;

  const isRunning = data.status === 'running';
  const isCritical = ['management-service', 'redis', 'ibkr-gateway'].includes(data.name);
  const stats = data.stats;

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="h4" gutterBottom>
            Service: {data.name}
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Chip
              label={data.status}
              color={isRunning ? 'success' : 'error'}
              variant="outlined"
              className={`status-indicator status-${data.status?.toLowerCase()}`}
            />
            <Typography variant="body2" color="text.secondary">
              Last updated: {new Date(data.last_update).toLocaleString()}
            </Typography>
          </Box>
        </Box>
        
        <Box display="flex" alignItems="center" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                icon={<AutoRefreshIcon />}
                checkedIcon={<AutoRefreshIcon />}
              />
            }
            label="Auto Refresh"
          />
          
          <ButtonGroup variant="contained">
            <Button
              startIcon={<StartIcon />}
              onClick={() => handleAction('start')}
              disabled={isRunning || actionLoading === 'start' || isCritical}
              color="success"
            >
              Start
            </Button>
            <Button
              startIcon={<StopIcon />}
              onClick={() => handleAction('stop')}
              disabled={!isRunning || actionLoading === 'stop' || isCritical}
              color="error"
            >
              Stop
            </Button>
            <Button
              startIcon={<RestartIcon />}
              onClick={() => handleAction('restart')}
              disabled={actionLoading === 'restart' || isCritical}
              color="warning"
            >
              Restart
            </Button>
          </ButtonGroup>
          
          <Button
            startIcon={<LogsIcon />}
            onClick={fetchLogs}
            disabled={logsLoading}
            variant="outlined"
          >
            View Logs
          </Button>
        </Box>
      </Box>

      {/* Service Information */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Service Information" />
            <CardContent>
              <List dense>
                <ListItem>
                  <ListItemText primary="Container ID" secondary={data.id} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Image" secondary={data.image} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Status" secondary={data.status} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="State" secondary={data.state} />
                </ListItem>
                <ListItem>
                  <ListItemText 
                    primary="Created" 
                    secondary={data.created ? new Date(data.created).toLocaleString() : 'N/A'} 
                  />
                </ListItem>
                {data.ports && data.ports.length > 0 && (
                  <ListItem>
                    <ListItemText 
                      primary="Ports" 
                      secondary={data.ports.join(', ')} 
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Resource Usage" />
            <CardContent>
              {stats && !stats.error ? (
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="CPU Usage" 
                      secondary={`${stats.cpu_usage_percent?.toFixed(2)}%`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Memory Usage" 
                      secondary={`${formatBytes(stats.memory_usage_bytes)} / ${formatBytes(stats.memory_limit_bytes)} (${stats.memory_usage_percent?.toFixed(2)}%)`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Network RX" 
                      secondary={formatBytes(stats.network_rx_bytes)} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Network TX" 
                      secondary={formatBytes(stats.network_tx_bytes)} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Block Read" 
                      secondary={formatBytes(stats.block_read_bytes)} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Block Write" 
                      secondary={formatBytes(stats.block_write_bytes)} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Stats Updated" 
                      secondary={new Date(stats.timestamp).toLocaleString()} 
                    />
                  </ListItem>
                </List>
              ) : (
                <Typography color="text.secondary">
                  {isRunning ? 'Stats not available' : 'Container not running'}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Labels if any */}
        {data.labels && Object.keys(data.labels).length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Labels" />
              <CardContent>
                <List dense>
                  {Object.entries(data.labels).map(([key, value]) => (
                    <ListItem key={key}>
                      <ListItemText primary={key} secondary={value as string} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, action: null })}
      >
        <DialogTitle>
          Confirm {confirmDialog.action?.toUpperCase()} Container
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {confirmDialog.action} the container "{data.name}"?
          </Typography>
          {isCritical && (
            <Typography color="error" variant="body2" sx={{ mt: 1 }}>
              Warning: This is a critical service and the action may affect system stability.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setConfirmDialog({ open: false, action: null })}
          >
            Cancel
          </Button>
          <Button 
            onClick={() => executeAction(confirmDialog.action as 'stop' | 'restart')}
            color={confirmDialog.action === 'stop' ? 'error' : 'warning'}
            variant="contained"
          >
            {confirmDialog.action?.toUpperCase()}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Logs Dialog */}
      <Dialog
        open={logsDialog}
        onClose={() => setLogsDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Container Logs: {data.name}
        </DialogTitle>
        <DialogContent>
          <Paper className="log-viewer" sx={{ maxHeight: 500, overflow: 'auto' }}>
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <Typography
                  key={index}
                  variant="body2"
                  component="div"
                  className={`log-line ${getLogLineClass(line)}`}
                  sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}
                >
                  {line}
                </Typography>
              ))
            ) : (
              <Typography color="text.secondary">
                No logs available
              </Typography>
            )}
          </Paper>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialog(false)}>
            Close
          </Button>
          <Button onClick={fetchLogs} disabled={logsLoading}>
            Refresh Logs
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ContainerShow;