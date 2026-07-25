/**
 * Reusable client for interacting with the DigitalOcean API.
 * Configured via process.env.DIGITALOCEAN_API_TOKEN.
 */
class DigitalOceanClient {
  constructor(token = process.env.DIGITALOCEAN_API_TOKEN) {
    if (!token) {
      throw new Error("DigitalOcean API token is required. Set DIGITALOCEAN_API_TOKEN env variable.");
    }
    this.token = token;
    this.baseUrl = "https://api.digitalocean.com/v2";
  }

  /**
   * Helper method to perform requests to the DigitalOcean API
   * @private
   */
  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      "Authorization": `Bearer ${this.token}`,
      "Content-Type": "application/json",
      ...options.headers,
    };

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`DigitalOcean API request failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  /**
   * Create a new App Platform app
   * @param {Object} appSpec - The app specification object
   * @returns {Promise<Object>} The created app details
   */
  async createApp(appSpec) {
    return this._request("/apps", {
      method: "POST",
      body: JSON.stringify({ spec: appSpec }),
    });
  }

  /**
   * Update an existing App Platform app
   * @param {string} appId - The ID of the app to update
   * @param {Object} appSpec - The updated app specification object
   * @returns {Promise<Object>} The updated app details
   */
  async updateApp(appId, appSpec) {
    return this._request(`/apps/${appId}`, {
      method: "PUT",
      body: JSON.stringify({ spec: appSpec }),
    });
  }

  /**
   * Delete an existing App Platform app
   * @param {string} appId - The ID of the app to delete
   * @returns {Promise<null>}
   */
  async deleteApp(appId) {
    return this._request(`/apps/${appId}`, {
      method: "DELETE",
    });
  }

  /**
   * Retrieve the details of a specific deployment
   * @param {string} appId - The app ID
   * @param {string} deploymentId - The deployment ID
   * @returns {Promise<Object>} The deployment details
   */
  async getDeploymentStatus(appId, deploymentId) {
    return this._request(`/apps/${appId}/deployments/${deploymentId}`);
  }

  /**
   * Retrieve the logs for a specific deployment
   * @param {string} appId - The app ID
   * @param {string} deploymentId - The deployment ID
   * @returns {Promise<Object>} The deployment logs details
   */
  async getLogs(appId, deploymentId) {
    return this._request(`/apps/${appId}/deployments/${deploymentId}/logs`);
  }

  /**
   * Trigger a new deployment (restart/redeploy) for an app
   * @param {string} appId - The app ID
   * @returns {Promise<Object>} The newly created deployment details
   */
  async restartDeployment(appId) {
    return this._request(`/apps/${appId}/deployments`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }
}

module.exports = DigitalOceanClient;
