import { DataProvider, GetListParams, GetOneParams, UpdateParams, CreateParams, DeleteParams } from 'react-admin';

const API_URL = '/api';

interface ApiResponse<T> {
  data: T;
  total?: number;
}

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} ${error}`);
  }
  return response.json();
};

export const dataProvider: DataProvider = {
  getList: async (resource: string, params: GetListParams) => {
    let url = `${API_URL}/${resource}`;
    
    // Handle different resource types
    switch (resource) {
      case 'dashboard-overview':
        url = `${API_URL}/dashboard/overview`;
        break;
      case 'accounts':
        url = `${API_URL}/dashboard/accounts`;
        break;
      case 'containers':
        url = `${API_URL}/containers`;
        break;
      case 'logs':
        // For logs, we'll implement this separately
        throw new Error('Logs resource should use custom implementation');
      default:
        break;
    }
    
    const response = await fetch(url);
    const data = await handleResponse<any>(response);
    
    // Handle different response formats
    if (resource === 'dashboard-overview') {
      return {
        data: [data], // Wrap single object in array for react-admin
        total: 1,
      };
    }
    
    if (Array.isArray(data)) {
      return {
        data: data.map((item, index) => ({
          ...item,
          id: item.id || item.account_id || item.name || index.toString()
        })),
        total: data.length,
      };
    }
    
    return {
      data: [{ ...data, id: data.id || '1' }],
      total: 1,
    };
  },

  getOne: async (resource: string, params: GetOneParams) => {
    let url = `${API_URL}/${resource}/${params.id}`;
    
    // Handle different resource types
    switch (resource) {
      case 'accounts':
        url = `${API_URL}/dashboard/accounts/${params.id}`;
        break;
      case 'containers':
        url = `${API_URL}/containers/${params.id}/stats`;
        break;
      default:
        break;
    }
    
    const response = await fetch(url);
    const data = await handleResponse<any>(response);
    
    return {
      data: {
        ...data,
        id: data.id || data.account_id || data.name || params.id
      }
    };
  },

  getMany: async (resource: string, params: { ids: any[] }) => {
    // For resources that support batch retrieval
    const promises = params.ids.map(id => 
      dataProvider.getOne(resource, { id })
    );
    
    const results = await Promise.all(promises);
    return {
      data: results.map(result => result.data)
    };
  },

  getManyReference: async (resource: string, params: any) => {
    // Handle related resources
    if (resource === 'positions' && params.target === 'account_id') {
      const url = `${API_URL}/dashboard/accounts/${params.id}/positions`;
      const response = await fetch(url);
      const data = await handleResponse<any[]>(response);
      
      return {
        data: data.map((item, index) => ({
          ...item,
          id: `${params.id}-${item.symbol || index}`
        })),
        total: data.length,
      };
    }
    
    throw new Error(`getManyReference not implemented for ${resource}`);
  },

  create: async (resource: string, params: CreateParams) => {
    // Most resources are read-only, but we might support creating new accounts
    if (resource === 'accounts') {
      const response = await fetch(`${API_URL}/config/accounts`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params.data),
      });
      
      const data = await handleResponse<any>(response);
      return {
        data: { ...params.data, id: params.data.account_id }
      };
    }
    
    throw new Error(`create not supported for ${resource}`);
  },

  update: async (resource: string, params: UpdateParams) => {
    // Handle configuration updates
    if (resource === 'env-config') {
      const response = await fetch(`${API_URL}/config/env`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params.data),
      });
      
      const data = await handleResponse<any>(response);
      return {
        data: { ...params.data, id: params.id }
      };
    }
    
    if (resource === 'accounts-config') {
      const response = await fetch(`${API_URL}/config/accounts`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params.data),
      });
      
      const data = await handleResponse<any>(response);
      return {
        data: { ...params.data, id: params.id }
      };
    }
    
    throw new Error(`update not supported for ${resource}`);
  },

  updateMany: async (resource: string, params: { ids: any[]; data: any }) => {
    const promises = params.ids.map(id =>
      dataProvider.update(resource, { id, data: params.data, previousData: {} })
    );
    
    const results = await Promise.all(promises);
    return {
      data: results.map(result => result.data.id)
    };
  },

  delete: async (resource: string, params: DeleteParams) => {
    throw new Error(`delete not supported for ${resource}`);
  },

  deleteMany: async (resource: string, params: { ids: any[] }) => {
    throw new Error(`deleteMany not supported for ${resource}`);
  },
};

// Custom API functions for specific dashboard needs
export const dashboardApi = {
  getAccountPnL: async (accountId: string) => {
    const response = await fetch(`${API_URL}/dashboard/accounts/${accountId}/pnl`);
    return handleResponse<any>(response);
  },

  getContainerLogs: async (containerName: string, tail: number = 100) => {
    const response = await fetch(`${API_URL}/containers/${containerName}/logs?tail=${tail}`);
    return handleResponse<string[]>(response);
  },

  controlContainer: async (containerName: string, action: 'start' | 'stop' | 'restart') => {
    const response = await fetch(`${API_URL}/containers/${containerName}/${action}`, {
      method: 'POST',
    });
    return handleResponse<any>(response);
  },

  restartServices: async (configType: 'env' | 'accounts') => {
    const response = await fetch(`${API_URL}/config/restart-services?config_type=${configType}`, {
      method: 'POST',
    });
    return handleResponse<any>(response);
  },

  getConfigBackups: async () => {
    const response = await fetch(`${API_URL}/config/backups`);
    return handleResponse<any[]>(response);
  },
};

export default dataProvider;