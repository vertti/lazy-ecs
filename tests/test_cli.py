import sys
from unittest.mock import Mock, patch

from lazy_ecs import _create_aws_client, main


@patch("lazy_ecs._create_cloudwatch_client")
@patch("lazy_ecs._create_sts_client")
@patch("lazy_ecs._create_logs_client")
@patch("lazy_ecs._create_aws_client")
@patch("lazy_ecs.ECSNavigator")
@patch("lazy_ecs.console")
def test_main_successful_flow(
    mock_console,
    mock_navigator_class,
    mock_create_client,
    mock_create_logs_client,
    mock_create_sts_client,
    mock_create_cloudwatch_client,
) -> None:
    """Test main function with successful cluster selection."""
    mock_navigator = Mock()
    mock_navigator.select_cluster.return_value = "production"
    mock_navigator_class.return_value = mock_navigator

    with patch.object(sys, "argv", ["lazy-ecs"]):
        main()

    mock_create_client.assert_called_once_with(None)
    mock_create_logs_client.assert_called_once_with(None)
    mock_create_sts_client.assert_called_once_with(None)
    mock_create_cloudwatch_client.assert_called_once_with(None)
    mock_navigator.select_cluster.assert_called_once()
    mock_console.print.assert_any_call("🚀 Welcome to lazy-ecs!", style="bold cyan")
    mock_console.print.assert_any_call("\n✅ Selected cluster: production", style="green")


@patch("lazy_ecs._create_cloudwatch_client")
@patch("lazy_ecs._create_sts_client")
@patch("lazy_ecs._create_logs_client")
@patch("lazy_ecs._create_aws_client")
@patch("lazy_ecs.ECSNavigator")
@patch("lazy_ecs.console")
def test_main_no_cluster_selected(
    mock_console,
    mock_navigator_class,
    _mock_create_client,
    _mock_create_logs_client,
    _mock_create_sts_client,
    _mock_create_cloudwatch_client,
) -> None:
    """Test main function when no cluster is selected."""
    mock_navigator = Mock()
    mock_navigator.select_cluster.return_value = None
    mock_navigator_class.return_value = mock_navigator

    with patch.object(sys, "argv", ["lazy-ecs"]):
        main()

    mock_console.print.assert_any_call("\n❌ No cluster selected. Goodbye!", style="yellow")


@patch("lazy_ecs._create_cloudwatch_client")
@patch("lazy_ecs._create_sts_client")
@patch("lazy_ecs._create_logs_client")
@patch("lazy_ecs._create_aws_client")
@patch("lazy_ecs.console")
def test_main_aws_error(
    mock_console,
    mock_create_client,
    _mock_create_logs_client,
    _mock_create_sts_client,
    _mock_create_cloudwatch_client,
) -> None:
    """Test main function with AWS connection error."""
    mock_create_client.side_effect = Exception("No credentials found")

    with patch.object(sys, "argv", ["lazy-ecs"]):
        main()

    mock_console.print.assert_any_call("\n❌ Error: No credentials found", style="red")
    mock_console.print.assert_any_call("Make sure your AWS credentials are configured.", style="dim")


@patch("lazy_ecs._create_cloudwatch_client")
@patch("lazy_ecs._create_sts_client")
@patch("lazy_ecs._create_logs_client")
@patch("lazy_ecs._create_aws_client")
@patch("lazy_ecs.ECSNavigator")
@patch("lazy_ecs.console")
def test_main_with_profile_argument(
    _mock_console,
    mock_navigator_class,
    mock_create_client,
    mock_create_logs_client,
    mock_create_sts_client,
    mock_create_cloudwatch_client,
) -> None:
    """Test main function with --profile argument."""
    mock_navigator = Mock()
    mock_navigator.select_cluster.return_value = "production"
    mock_navigator_class.return_value = mock_navigator

    with patch.object(sys, "argv", ["lazy-ecs", "--profile", "my-profile"]):
        main()

    mock_create_client.assert_called_once_with("my-profile")
    mock_create_logs_client.assert_called_once_with("my-profile")
    mock_create_sts_client.assert_called_once_with("my-profile")
    mock_create_cloudwatch_client.assert_called_once_with("my-profile")


def test_create_aws_client_without_profile():
    """Test _create_aws_client without profile returns default client."""
    with patch("lazy_ecs.boto3.client") as mock_client:
        _create_aws_client(None)
        # Should be called with ECS and config for connection pooling
        assert mock_client.call_count == 1
        args, kwargs = mock_client.call_args
        assert args[0] == "ecs"
        assert "config" in kwargs


def test_create_aws_client_with_profile():
    """Test _create_aws_client with profile uses Session."""
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client

    with patch("lazy_ecs.boto3.Session", return_value=mock_session) as mock_session_class:
        result = _create_aws_client("my-profile")

        mock_session_class.assert_called_once_with(profile_name="my-profile")
        # Should be called with ECS and config for connection pooling
        assert mock_session.client.call_count == 1
        args, kwargs = mock_session.client.call_args
        assert args[0] == "ecs"
        assert "config" in kwargs
        assert result == mock_client
