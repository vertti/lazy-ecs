from click.testing import CliRunner
from lazy_ecs import main


def test_main_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "A CLI tool for working with AWS services." in result.output


def test_version_command():
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "lazy-ecs 0.1.0" in result.output


def test_ecs_help():
    runner = CliRunner()
    result = runner.invoke(main, ["ecs", "--help"])
    assert result.exit_code == 0
    assert "Commands for Amazon ECS." in result.output


def test_ecs_list_clusters():
    runner = CliRunner()
    result = runner.invoke(main, ["ecs", "list-clusters"])
    assert result.exit_code == 0
    assert "Listing ECS clusters..." in result.output
