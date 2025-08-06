from setuptools import setup, find_packages

MAIN_MODULE = 'agent'

# Find the agent package that contains the main module
packages = find_packages('.')
agent_package = 'ofc_afc_test_agent'

# Define the agent entry point
entry_point = f'{agent_package}.{MAIN_MODULE}:ofc_afc_test_agent'

setup(
    name=agent_package + 'agent',
    version="0.1",
    author="Lawrence Berkeley National Laboratory",
    author_email="ofc@lbl.gov",
    description="AFC Test Agent for OpenFacadeControl integration",
    install_requires=['volttron', 'pandas', 'numpy'],
    packages=packages,
    entry_points={
        'setuptools.installation': [
            'eggsecutable = ' + entry_point,
        ]
    }
)