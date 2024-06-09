from datetime import datetime, timezone
from typing import Optional
import typer
from devbox import __app_name__, __version__, ec2
app = typer.Typer()
from requests import get

@app.command()
def start(instance_name: str = typer.Option(
        "devbox",
        "--instance-name",
        "-i",
        help="Name of the EC2 instance to start. If not specified, the default instance will be used.",
        envvar="EC2_INSTANCE_NAME",
        show_default=True)) -> str:
    """Starts your dev box"""
    # First get my local IP address
    ip = get('https://api.ipify.org').content.decode('utf8')
    # Then start my EC2 instance
    id, public_ip = ec2.start_instance(instance_name, ip)
    typer.echo(f"Started instance {instance_name} ({id}) at {public_ip}")

@app.command()
def stop(instance_name: str = typer.Option(
        "devbox",
        "--instance-name",
        "-i",
        help="Name of the EC2 instance to stop. If not specified, the default instance will be used.",
        envvar="EC2_INSTANCE_NAME",
        show_default=True)):
    """Stops your dev box"""
    id = ec2.stop_instance(instance_name)
    typer.echo(f"Stopped instance {instance_name} ({id})")

@app.command()
def status(instance_name: str = typer.Option(
        "devbox",
        "--instance-name",
        "-i",
        help="Name of the EC2 instance to get. If not specified, the default instance will be used.",
        envvar="EC2_INSTANCE_NAME",
        show_default=True)):
    """Shows the status of your dev box"""
    status, ip = ec2.get_instance_status(instance_name)
    typer.echo(f"Instance {instance_name} is {status} at IP {ip}")


@app.command()
def reboot(instance_name: str = typer.Option(
        "devbox",
        "--instance-name",
        "-i",
        help="Name of the EC2 instance to restart. If not specified, the default instance will be used.",
        envvar="EC2_INSTANCE_NAME",
        show_default=True)):
    """Reboots your dev box"""
    id = ec2.reboot_instance(instance_name)
    typer.echo(f"Rebooted instance {instance_name} ({id})")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()

@app.callback()
def main(version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True)) -> None:
    """
    Welcome to the SRNet CLI!
    """
    pass
