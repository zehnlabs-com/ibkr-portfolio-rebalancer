import React from 'react';
import { NumberField, NumberFieldProps } from 'react-admin';

export const CurrencyField: React.FC<NumberFieldProps> = (props) => {
  return (
    <NumberField
      {...props}
      options={{
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }}
    />
  );
};

export default CurrencyField;