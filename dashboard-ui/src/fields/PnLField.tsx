import React from 'react';
import { FunctionField, FunctionFieldProps } from 'react-admin';
import { Chip, Box } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

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
          <Box display="flex" alignItems="center" gap={0.5}>
            <Chip
              icon={isPositive ? <TrendingUp fontSize="small" /> : <TrendingDown fontSize="small" />}
              label={label}
              color={isPositive ? 'success' : 'error'}
              variant="outlined"
              size="small"
              sx={{
                fontWeight: 600,
                '& .MuiChip-icon': {
                  fontSize: '16px',
                },
              }}
            />
          </Box>
        );
      }}
    />
  );
};

export default PnLField;