from unittest.mock import Mock, patch

from lazy_ecs import main


@patch("lazy_ecs.boto3.client")
@patch("lazy_ecs.ECSNavigator")
@patch("lazy_ecs.console")
def test_main_successful_flow(mock_console, mock_navigator_class, mock_boto3_client) -> None:
    """Test main function with successful cluster selection."""
    mock_navigator = Mock()
    mock_navigator.select_cluster.return_value = "production"
    mock_navigator_class.return_value = mock_navigator

    main()

    mock_boto3_client.assert_called_once_with("ecs")
    mock_navigator.select_cluster.assert_called_once()
    mock_console.print.assert_any_call("🚀 Welcome to lazy-ecs!", style="bold cyan")
    mock_console.print.assert_any_call("\n✅ Selected cluster: production", style="green")


@patch("lazy_ecs.boto3.client")
@patch("lazy_ecs.ECSNavigator")
@patch("lazy_ecs.console")
def test_main_no_cluster_selected(mock_console, mock_navigator_class, _mock_boto3_client) -> None:
    """Test main function when no cluster is selected."""
    mock_navigator = Mock()
    mock_navigator.select_cluster.return_value = None
    mock_navigator_class.return_value = mock_navigator

    main()

    mock_console.print.assert_any_call("\n❌ No cluster selected. Goodbye!", style="yellow")


@patch("lazy_ecs.boto3.client")
@patch("lazy_ecs.console")
def test_main_aws_error(mock_console, mock_boto3_client) -> None:
    """Test main function with AWS connection error."""
    mock_boto3_client.side_effect = Exception("No credentials found")

    main()

    mock_console.print.assert_any_call("\n❌ Error: No credentials found", style="red")
    mock_console.print.assert_any_call("Make sure your AWS credentials are configured.", style="dim")
