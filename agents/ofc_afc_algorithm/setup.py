from setuptools import setup, find_packages

MAIN_MODULE = 'agent'

# Find the agent package that contains the main module
packages = find_packages('.')
agent_package = 'ofc_afc_algorithm'

# Define the agent entry point
entry_point = f'{agent_package}.{MAIN_MODULE}:ofc_afc_algorithm'

setup(
    name=agent_package + 'agent',
    version="0.2",
    author="Lawrence Berkeley National Laboratory",
    author_email="ofc@lbl.gov",
    description="Advanced Facade Controller (AFC) Algorithm Agent for OpenFacadeControl",
    long_description="""
    Production-ready AFC integration agent that provides Model Predictive Control (MPC)
    optimization for facade and HVAC systems. Features include:
    
    - Weather forecast integration
    - Advanced daylighting and glare analysis  
    - Multi-objective optimization (energy, comfort, cost)
    - Fallback to heuristic control
    - Real-time performance monitoring
    - Device-specific control strategies
    - Building template system
    """,
    install_requires=[
        'volttron>=8.0',
        'pandas>=1.3.0',
        'numpy>=1.20.0',
        'requests>=2.25.0'
    ],
    extras_require={
        'afc': [
            'afc>=1.5.0',
            'doper',
            'frads',
            'pyomo>=6.0',
            'matplotlib>=3.3.0'
        ],
        'weather': [
            'requests>=2.25.0',
            'pvlib>=0.9.0'
        ]
    },
    packages=packages,
    include_package_data=True,
    package_data={
        agent_package: [
            'config/*.config',
            'config/building_templates/*.json'
        ]
    },
    entry_points={
        'setuptools.installation': [
            'eggsecutable = ' + entry_point,
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering",
        "Topic :: Home Automation",
    ],
    python_requires='>=3.8',
)