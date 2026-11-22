//! Agent orchestration for openScience

use std::collections::HashMap;
use std::sync::Arc;

use dashmap::DashMap;
use tracing::{debug, error, info, warn};

use crate::agent::{Agent, AgentCategory, AgentMetadata, AgentResult};
use crate::error::{OpenScienceError, Result};
use crate::sandbox::{Sandbox, SandboxConfig};

/// Task execution result
pub type TaskResult = Result<AgentResult>;

/// Agent orchestrator - routes tasks to appropriate agents
#[derive(Debug)]
pub struct AgentOrchestrator {
    /// Registry of all available agents
    agents: Arc<DashMap<String, Box<dyn Agent>>>,
    /// Category-based agent index
    agent_registry: Arc<DashMap<AgentCategory, Vec<String>>>,
    /// Security sandbox
    sandbox: Option<Sandbox>,
    /// Default compute backend
    compute_backend: String,
}

impl AgentOrchestrator {
    /// Create a new agent orchestrator
    pub fn new(sandbox_config: Option<SandboxConfig>, compute_backend: String) -> Self {
        let sandbox = sandbox_config.map(|config| Sandbox::new(config));

        Self {
            agents: Arc::new(DashMap::new()),
            agent_registry: Arc::new(DashMap::new()),
            sandbox,
            compute_backend,
        }
    }

    /// Register an agent with the orchestrator
    pub fn register_agent<A: Agent + 'static>(&self, agent: A) -> Result<()> {
        let metadata = agent.metadata().clone();
        let name = metadata.name.clone();
        let category = metadata.category.clone();

        // Check if agent already exists
        if self.agents.contains_key(&name) {
            return Err(OpenScienceError::OrchestrationError(format!(
                "Agent '{}' already registered",
                name
            )));
        }

        // Add to agent registry
        self.agent_registry
            .entry(category)
            .or_insert_with(Vec::new)
            .push(name.clone());

        // Add to main agent map
        self.agents.insert(name.clone(), Box::new(agent));

        info!("Registered agent: {}", name);
        Ok(())
    }

    /// Get an agent by name
    pub fn get_agent(&self, name: &str) -> Result<std::sync::Arc<Box<dyn Agent + '_>>> {
        self.agents
            .get(name)
            .map(|entry| std::sync::Arc::new(entry.value()))
            .ok_or_else(|| OpenScienceError::OrchestrationError(format!("Agent '{}' not found", name)))
    }

    /// Get all agents in a category
    pub fn get_agents_by_category(&self, category: &AgentCategory) -> Vec<String> {
        self.agent_registry
            .get(category)
            .map(|agents| agents.value().clone())
            .unwrap_or_default()
    }

    /// List all registered agent names
    pub fn list_agents(&self) -> Vec<String> {
        self.agents.iter().map(|entry| entry.key().clone()).collect()
    }

    /// Get agent metadata
    pub fn get_agent_metadata(&self, name: &str) -> Result<AgentMetadata> {
        let agent = self.get_agent(name)?;
        Ok(agent.metadata().clone())
    }

    /// Execute a task using the best matching agent
    pub async fn execute_task(&self, task: &crate::agent::Task) -> TaskResult {
        info!("Executing task: {}", task.description);

        // Validate task
        if task.description.trim().is_empty() {
            return Err(OpenScienceError::ValidationError(
                "Task description cannot be empty".to_string(),
            ));
        }

        // Try to find matching agent
        let agent_name = self.select_agent(task)?;
        debug!("Selected agent: {}", agent_name);

        // Execute with agent
        self.execute_agent(&agent_name, task).await
    }

    /// Execute a task with a specific agent
    pub async fn execute_agent(&self, agent_name: &str, task: &crate::agent::Task) -> TaskResult {
        let agent = self.get_agent(agent_name)?;
        let metadata = agent.metadata().clone();

        debug!(
            "Executing agent '{}' with category '{}'",
            metadata.name, metadata.category
        );

        // Apply sandbox if configured
        let start_time = std::time::Instant::now();

        let result = if let Some(sandbox) = &self.sandbox {
            sandbox.execute_agent(agent.as_ref(), task).await
        } else {
            agent.execute(task, &crate::agent::TaskContext {
                project_dir: ".".to_string(),
                data: HashMap::new(),
                results: HashMap::new(),
                sandbox_config: None,
            })
        };

        let execution_time = start_time.elapsed();

        match result {
            Ok(mut agent_result) => {
                agent_result.execution_time_ms = execution_time.as_millis() as u64;
                agent_result.success = true;
                info!(
                    "Agent '{}' completed successfully in {}ms",
                    agent_name,
                    agent_result.execution_time_ms
                );
                Ok(agent_result)
            }
            Err(e) => {
                error!("Agent '{}' failed: {}", agent_name, e);
                Err(e)
            }
        }
    }

    /// Select the best agent for a task
    fn select_agent(&self, task: &crate::agent::Task) -> Result<String> {
        // If specialist is specified, use it
        if let Some(specialist) = &task.specialist {
            if self.agents.contains_key(specialist) {
                return Ok(specialist.clone());
            } else {
                warn!("Specialist agent '{}' not found", specialist);
            }
        }

        // Find agents that can execute this task
        let mut candidates: Vec<String> = self
            .agents
            .iter()
            .filter_map(|entry| {
                let agent = entry.value();
                if agent.can_execute(task) {
                    Some(entry.key().clone())
                } else {
                    None
                }
            })
            .collect();

        if candidates.is_empty() {
            // Try fallback based on task description keywords
            let description = task.description.to_lowercase();

            // Keyword-based fallback mapping
            let keyword_map = [
                ("quality control", "qc_analyzer"),
                ("qc", "qc_analyzer"),
                ("clustering", "scanpy_specialist"),
                ("single cell", "scanpy_specialist"),
                ("rna-seq", "deseq2_specialist"),
                ("differential expression", "deseq2_specialist"),
                ("literature", "pubmed_search"),
                ("papers", "pubmed_search"),
                ("figure", "matplotlib_stylist"),
                ("plot", "matplotlib_stylist"),
                ("write", "abstract_writer"),
                ("methods", "methods_writer"),
            ];

            for (keyword, agent_name) in &keyword_map {
                if description.contains(keyword) && self.agents.contains_key(*agent_name) {
                    debug!("Fallback: selected '{}' for keyword '{}'", agent_name, keyword);
                    return Ok(agent_name.to_string());
                }
            }

            // Ultimate fallback: first available agent
            candidates = self.list_agents();
            if candidates.is_empty() {
                return Err(OpenScienceError::OrchestrationError(
                    "No agents available".to_string(),
                ));
            }
        }

        // Return first candidate (could be improved with ranking)
        let selected = candidates.first().unwrap().clone();
        Ok(selected)
    }

    /// Answer a natural language question
    pub async fn answer_question(&self, question: &str) -> Result<String> {
        let task = crate::agent::Task {
            description: question.to_string(),
            parameters: serde_json::json!({"question": question}),
            specialist: None,
            priority: 5,
            timeout_seconds: Some(300),
        };

        let result = self.execute_task(&task).await?;
        Ok(result.data.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent::MockAgent;
    use std::collections::HashMap;

    fn create_test_orchestrator() -> AgentOrchestrator {
        AgentOrchestrator::new(None, "local".to_string())
    }

    #[tokio::test]
    async fn test_orchestrator_creation() {
        let orchestrator = create_test_orchestrator();
        assert!(orchestrator.list_agents().is_empty());
        assert_eq!(orchestrator.compute_backend, "local");
    }

    #[tokio::test]
    async fn test_agent_registration() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();

        let result = orchestrator.register_agent(agent);
        assert!(result.is_ok());

        assert_eq!(orchestrator.list_agents(), vec!["mock_agent"]);
    }

    #[tokio::test]
    async fn test_duplicate_agent_registration() {
        let orchestrator = create_test_orchestrator();
        let agent1 = MockAgent::new();
        let agent2 = MockAgent::new();

        assert!(orchestrator.register_agent(agent1).is_ok());
        assert!(orchestrator.register_agent(agent2).is_err());
    }

    #[tokio::test]
    async fn test_get_agent() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        orchestrator.register_agent(agent).unwrap();

        let agent_ref = orchestrator.get_agent("mock_agent");
        assert!(agent_ref.is_ok());

        let missing = orchestrator.get_agent("missing");
        assert!(missing.is_err());
    }

    #[tokio::test]
    async fn test_get_agents_by_category() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        let category = agent.metadata().category.clone();
        orchestrator.register_agent(agent).unwrap();

        let agents = orchestrator.get_agents_by_category(&category);
        assert_eq!(agents, vec!["mock_agent"]);

        let literature_agents = orchestrator.get_agents_by_category(&AgentCategory::Literature);
        assert!(literature_agents.is_empty());
    }

    #[tokio::test]
    async fn test_select_agent_with_specialist() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        orchestrator.register_agent(agent).unwrap();

        let task = crate::agent::Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };

        let selected = orchestrator.select_agent(&task);
        assert_eq!(selected.unwrap(), "mock_agent");
    }

    #[tokio::test]
    async fn test_select_agent_fallback() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        orchestrator.register_agent(agent).unwrap();

        let task = crate::agent::Task {
            description: "quality control analysis".to_string(),
            parameters: serde_json::json!({}),
            specialist: None,
            priority: 5,
            timeout_seconds: None,
        };

        let selected = orchestrator.select_agent(&task);
        assert_eq!(selected.unwrap(), "mock_agent"); // Falls back to mock_agent since it's the only one
    }

    #[tokio::test]
    async fn test_select_agent_no_agents() {
        let orchestrator = create_test_orchestrator();
        let task = crate::agent::Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: None,
            priority: 5,
            timeout_seconds: None,
        };

        let selected = orchestrator.select_agent(&task);
        assert!(selected.is_err());
    }

    #[tokio::test]
    async fn test_execute_task() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        orchestrator.register_agent(agent).unwrap();

        let task = crate::agent::Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: Some("mock_agent".to_string()),
            priority: 5,
            timeout_seconds: None,
        };

        let result = orchestrator.execute_task(&task).await;
        assert!(result.is_ok());

        let result = result.unwrap();
        assert_eq!(result.agent, "mock_agent");
        assert!(result.success);
    }

    #[tokio::test]
    async fn test_execute_agent() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        orchestrator.register_agent(agent).unwrap();

        let task = crate::agent::Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: None,
            priority: 5,
            timeout_seconds: None,
        };

        let result = orchestrator.execute_agent("mock_agent", &task).await;
        assert!(result.is_ok());

        let result = result.unwrap();
        assert_eq!(result.agent, "mock_agent");
        assert!(result.success);
    }

    #[tokio::test]
    async fn test_execute_agent_not_found() {
        let orchestrator = create_test_orchestrator();
        let task = crate::agent::Task {
            description: "Test task".to_string(),
            parameters: serde_json::json!({}),
            specialist: None,
            priority: 5,
            timeout_seconds: None,
        };

        let result = orchestrator.execute_agent("missing_agent", &task).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_get_agent_metadata() {
        let orchestrator = create_test_orchestrator();
        let agent = MockAgent::new();
        let expected_metadata = agent.metadata().clone();
        orchestrator.register_agent(agent).unwrap();

        let metadata = orchestrator.get_agent_metadata("mock_agent");
        assert!(metadata.is_ok());
        assert_eq!(metadata.unwrap(), expected_metadata);
    }
}
