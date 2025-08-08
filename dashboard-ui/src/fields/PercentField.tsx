import React from 'react';
import { FunctionField, FunctionFieldProps } from 'react-admin';
import { Typography } from '@mui/material';

interface PercentFieldProps extends Omit<FunctionFieldProps, 'render'> {
  showSign?: boolean;
}

export const PercentField: React.FC<PercentFieldProps> = ({ 
  showSign = true,
  ...props 
}) => {
  return (
    <FunctionField
      {...props}
      render={(record: any) => {
        const value = record[props.source as string];
        if (value == null) return null;
        
        const formatted = `${showSign && value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
        const color = value >= 0 ? 'success.main' : 'error.main';
        
        return (
          <Typography 
            variant="body2" 
            sx={{ color, fontFamily: 'monospace' }}
          >
            {formatted}
          </Typography>
        );
      }}
    />
  );
};

export default PercentField;