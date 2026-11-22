//! openScience Core - High-performance scientific AI workbench
//!
//! This library provides the core infrastructure for orchestrating scientific AI agents,
//! managing compute resources, and enforcing security policies.

pub mod agent;
pub mod error;
pub mod orchestrator;
pub mod sandbox;
pub mod session;

// Re-export main types for convenience
pub use agent::{Agent, AgentMetadata, AgentResult, AgentCategory};
pub use error::{OpenScienceError, Result};
pub use orchestrator::{AgentOrchestrator, Task, TaskContext, TaskResult};
pub use sandbox::{SecurityPolicy, Sandbox, SandboxConfig};

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Initialize the library with default settings
pub fn init() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_not_empty() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_init() {
        // Should not panic
        init();
    }
}
