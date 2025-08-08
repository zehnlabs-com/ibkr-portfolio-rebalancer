import React from 'react';
import { Admin, Resource, CustomRoutes } from 'react-admin';
import { Route } from 'react-router-dom';
import CssBaseline from '@mui/material/CssBaseline';

import { dataProvider } from './providers/dataProvider';
import { ThemeProvider } from './theme/ThemeContext';
import './theme/customStyles.scss';

// Import components
import Dashboard from './Dashboard';
import { AccountList, AccountShow } from './components/accounts';
import { ContainerList, ContainerShow } from './components/containers';
import { LogList } from './components/logs';
import { EnvConfigEdit, AccountsConfigEdit } from './components/config';
import { CustomAppBar } from './components/CustomAppBar';

// Modern Icons
import DashboardIcon from '@mui/icons-material/SpaceDashboard';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import CloudIcon from '@mui/icons-material/Cloud';
import ArticleIcon from '@mui/icons-material/Article';
import SettingsIcon from '@mui/icons-material/Settings';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <CssBaseline />
      <Admin
        dataProvider={dataProvider}
        dashboard={Dashboard}
        title="Portfolio Dashboard"
        appBar={CustomAppBar}
      >
        {/* Portfolio Resources */}
        <Resource
          name="accounts"
          list={AccountList}
          show={AccountShow}
          icon={AccountBalanceWalletIcon}
          options={{ label: 'Accounts' }}
        />
        
        {/* System Resources */}
        <Resource
          name="containers"
          list={ContainerList}
          show={ContainerShow}
          icon={CloudIcon}
          options={{ label: 'Services' }}
        />
        
        <Resource
          name="logs"
          list={LogList}
          icon={ArticleIcon}
          options={{ label: 'Logs' }}
        />
        
        {/* Configuration Routes */}
        <CustomRoutes>
          <Route path="/config/env" element={<EnvConfigEdit />} />
          <Route path="/config/accounts" element={<AccountsConfigEdit />} />
        </CustomRoutes>
      </Admin>
    </ThemeProvider>
  );
};

export default App;