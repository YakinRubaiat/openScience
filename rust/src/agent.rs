//! Agent types and traits for openScience

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::error::Result;

/// Agent category classification
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AgentCategory {
    /// Literature review and analysis
    Literature,
    /// Experimental design and planning
    Experiment,
    /// Data management and validation
    DataManagement,
    /// Data analysis and computation
    Analysis,
    /// Figure and visualization generation
    Visualization,
    /// Scientific writing and documentation
    Writing,
    /// Code review and quality assurance
    Review,
}

impl std::fmt::Display for AgentCategory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Literature => write!(f, "literature"),
            Self::Experiment => write!(f, "experiment"),
            Self::DataManagement => write!(f, "data_management"),
            Self::Analysis => write!(f, "analysis"),
            Self::Visualization => write!(f, "visualization"),
            Self::Writing => write!(f, "writing"),
            Self::Review => write!(f, "review"),
        }
    }
}

/// Metadata describing an agent's capabilities
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMetadata {
    /// Unique agent name
    pub name: String,
    /// Agent category
    pub category: AgentCategory,
    /// Human-readable description
    pub description: String,
    /// Required skills for this agent
    pub required_skills: Vec<String>,
    /// Expected input types
    pub input_types: Vec<String>,
    /// Expected output types
    pub output_types: Vec<String>,
    /// Version of the agent
    pub version: String,
}

/// Result from agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResult {
    /// Name of the agent that produced this result
    pub agent: String,
    /// Result data payload
    pub data: serde_json::Value,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Execution artifacts (files, logs, etc.)
    pub artifacts: Vec<String>,
    /// Execution time in milliseconds
    pub execution_time_ms: u64,
    /// Success status
    pub success: bool,
}

/// Trait for all scientific agents
#[async_trait::async_trait]
pub trait Agent: Send + Sync + std::fmt::Debug {
    /// Get agent metadata
    fn metadata(&self) -> &AgentMetadata;

    /// Execute the agent's task
    async fn execute(&mut self, task: &Task, context: &TaskContext) -> Result<AgentResult>;

    /// Validate that this agent can handle the given task
    fn can_execute(&self, task: &Task) -> bool {
        // Default implementation: check if task description matches agent capabilities
        let description = task.description.to_lowercase();
        let name = self.metadata().name.to_lowercase();
        description.contains(&name)
            || task.specialist.as_ref().map_or(false, |s| s == &self.metadata().name)
    }
}

/// A task to be executed by an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    /// Natural language task description
    pub description: String,
    /// Task parameters
    pub parameters: serde_json::Value,
    /// Specific agent to use (optional)
    pub specialist: Option<String>,
    /// Task priority (0-10, 10 = highest)
    pub priority: u8,
    /// Timeout in seconds (None = no timeout)
    pub timeout_seconds: Option<u64>,
}

/// Execution context for agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskContext {
    /// Project directory
    pub project_dir: String,
    /// Data available for the task
    pub data: HashMap<String, serde_json::Value>,
    /// Previous results from the session
    pub results: HashMap<String, AgentResult>,
    /// Security sandbox configuration
    pub sandbox_config: Option<crate::sandbox::SandboxConfig>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    // Test agent implementation for testing
    #[derive(Debug)]
    struct MockAgent {
        metadata: AgentMetadata,
        should_fail: bool,
    }

    #[async_trait::async_trait]
    impl Agent for MockAgent {
        fn metadata(&self) -> &AgentMetadata {
            &self.metadata
        }

        async fn execute(&mut self, _task: &Task, _context: &TaskContext) -> Result<AgentResult> {
            if self.should_fail {
                return Err(crate::error::OpenScienceError::AgentError(
                    "Mock failure".to_string(),
                ));
            }

            Ok(AgentResult {
                agent: self.metadata.name.clone(),
                data: serde_json::json!({"result": "success"}),
                metadata: HashMap::new(),
                artifacts: vec![],
                execution_time_ms: 100,
                success: true,
            })
        }
    }

    fn create_mock_agent() -> MockAgent {
        MockAgent {
            metadata: AgentMetadata {
                name: "mock_agent".to_string(),
                category: AgentCategory::Analysis,
                description: "A mock agent for testing".to_string(),
                required_skills: vec!["mock_skill".to_string()],
                input_types: vec!["mock_input".to_string()],
                output_types: vec!["mock_output".to_string()],
                version: "1.0.0".to_string(),
            },
            should_fail: false,
        }
    }

    #[test]
    fn test_agent_category_display() {
        assert_eq!(AgentCategory::Literature.to_string(), "literature");
        assert_eq!(AgentCategory::Analysis.to_string(), "analysis");
        assert_eq!(AgentCategory::Review.to_string(), "review");
    }

    #[test]
    fn test_agent_metadata() {
        let metadata = AgentMetadata {
            name: "test_agent".to_string(),
            category: AgentCategory::Analysis,
            description: "Test agent".to_string(),
            required_skills: vec!["skill1".to_string(), "skill2".to_string()],
            input_types: vec!["input1".to_string()],
            output_types: vec!["output1".to_string()],
            version: "1.0.0".to_string(),
        };

        assert_eq!(metadata.name, "test_agent");
        assert_eq!(metadata.category, AgentCategory::Analysis);
        assert_eq!(metadata.required_skills.len(), 2);
    }

    #[test]
    fn test_task_creation() {
        let task = Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({"param": "value"}),
            specialist: Some("test_agent".to_string()),
            priority: 5,
            timeout_seconds: Some(60),
        };

        assert_eq!(task.description, "Test task");
        assert_eq!(task.priority, 5);
        assert!(task.specialist.is_some());
    }

    #[tokio::test]
    async fn test_agent_can_execute() {
        let agent = create_mock_agent();

        // Test with matching specialist
        let task = Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };
        assert!(agent.can_execute(&task));

        // Test with matching description
        let task2 = Task {
            description: "Run mock_agent analysis".to_string(),
            parameters: serde_json::json!({}),
            specialist: None,
            priority: 5,
            timeout_seconds: None,
        };
        assert!(agent.can_execute(&task2));

        // Test with non-matching
        let task3 = Task {
            description: "Other task".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("other_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };
        assert!(!agent.can_execute(&task3));
    }

    #[tokio::test]
    async fn test_agent_execute() {
        let mut agent = create_mock_agent();
        let task = Task {
            description: "Test".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };
        let context = TaskContext {
            project_dir: "/tmp".to_string(),
            data: HashMap::new(),
            results: HashMap::new(),
            sandbox_config: None,
        };

        let result = agent.execute(&task, &context).await;
        assert!(result.is_ok());

        let result = result.unwrap();
        assert_eq!(result.agent, "mock_agent");
        assert!(result.success);
        assert_eq!(result.execution_time_ms, 100);
    }

    #[tokio::test]
    async fn test_agent_execute_failure() {
        let mut agent = MockAgent {
            should_fail: true,
            ..create_mock_agent()
        };

        let task = Task {
            description: "Test".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };
        let context = TaskContext {
            project_dir: "/tmp".to_string(),
            data: HashMap::new(),
            results: HashMap::new(),
            sandbox_config: None,
        };

        let result = agent.execute(&task, &context).await;
        assert!(result.is_err());
    }

    #[test]
    fn test_agent_result_serialization() {
        let result = AgentResult {
            agent: "test".to_string(),
            data: serde_json::json!({"key": "value"}),
            metadata: HashMap::new(),
            artifacts: vec!["file.txt".to_string()],
            execution_time_ms: 500,
            success: true,
        };

        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("test"));
        assert!(json.contains("success"));

        let deserialized: AgentResult = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.agent, "test");
        assert!(deserialized.success);
    }
}
