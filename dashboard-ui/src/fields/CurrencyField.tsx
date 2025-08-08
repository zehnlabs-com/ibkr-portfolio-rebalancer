import React from 'react';
import { NumberField, NumberFieldProps } from 'react-admin';
import { Box, Typography } from '@mui/material';
import { AttachMoney } from '@mui/icons-material';

export const CurrencyField: React.FC<NumberFieldProps> = (props) => {
  return (
    <Box display="flex" alignItems="center" gap={0.5}>
      <AttachMoney sx={{ fontSize: 16, color: 'text.secondary' }} />
      <NumberField
        {...props}
        options={{
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        }}
        sx={{
          fontWeight: 600,
          fontFamily: 'Monaco, Menlo, monospace',
          ...props.sx
        }}
      />
    </Box>
  );
};

export default CurrencyField;