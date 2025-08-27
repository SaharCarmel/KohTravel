/**
 * Shared configuration for KohTravel2 local development
 * Handles port offsets for running multiple instances in parallel
 */

/**
 * Get service URLs for current environment
 * @returns {Object} Service URLs object
 */
export function getServiceURLs() {
  // For development, use port offsets
  const offset = parseInt(process.env.SERVICE_PORT_OFFSET || '0');
  
  return {
    frontend: `http://localhost:${3000 + offset}`,
    api: `http://localhost:${8000 + offset}`,
    agent: `http://localhost:${8001 + offset}`
  };
}

/**
 * Get the agent service URL
 * @returns {string} Agent service URL
 */
export function getAgentURL() {
  return getServiceURLs().agent;
}

/**
 * Get the main API URL
 * @returns {string} Main API URL
 */
export function getAPIURL() {
  return getServiceURLs().api;
}

/**
 * Get CORS origins for development with multiple port offsets
 * @returns {Array<string>} Array of allowed origins
 */
export function getCORSOrigins() {
  const origins = [];
  
  // Support port offsets 0, 10, 20, 30 for parallel development
  for (let offset = 0; offset <= 30; offset += 10) {
    origins.push(
      `http://localhost:${3000 + offset}`,
      `http://localhost:${8000 + offset}`,
      `http://localhost:${8001 + offset}`
    );
  }
  
  return origins;
}