import React from 'react';
import { FunctionField, FunctionFieldProps } from 'react-admin';
import { Chip } from '@mui/material';

interface PnLFieldProps extends Omit<FunctionFieldProps, 'render'> {
  format?: 'currency' | 'percent';
}

export const PnLField: React.FC<PnLFieldProps> = ({ 
  format = 'currency',
  ...props 
}) => {
  return (
    <FunctionField
      {...props}
      render={(record: any) => {
        const value = record[props.source as string];
        if (value == null) return null;
        
        const isPositive = value >= 0;
        let label: string;
        
        if (format === 'currency') {
          label = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
          }).format(value);
        } else {
          label = `${isPositive ? '+' : ''}${value.toFixed(2)}%`;
        }
        
        return (
          <Chip
            label={label}
            color={isPositive ? 'success' : 'error'}
            variant="outlined"
            size="small"
          />
        );
      }}
    />
  );
};

export default PnLField;