import React, { useState } from 'react';
import {
  Show,
  SimpleShowLayout,
  TextField,
  DateField,
  FunctionField,
  useRecordContext,
  useNotify,
  useRefresh,
  TopToolbar,
  Button,
  Labeled,
} from 'react-admin';
import {
  Card,
  CardContent,
  CardHeader,
  Grid,
  Typography,
  Box,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon,
  Description as LogsIcon,
} from '@mui/icons-material';
import { customApi } from '../../providers/dataProvider';
import { useRealtimeResource } from '../../providers/realtimeProvider';

const formatBytes = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

// React-Admin style field for status with chip
const StatusField: React.FC = () => {
  const record = useRecordContext();
  if (!record) return null;
  
  return (
    <Chip
      label={record.status}
      color={record.status === 'running' ? 'success' : 'error'}
      variant="outlined"
    />
  );
};

// React-Admin style field for ports
const PortsField: React.FC = () => {
  const record = useRecordContext();
  if (!record?.ports || record.ports.length === 0) return <span>-</span>;
  
  return <span>{record.ports.join(', ')}</span>;
};

// React-Admin style field for resource stats
const ResourceStatsField: React.FC<{ stat: string; format?: 'bytes' | 'percent' }> = ({ 
  stat, 
  format 
}) => {
  const record = useRecordContext();
  
  if (!record?.stats || record.stats.error) {
    return <span>N/A</span>;
  }
  
  const value = record.stats[stat];
  if (value == null) return <span>N/A</span>;
  
  if (format === 'bytes') {
    return <span>{formatBytes(value)}</span>;
  }
  
  if (format === 'percent') {
    return <span>{value.toFixed(2)}%</span>;
  }
  
  return <span>{value}</span>;
};

// Container Actions using react-admin TopToolbar pattern
const ContainerActions: React.FC = () => {
  const record = useRecordContext();
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = useState<string | null>(null);
  const [logsDialog, setLogsDialog] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  
  if (!record) return null;

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    const isCritical = ['management-service', 'redis', 'ibkr-gateway'].includes(record.name);
    if (isCritical && (action === 'stop' || action === 'restart')) {
      if (!window.confirm(`Are you sure you want to ${action} the critical service "${record.name}"?`)) {
        return;
      }
    }
    
    setLoading(action);
    try {
      await customApi.controlContainer(record.name, action);
      notify(`Container ${record.name} ${action}ed successfully`, { type: 'success' });
      setTimeout(refresh, 1000);
    } catch (error) {
      notify(`Failed to ${action} container: ${error}`, { type: 'error' });
    } finally {
      setLoading(null);
    }
  };

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const logData = await customApi.getContainerLogs(record.name, 200);
      setLogs(logData);
      setLogsDialog(true);
    } catch (error) {
      notify(`Failed to fetch logs: ${error}`, { type: 'error' });
    } finally {
      setLogsLoading(false);
    }
  };

  const getLogLineColor = (line: string): string => {
    const lowerLine = line.toLowerCase();
    if (lowerLine.includes('error') || lowerLine.includes('fatal')) return '#f44336';
    if (lowerLine.includes('warn')) return '#ff9800';
    if (lowerLine.includes('info')) return '#2196f3';
    if (lowerLine.includes('debug')) return '#9e9e9e';
    return '#ffffff';
  };

  const isRunning = record.status === 'running';

  return (
    <>
      <TopToolbar>
        <Button
          onClick={() => handleAction('start')}
          disabled={isRunning || loading !== null}
          startIcon={<StartIcon />}
          label="Start"
          variant="contained"
          color="success"
        />
        <Button
          onClick={() => handleAction('stop')}
          disabled={!isRunning || loading !== null}
          startIcon={<StopIcon />}
          label="Stop"
          variant="contained"
          color="error"
        />
        <Button
          onClick={() => handleAction('restart')}
          disabled={loading !== null}
          startIcon={<RestartIcon />}
          label="Restart"
          variant="contained"
          color="warning"
        />
        <Button
          onClick={fetchLogs}
          disabled={logsLoading}
          startIcon={logsLoading ? <CircularProgress size={20} /> : <LogsIcon />}
          label="View Logs"
          variant="outlined"
        />
      </TopToolbar>

      {/* Logs Dialog */}
      <Dialog
        open={logsDialog}
        onClose={() => setLogsDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Container Logs: {record.name}
        </DialogTitle>
        <DialogContent>
          <Paper 
            sx={{ 
              maxHeight: 500, 
              overflow: 'auto',
              backgroundColor: '#1e1e1e',
              p: 2
            }}
          >
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <Typography
                  key={index}
                  variant="body2"
                  component="div"
                  sx={{ 
                    fontFamily: 'monospace', 
                    whiteSpace: 'pre-wrap',
                    color: getLogLineColor(line),
                    fontSize: '0.875rem',
                    lineHeight: 1.4,
                    mb: 0.25
                  }}
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
    </>
  );
};

const ContainerShow: React.FC = () => {
  // Enable real-time updates for this container
  useRealtimeResource('containers');

  return (
    <Show actions={<ContainerActions />}>
      <SimpleShowLayout>
        {/* Basic Information */}
        <Typography variant="h6" gutterBottom>
          Service Information
        </Typography>
        
        <TextField source="id" label="Container ID" />
        <TextField source="name" label="Name" />
        <TextField source="image" label="Image" />
        <Labeled label="Status">
          <StatusField />
        </Labeled>
        <TextField source="state" label="State" />
        <DateField 
          source="created" 
          label="Created" 
          showTime
          options={{
            dateStyle: 'medium',
            timeStyle: 'short'
          }}
        />
        <Labeled label="Ports">
          <PortsField />
        </Labeled>
        
        {/* Resource Usage */}
        <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
          Resource Usage
        </Typography>
        
        <Labeled label="CPU Usage">
          <ResourceStatsField stat="cpu_usage_percent" format="percent" />
        </Labeled>
        
        <Labeled label="Memory Usage">
          <FunctionField
            render={(record: any) => {
              if (!record?.stats || record.stats.error) return 'N/A';
              const { memory_usage_bytes, memory_limit_bytes, memory_usage_percent } = record.stats;
              return `${formatBytes(memory_usage_bytes)} / ${formatBytes(memory_limit_bytes)} (${memory_usage_percent?.toFixed(2)}%)`;
            }}
          />
        </Labeled>
        
        <Labeled label="Network RX">
          <ResourceStatsField stat="network_rx_bytes" format="bytes" />
        </Labeled>
        
        <Labeled label="Network TX">
          <ResourceStatsField stat="network_tx_bytes" format="bytes" />
        </Labeled>
        
        <Labeled label="Block Read">
          <ResourceStatsField stat="block_read_bytes" format="bytes" />
        </Labeled>
        
        <Labeled label="Block Write">
          <ResourceStatsField stat="block_write_bytes" format="bytes" />
        </Labeled>
        
        <DateField 
          source="last_update" 
          label="Last Updated" 
          showTime
          options={{
            dateStyle: 'medium',
            timeStyle: 'medium'
          }}
        />
        
        {/* Labels Section - only show if labels exist */}
        <FunctionField
          render={(record: any) => {
            if (!record?.labels || Object.keys(record.labels).length === 0) {
              return null;
            }
            
            return (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Labels
                </Typography>
                {Object.entries(record.labels).map(([key, value]) => (
                  <Box key={key} sx={{ mb: 1 }}>
                    <Typography variant="body2">
                      <strong>{key}:</strong> {value as string}
                    </Typography>
                  </Box>
                ))}
              </Box>
            );
          }}
        />
      </SimpleShowLayout>
    </Show>
  );
};

export default ContainerShow;