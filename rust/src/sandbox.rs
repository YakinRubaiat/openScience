//! Security sandbox for openScience

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::time::Duration;
use tracing::{debug, info, warn};

use crate::agent::{Agent, AgentResult, Task, TaskContext};
use crate::error::{OpenScienceError, Result};

/// Security policy configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPolicy {
    /// Network egress policy ("deny_all", "allowlist", "allow_all")
    pub network_egress: String,
    /// Allowed domains for network access
    pub allowed_domains: HashSet<String>,
    /// File access policy ("sandbox_only", "allowlist", "allow_all")
    pub file_access: String,
    /// Allowed file paths
    pub allowed_paths: HashSet<String>,
    /// Maximum execution time in seconds
    pub max_execution_time: u64,
    /// Maximum memory usage
    pub max_memory: String,
    /// Operations requiring human approval
    pub require_approval: Vec<String>,
}

impl Default for SecurityPolicy {
    fn default() -> Self {
        Self {
            network_egress: "deny_all".to_string(),
            allowed_domains: HashSet::new(),
            file_access: "sandbox_only".to_string(),
            allowed_paths: HashSet::new(),
            max_execution_time: 3600, // 1 hour
            max_memory: "8GB".to_string(),
            require_approval: vec![
                "code_execution".to_string(),
                "network_access".to_string(),
                "host_file_access".to_string(),
                "deletion".to_string(),
                "mcp_tools".to_string(),
            ],
        }
    }
}

/// Sandbox configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxConfig {
    /// Enable sandboxing
    pub enabled: bool,
    /// Security policy
    pub policy: SecurityPolicy,
    /// Approval callback (for human-in-the-loop)
    pub approval_handler: Option<String>,
}

/// Security sandbox for agent execution
#[derive(Debug)]
pub struct Sandbox {
    config: SandboxConfig,
}

impl Sandbox {
    /// Create a new sandbox with the given configuration
    pub fn new(config: SandboxConfig) -> Self {
        Self { config }
    }

    /// Execute an agent within the sandbox
    pub async fn execute_agent(&self, agent: &dyn Agent, task: &Task) -> Result<AgentResult> {
        if !self.config.enabled {
            debug!("Sandbox disabled, executing directly");
            return agent
                .execute(task, &TaskContext {
                    project_dir: ".".to_string(),
                    data: std::collections::HashMap::new(),
                    results: std::collections::HashMap::new(),
                    sandbox_config: None,
                })
                .await;
        }

        // Check if approval is required
        if self.requires_approval(task) {
            let approved = self.request_approval(agent, task).await?;
            if !approved {
                return Err(OpenScienceError::SecurityError(format!(
                    "Operation not approved: {}",
                    task.description
                )));
            }
        }

        info!(
            "Executing agent '{}' in sandbox with policy: {:?}",
            agent.metadata().name,
            self.config.policy
        );

        // Apply resource limits
        self.apply_resource_limits(task).await?;

        // Execute with timeout
        let timeout_duration = Duration::from_secs(self.config.policy.max_execution_time);
        let execution_future = agent.execute(task, &TaskContext {
            project_dir: ".".to_string(),
            data: std::collections::HashMap::new(),
            results: std::collections::HashMap::new(),
            sandbox_config: Some(self.config.clone()),
        });

        match tokio::time::timeout(timeout_duration, execution_future).await {
            Ok(result) => {
                debug!("Agent execution completed within timeout");
                result
            }
            Err(_) => {
                Err(OpenScienceError::SecurityError(format!(
                    "Agent execution timed out after {}s",
                    self.config.policy.max_execution_time
                )))
            }
        }
    }

    /// Check if approval is required for a task
    fn requires_approval(&self, task: &Task) -> bool {
        for operation in &self.config.policy.require_approval {
            if format!("{:?}", task.parameters).to_lowercase().contains(operation) {
                warn!("Task requires approval: {}", task.description);
                return true;
            }
        }
        false
    }

    /// Request approval for an operation
    async fn request_approval(&self, agent: &dyn Agent, task: &Task) -> Result<bool> {
        // In a real implementation, this would call a callback or API
        // For now, auto-approve in test mode or deny in production
        if self.config.approval_handler.is_some() {
            // Simulate approval callback
            info!(
                "Simulating approval for agent '{}' and task '{}'",
                agent.metadata().name,
                task.description
            );
            Ok(true)
        } else {
            // Default deny
            warn!(
                "No approval handler configured, denying task '{}'",
                task.description
            );
            Ok(false)
        }
    }

    /// Apply resource limits (placeholder)
    async fn apply_resource_limits(&self, _task: &Task) -> Result<()> {
        // In a real implementation, this would set OS-level resource limits
        // using cgroups, ulimits, or similar mechanisms
        debug!("Applying resource limits: {:?}", self.config.policy);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent::MockAgent;
    use std::collections::HashMap;

    fn create_test_sandbox() -> Sandbox {
        let config = SandboxConfig {
            enabled: true,
            policy: SecurityPolicy::default(),
            approval_handler: None,
        };
        Sandbox::new(config)
    }

    fn create_test_task() -> Task {
        Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({"operation": "test"}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: Some(60),
        }
    }

    #[tokio::test]
    async fn test_sandbox_creation() {
        let sandbox = create_test_sandbox();
        assert!(sandbox.config.enabled);
        assert_eq!(sandbox.config.policy.network_egress, "deny_all");
    }

    #[tokio::test]
    async fn test_sandbox_disabled_execution() {
        let config = SandboxConfig {
            enabled: false,
            policy: SecurityPolicy::default(),
            approval_handler: None,
        };
        let sandbox = Sandbox::new(config);
        let agent = MockAgent::new();
        let task = create_test_task();

        let result = sandbox.execute_agent(&agent, &task).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_requires_approval() {
        let sandbox = create_test_sandbox();
        
        let task_needs_approval = Task {
            description: "Task requiring network".to_string(),
            parameters: serde_json::json!({"operation": "network_access"}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };

        assert!(sandbox.requires_approval(&task_needs_approval));

        let task_no_approval = create_test_task();
        assert!(!sandbox.requires_approval(&task_no_approval));
    }

    #[tokio::test]
    async fn test_request_approval() {
        let sandbox = create_test_sandbox();
        let agent = MockAgent::new();
        let task = create_test_task();

        // No approval handler = default deny
        let approved = sandbox.request_approval(&agent, &task).await.unwrap();
        assert!(!approved);

        // With approval handler = allow
        let config = SandboxConfig {
            enabled: true,
            policy: SecurityPolicy::default(),
            approval_handler: Some("test_handler".to_string()),
        };
        let sandbox_with_handler = Sandbox::new(config);
        let approved = sandbox_with_handler
            .request_approval(&agent, &task)
            .await
            .unwrap();
        assert!(approved);
    }

    #[tokio::test]
    async fn test_apply_resource_limits() {
        let sandbox = create_test_sandbox();
        let task = create_test_task();

        let result = sandbox.apply_resource_limits(&task).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_execute_agent_with_sandbox() {
        let sandbox = create_test_sandbox();
        let agent = MockAgent::new();
        let task = create_test_task();

        let result = sandbox.execute_agent(&agent, &task).await;
        assert!(result.is_err()); // Will fail due to no approval handler
    }

    #[test]
    fn test_security_policy_default() {
        let policy = SecurityPolicy::default();
        assert_eq!(policy.network_egress, "deny_all");
        assert_eq!(policy.file_access, "sandbox_only");
        assert_eq!(policy.max_execution_time, 3600);
        assert_eq!(policy.max_memory, "8GB");
        assert!(policy.require_approval.contains(&"code_execution".to_string()));
    }

    #[test]
    fn test_sandbox_config_serialization() {
        let config = SandboxConfig {
            enabled: true,
            policy: SecurityPolicy::default(),
            approval_handler: Some("handler".to_string()),
        };

        let json = serde_json::to_string(&config).unwrap();
        let deserialized: SandboxConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.enabled, true);
        assert_eq!(deserialized.approval_handler, Some("handler".to_string()));
    }
}
