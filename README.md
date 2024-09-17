*** Copyright Notice ***

OpenFacadeControl (OFC) Copyright (c) 2024, The Regents of the University
of California, through Lawrence Berkeley National Laboratory (subject to receipt
of any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Intellectual Property Office at
IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department
of Energy and the U.S. Government consequently retains certain rights.  As
such, the U.S. Government has been granted for itself and others acting on
its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
Software to reproduce, distribute copies to the public, prepare derivative 
works, and perform publicly and display publicly, and to permit others to do so.

# OpenFacadeControl

## Overview

OpenFacadeControl expands on the VOLTTRON platform to provide a system for monitoring and controlling building states.  OpenFacadeControl provides functionality in several areas that may be used independently or in concert.  They are:
- [Device drivers](#Device-drivers)
- [Area controllers](#Area-controllers)
- [Control algorithms](#Control-algorithms)
- [Device simulators](#Device-simulators)
- [UI](UI)

## Install

OpenFacadeControl was developed against VOLTTRON 8.2.  An install script is forthcoming.

Instructions:

0. For this example it is assumed everything is relative to ~ (home).
1. Clone this repo.  
2. Install the VOLLTRON requirments from https://volttron.readthedocs.io/en/develop/introduction/platform-install.html
3. Clone the 8.2 branch of the VOLTTRON repo by `git  clone  https://github.com/VOLTTRON/volttron  --branch releases/8.2`
4. `cp OpenFacadeControl/device_interface/* volttron/services/core/PlatformDriverAgent/platform_driver/interfaces`
5. `cp OpenFacadeControl/* volttron/OpenFacadeControl`
6. Follow the VOLTTRON install instructions starting from Step 3 https://volttron.readthedocs.io/en/develop/introduction/platform-install.html and say yes to the following when prompted (and any associated "Should the agent autostart" questions):
  - Is this instance web enabled?
  - Will this instance be controlled by volttron central?
  - Would you like to install a platform historian?
  - Would you like to install a platform driver
 7. (Optional) Setup example device driver configs by doing `./OpenFacadeControl/reset-ofc-configs`
 8. (Optional) Setup example simulated device servers by doing `./OpenFacadeControl/simulation/reset-ofc-simulation-server-configs`

## Device drivers

- Cree light
  - [registers](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/cree_light_registers.json)   
  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_71T_A1_cree_light.config)
- Cree occupancy
  - [registers](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/cree_occupancy_registers.json)   
  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_71T_A1_cree_occupancy.config)
- Enlighted facade
  - [registers](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/enlighted_facade_registers.json)   
  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_71T_A1_enlighted_facade.config)
- Enlighted glare
  - [registers](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/enlighted_glare_registers.json)   
  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_71T_A1_enlighted_glare.config)
- Hunter Douglas Illuminance
  - [registers](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/hunter_douglas_illuminance_registers.json)   
  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_71T_A1_hunter_douglas_illuminance.config)

## Area controllers

The area controller agent is responsible for knowing which devices correspond to each area, sending out requests for algorithmic adjustments, and then attempting to actuate the devices to correspond to the desired state.

Each area is defined by configurations beginning with `areas/` in the agent's config store.

  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_area_controller_example.config)

An area's control algorithm can be configured in the area's config file.  The area controller will post a message to the topic defined by the config file.  The contents of the message is the various device types and endpoints in the area.  The control algorithm is responsible for gathering any sensor data it may need from either the historian or anywhere else it may like.  

Once the algorithm has decided the new states for the area it should call the area controller's `do_control` method with the desired values.

## Control algorithms

OpenFacadeControl provides a general purpose configurable control algorithm

  - [example config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/ofc_generic_control_algorithm.config)


## Device simulators

OpenFacadeControl provides basic simulation functionality in the form of simple servers meant to mimic real-world devices.  The ofc_simulation_server_manager agent creates and manages servers based on configurations in its config store that start with`servers/`

- Cree light
  - [example simulation server config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/simulation_server/simulated_Light_server_port_52300_config.json)
- Cree occupancy
  - [example simulation server config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/simulation_server/simulated_Occupancy_server_port_52200_config.json)
- Enlighted facade
  - [example simulation server config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/simulation_server/simulated_Façade_State_server_port_52400_config.json)
- Enlighted glare
  - [example simulation server config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/simulation_server/simulated_Glare_server_port_52000_config.json)
- Hunter Douglas Illuminance
  - [example simulation server config](https://github.com/LBNL-ETA/OpenFacadeControl/blob/main/configs/simulation_server/simulated_Illuminance_server_port_52100_config.json)



## UI

The UI is a basic interface built using react.  Build script to be incorporated with install script forthcoming.

