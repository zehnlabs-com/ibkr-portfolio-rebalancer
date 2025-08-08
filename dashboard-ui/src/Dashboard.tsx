import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Grid,
  Typography,
  Box,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  AccountBalance as AccountIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Storage as StorageIcon,
  Speed as SpeedIcon
} from '@mui/icons-material';

import { useRealTimeData } from './providers/websocketProvider';
import { dashboardApi } from './providers/dataProvider';

interface AccountSummary {
  account_id: string;
  current_value: number;
  todays_pnl: number;
  todays_pnl_percent: number;
  positions_count: number;
  last_update: string;
}

interface DashboardOverview {
  total_accounts: number;
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  accounts: AccountSummary[];
  last_update: string;
}

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
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<string>('Connecting');

  // WebSocket for real-time updates
  const { isConnected, connectionStatus: wsStatus } = useRealTimeData(
    'accounts',
    (data) => {
      console.log('Received real-time account update:', data);
      // Refresh overview data when we get updates
      fetchOverview();
    }
  );

  const fetchOverview = async () => {
    try {
      const response = await fetch('/api/dashboard/overview');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data: DashboardOverview = await response.json();
      setOverview(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch dashboard overview:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    
    // Refresh every 30 seconds as fallback
    const interval = setInterval(fetchOverview, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setConnectionStatus(wsStatus);
  }, [wsStatus]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load dashboard data: {error}
        </Alert>
      </Box>
    );
  }

  if (!overview) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          No data available
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Portfolio Dashboard
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Chip
            icon={<SpeedIcon />}
            label={`WebSocket: ${connectionStatus}`}
            color={isConnected ? 'success' : 'error'}
            variant="outlined"
            size="small"
          />
          <Typography variant="body2" color="text.secondary">
            Last updated: {new Date(overview.last_update).toLocaleString()}
          </Typography>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} className="dashboard-grid">
        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Accounts
                  </Typography>
                  <Typography variant="h4">
                    {overview.total_accounts}
                  </Typography>
                </Box>
                <AccountIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Portfolio Value
                  </Typography>
                  <Typography variant="h4">
                    {formatCurrency(overview.total_value)}
                  </Typography>
                </Box>
                <AccountIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Today's P&L
                  </Typography>
                  <Typography 
                    variant="h4" 
                    className={overview.total_pnl >= 0 ? 'metric-positive' : 'metric-negative'}
                  >
                    {formatCurrency(overview.total_pnl)}
                  </Typography>
                </Box>
                {overview.total_pnl >= 0 ? 
                  <TrendingUpIcon color="success" sx={{ fontSize: 40 }} /> :
                  <TrendingDownIcon color="error" sx={{ fontSize: 40 }} />
                }
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card className="portfolio-card">
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Today's P&L %
                  </Typography>
                  <Typography 
                    variant="h4" 
                    className={overview.total_pnl_percent >= 0 ? 'metric-positive' : 'metric-negative'}
                  >
                    {formatPercent(overview.total_pnl_percent)}
                  </Typography>
                </Box>
                {overview.total_pnl_percent >= 0 ? 
                  <TrendingUpIcon color="success" sx={{ fontSize: 40 }} /> :
                  <TrendingDownIcon color="error" sx={{ fontSize: 40 }} />
                }
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Account Details */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom className="section-title">
          Account Overview
        </Typography>
        <Grid container spacing={3}>
          {overview.accounts.map((account) => (
            <Grid item xs={12} sm={6} md={4} key={account.account_id}>
              <Card className="portfolio-card">
                <CardHeader
                  title={account.account_id}
                  className="account-header"
                  titleTypographyProps={{ variant: 'h6' }}
                />
                <CardContent>
                  <Box className="account-metrics">
                    <Box className="metric-card">
                      <Typography className="metric-label">
                        Current Value
                      </Typography>
                      <Typography className="metric-value">
                        {formatCurrency(account.current_value)}
                      </Typography>
                    </Box>
                    
                    <Box className="metric-card">
                      <Typography className="metric-label">
                        Today's P&L
                      </Typography>
                      <Typography 
                        className={`metric-value ${account.todays_pnl >= 0 ? 'metric-positive' : 'metric-negative'}`}
                      >
                        {formatCurrency(account.todays_pnl)}
                      </Typography>
                      <Typography 
                        className={`metric-change ${account.todays_pnl_percent >= 0 ? 'metric-positive' : 'metric-negative'}`}
                      >
                        {formatPercent(account.todays_pnl_percent)}
                      </Typography>
                    </Box>
                    
                    <Box className="metric-card">
                      <Typography className="metric-label">
                        Positions
                      </Typography>
                      <Typography className="metric-value">
                        {account.positions_count}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;