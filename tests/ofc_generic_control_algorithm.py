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
from unittest.mock import MagicMock, patch
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent
from ofc_generic_control_algorithm import OFCGenericControlAlgorithm, ofc_generic_control_algorithm


@pytest.fixture
def agent():
    """
    Fixture to initialize the OFCGenericControlAlgorithm agent with mock configuration.
    """
    config = {
        "algorithm_params": []
    }
    return OFCGenericControlAlgorithm(config)


def test_agent_initialization(agent):
    """
    Test that the agent initializes with the correct attributes.
    """
    assert isinstance(agent, OFCGenericControlAlgorithm)
    assert agent.config == {"algorithm_params": []}
    assert agent.control_ct == 0
    assert agent.counter == 0
    assert agent.control_inputs == ["Occupancy", "Glare", "Illuminance", "Solar Radiation"]
    assert agent.control_outputs == ["Light", "Façade State"]


def test_configure(agent):
    """
    Test that the agent correctly updates its configuration.
    """
    config_name = "test_config"
    action = "NEW"
    contents = {"algorithm_params": [
        {"Inputs": [{"Type": "Illuminance", "Threshold": 50}], "Outputs": [{"Type": "Light", "Setting": 0.5}]}]}

    agent.configure(config_name, action, contents)

    assert agent.algorithm_params == contents


@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.get_topic_data_from_historian')
def test_get_all_input_data(mock_get_data, agent):
    """
    Test the `get_all_input_data` method to ensure it fetches all data for given inputs.
    """
    mock_get_data.return_value = {"values": [(1, 100)]}

    inputs = {
        "Illuminance": ["topic1"],
        "Glare": ["topic2"]
    }

    result = agent.get_all_input_data(inputs)
    assert result["Illuminance"]["topic1"] == [(1, 100)]
    assert mock_get_data.called


def test_process_input_data(agent):
    """
    Test the `process_input_data` method to ensure it correctly calculates averages.
    """
    input_data = {
        "Illuminance": {"topic1": [(1, 100), (2, 200)]},
        "Glare": {"topic2": [(1, None), (2, 50)]}
    }

    averages = agent.process_input_data(input_data)
    assert averages["Illuminance"] == 150  # Average of 100 and 200
    assert averages["Glare"] == 50  # Single valid value


def test_calculate_state(agent):
    """
    Test the `calculate_state` method to ensure the correct control outputs are calculated.
    """
    agent.algorithm_params = [
        {
            "Inputs": [{"Type": "Illuminance", "Threshold": 50}],
            "Outputs": [{"Type": "Light", "Setting": 0.5}]
        }
    ]

    input_data = {"Illuminance": 100}

    result = agent.calculate_state(input_data)
    assert result["Light"]["value"] == 0.5
    assert result["Light"]["reason"] == "Illuminance: 100 >= 50"


@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.get_all_input_data')
@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.process_input_data')
@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.calculate_state')
@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.vip.pubsub.publish')
@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.vip.rpc.call')
def test_handle_area_control_request(mock_rpc, mock_publish, mock_calculate_state, mock_process_input, mock_get_data,
                                     agent):
    """
    Test the `_handle_area_control_request` method to ensure it processes requests and publishes control messages.
    """
    # Mock return values for the various steps
    mock_get_data.return_value = {"Illuminance": [(1, 100)]}
    mock_process_input.return_value = {"Illuminance": 100}
    mock_calculate_state.return_value = {"Light": {"value": 0.5, "reason": "Illuminance: 100 >= 50"}}

    # Prepare a mock message
    message = {
        "area": "test_area",
        "endpoints": {"Illuminance": ["topic1"]}
    }

    # Call the handler
    agent._handle_area_control_request(None, None, None, "agent/ofc_generic_control_algorithm", None, message)

    # Check that the control logic was executed and messages were published
    mock_get_data.assert_called_once_with({"Illuminance": ["topic1"]})
    mock_publish.assert_called_once()
    mock_rpc.assert_called_once_with(None, "do_control", "test_area", 0.5, 0)


@patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm.get_topic_data_from_historian')
def test_get_topic_data_from_historian(mock_get_data, agent):
    """
    Test the `get_topic_data_from_historian` method to ensure it retrieves historical data.
    """
    mock_get_data.return_value = {"values": [(1, 100), (2, 200)]}

    topic = "test_topic"
    result = agent.get_topic_data_from_historian(topic)

    assert result == {"values": [(1, 100), (2, 200)]}
    mock_get_data.assert_called_once_with('platform.historian', 'query', topic=topic, count=10, order="LAST_TO_FIRST")


def test_main(mocker):
    """
    Test the main entry point to ensure the agent is started correctly.
    """
    mock_vip_main = mocker.patch('ofc_generic_control_algorithm.utils.vip_main')
    mocker.patch('ofc_generic_control_algorithm.OFCGenericControlAlgorithm')

    ofc_generic_control_algorithm(config_path="test_config")
    mock_vip_main.assert_called_once()
