/**
 * Utility for validating incoming deployment plans.
 */
class DeploymentValidator {
  /**
   * Validates a deployment plan payload against standard constraints.
   * @param {Object} plan - The deployment plan to validate
   * @returns {Object} { isValid: boolean, errors: string[] }
   */
  static validate(plan) {
    const errors = [];

    if (!plan || typeof plan !== 'object') {
      return {
        isValid: false,
        errors: ['Deployment plan must be a non-null object.'],
      };
    }

    // 1. App Name Validation
    if (!plan.appName) {
      errors.push('appName is required.');
    } else if (typeof plan.appName !== 'string') {
      errors.push('appName must be a string.');
    } else if (!/^[a-z0-9-]+$/.test(plan.appName)) {
      errors.push('appName must only contain lowercase alphanumeric characters and dashes (e.g., "my-app").');
    }

    // 2. Repository Validation
    if (!plan.repository) {
      errors.push('repository is required.');
    } else if (typeof plan.repository !== 'string') {
      errors.push('repository must be a string.');
    } else {
      const gitUrlPattern = /^(https:\/\/github\.com\/|git@github\.com:)[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\.git)?$/;
      const genericGitPattern = /^(https?|git|ssh):\/\/[^\s$.?#].[^\s]*$/;
      if (!gitUrlPattern.test(plan.repository) && !genericGitPattern.test(plan.repository)) {
        errors.push('repository must be a valid Git URL (HTTPS/SSH GitHub URL or generic repository URL).');
      }
    }

    // 3. Branch Validation
    if (!plan.branch) {
      errors.push('branch is required.');
    } else if (typeof plan.branch !== 'string' || plan.branch.trim() === '') {
      errors.push('branch must be a non-empty string.');
    }

    // 4. Runtime Validation
    if (!plan.runtime) {
      errors.push('runtime is required.');
    } else if (typeof plan.runtime !== 'string') {
      errors.push('runtime must be a string.');
    } else {
      const allowedRuntimes = ['node', 'nodejs', 'python', 'go', 'docker', 'static', 'ruby', 'php', 'java'];
      const lowercaseRuntime = plan.runtime.toLowerCase();
      if (!allowedRuntimes.some(r => lowercaseRuntime.includes(r))) {
        errors.push(`runtime "${plan.runtime}" is not recognized. Expected one of: ${allowedRuntimes.join(', ')}.`);
      }
    }

    // 5. Environment Variables Validation
    if (plan.env !== undefined && plan.env !== null) {
      if (typeof plan.env !== 'object' || Array.isArray(plan.env)) {
        errors.push('env must be a key-value object.');
      } else {
        for (const [key, value] of Object.entries(plan.env)) {
          if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
            errors.push(`Environment variable key "${key}" must be a valid identifier (alphanumeric and start with a letter/underscore).`);
          }
          if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') {
            errors.push(`Environment variable "${key}" value must be a string, number, or boolean.`);
          }
        }
      }
    }

    // 6. Region Validation
    if (!plan.region) {
      errors.push('region is required.');
    } else if (typeof plan.region !== 'string') {
      errors.push('region must be a string.');
    } else {
      const validRegions = ['nyc1', 'nyc3', 'ams3', 'sfo2', 'sfo3', 'sgp1', 'lon1', 'fra1', 'tor1', 'blr1'];
      if (!validRegions.includes(plan.region.toLowerCase())) {
        errors.push(`region "${plan.region}" is invalid. Must be one of: ${validRegions.join(', ')}.`);
      }
    }

    // 7. Database Validation
    if (plan.database !== undefined && plan.database !== null) {
      if (typeof plan.database !== 'object' || Array.isArray(plan.database)) {
        errors.push('database config must be an object.');
      } else {
        const { engine, version, size } = plan.database;
        if (!engine) {
          errors.push('database.engine is required when database configuration is provided.');
        } else {
          const validEngines = ['mongodb', 'postgresql', 'mysql', 'redis'];
          if (!validEngines.includes(engine.toLowerCase())) {
            errors.push(`database.engine "${engine}" is invalid. Must be one of: ${validEngines.join(', ')}.`);
          }
        }
        if (version && typeof version !== 'string' && typeof version !== 'number') {
          errors.push('database.version must be a string or number.');
        }
        if (size && typeof size !== 'string') {
          errors.push('database.size must be a size slug string.');
        }
      }
    }

    // 8. Scaling Validation
    if (plan.scaling !== undefined && plan.scaling !== null) {
      if (typeof plan.scaling !== 'object' || Array.isArray(plan.scaling)) {
        errors.push('scaling config must be an object.');
      } else {
        const { instances, size } = plan.scaling;
        if (instances !== undefined) {
          if (!Number.isInteger(instances) || instances < 1) {
            errors.push('scaling.instances must be a positive integer >= 1.');
          }
        }
        if (size && typeof size !== 'string') {
          errors.push('scaling.size must be a size slug string.');
        }
      }
    }

    // 9. Ports Validation
    if (plan.ports !== undefined && plan.ports !== null) {
      if (!Array.isArray(plan.ports)) {
        errors.push('ports must be an array of integers.');
      } else {
        if (plan.ports.length === 0) {
          errors.push('ports array cannot be empty if specified.');
        }
        plan.ports.forEach((port, idx) => {
          if (!Number.isInteger(port) || port < 1 || port > 65535) {
            errors.push(`ports[${idx}] must be a valid port number (1-65535).`);
          }
        });
      }
    } else if (plan.port !== undefined && plan.port !== null) {
      if (!Number.isInteger(plan.port) || plan.port < 1 || plan.port > 65535) {
        errors.push('port must be a valid port number (1-65535).');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }
}

module.exports = DeploymentValidator;
