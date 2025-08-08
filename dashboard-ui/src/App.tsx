import React from 'react';
import { Admin, Resource, CustomRoutes } from 'react-admin';
import { Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { dataProvider } from './providers/dataProvider';
import zehnlabsTheme from './theme/zehnlabsTheme';
import './theme/customStyles.scss';

// Import components
import Dashboard from './Dashboard';
import { AccountList, AccountShow } from './components/accounts';
import { ContainerList, ContainerShow } from './components/containers';
import { LogList } from './components/logs';
import { EnvConfigEdit, AccountsConfigEdit } from './components/config';

// Icons
import DashboardIcon from '@mui/icons-material/Dashboard';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import StorageIcon from '@mui/icons-material/Storage';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';

const App: React.FC = () => {
  return (
    <ThemeProvider theme={zehnlabsTheme}>
      <CssBaseline />
      <Admin
        dataProvider={dataProvider}
        dashboard={Dashboard}
        title="Portfolio Dashboard"
        theme={zehnlabsTheme}
      >
        {/* Portfolio Resources */}
        <Resource
          name="accounts"
          list={AccountList}
          show={AccountShow}
          icon={AccountBalanceIcon}
          options={{ label: 'Accounts' }}
        />
        
        {/* System Resources */}
        <Resource
          name="containers"
          list={ContainerList}
          show={ContainerShow}
          icon={StorageIcon}
          options={{ label: 'Services' }}
        />
        
        <Resource
          name="logs"
          list={LogList}
          icon={DescriptionIcon}
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