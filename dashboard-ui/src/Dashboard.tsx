import React from 'react';
import { useGetOne, Loading, Error } from 'react-admin';
import {
  Card,
  CardContent,
  Grid,
  Typography,
  Box,
} from '@mui/material';
import {
  AccountBalanceWallet as WalletIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Groups as GroupsIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import TimeAgo from 'react-timeago';
import { CurrencyField, PercentField } from './fields';

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

const Dashboard: React.FC = () => {
  const { data, isLoading, error, refetch } = useGetOne('dashboard', { id: 'overview' });

  // Auto-refresh every 30 seconds
  React.useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  if (isLoading) return <Loading />;
  if (error) return <Error error={error} />;
  if (!data) return null;

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Portfolio Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Last updated: <TimeAgo date={data.last_update} />
        </Typography>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Accounts
                  </Typography>
                  <Typography variant="h4">
                    {data.total_accounts}
                  </Typography>
                </Box>
                <GroupsIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Portfolio Value
                  </Typography>
                  <Typography variant="h4">
                    {formatCurrency(data.total_value)}
                  </Typography>
                </Box>
                <WalletIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Today's P&L
                  </Typography>
                  <Typography 
                    variant="h4" 
                    sx={{ color: data.total_pnl >= 0 ? 'success.main' : 'error.main' }}
                  >
                    {formatCurrency(data.total_pnl)}
                  </Typography>
                </Box>
                {data.total_pnl >= 0 ? 
                  <TrendingUpIcon color="success" sx={{ fontSize: 40 }} /> :
                  <TrendingDownIcon color="error" sx={{ fontSize: 40 }} />
                }
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Today's P&L %
                  </Typography>
                  <Typography 
                    variant="h4" 
                    sx={{ color: data.total_pnl_percent >= 0 ? 'success.main' : 'error.main' }}
                  >
                    {formatPercent(data.total_pnl_percent)}
                  </Typography>
                </Box>
                {data.total_pnl_percent >= 0 ? 
                  <TrendingUpIcon color="success" sx={{ fontSize: 40 }} /> :
                  <TrendingDownIcon color="error" sx={{ fontSize: 40 }} />
                }
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Account Details */}
      {data.accounts && data.accounts.length > 0 && (
        <Box mt={4}>
          <Typography variant="h5" gutterBottom>
            Account Overview
          </Typography>
          <Grid container spacing={3}>
            {data.accounts.map((account: any) => (
              <Grid item xs={12} sm={6} md={4} key={account.account_id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {account.account_id}
                    </Typography>
                    
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Current Value
                      </Typography>
                      <Typography variant="h6">
                        {formatCurrency(account.current_value)}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Today's P&L
                      </Typography>
                      <Typography 
                        variant="h6"
                        sx={{ color: account.todays_pnl >= 0 ? 'success.main' : 'error.main' }}
                      >
                        {formatCurrency(account.todays_pnl)}
                      </Typography>
                      <Typography 
                        variant="body2"
                        sx={{ color: account.todays_pnl_percent >= 0 ? 'success.main' : 'error.main' }}
                      >
                        {formatPercent(account.todays_pnl_percent)}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Positions: {account.positions_count}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default Dashboard;