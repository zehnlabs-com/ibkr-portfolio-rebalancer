import React, { useState } from 'react';
import {
  List,
  Datagrid,
  TextField,
  DateField,
  FunctionField,
  useRefresh,
  useNotify
} from 'react-admin';
import {
  Button,
  ButtonGroup,
  Chip,
  Typography,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon
} from '@mui/icons-material';
import { dashboardApi } from '../../providers/dataProvider';
import { useRealTimeData } from '../../providers/websocketProvider';

const StatusField = ({ record, source }: { record: any; source: string }) => {
  const status = record[source];
  
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'running':
        return 'success';
      case 'stopped':
      case 'exited':
        return 'error';
      case 'restarting':
        return 'warning';
      default:
        return 'default';
    }
  };
  
  return (
    <Chip
      label={status}
      color={getStatusColor(status) as any}
      variant="outlined"
      size="small"
      className={`status-indicator status-${status?.toLowerCase()}`}
    />
  );
};

const StatsField = ({ record }: { record: any }) => {
  const stats = record.stats;
  
  if (!stats || stats.error) {
    return (
      <Typography variant="body2" color="text.secondary">
        N/A
      </Typography>
    );
  }
  
  return (
    <Box className="container-stats">
      <Box className="stat-item">
        <Typography className="stat-label">CPU</Typography>
        <Typography className="stat-value">
          {stats.cpu_usage_percent?.toFixed(1)}%
        </Typography>
      </Box>
      <Box className="stat-item">
        <Typography className="stat-label">Memory</Typography>
        <Typography className="stat-value">
          {stats.memory_usage_percent?.toFixed(1)}%
        </Typography>
      </Box>
    </Box>
  );
};

const ContainerActions = ({ record }: { record: any }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; action: string | null; }>({ open: false, action: null });
  const notify = useNotify();
  const refresh = useRefresh();
  
  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    if (action === 'stop' || action === 'restart') {
      setConfirmDialog({ open: true, action });
      return;
    }
    
    await executeAction(action);
  };
  
  const executeAction = async (action: 'start' | 'stop' | 'restart') => {
    setLoading(action);
    setConfirmDialog({ open: false, action: null });
    
    try {
      const result = await dashboardApi.controlContainer(record.name, action);
      notify(`Container ${action} successful: ${result.message}`, { type: 'success' });
      refresh();
    } catch (error) {
      notify(`Failed to ${action} container: ${error}`, { type: 'error' });
    } finally {
      setLoading(null);
    }
  };
  
  const isRunning = record.status === 'running';
  const isCritical = ['management-service', 'redis', 'ibkr-gateway'].includes(record.name);
  
  return (
    <>
      <ButtonGroup size="small" variant="outlined">
        <Button
          startIcon={<StartIcon />}
          onClick={() => handleAction('start')}
          disabled={isRunning || loading === 'start' || isCritical}
          loading={loading === 'start'}
        >
          Start
        </Button>
        <Button
          startIcon={<StopIcon />}
          onClick={() => handleAction('stop')}
          disabled={!isRunning || loading === 'stop' || isCritical}
          loading={loading === 'stop'}
          color="error"
        >
          Stop
        </Button>
        <Button
          startIcon={<RestartIcon />}
          onClick={() => handleAction('restart')}
          disabled={loading === 'restart' || isCritical}
          loading={loading === 'restart'}
          color="warning"
        >
          Restart
        </Button>
      </ButtonGroup>
      
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, action: null })}
      >
        <DialogTitle>
          Confirm {confirmDialog.action?.toUpperCase()} Container
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {confirmDialog.action} the container "{record.name}"?
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
    </>
  );
};

const ContainerList: React.FC = () => {
  const refresh = useRefresh();
  
  // Set up real-time updates
  useRealTimeData('containers', () => {
    refresh();
  });

  return (
    <List
      title="Docker Services"
      sort={{ field: 'name', order: 'ASC' }}
      perPage={25}
    >
      <Datagrid rowClick="show">
        <TextField source="name" label="Service Name" />
        
        <FunctionField
          source="status"
          label="Status"
          render={(record: any) => <StatusField record={record} source="status" />}
        />
        
        <TextField source="image" label="Image" />
        
        <FunctionField
          source="stats"
          label="Resource Usage"
          render={(record: any) => <StatsField record={record} />}
        />
        
        <DateField 
          source="last_update" 
          label="Last Updated" 
          showTime 
          options={{
            timeStyle: 'medium',
            dateStyle: 'short'
          }}
        />
        
        <FunctionField
          label="Actions"
          render={(record: any) => <ContainerActions record={record} />}
        />
      </Datagrid>
    </List>
  );
};

export default ContainerList;