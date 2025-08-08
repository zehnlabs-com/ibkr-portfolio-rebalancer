import { DataProvider, GetListParams, GetOneParams, UpdateParams } from 'react-admin';

const API_URL = '/api';

const fetchJson = async (url: string, options: RequestInit = {}) => {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return response.json();
};

export const dataProvider: DataProvider = {
  getList: async (resource: string, params: GetListParams) => {
    const { page = 1, perPage = 10, sort, filter } = params;
    
    const url = (() => {
      switch (resource) {
        case 'accounts':
          return `${API_URL}/dashboard/accounts`;
        case 'containers':
          return `${API_URL}/containers`;
        case 'logs':
          return `${API_URL}/containers/${filter?.container || 'event-processor'}/logs?tail=${perPage}`;
        default:
          return `${API_URL}/${resource}`;
      }
    })();

    const data = await fetchJson(url);
    
    // Ensure data is array and has ids
    const items = Array.isArray(data) ? data : [data];
    const normalizedData = items.map((item, index) => ({
      ...item,
      id: item.id || item.account_id || item.name || index
    }));

    return {
      data: normalizedData,
      total: normalizedData.length,
    };
  },

  getOne: async (resource: string, params: GetOneParams) => {
    const url = (() => {
      switch (resource) {
        case 'accounts':
          return `${API_URL}/dashboard/accounts/${params.id}`;
        case 'containers':
          return `${API_URL}/containers/${params.id}/stats`;
        case 'dashboard':
          return `${API_URL}/dashboard/overview`;
        default:
          return `${API_URL}/${resource}/${params.id}`;
      }
    })();

    const data = await fetchJson(url);
    
    return {
      data: {
        ...data,
        id: data.id || data.account_id || data.name || params.id
      }
    };
  },

  getMany: async (resource: string, params: { ids: any[] }) => {
    const promises = params.ids.map(id => 
      dataProvider.getOne(resource, { id })
    );
    
    const results = await Promise.all(promises);
    return {
      data: results.map(result => result.data)
    };
  },

  getManyReference: async (resource: string, params: any) => {
    if (resource === 'positions' && params.target === 'account_id') {
      const url = `${API_URL}/dashboard/accounts/${params.id}/positions`;
      const data = await fetchJson(url);
      
      const positions = Array.isArray(data) ? data : [];
      return {
        data: positions.map((item, index) => ({
          ...item,
          id: `${params.id}-${item.symbol || index}`
        })),
        total: positions.length,
      };
    }
    
    return { data: [], total: 0 };
  },

  create: async () => {
    throw new Error('Create operation not supported');
  },

  update: async (resource: string, params: UpdateParams) => {
    if (resource === 'config-env') {
      await fetchJson(`${API_URL}/config/env`, {
        method: 'PUT',
        body: JSON.stringify(params.data),
      });
      
      return { data: { ...params.data, id: params.id } };
    }
    
    if (resource === 'config-accounts') {
      await fetchJson(`${API_URL}/config/accounts`, {
        method: 'PUT',
        body: JSON.stringify(params.data),
      });
      
      return { data: { ...params.data, id: params.id } };
    }
    
    throw new Error(`Update not supported for ${resource}`);
  },

  updateMany: async () => {
    throw new Error('UpdateMany operation not supported');
  },

  delete: async () => {
    throw new Error('Delete operation not supported');
  },

  deleteMany: async () => {
    throw new Error('DeleteMany operation not supported');
  },
};

// Custom API functions for non-CRUD operations
export const customApi = {
  getDashboardOverview: () => fetchJson(`${API_URL}/dashboard/overview`),
  
  getContainerLogs: (container: string, tail = 100) => 
    fetchJson(`${API_URL}/containers/${container}/logs?tail=${tail}`),
  
  controlContainer: (container: string, action: 'start' | 'stop' | 'restart') =>
    fetchJson(`${API_URL}/containers/${container}/${action}`, { method: 'POST' }),
  
  restartServices: (configType: 'env' | 'accounts') =>
    fetchJson(`${API_URL}/config/restart-services?config_type=${configType}`, { method: 'POST' }),
  
  getConfig: (type: 'env' | 'accounts') =>
    fetchJson(`${API_URL}/config/${type}`),
};

export default dataProvider;