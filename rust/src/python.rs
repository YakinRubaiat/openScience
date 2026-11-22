//! Python bindings for openScience core using PyO3

use pyo3::prelude::*;
use pyo3::types::PyModule;

use crate::agent::{AgentCategory, AgentResult};
use crate::error::OpenScienceError;
use crate::orchestrator::AgentOrchestrator;
use crate::sandbox::{Sandbox, SandboxConfig};
use crate::session::ScienceSession;

/// Python wrapper for AgentCategory
#[pyclass]
#[derive(Clone)]
pub struct PyAgentCategory {
    category: AgentCategory,
}

#[pymethods]
impl PyAgentCategory {
    #[new]
    fn new(name: &str) -> PyResult<Self> {
        let category = match name.to_lowercase().as_str() {
            "literature" => AgentCategory::Literature,
            "experiment" => AgentCategory::Experiment,
            "data_management" => AgentCategory::DataManagement,
            "analysis" => AgentCategory::Analysis,
            "visualization" => AgentCategory::Visualization,
            "writing" => AgentCategory::Writing,
            "review" => AgentCategory::Review,
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid agent category: {}", name),
            )),
        };
        Ok(Self { category })
    }

    fn name(&self) -> String {
        self.category.to_string()
    }

    fn __repr__(&self) -> String {
        format!("AgentCategory('{}')", self.category)
    }
}

/// Python wrapper for AgentResult
#[pyclass]
#[derive(Clone)]
pub struct PyAgentResult {
    result: AgentResult,
}

#[pymethods]
impl PyAgentResult {
    #[getter]
    fn agent(&self) -> String {
        self.result.agent.clone()
    }

    #[getter]
    fn data(&self) -> PyObject {
        Python::with_gil(|py| {
            match serde_json::to_string(&self.result.data) {
                Ok(json) => json.into_py(py),
                Err(_) => py.None(),
            }
        })
    }

    #[getter]
    fn success(&self) -> bool {
        self.result.success
    }

    #[getter]
    fn execution_time_ms(&self) -> u64 {
        self.result.execution_time_ms
    }

    fn __repr__(&self) -> String {
        format!("AgentResult(agent='{}', success={})", self.result.agent, self.result.success)
    }
}

/// Python wrapper for AgentOrchestrator
#[pyclass]
pub struct PyAgentOrchestrator {
    orchestrator: AgentOrchestrator,
}

#[pymethods]
impl PyAgentOrchestrator {
    #[new]
    fn new(sandbox_config: Option<&str>, compute_backend: &str) -> PyResult<Self> {
        let config = sandbox_config.and_then(|s| serde_json::from_str(s).ok());
        let orchestrator = AgentOrchestrator::new(config, compute_backend.to_string());
        Ok(Self { orchestrator })
    }

    fn register_agent(&self, name: &str, category: &PyAgentCategory, metadata_json: &str) -> PyResult<()> {
        let metadata: crate::agent::AgentMetadata = serde_json::from_str(metadata_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        // For Python, we'll use a simplified registration
        // In a real implementation, we'd need to convert Python agents to Rust agents
        let python_agent = crate::agent::MockAgent::from_python(name, category.category.clone(), metadata);
        
        self.orchestrator
            .register_agent(python_agent)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn list_agents(&self) -> Vec<String> {
        self.orchestrator.list_agents()
    }

    fn get_agents_by_category(&self, category: &PyAgentCategory) -> Vec<String> {
        self.orchestrator.get_agents_by_category(&category.category)
    }

    fn execute_task(&mut self, task_json: &str) -> PyResult<String> {
        let task: crate::agent::Task = serde_json::from_str(task_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        // Convert async to sync for Python
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let result = rt.block_on(self.orchestrator.execute_task(&task))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        serde_json::to_string(&result)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn execute_agent(&mut self, agent_name: &str, task_json: &str) -> PyResult<String> {
        let task: crate::agent::Task = serde_json::from_str(task_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let result = rt.block_on(self.orchestrator.execute_agent(agent_name, &task))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        serde_json::to_string(&result)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn answer_question(&mut self, question: &str) -> PyResult<String> {
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        rt.block_on(self.orchestrator.answer_question(question))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn __repr__(&self) -> String {
        format!("AgentOrchestrator(agents={})", self.orchestrator.list_agents().len())
    }
}

/// Python wrapper for ScienceSession
#[pyclass]
pub struct PyScienceSession {
    session: ScienceSession,
}

#[pymethods]
impl PyScienceSession {
    #[new]
    fn new(project_dir: Option<&str>, compute_backend: &str, sandbox_config: Option<&str>) -> PyResult<Self> {
        let project_dir = project_dir.map(|s| std::path::PathBuf::from(s));
        let config = sandbox_config.and_then(|s| serde_json::from_str(s).ok());
        
        let session = ScienceSession::new(project_dir, compute_backend, config)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(Self { session })
    }

    fn load_data(&mut self, file_path: &str, format: &str, name: Option<&str>, parameters_json: Option<&str>) -> PyResult<()> {
        let parameters = parameters_json.and_then(|s| serde_json::from_str(s).ok());
        
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        rt.block_on(self.session.load_data(file_path, format, name, parameters))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn analyze(&mut self, task: &str, specialist: Option<&str>, data_key: Option<&str>, parameters_json: Option<&str>) -> PyResult<String> {
        let parameters = parameters_json.and_then(|s| serde_json::from_str(s).ok());
        
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let result = rt.block_on(self.session.analyze(task, specialist, data_key, parameters))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        serde_json::to_string(&result)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn get_data(&self, name: &str) -> PyResult<Option<String>> {
        self.session.get_data(name)
            .map(|v| serde_json::to_string(v))
            .transpose()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn get_result(&self, task: &str) -> Option<PyAgentResult> {
        self.session.get_result(task)
            .map(|result| PyAgentResult { result: result.clone() })
    }

    fn list_data(&self) -> Vec<String> {
        self.session.list_data()
    }

    fn list_results(&self) -> Vec<String> {
        self.session.list_results()
    }

    fn save(&self, path: &str) -> PyResult<()> {
        self.session.save(path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    #[staticmethod]
    fn load(path: &str, compute_backend: &str, sandbox_config: Option<&str>) -> PyResult<Self> {
        let config = sandbox_config.and_then(|s| serde_json::from_str(s).ok());
        
        let session = ScienceSession::load(path, compute_backend, config)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(Self { session })
    }

    fn __repr__(&self) -> String {
        format!("ScienceSession(project_dir='{}', data_items={}, results={})",
            self.session.project_dir.display(),
            self.session.data.len(),
            self.session.results.len()
        )
    }
}

/// Python module definition
#[pymodule]
fn openscience_core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyAgentCategory>()?;
    m.add_class::<PyAgentResult>()?;
    m.add_class::<PyAgentOrchestrator>()?;
    m.add_class::<PyScienceSession>()?;
    
    // Add version
    m.add("__version__", crate::VERSION)?;
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_category_creation() {
        let category = PyAgentCategory::new("analysis").unwrap();
        assert_eq!(category.name(), "analysis");
        
        let invalid = PyAgentCategory::new("invalid");
        assert!(invalid.is_err());
    }

    #[test]
    fn test_orchestrator_creation() {
        let orchestrator = PyAgentOrchestrator::new(None, "local").unwrap();
        assert_eq!(orchestrator.list_agents().len(), 0);
        assert_eq!(orchestrator.__repr__(), "AgentOrchestrator(agents=0)");
    }

    #[test]
    fn test_session_creation() {
        let session = PyScienceSession::new(None, "local", None).unwrap();
        assert_eq!(session.list_data().len(), 0);
        assert_eq!(session.list_results().len(), 0);
    }
}
