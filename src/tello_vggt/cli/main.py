"""CLI entry point for tello_vggt."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from tello_vggt.core.config import load_config, get_config, AppConfig
from tello_vggt.core.logging_config import setup_logging, get_logger
from tello_vggt.core.mission import MissionManager

# Create typer app
app = typer.Typer(
    name="tello-vggt",
    help="3D reconstruction pipeline for DJI Tello using VGGT-Omega",
)

logger = get_logger(__name__)


# ============================================================================
# Global Options
# ============================================================================


def setup_context(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> AppConfig:
    """Setup global context and return config."""
    # Load config
    if config_path:
        config = load_config(config_path)
    else:
        config = load_config()
    
    # Override log level if specified
    if verbose:
        log_level = "DEBUG"
    config.log_level = log_level
    
    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_dir=config.logs_dir,
        log_to_file=config.log_to_file,
    )
    
    return config


# ============================================================================
# Subcommands
# ============================================================================


@app.command()
def record(
    duration: Annotated[
        Optional[int],
        typer.Option("--duration", "-d", help="Recording duration in seconds (None = until Ctrl+C)")
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output mission directory")
    ] = None,
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
):
    """Record video from DJI Tello drone."""
    config = setup_context(config_path=config_path)
    logger.info(f"Starting Tello recording for {duration}s" if duration else "Starting Tello recording until interrupt")
    
    from tello_vggt.cli.commands.record import cmd_record
    cmd_record(config=config, duration=duration, output_dir=output)


@app.command()
def video(
    input_video: Annotated[
        Path,
        typer.Argument(help="Input video file path"),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output mission directory")
    ] = None,
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
    skip_inference: bool = typer.Option(
        False,
        "--skip-inference",
        help="Only extract frames, skip VGGT inference",
    ),
    skip_export: bool = typer.Option(
        False,
        "--skip-export",
        help="Skip final GLB export",
    ),
):
    """Reconstruct from video file."""
    config = setup_context(config_path=config_path)
    logger.info(f"Processing video: {input_video}")
    
    from tello_vggt.cli.commands.video import cmd_video
    cmd_video(
        config=config,
        video_path=input_video,
        output_dir=output,
        skip_inference=skip_inference,
        skip_export=skip_export,
    )


@app.command()
def rebuild(
    mission: Annotated[
        Path,
        typer.Argument(help="Mission directory or mission ID"),
    ],
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
    re_export: bool = typer.Option(
        False,
        "--re-export",
        help="Force re-export GLB even if it exists",
    ),
):
    """Rebuild GLB from existing mission chunks."""
    config = setup_context(config_path=config_path)
    logger.info(f"Rebuilding mission: {mission}")
    
    from tello_vggt.cli.commands.rebuild import cmd_rebuild
    cmd_rebuild(config=config, mission_path=mission, re_export=re_export)


@app.command()
def list_missions(
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
):
    """List all missions."""
    config = setup_context(config_path=config_path)
    
    manager = MissionManager(config.missions_dir)
    missions = manager.list_missions()
    
    if not missions:
        typer.echo("No missions found.")
        return
    
    typer.echo("\n📋 Available Missions:\n")
    for mission in missions:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "inferenced": "🔄",
            "initialized": "⏱️",
        }.get(mission.get_status().value, "❓")
        
        typer.echo(
            f"{status_emoji} {mission.mission_id}"
            f" [{mission.get_status().value}]"
            f" | Frames: {mission.num_frames} | Chunks: {mission.num_chunks}"
        )
        typer.echo(f"   Created: {mission.metadata.created_at}\n")


@app.command()
def show_config(
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Save config to file")
    ] = None,
):
    """Display current configuration."""
    config = setup_context(config_path=config_path)
    
    yaml_str = config.to_yaml()
    
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_str)
        typer.echo(f"✅ Configuration saved to: {output}")
    else:
        typer.echo("\n" + "=" * 70)
        typer.echo("📋 Current Configuration")
        typer.echo("=" * 70 + "\n")
        typer.echo(yaml_str)


@app.command()
def init_config(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output config file path"),
    ] = Path("config.yaml"),
):
    """Initialize a new configuration file from template."""
    config = AppConfig()
    config.save_yaml(output)
    typer.echo(f"✅ Configuration file created: {output}")
    typer.echo(f"📝 Edit the file and use: tello-vggt --config {output}")


@app.command()
def gaussian_splatting(
    mission: Annotated[
        Path,
        typer.Argument(help="Mission directory or mission ID"),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory for Gaussian Splatting")
    ] = None,
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
    skip_training: bool = typer.Option(
        False,
        "--skip-training",
        help="Skip training, only export",
    ),
):
    """Generate Gaussian Splatting rendering from mission."""
    config = setup_context(config_path=config_path)
    logger.info(f"Generating Gaussian Splatting for mission: {mission}")
    
    from tello_vggt.cli.commands.gaussian_splatting import cmd_gaussian_splatting
    cmd_gaussian_splatting(
        config=config,
        mission_path=mission,
        output=output,
        skip_training=skip_training,
    )


@app.command()
def semantic_segmentation(
    mission: Annotated[
        Path,
        typer.Argument(help="Mission directory or mission ID"),
    ],
    checkpoint: Annotated[
        Optional[Path],
        typer.Option("--checkpoint", "-c", help="Deep Anything V3 checkpoint path")
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory")
    ] = None,
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Configuration YAML file")
    ] = None,
):
    """Generate semantic segmentation with Deep Anything V3."""
    config = setup_context(config_path=config_path)
    
    if checkpoint:
        config.gaussian_splatting.deep_anything_v3_checkpoint = checkpoint
    
    logger.info(f"Generating semantic segmentation for mission: {mission}")
    
    from tello_vggt.cli.commands.semantic_segmentation import cmd_semantic_segmentation
    cmd_semantic_segmentation(
        config=config,
        mission_path=mission,
        output=output,
    )


@app.callback()
def main(ctx: typer.Context):
    """Tello VGGT-Omega 3D Reconstruction Pipeline."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
