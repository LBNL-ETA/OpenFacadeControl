import pytest
from unittest.mock import patch, MagicMock
from volttron.platform.vip.agent import Agent
from ofc_web_agent import OFCWebAgent


@pytest.fixture
def agent():
    """
    Fixture to initialize the OFCWebAgent agent with mock configuration.
    """
    config = {}
    return OFCWebAgent(config_path="test_config")


def test_agent_initialization(agent):
    """
    Test that the agent initializes with the correct attributes.
    """
    assert isinstance(agent, OFCWebAgent)
    assert agent.vip is not None  # Check if the agent is initialized with the VIP interface


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_onstart(mock_vip, agent):
    """
    Test the `onstart` method to ensure that the web interface is registered.
    """
    agent.onstart(sender=None)
    mock_vip.web.register_path.assert_called_once_with("/ofc_ui", agent.WEBROOT)


def test_hello(agent):
    """
    Test the `hello` RPC method to ensure it returns the correct greeting.
    """
    result = agent.hello()
    assert result == "hello"


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_controller_endpoint(mock_vip, agent):
    """
    Test the `controller_endpoint` method to ensure it returns controller data.
    """
    mock_vip.rpc.call.return_value.get.return_value = {"key": "value"}

    result = agent.controller_endpoint(env={}, data={})
    mock_vip.rpc.call.assert_called_once_with('ofs.area_controller', 'endpoints')
    assert result['result'] == {"key": "value"}


@patch('ofc_web_agent.OFCWebAgent.get_ofc_agents')
def test_areas_no_path(mock_get_ofc_agents, agent):
    """
    Test the `areas` RPC method when no path is provided to ensure it returns area configurations.
    """
    mock_get_ofc_agents.return_value = ["ofc.controller.area1", "ofc.controller.area2"]

    agent.config_files = MagicMock(return_value={"Area": "Area 1"})
    result = agent.areas()

    assert result == ["Area 1", "Area 1"]
    agent.config_files.assert_called()


@patch('ofc_web_agent.os.path.join')
@patch('ofc_web_agent.json.load')
def test_areas_schema(mock_json_load, mock_path_join, agent):
    """
    Test the `areas` RPC method when the path is "schema" to ensure the schema is returned.
    """
    mock_json_load.return_value = {"schema": "data"}

    result = agent.areas(path="schema")
    assert result == {"schema": "data"}


@patch('ofc_web_agent.OFCWebAgent.config_files')
def test_areas_with_path(mock_config_files, agent):
    """
    Test the `areas` RPC method when a valid path is provided to ensure it returns configuration data.
    """
    mock_config_files.return_value = {"Area": "Test Area"}
    result = agent.areas(path="some_path")
    assert result == {"Area": "Test Area"}


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_get_ofc_agents(mock_vip, agent):
    """
    Test the `get_ofc_agents` method to ensure it retrieves a list of OFC agents.
    """
    mock_vip.rpc.call.return_value.get.return_value = [
        {"identity": "ofc.controller.test1"},
        {"identity": "ofc.test2"},
    ]

    result = agent.get_ofc_agents()
    assert result == ["ofc.controller.test1", "ofc.test2"]


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_topics_endpoint(mock_vip, agent):
    """
    Test the `topics_endpoint` method to ensure it retrieves a list of topics.
    """
    mock_vip.rpc.call.return_value.get.return_value = ["ofc_analysis/some_topic", "some_other_topic"]

    result = agent.topics_endpoint()
    assert result == ["some_other_topic"]


@patch('ofc_web_agent.OFCWebAgent.get_topic_data_from_historian')
def test_algorithm_output_topics_endpoint(mock_get_topic_data, agent):
    """
    Test the `algorithm_output_topics_endpoint` method to ensure it retrieves algorithm output topics.
    """
    mock_get_topic_data.side_effect = [
        {"values": [(1, "action_value")]},
        {"values": [(1, "reason_value")]}
    ]

    result = agent.algorithm_output_topics_endpoint(path="/ofc_analysis/some_path")

    assert result == [{"timestamp": 1, "action": "action_value", "reason": "reason_value"}]


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_config_files_no_path(mock_vip, agent):
    """
    Test the `config_files` method when no path is provided to ensure it retrieves a list of configurations.
    """
    mock_vip.rpc.call.return_value.get.return_value = ["devices/device1", "devices/device2"]

    result = agent.config_files()
    assert result == ["devices/device1", "devices/device2"]
    mock_vip.rpc.call.assert_called_once_with('config.store', 'manage_list_configs', "platform.driver")


@patch('ofc_web_agent.os.path.join')
@patch('ofc_web_agent.json.load')
def test_config_files_schema(mock_json_load, mock_path_join, agent):
    """
    Test the `config_files` method when the path is "schema" to ensure the correct schema is returned.
    """
    mock_json_load.return_value = {"schema": "test_schema"}

    result = agent.config_files(path="schema")
    assert result == {"schema": "test_schema"}


@patch('ofc_web_agent.OFCWebAgent.vip')
def test_config_files_with_path(mock_vip, agent):
    """
    Test the `config_files` method when a valid path is provided to ensure it returns the correct configuration data.
    """
    mock_vip.rpc.call.return_value.get.return_value = json.dumps({"key": "value"})

    result = agent.config_files(path="some_path")
    assert result == {"key": "value"}
    mock_vip.rpc.call.assert_called_once_with('config.store', 'manage_get', "platform.driver", "some_path")


def test_main(mocker):
    """
    Test the main entry point to ensure the agent is started correctly.
    """
    mock_vip_main = mocker.patch('ofc_web_agent.utils.vip_main')
    mocker.patch('ofc_web_agent.OFCWebAgent')

    # Call the main function
    from ofc_web_agent import main
    main()

    mock_vip_main.assert_called_once()
