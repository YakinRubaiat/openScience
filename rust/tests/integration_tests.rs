//! Integration tests for openScience core

use openscience_core::agent::{Agent, AgentCategory, AgentMetadata, Task, TaskContext};
use openscience_core::error::Result;
use openscience_core::orchestrator::AgentOrchestrator;
use openscience_core::sandbox::{Sandbox, SandboxConfig, SecurityPolicy};
use openscience_core::session::ScienceSession;
use std::collections::HashMap;
use tempfile::TempDir;

// Test agent for integration testing
#[derive(Debug)]
struct IntegrationTestAgent {
    metadata: AgentMetadata,
    should_succeed: bool,
}

#[async_trait::async_trait]
impl Agent for IntegrationTestAgent {
    fn metadata(&self) -> &AgentMetadata {
        &self.metadata
    }

    async fn execute(&mut self, task: &Task, context: &TaskContext) -> Result<crate::agent::AgentResult> {
        if !self.should_succeed {
            return Err(crate::error::OpenScienceError::AgentError(
                "Integration test failure".to_string(),
            ));
        }

        Ok(crate::agent::AgentResult {
            agent: self.metadata.name.clone(),
            data: serde_json::json!({
                "task": task.description,
                "data_keys": context.data.keys().collect::<Vec<_>>(),
                "success": true,
            }),
            metadata: HashMap::new(),
            artifacts: vec![],
            execution_time_ms: 50,
            success: true,
        })
    }
}

fn create_test_agent(name: &str, category: AgentCategory) -> IntegrationTestAgent {
    IntegrationTestAgent {
        metadata: AgentMetadata {
            name: name.to_string(),
            category,
            description: format!("Test agent: {}", name),
            required_skills: vec!["test_skill".to_string()],
            input_types: vec!["test_input".to_string()],
            output_types: vec!["test_output".to_string()],
            version: "1.0.0".to_string(),
        },
        should_succeed: true,
    }
}

fn create_test_session(temp_dir: &TempDir) -> Result<ScienceSession> {
    ScienceSession::new(
        Some(temp_dir.path().to_path_buf()),
        "local",
        None,
    )
}

fn create_test_task(description: &str, specialist: Option<&str>) -> Task {
    Task {
        description: description.to_string(),
        parameters: serde_json::json!({"test": true}),
        specialist: specialist.map(|s| s.to_string()),
        priority: 5,
        timeout_seconds: Some(60),
    }
}

#[tokio::test]
async fn test_orchestrator_agent_registration() {
    let orchestrator = AgentOrchestrator::new(None, "local".to_string());
    
    // Register test agents
    let agent1 = create_test_agent("test_agent_1", AgentCategory::Analysis);
    let agent2 = create_test_agent("test_agent_2", AgentCategory::Literature);
    
    assert!(orchestrator.register_agent(agent1).is_ok());
    assert!(orchestrator.register_agent(agent2).is_ok());
    
    // Verify registration
    let agents = orchestrator.list_agents();
    assert_eq!(agents.len(), 2);
    assert!(agents.contains(&"test_agent_1".to_string()));
    assert!(agents.contains(&"test_agent_2".to_string()));
}

#[tokio::test]
async fn test_orchestrator_task_execution() {
    let orchestrator = AgentOrchestrator::new(None, "local".to_string());
    
    // Register agents
    let agent = create_test_agent("test_agent", AgentCategory::Analysis);
    orchestrator.register_agent(agent).unwrap();
    
    // Execute task
    let task = create_test_task("Test analysis", Some("test_agent"));
    let result = orchestrator.execute_task(&task).await;
    
    assert!(result.is_ok());
    let result = result.unwrap();
    assert_eq!(result.agent, "test_agent");
    assert!(result.success);
    assert_eq!(result.data["task"], "Test analysis");
}

#[tokio::test]
async fn test_orchestrator_agent_fallback() {
    let orchestrator = AgentOrchestrator::new(None, "local".to_string());
    
    // Register agents with different specialties
    let qc_agent = create_test_agent("qc_analyzer", AgentCategory::Analysis);
    let pubmed_agent = create_test_agent("pubmed_search", AgentCategory::Literature);
    
    orchestrator.register_agent(qc_agent).unwrap();
    orchestrator.register_agent(pubmed_agent).unwrap();
    
    // Task with no specialist - should fallback
    let task = create_test_task("quality control analysis", None);
    let result = orchestrator.execute_task(&task).await;
    
    // Should execute some agent (fallback logic)
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_sandbox_execution() {
    let sandbox_config = SandboxConfig {
        enabled: true,
        policy: SecurityPolicy::default(),
        approval_handler: Some("test_handler".to_string()),
    };
    
    let sandbox = Sandbox::new(sandbox_config);
    let agent = create_test_agent("sandbox_test", AgentCategory::Analysis);
    let task = create_test_task("Sandbox test", Some("sandbox_test"));
    
    let result = sandbox.execute_agent(&agent, &task).await;
    assert!(result.is_ok());
    
    let result = result.unwrap();
    assert!(result.success);
    assert_eq!(result.agent, "sandbox_test");
}

#[tokio::test]
async fn test_sandbox_disabled() {
    let sandbox_config = SandboxConfig {
        enabled: false,
        policy: SecurityPolicy::default(),
        approval_handler: None,
    };
    
    let sandbox = Sandbox::new(sandbox_config);
    let agent = create_test_agent("no_sandbox_test", AgentCategory::Analysis);
    let task = create_test_task("No sandbox test", Some("no_sandbox_test"));
    
    let result = sandbox.execute_agent(&agent, &task).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_session_data_management() {
    let temp_dir = TempDir::new().unwrap();
    let mut session = create_test_session(&temp_dir).unwrap();
    
    // Register a test agent
    let agent = create_test_agent("data_ingestor", AgentCategory::DataManagement);
    session.orchestrator.register_agent(agent).unwrap();
    
    // Create a temporary data file
    let data_path = temp_dir.path().join("test_data.csv");
    std::fs::write(&data_path, "value\n42\n").unwrap();
    
    // Load data
    let result = session.load_data(&data_path, "csv", Some("test_dataset"), None).await;
    assert!(result.is_ok());
    
    // Check data was loaded
    assert!(session.get_data("test_dataset").is_some());
    assert_eq!(session.list_data(), vec!["test_dataset"]);
}

#[tokio::test]
async fn test_session_result_storage() {
    let temp_dir = TempDir::new().unwrap();
    let mut session = create_test_session(&temp_dir).unwrap();
    
    // Register agent
    let agent = create_test_agent("test_analysis", AgentCategory::Analysis);
    session.orchestrator.register_agent(agent).unwrap();
    
    // Execute task
    let task = create_test_task("Test analysis", Some("test_analysis"));
    let result = session.orchestrator.execute_task(&task).await.unwrap();
    
    // Store result
    session.results.insert("test_analysis".to_string(), result);
    
    // Verify
    assert!(session.get_result("test_analysis").is_some());
    assert_eq!(session.list_results(), vec!["test_analysis"]);
}

#[test]
fn test_session_persistence() {
    let temp_dir = TempDir::new().unwrap();
    let mut session = create_test_session(&temp_dir).unwrap();
    
    // Add data
    session.data.insert("test".to_string(), serde_json::json!(123));
    
    // Save
    let save_path = temp_dir.path().join("session.json");
    let save_result = session.save(&save_path);
    assert!(save_result.is_ok());
    assert!(save_path.exists());
    
    // Load
    let load_result = ScienceSession::load(&save_path, "local", None);
    assert!(load_result.is_ok());
    
    let loaded = load_result.unwrap();
    assert_eq!(loaded.data.len(), 1);
    assert_eq!(loaded.data.get("test").unwrap(), &serde_json::json!(123));
}

#[tokio::test]
async fn test_agent_can_execute() {
    let agent = create_test_agent("test_agent", AgentCategory::Analysis);
    
    // Matching specialist
    let task = create_test_task("Test", Some("test_agent"));
    assert!(agent.can_execute(&task));
    
    // Non-matching specialist
    let task = create_test_task("Test", Some("other_agent"));
    assert!(!agent.can_execute(&task));
    
    // Matching by description
    let task = create_test_task("Run test_agent analysis", None);
    assert!(agent.can_execute(&task));
    
    // Non-matching
    let task = create_test_task("Something else", None);
    assert!(!agent.can_execute(&task));
}

#[tokio::test]
async fn test_error_handling() {
    let failing_agent = IntegrationTestAgent {
        metadata: AgentMetadata {
            name: "failing_agent".to_string(),
            category: AgentCategory::Analysis,
            description: "A failing test agent".to_string(),
            required_skills: vec![],
            input_types: vec![],
            output_types: vec![],
            version: "1.0.0".to_string(),
        },
        should_succeed: false,
    };
    
    let orchestrator = AgentOrchestrator::new(None, "local".to_string());
    orchestrator.register_agent(failing_agent).unwrap();
    
    let task = create_test_task("Test failure", Some("failing_agent"));
    let result = orchestrator.execute_task(&task).await;
    
    assert!(result.is_err());
}

#[test]
fn test_agent_category_serialization() {
    let category = AgentCategory::Analysis;
    let json = serde_json::to_string(&category).unwrap();
    assert_eq!(json, "\"analysis\"");
    
    let deserialized: AgentCategory = serde_json::from_str(&json).unwrap();
    assert_eq!(deserialized, AgentCategory::Analysis);
}

#[test]
fn test_task_serialization() {
    let task = create_test_task("Test", Some("agent"));
    let json = serde_json::to_string(&task).unwrap();
    assert!(json.contains("Test"));
    
    let deserialized: Task = serde_json::from_str(&json).unwrap();
    assert_eq!(deserialized.description, "Test");
    assert_eq!(deserialized.specialist, Some("agent".to_string()));
}
