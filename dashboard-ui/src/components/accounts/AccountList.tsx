import React from 'react';
import {
  List,
  Datagrid,
  TextField,
  NumberField,
  DateField,
  ChipField,
  FunctionField,
  useRefresh
} from 'react-admin';
import { Chip, Box, Typography } from '@mui/material';
import { useRealTimeData } from '../../providers/websocketProvider';

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2
  }).format(value);
};

const formatPercent = (value: number): string => {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
};

const PnLField = ({ record, source }: { record: any; source: string }) => {
  const value = record[source];
  const isPositive = value >= 0;
  
  return (
    <Chip
      label={formatCurrency(value)}
      color={isPositive ? 'success' : 'error'}
      variant="outlined"
      size="small"
    />
  );
};

const PnLPercentField = ({ record, source }: { record: any; source: string }) => {
  const value = record[source];
  const isPositive = value >= 0;
  
  return (
    <Chip
      label={formatPercent(value)}
      color={isPositive ? 'success' : 'error'}
      variant="outlined"
      size="small"
    />
  );
};

const AccountList: React.FC = () => {
  const refresh = useRefresh();
  
  // Set up real-time updates
  useRealTimeData('accounts', () => {
    refresh();
  });

  return (
    <List
      title="Portfolio Accounts"
      sort={{ field: 'current_value', order: 'DESC' }}
      perPage={25}
    >
      <Datagrid rowClick="show">
        <TextField source="account_id" label="Account ID" />
        
        <FunctionField
          source="current_value"
          label="Current Value"
          render={(record: any) => (
            <Typography variant="body2" fontFamily="monospace">
              {formatCurrency(record.current_value)}
            </Typography>
          )}
        />
        
        <FunctionField
          source="todays_pnl"
          label="Today's P&L"
          render={(record: any) => <PnLField record={record} source="todays_pnl" />}
        />
        
        <FunctionField
          source="todays_pnl_percent"
          label="Today's P&L %"
          render={(record: any) => <PnLPercentField record={record} source="todays_pnl_percent" />}
        />
        
        <NumberField source="positions_count" label="Positions" />
        
        <DateField 
          source="last_update" 
          label="Last Updated" 
          showTime 
          options={{
            timeStyle: 'medium',
            dateStyle: 'short'
          }}
        />
      </Datagrid>
    </List>
  );
};

export default AccountList;