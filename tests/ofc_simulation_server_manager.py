# *** Copyright Notice ***
# 
# OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
# of California, through Lawrence Berkeley National Laboratory (subject to receipt
# of any required approvals from the U.S. Dept. of Energy). All rights reserved.
# 
# If you have questions about your rights to use or distribute this software,
# please contact Berkeley Lab's Intellectual Property Office at
# IPO@lbl.gov.
# 
# NOTICE.  This Software was developed under funding from the U.S. Department
# of Energy and the U.S. Government consequently retains certain rights.  As
# such, the U.S. Government has been granted for itself and others acting on
# its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
# Software to reproduce, distribute copies to the public, prepare derivative 
# works, and perform publicly and display publicly, and to permit others to do so.

import pytest
from unittest.mock import patch, MagicMock
from ofc_simulation_server_manager import OFCSimulationServerManager, create_read_only_server, create_read_write_server

@pytest.fixture
def agent():
    """
    Fixture to initialize the OFCSimulationServerManager agent with mock configuration.
    """
    config = {}
    return OFCSimulationServerManager(config)


def test_agent_initialization(agent):
    """
    Test that the agent initializes with the correct attributes.
    """
    assert isinstance(agent, OFCSimulationServerManager)
    assert agent.config == {}
    assert agent.server_threads == {}


@patch('ofc_simulation_server_manager.create_server_in_thread')
def test_add_server(mock_create_server, agent):
    """
    Test the `add_server` method to ensure a server is added correctly and started.
    """
    mock_thread = MagicMock()
    mock_create_server.return_value = mock_thread

    config_name = "test_server"
    contents = {
        "type": "Light",
        "port": 5000,
        "endpoint": "/test",
        "value_field": "light_level"
    }

    agent.add_server(config_name, action="NEW", contents=contents)

    assert config_name in agent.server_threads
    mock_create_server.assert_called_once_with(endpoint="/test", port=5000, api_key=None, server_type="Light", value_field="light_level", simulated_values=None)
    mock_thread.start.assert_called_once()


@patch('ofc_simulation_server_manager.create_server_in_thread')
def test_add_server_existing(mock_create_server, agent):
    """
    Test the `add_server` method to ensure that existing servers are stopped before adding a new one.
    """
    mock_thread = MagicMock()
    mock_create_server.return_value = mock_thread

    # Add an existing server
    existing_server = MagicMock()
    agent.server_threads["test_server"] = existing_server

    contents = {
        "type": "Light",
        "port": 5000,
        "endpoint": "/test",
        "value_field": "light_level"
    }

    agent.add_server("test_server", action="NEW", contents=contents)

    # Ensure the existing server was stopped
    existing_server.stop.assert_called_once()

    # Ensure the new server was created and started
    mock_create_server.assert_called_once_with(endpoint="/test", port=5000, api_key=None, server_type="Light", value_field="light_level", simulated_values=None)
    mock_thread.start.assert_called_once()


def test_remove_server(agent):
    """
    Test the `remove_server` method to ensure a server is removed and stopped.
    """
    # Add an existing server
    existing_server = MagicMock()
    agent.server_threads["test_server"] = existing_server

    agent.remove_server("test_server", action="DELETE", contents={})

    # Ensure the server was stopped and removed from the thread dictionary
    existing_server.stop.assert_called_once()
    assert "test_server" not in agent.server_threads


@patch('ofc_simulation_server_manager.OFCSimulationServerManager.fetch_config')
def test_fetch_all_configs(mock_fetch_config, agent):
    """
    Test the `fetch_all_configs` method to ensure it fetches all configurations correctly.
    """
    mock_fetch_config.return_value = {"config_data": "test"}

    mock_rpc = MagicMock()
    mock_rpc.call.return_value.get.return_value = ["config_1", "config_2"]

    agent.vip = MagicMock()
    agent.vip.rpc = mock_rpc

    result = agent.fetch_all_configs()

    assert "config_1" in result
    assert "config_2" in result
    mock_fetch_config.assert_any_call("config_1")
    mock_fetch_config.assert_any_call("config_2")


@patch('ofc_simulation_server_manager.OFCSimulationServerManager.fetch_config')
def test_fetch_config(mock_fetch_config, agent):
    """
    Test the `fetch_config` method to ensure it correctly retrieves a configuration by name.
    """
    mock_rpc = MagicMock()
    mock_rpc.call.return_value.get.return_value = {"config_data": "test"}

    agent.vip = MagicMock()
    agent.vip.rpc = mock_rpc

    config_name = "test_config"
    result = agent.fetch_config(config_name)

    assert result == {"config_data": "test"}
    mock_rpc.call.assert_called_once_with('config.store', 'manage_get', agent.core.identity, config_name)


@patch('ofc_simulation_server_manager.OFCSimulationServerManager.add_server')
@patch('ofc_simulation_server_manager.OFCSimulationServerManager.remove_server')
def test_configure_add_server(mock_remove_server, mock_add_server, agent):
    """
    Test the `configure` method to ensure that a server is added on configuration updates.
    """
    config_name = "test_server"
    action = "NEW"
    contents = {"type": "Light", "port": 5000, "endpoint": "/test"}

    agent.configure(config_name, action, contents)

    mock_add_server.assert_called_once_with(config_name, action, contents)
    mock_remove_server.assert_not_called()


def test_stop_server(agent):
    """
    Test the `stop_server` method to ensure a server is stopped by name.
    """
    mock_server = MagicMock()
    agent.server_threads["test_server"] = mock_server

    agent.stop_server("test_server")

    mock_server.stop.assert_called_once()


def test_reset_server(agent, mocker):
    """
    Test the `reset_server` method to ensure the server is reset with the updated configuration.
    """
    mock_configure = mocker.patch.object(agent, "configure")

    mock_config = {"type": "Light", "port": 5000}
    agent.vip.config.get.return_value = mock_config

    agent.reset_server("test_server")

    agent.vip.config.get.assert_called_once_with(config_name="test_server")
    mock_configure.assert_called_once_with("test_server", "UPDATE", mock_config)


def test_main(mocker):
    """
    Test the main entry point to ensure the agent is started correctly.
    """
    mock_vip_main = mocker.patch('ofc_simulation_server_manager.utils.vip_main')
    mocker.patch('ofc_simulation_server_manager.OFCSimulationServerManager')

    ofc_simulation_server_manager(config_path="test_config")
    mock_vip_main.assert_called_once()
