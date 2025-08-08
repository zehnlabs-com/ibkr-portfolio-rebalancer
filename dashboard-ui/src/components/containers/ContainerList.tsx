import React from 'react';
import {
  List,
  Datagrid,
  TextField,
  FunctionField,
  Button,
  useNotify,
  useRefresh,
  BooleanField,
} from 'react-admin';
import { Chip, Box } from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon,
} from '@mui/icons-material';
import { customApi } from '../../providers/dataProvider';
import { useRealtimeResource } from '../../providers/realtimeProvider';

const StatusField: React.FC<{ record?: any }> = ({ record }) => {
  if (!record) return null;
  
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
      label={record.status}
      color={getStatusColor(record.status) as any}
      variant="outlined"
      size="small"
    />
  );
};

const ContainerActions: React.FC<{ record?: any }> = ({ record }) => {
  const notify = useNotify();
  const refresh = useRefresh();
  const [loading, setLoading] = React.useState<string | null>(null);
  
  if (!record) return null;

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    // Confirm for critical containers
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
      refresh();
    } catch (error) {
      notify(`Failed to ${action} container: ${error}`, { type: 'error' });
    } finally {
      setLoading(null);
    }
  };

  const isRunning = record.status === 'running';

  return (
    <Box display="flex" gap={1}>
      <Button
        size="small"
        onClick={() => handleAction('start')}
        disabled={isRunning || loading !== null}
        startIcon={<StartIcon />}
        label="Start"
      />
      <Button
        size="small"
        onClick={() => handleAction('stop')}
        disabled={!isRunning || loading !== null}
        startIcon={<StopIcon />}
        label="Stop"
      />
      <Button
        size="small"
        onClick={() => handleAction('restart')}
        disabled={loading !== null}
        startIcon={<RestartIcon />}
        label="Restart"
      />
    </Box>
  );
};

const ContainerList: React.FC = () => {
  // Enable real-time updates for containers
  useRealtimeResource('containers');

  return (
    <List
      title="Service Containers"
      perPage={25}
      sort={{ field: 'name', order: 'ASC' }}
      storeKey="containers.list"
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="name" label="Container Name" />
        
        <FunctionField
          label="Status"
          render={(record: any) => <StatusField record={record} />}
        />
        
        <TextField source="image" label="Image" />
        
        <FunctionField
          label="CPU"
          render={(record: any) => 
            record.stats?.cpu_usage_percent 
              ? `${record.stats.cpu_usage_percent.toFixed(1)}%` 
              : 'N/A'
          }
        />
        
        <FunctionField
          label="Memory"
          render={(record: any) => 
            record.stats?.memory_usage_percent 
              ? `${record.stats.memory_usage_percent.toFixed(1)}%`
              : 'N/A'
          }
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