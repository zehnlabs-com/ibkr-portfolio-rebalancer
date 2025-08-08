import React from 'react';
import {
  Show,
  SimpleShowLayout,
  TextField,
  DateField,
  NumberField,
  FunctionField,
  Labeled,
  useRecordContext,
} from 'react-admin';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import { CurrencyField, PnLField, PercentField } from '../../fields';

const PositionsTable: React.FC = () => {
  const record = useRecordContext();
  
  if (!record?.positions || record.positions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">
          No positions found
        </Typography>
      </Box>
    );
  }

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value);

  const formatPercent = (value: number) =>
    `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <TableContainer component={Paper} elevation={1}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell><strong>Symbol</strong></TableCell>
            <TableCell align="right"><strong>Quantity</strong></TableCell>
            <TableCell align="right"><strong>Avg Cost</strong></TableCell>
            <TableCell align="right"><strong>Current Price</strong></TableCell>
            <TableCell align="right"><strong>Market Value</strong></TableCell>
            <TableCell align="right"><strong>Unrealized P&L</strong></TableCell>
            <TableCell align="right"><strong>P&L %</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {record.positions.map((position: any, index: number) => (
            <TableRow key={`${position.symbol}-${index}`}>
              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {position.symbol}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" fontFamily="monospace">
                  {position.quantity.toLocaleString()}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" fontFamily="monospace">
                  {formatCurrency(position.avg_cost)}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" fontFamily="monospace">
                  {formatCurrency(position.current_price)}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" fontFamily="monospace">
                  {formatCurrency(position.market_value)}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Chip
                  label={formatCurrency(position.unrealized_pnl)}
                  color={position.unrealized_pnl >= 0 ? 'success' : 'error'}
                  variant="outlined"
                  size="small"
                />
              </TableCell>
              <TableCell align="right">
                <Chip
                  label={formatPercent(position.unrealized_pnl_percent)}
                  color={position.unrealized_pnl_percent >= 0 ? 'success' : 'error'}
                  variant="outlined"
                  size="small"
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const AccountSummaryCards: React.FC = () => {
  const record = useRecordContext();
  
  if (!record) return null;

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              Current Value
            </Typography>
            <CurrencyField source="current_value" />
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              Previous Close
            </Typography>
            <CurrencyField source="last_close_netliq" />
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              Today's P&L
            </Typography>
            <Box>
              <PnLField source="todays_pnl" format="currency" />
              <PnLField source="todays_pnl_percent" format="percent" />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              Positions
            </Typography>
            <NumberField source="positions_count" />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

const AccountShow: React.FC = () => {
  return (
    <Show>
      <SimpleShowLayout>
        <Box sx={{ p: 2 }}>
          <Typography variant="h5" gutterBottom>
            <TextField source="account_id" />
          </Typography>
          
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Last updated: <DateField source="last_update" showTime />
          </Typography>

          <AccountSummaryCards />

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Current Positions
          </Typography>
          
          <PositionsTable />
        </Box>
      </SimpleShowLayout>
    </Show>
  );
};

export default AccountShow;