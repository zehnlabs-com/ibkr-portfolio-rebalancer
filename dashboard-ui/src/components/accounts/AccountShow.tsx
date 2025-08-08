import React from 'react';
import {
  Show,
  SimpleShowLayout,
  TextField,
  NumberField,
  DateField,
  Datagrid,
  FunctionField,
  useGetOne,
  useRefresh,
  Loading,
  Error
} from 'react-admin';
import {
  Card,
  CardContent,
  CardHeader,
  Grid,
  Typography,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import { useParams } from 'react-router-dom';
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

const PositionsTable: React.FC<{ positions: any[] }> = ({ positions }) => {
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
            <TableCell align="right"><strong>Unrealized P&L %</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {positions.map((position, index) => (
            <TableRow key={`${position.symbol}-${index}`} className="position-row">
              <TableCell className="symbol-cell">
                <Typography variant="body2" fontWeight={600}>
                  {position.symbol}
                </Typography>
              </TableCell>
              <TableCell align="right" className="quantity-cell">
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
              <TableCell align="right" className="pnl-cell">
                <Chip
                  label={formatCurrency(position.unrealized_pnl)}
                  color={position.unrealized_pnl >= 0 ? 'success' : 'error'}
                  variant="outlined"
                  size="small"
                />
              </TableCell>
              <TableCell align="right" className="pnl-cell">
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

const AccountShow: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const refresh = useRefresh();
  
  const { data, isLoading, error } = useGetOne('accounts', { id: id! });
  
  // Set up real-time updates
  useRealTimeData('accounts', (updateData) => {
    if (updateData.account_id === id) {
      refresh();
    }
  });

  if (isLoading) return <Loading />;
  if (error) return <Error />;
  if (!data) return null;

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Account Details: {data.account_id}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Last updated: {new Date(data.last_update).toLocaleString()}
        </Typography>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} className="dashboard-grid" sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Current Value
              </Typography>
              <Typography variant="h4">
                {formatCurrency(data.current_value)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Previous Close
              </Typography>
              <Typography variant="h4">
                {formatCurrency(data.last_close_netliq)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Today's P&L
              </Typography>
              <Typography 
                variant="h4" 
                className={data.todays_pnl >= 0 ? 'metric-positive' : 'metric-negative'}
              >
                {formatCurrency(data.todays_pnl)}
              </Typography>
              <Typography 
                variant="body2" 
                className={data.todays_pnl_percent >= 0 ? 'metric-positive' : 'metric-negative'}
              >
                {formatPercent(data.todays_pnl_percent)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Positions
              </Typography>
              <Typography variant="h4">
                {data.positions_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Positions Table */}
      {data.positions && data.positions.length > 0 && (
        <Box>
          <Typography variant="h5" gutterBottom className="section-title">
            Current Positions
          </Typography>
          <PositionsTable positions={data.positions} />
        </Box>
      )}

      {data.positions?.length === 0 && (
        <Box className="empty-state">
          <Typography className="empty-message">
            No positions found
          </Typography>
          <Typography className="empty-description">
            This account currently has no open positions.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default AccountShow;