/**
 * Utility for monitoring DigitalOcean deployments and tracking state transitions.
 */
class DeploymentMonitor {
  /**
   * Maps DigitalOcean deployment phases to our simplified states:
   * Pending, Building, Deploying, Active, Failed
   * @param {string} phase - DigitalOcean deployment phase
   * @returns {string} Simplified state
   */
  static mapDOPhase(phase) {
    if (!phase) return 'Pending';
    
    switch (phase.toUpperCase()) {
      case 'PENDING':
        return 'Pending';
      case 'BUILDING':
        return 'Building';
      case 'DEPLOYING':
        return 'Deploying';
      case 'ACTIVE':
      case 'SUPERSEDED':
        return 'Active';
      case 'ERROR':
      case 'CANCELED':
      case 'CANCELLED':
      case 'FAILED':
        return 'Failed';
      default:
        return 'Deploying'; // Fallback for transitionary states
    }
  }

  /**
   * Polls the deployment status until it reaches a terminal state (Active or Failed) or times out.
   * @param {Object} client - Instance of DigitalOceanClient
   * @param {string} appId - The DigitalOcean App ID
   * @param {string} deploymentId - The DigitalOcean Deployment ID
   * @param {Object} options - Polling options
   * @param {number} options.intervalMs - Time to wait between polls (default: 5000)
   * @param {number} options.timeoutMs - Maximum time to poll before throwing a timeout error (default: 600000)
   * @param {function} options.onProgress - Callback function triggered on each status update: (state, rawDeployment) => {}
   * @returns {Promise<Object>} The final deployment detail object
   */
  static async waitUntilReady(client, appId, deploymentId, options = {}) {
    const intervalMs = options.intervalMs || 5000;
    const timeoutMs = options.timeoutMs || 600000; // 10 minutes default
    const onProgress = options.onProgress || (() => {});
    
    const startTime = Date.now();
    
    while (true) {
      if (Date.now() - startTime > timeoutMs) {
        throw new Error(`Deployment monitoring timed out after ${timeoutMs / 1000} seconds.`);
      }

      try {
        const response = await client.getDeploymentStatus(appId, deploymentId);
        const deployment = response && response.deployment ? response.deployment : response;
        
        if (!deployment) {
          throw new Error('Received empty response from DigitalOcean deployment status API.');
        }

        const rawPhase = deployment.phase || 'PENDING';
        const mappedState = this.mapDOPhase(rawPhase);

        // Notify caller of current progress
        onProgress(mappedState, deployment);

        if (mappedState === 'Active') {
          return deployment;
        }

        if (mappedState === 'Failed') {
          throw new Error(`Deployment failed. DigitalOcean raw phase: ${rawPhase}. Reason: ${deployment.reason || 'Unknown error'}`);
        }

      } catch (error) {
        if (error.message.includes('Deployment failed')) {
          throw error;
        }
        // Notify progress callback of the error transition state
        onProgress('Deploying', { phase: 'DEPLOYING', error: error.message });
      }

      // Wait for next polling interval
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
  }
}

module.exports = DeploymentMonitor;
