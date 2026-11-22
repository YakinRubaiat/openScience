//! Session management for openScience

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

use crate::agent::Agent;
use crate::error::Result;
use crate::orchestrator::AgentOrchestrator;
use crate::sandbox::SandboxConfig;

/// A scientific analysis session
#[derive(Debug)]
pub struct ScienceSession {
    /// Project directory
    pub project_dir: PathBuf,
    /// Agent orchestrator
    pub orchestrator: AgentOrchestrator,
    /// Current session data
    pub data: HashMap<String, serde_json::Value>,
    /// Session results
    pub results: HashMap<String, crate::agent::AgentResult>,
    /// Session artifacts (files)
    pub artifacts: Vec<PathBuf>,
    /// Sandbox configuration
    pub sandbox_config: Option<SandboxConfig>,
}

impl ScienceSession {
    /// Create a new science session
    pub fn new(
        project_dir: Option<PathBuf>,
        compute_backend: &str,
        sandbox_config: Option<SandboxConfig>,
    ) -> Result<Self> {
        let project_dir = project_dir.unwrap_or_else(|| PathBuf::from("."));
        
        let orchestrator = AgentOrchestrator::new(
            sandbox_config.clone(),
            compute_backend.to_string(),
        );

        Ok(Self {
            project_dir,
            orchestrator,
            data: HashMap::new(),
            results: HashMap::new(),
            artifacts: Vec::new(),
            sandbox_config,
        })
    }

    /// Load data into the session
    pub async fn load_data<P: AsRef<Path>>(
        &mut self,
        file_path: P,
        format: &str,
        name: Option<&str>,
        parameters: Option<serde_json::Value>,
    ) -> Result<()> {
        let path = file_path.as_ref();
        let name = name.unwrap_or_else(|| {
            path.file_stem()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string()
        });

        let task = crate::agent::Task {
            description: format!("Load {} data from {}", format, path.display()),
            parameters: serde_json::json!({
                "file_path": path.to_string_lossy(),
                "format_hint": format,
                "name": name,
            })
            .merge(parameters.unwrap_or_default()),
            specialist: Some("data_ingestor".to_string()),
            priority: 5,
            timeout_seconds: Some(3600),
        };

        let result = self.orchestrator.execute_task(&task).await?;
        self.data.insert(name.to_string(), result.data);
        Ok(())
    }

    /// Run an analysis task
    pub async fn analyze(
        &mut self,
        task: &str,
        specialist: Option<&str>,
        data_key: Option<&str>,
        parameters: Option<serde_json::Value>,
    ) -> Result<crate::agent::AgentResult> {
        let context = self.build_context();
        
        let task = crate::agent::Task {
            description: task.to_string(),
            parameters: serde_json::json!({
                "data_key": data_key,
            })
            .merge(parameters.unwrap_or_default()),
            specialist: specialist.map(|s| s.to_string()),
            priority: 5,
            timeout_seconds: Some(3600),
        };

        let result = self.orchestrator.execute_task_with_context(&task, context).await?;
        self.results.insert(task.to_string(), result.clone());
        Ok(result)
    }

    /// Get a result by task description
    pub fn get_result(&self, task: &str) -> Option<&crate::agent::AgentResult> {
        self.results.get(task)
    }

    /// Get loaded data by name
    pub fn get_data(&self, name: &str) -> Option<&serde_json::Value> {
        self.data.get(name)
    }

    /// Get all loaded data names
    pub fn list_data(&self) -> Vec<String> {
        self.data.keys().cloned().collect()
    }

    /// Get all result task descriptions
    pub fn list_results(&self) -> Vec<String> {
        self.results.keys().cloned().collect()
    }

    /// Save session state to disk
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let path = path.as_ref();
        
        // Create directory if it doesn't exist
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let state = SessionState {
            data: self.data.clone(),
            results: self.results.clone(),
            artifacts: self.artifacts.iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect(),
            project_dir: self.project_dir.to_string_lossy().to_string(),
        };

        let json = serde_json::to_string_pretty(&state)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    /// Load a saved session from disk
    pub fn load<P: AsRef<Path>>(
        path: P,
        compute_backend: &str,
        sandbox_config: Option<SandboxConfig>,
    ) -> Result<Self> {
        let path = path.as_ref();
        let json = std::fs::read_to_string(path)?;
        let state: SessionState = serde_json::from_str(&json)?;

        let project_dir = PathBuf::from(state.project_dir);
        
        let mut session = Self::new(
            Some(project_dir),
            compute_backend,
            sandbox_config,
        )?;

        session.data = state.data;
        session.results = state.results;
        session.artifacts = state.artifacts.iter()
            .map(|s| PathBuf::from(s))
            .collect();

        Ok(session)
    }

    /// Build execution context for agents
    fn build_context(&self) -> TaskContext {
        TaskContext {
            project_dir: self.project_dir.to_string_lossy().to_string(),
            data: self.data.clone(),
            results: self.results.clone().into_iter()
                .map(|(k, v)| (k, v))
                .collect(),
            sandbox_config: self.sandbox_config.clone(),
        }
    }
}

/// Serializable session state
#[derive(Serialize, Deserialize)]
struct SessionState {
    data: HashMap<String, serde_json::Value>,
    results: HashMap<String, crate::agent::AgentResult>,
    artifacts: Vec<String>,
    project_dir: String,
}

// Extension trait for merging JSON values
trait JsonMerge {
    fn merge(self, other: serde_json::Value) -> serde_json::Value;
}

impl JsonMerge for serde_json::Value {
    fn merge(self, other: serde_json::Value) -> serde_json::Value {
        match (self, other) {
            (serde_json::Value::Object(mut a), serde_json::Value::Object(b)) => {
                for (k, v) in b {
                    a.insert(k, v);
                }
                serde_json::Value::Object(a)
            }
            (_, other) => other,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn create_test_session() -> Result<ScienceSession> {
        let temp_dir = TempDir::new()?;
        ScienceSession::new(
            Some(temp_dir.path().to_path_buf()),
            "local",
            None,
        )
    }

    #[test]
    fn test_session_creation() {
        let session = create_test_session();
        assert!(session.is_ok());
        
        let session = session.unwrap();
        assert!(session.project_dir.exists());
        assert_eq!(session.data.len(), 0);
        assert_eq!(session.results.len(), 0);
    }

    #[tokio::test]
    async fn test_list_operations() {
        let mut session = create_test_session().unwrap();
        
        // Initially empty
        assert!(session.list_data().is_empty());
        assert!(session.list_results().is_empty());

        // Add some dummy data
        session.data.insert("test_data".to_string(), serde_json::json!({"value": 42}));
        session.results.insert("test_analysis".to_string(), 
            crate::agent::AgentResult {
                agent: "test_agent".to_string(),
                data: serde_json::json!({"result": "success"}),
                metadata: std::collections::HashMap::new(),
                artifacts: vec![],
                execution_time_ms: 100,
                success: true,
            }
        );

        assert_eq!(session.list_data(), vec!["test_data"]);
        assert_eq!(session.list_results(), vec!["test_analysis"]);
    }

    #[tokio::test]
    async fn test_save_and_load() {
        let temp_dir = TempDir::new().unwrap();
        let save_path = temp_dir.path().join("session.json");

        let mut session = create_test_session().unwrap();
        
        // Add data
        session.data.insert("test_data".to_string(), serde_json::json!({"value": 123}));

        // Save
        let save_result = session.save(&save_path);
        assert!(save_result.is_ok());
        assert!(save_path.exists());

        // Load
        let loaded = ScienceSession::load(&save_path, "local", None);
        assert!(loaded.is_ok());
        
        let loaded = loaded.unwrap();
        assert_eq!(loaded.data.len(), 1);
        assert_eq!(loaded.data.get("test_data").unwrap(), &serde_json::json!({"value": 123}));
    }

    #[tokio::test]
    async fn test_context_building() {
        let mut session = create_test_session().unwrap();
        session.data.insert("data1".to_string(), serde_json::json!({"x": 1}));
        
        let context = session.build_context();
        assert_eq!(context.project_dir, session.project_dir.to_string_lossy());
        assert_eq!(context.data.len(), 1);
        assert!(context.results.is_empty());
        assert!(context.sandbox_config.is_none());
    }

    #[test]
    fn test_json_merge() {
        let a = serde_json::json!({"a": 1, "b": {"c": 2}});
        let b = serde_json::json!({"b": {"d": 3}, "e": 4});
        let merged = a.merge(b);
        
        let expected = serde_json::json!({"a": 1, "b": {"d": 3}, "e": 4});
        assert_eq!(merged, expected);
    }
}
