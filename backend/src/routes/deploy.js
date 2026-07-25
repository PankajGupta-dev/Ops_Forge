const express = require('express');
const router = express.Router();
const DeploymentValidator = require('../utils/deploymentValidator');
const InfraDeployAgent = require('../agents/infraDeployAgent');

/**
 * @route POST /deploy
 * @desc Receives a deployment plan, validates it, and triggers Agent 2 (Infra & Deploy Agent)
 */
router.post('/deploy', async (req, res, next) => {
  try {
    const plan = req.body;

    // Validate the deployment plan payload
    const validation = DeploymentValidator.validate(plan);
    if (!validation.isValid) {
      return res.status(400).json({
        success: false,
        message: 'Validation failed for deployment plan.',
        errors: validation.errors,
      });
    }

    // Delegate execution to Agent 2
    const result = await InfraDeployAgent.deploy(plan);

    return res.status(202).json({
      success: true,
      message: 'Deployment process initiated successfully.',
      data: result,
    });
  } catch (error) {
    // Forward error to Express default/custom error handler
    next(error);
  }
});

module.exports = router;
