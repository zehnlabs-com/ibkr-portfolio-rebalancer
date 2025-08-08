import React from 'react';
import { useInput, FieldTitle } from 'react-admin';
import { TextField, Box, Typography } from '@mui/material';

interface JsonFieldProps {
  source: string;
  label?: string;
  helperText?: string;
  validate?: any;
}

export const JsonField: React.FC<JsonFieldProps> = ({ 
  source, 
  label, 
  helperText,
  validate 
}) => {
  const {
    field,
    fieldState: { error },
    formState: { isSubmitting }
  } = useInput({ source, validate });

  const [jsonError, setJsonError] = React.useState<string | null>(null);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    
    // Validate JSON
    try {
      if (value) {
        JSON.parse(value);
        setJsonError(null);
      }
    } catch (e) {
      setJsonError('Invalid JSON format');
    }
    
    field.onChange(value);
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(field.value);
      const formatted = JSON.stringify(parsed, null, 2);
      field.onChange(formatted);
      setJsonError(null);
    } catch (e) {
      setJsonError('Cannot format - invalid JSON');
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="body2" color="text.secondary">
          <FieldTitle label={label} source={source} />
        </Typography>
        <Box>
          <Typography
            component="span"
            variant="caption"
            sx={{ 
              cursor: 'pointer', 
              color: 'primary.main',
              textDecoration: 'underline',
              mr: 2
            }}
            onClick={formatJson}
          >
            Format JSON
          </Typography>
        </Box>
      </Box>
      
      <TextField
        {...field}
        onChange={handleChange}
        multiline
        rows={20}
        fullWidth
        variant="outlined"
        error={!!error || !!jsonError}
        helperText={error?.message || jsonError || helperText}
        disabled={isSubmitting}
        sx={{
          '& .MuiInputBase-input': {
            fontFamily: 'monospace',
            fontSize: '0.875rem',
          }
        }}
      />
    </Box>
  );
};

export default JsonField;