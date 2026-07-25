const InfraDeployAgent = require('../src/agents/infraDeployAgent');
const DigitalOceanClient = require('../src/integrations/digitalOceanClient');
const DeploymentValidator = require('../src/utils/deploymentValidator');

// Mock the DigitalOcean client integration
jest.mock('../src/integrations/digitalOceanClient');

describe('InfraDeployAgent - Agent 2 Unit Tests', () => {
  let mockClient;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default mock methods
    mockClient = {
      createApp: jest.fn(),
      getDeploymentStatus: jest.fn(),
    };
    
    DigitalOceanClient.mockImplementation(() => mockClient);
    
    // Set mock env token so the client constructor doesn't throw
    process.env.DIGITALOCEAN_API_TOKEN = 'mock-token';
    process.env.JWT_SECRET = 'mock-jwt';
    process.env.GEMINI_API_KEY = 'mock-gemini';
    process.env.MONGODB_ATLAS_URI = 'mongodb://mock';
    process.env.ELEVENLABS_API_KEY = 'mock-eleven';
  });

  const validPlan = {
    appName: 'my-test-app',
    repository: 'https://github.com/opsforge/test-app.git',
    branch: 'main',
    runtime: 'node',
    region: 'nyc3',
    ports: [8000],
    scaling: {
      instances: 2,
      size: 'basic-xs'
    },
    env: {
      NODE_ENV: 'production'
    }
  };

  test('✓ Validation - should validate correct deployment plan configurations', () => {
    const validation = DeploymentValidator.validate(validPlan);
    expect(validation.isValid).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  test('✓ Invalid payload - should fail validation on invalid payload structures', async () => {
    const invalidPlan = {
      appName: 'Invalid_App_Name_With_Caps_&_Symbols!',
      repository: 'invalid-git-url',
      branch: '',
      runtime: 'unknown-runtime',
      region: 'invalid-region'
    };

    const validation = DeploymentValidator.validate(invalidPlan);
    expect(validation.isValid).toBe(false);
    expect(validation.errors.length).toBeGreaterThan(0);

    // Call deploy with invalid plan should throw a validation error
    await expect(InfraDeployAgent.deploy(invalidPlan)).rejects.toThrow(/validation failed/i);
  });

  test('✓ Successful deployment - should provision app and poll to ACTIVE status', async () => {
    mockClient.createApp.mockResolvedValue({
      app: {
        id: 'do-app-uuid-123',
        live_url: 'https://my-test-app.ondigitalocean.app',
        active_deployment: { id: 'deploy-uuid-456' }
      }
    });

    mockClient.getDeploymentStatus
      .mockResolvedValueOnce({ deployment: { id: 'deploy-uuid-456', phase: 'BUILDING' } })
      .mockResolvedValueOnce({ deployment: { id: 'deploy-uuid-456', phase: 'DEPLOYING' } })
      .mockResolvedValueOnce({ deployment: { id: 'deploy-uuid-456', phase: 'ACTIVE' } });

    const result = await InfraDeployAgent.deploy(validPlan, {
      intervalMs: 1, // Rapid polling for tests
      timeoutMs: 100 // High timeout margin for rapid tests
    });

    expect(mockClient.createApp).toHaveBeenCalledTimes(1);
    expect(mockClient.getDeploymentStatus).toHaveBeenCalledTimes(3);
    expect(result).toEqual({
      status: 'success',
      appId: 'do-app-uuid-123',
      deploymentId: 'deploy-uuid-456',
      liveUrl: 'https://my-test-app.ondigitalocean.app',
      message: 'Infrastructure provisioned and application deployed successfully.'
    });
  });

  test('✓ Failed deployment - should stop polling and raise error if DO phase is ERROR', async () => {
    mockClient.createApp.mockResolvedValue({
      app: {
        id: 'do-app-uuid-123',
        active_deployment: { id: 'deploy-uuid-failed' }
      }
    });

    mockClient.getDeploymentStatus
      .mockResolvedValueOnce({ deployment: { id: 'deploy-uuid-failed', phase: 'BUILDING' } })
      .mockResolvedValueOnce({ deployment: { id: 'deploy-uuid-failed', phase: 'ERROR', reason: 'Out of memory' } });

    await expect(
      InfraDeployAgent.deploy(validPlan, {
        intervalMs: 1,
        timeoutMs: 100
      })
    ).rejects.toThrow(/Deployment failed.*Out of memory/);

    expect(mockClient.createApp).toHaveBeenCalledTimes(1);
    expect(mockClient.getDeploymentStatus).toHaveBeenCalledTimes(2);
  });

  test('✓ Timeout - should throw exception if deployment exceeds maximum timeout limit', async () => {
    mockClient.createApp.mockResolvedValue({
      app: {
        id: 'do-app-uuid-123',
        active_deployment: { id: 'deploy-uuid-timeout' }
      }
    });

    mockClient.getDeploymentStatus.mockResolvedValue({
      deployment: { id: 'deploy-uuid-timeout', phase: 'BUILDING' }
    });

    // 10ms timeout with 5ms interval should quickly trigger the timeout
    await expect(
      InfraDeployAgent.deploy(validPlan, {
        intervalMs: 5,
        timeoutMs: 10
      })
    ).rejects.toThrow(/monitoring timed out/i);
  });
});
