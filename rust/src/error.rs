//! Error types for openScience

use thiserror::Error;

/// Main error type for openScience operations
#[derive(Error, Debug)]
pub enum OpenScienceError {
    /// Agent execution failed
    #[error("Agent execution failed: {0}")]
    AgentError(String),

    /// Orchestration error
    #[error("Orchestration error: {0}")]
    OrchestrationError(String),

    /// Security violation
    #[error("Security violation: {0}")]
    SecurityError(String),

    /// Skill execution error
    #[error("Skill execution error: {0}")]
    SkillError(String),

    /// Connector error
    #[error("Connector error: {0}")]
    ConnectorError(String),

    /// Serialization/deserialization error
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    /// IO error
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    /// Async task error
    #[error("Async task error: {0}")]
    AsyncError(#[from] tokio::task::JoinError),

    /// Validation error
    #[error("Validation error: {0}")]
    ValidationError(String),

    /// Configuration error
    #[error("Configuration error: {0}")]
    ConfigError(String),

    /// Generic error with source
    #[error("Error: {0} (source: {source})")]
    WithSource {
        msg: String,
        #[source]
        source: Box<dyn std::error::Error + Send + Sync>,
    },
}

/// Result type alias for openScience operations
pub type Result<T> = std::result::Result<T, OpenScienceError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = OpenScienceError::AgentError("test failure".to_string());
        assert_eq!(err.to_string(), "Agent execution failed: test failure");

        let err = OpenScienceError::SecurityError("unauthorized".to_string());
        assert_eq!(err.to_string(), "Security violation: unauthorized");
    }

    #[test]
    fn test_from_serde_json() {
        let json_err = serde_json::from_str::<serde_json::Value>("invalid json").unwrap_err();
        let err: OpenScienceError = json_err.into();
        assert!(matches!(err, OpenScienceError::SerializationError(_)));
    }

    #[test]
    fn test_from_io_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err: OpenScienceError = io_err.into();
        assert!(matches!(err, OpenScienceError::IoError(_)));
    }
}
