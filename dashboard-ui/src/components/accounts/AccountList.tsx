import React from 'react';
import {
  List,
  Datagrid,
  TextField,
  NumberField,
  DateField,
  FunctionField,
} from 'react-admin';
import TimeAgo from 'react-timeago';
import { CurrencyField, PnLField } from '../../fields';
import { useRealtimeResource } from '../../providers/realtimeProvider';

const AccountList: React.FC = () => {
  // Enable real-time updates for accounts
  useRealtimeResource('accounts');
  
  return (
    <List
      title="Portfolio Accounts"
      sort={{ field: 'current_value', order: 'DESC' }}
      perPage={25}
      storeKey="accounts.list"
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="account_id" label="Account ID" />
        
        <CurrencyField
          source="current_value"
          label="Current Value"
          sx={{ fontFamily: 'monospace' }}
        />
        
        <PnLField
          source="todays_pnl"
          label="Today's P&L"
          format="currency"
        />
        
        <PnLField
          source="todays_pnl_percent"
          label="Today's P&L %"
          format="percent"
        />
        
        <NumberField source="positions_count" label="Positions" />
        
        <FunctionField 
          source="last_update" 
          label="Last Updated"
          render={(record: any) => <TimeAgo date={record.last_update} />}
        />
      </Datagrid>
    </List>
  );
};

export default AccountList;