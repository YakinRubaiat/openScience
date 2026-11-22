"""Command-line interface for openScience."""

import click
from pathlib import Path

from openscience import __version__


@click.group()
@click.version_option(version=__version__)
def cli():
    """openScience: Open-source AI workbench for scientific research."""
    pass


@cli.command()
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--compute", default="local", help="Default compute backend")
def init(project_dir: str, compute: str):
    """Initialize a new openScience project."""
    project_path = Path(project_dir)
    
    # Create directory structure
    dirs = [
        "data/raw",
        "data/processed", 
        "results",
        "figures",
        "notebooks",
        "config",
    ]
    
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
    
    # Create config file
    config = f"""# openScience configuration
compute:
  default: {compute}
  
data:
  raw_dir: data/raw
  processed_dir: data/processed
  
output:
  results_dir: results
  figures_dir: figures
  
sandbox:
  enabled: true
  network_policy: deny_all
"""
    
    (project_path / "openscience.yaml").write_text(config)
    
    click.echo(f"✅ Initialized openScience project in {project_path}")
    click.echo(f"   Config: {project_path / 'openscience.yaml'}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind")
@click.option("--port", default=8080, help="Port to bind")
@click.option("--daemon", is_flag=True, help="Run as daemon")
def start(host: str, port: int, daemon: bool):
    """Start the openScience daemon."""
    click.echo(f"🚀 Starting openScience daemon on {host}:{port}")
    
    from openscience.server import create_app
    
    app = create_app()
    
    if daemon:
        import daemon
        with daemon.DaemonContext():
            app.run(host=host, port=port)
    else:
        app.run(host=host, port=port, debug=True)


@cli.command()
@click.option("--browser/--no-browser", default=True, help="Open browser")
def ui(browser: bool):
    """Open the openScience web interface."""
    import webbrowser
    
    url = "http://localhost:8080"
    
    if browser:
        webbrowser.open(url)
        click.echo(f"🌐 Opened {url} in browser")
    else:
        click.echo(f"🌐 openScience UI: {url}")


@cli.command()
def agents():
    """List all available agents."""
    from openscience.core.orchestrator import AgentOrchestrator
    
    orch = AgentOrchestrator()
    
    by_category = {}
    for name, agent_class in orch.agents.items():
        cat = agent_class.metadata.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((name, agent_class.metadata.description))
    
    click.echo("\n🤖 Available Agents\n" + "=" * 50)
    
    for category, agents in sorted(by_category.items()):
        click.echo(f"\n📁 {category.upper()} ({len(agents)} agents)")
        click.echo("-" * 50)
        for name, desc in sorted(agents):
            click.echo(f"  • {name:<25} {desc}")
    
    click.echo(f"\n✅ Total: {len(orch.agents)} agents")


@cli.command()
def config():
    """Show current configuration."""
    config_path = Path("openscience.yaml")
    
    if config_path.exists():
        click.echo(config_path.read_text())
    else:
        click.echo("No configuration found. Run 'openscience init' first.")


if __name__ == "__main__":
    cli()
