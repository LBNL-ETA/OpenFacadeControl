/*
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
*/

import React, { useState, useEffect } from 'react';
import LightLevelChartComponent from '../components/ofcTimeseriesChart';
import OFCTopicsComponent from '../components/ofcTopics';

const OFCTimeseries = () => {

  const [selectedTopic, setSelectedTopic] = useState(null);

  const handleSelectionChange = (selectedValue) => {
    setSelectedTopic(selectedValue);
  };
  
  return (
    <div>
      <h1>Test graphing</h1>
      <OFCTopicsComponent onSelectionChange={handleSelectionChange} />
      <LightLevelChartComponent selectedTopic={selectedTopic}/>
    </div>
  );
};

export default OFCTimeseries;


/*
import React, { useState } from 'react';
import { AgChartsReact } from 'ag-charts-react';

const LightLevelChartComponent = () => {
  const [chartData, setChartData] = useState(null);

  const fetchData = async () => {
    try {
      //const response = await axios.get('https://your-api-base-url/my_endpoint');
      const response = await fetch('/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/LBNL/71T/A/cree_light/light%20level?count=20&order=LAST_TO_FIRST');  
      setChartData(response.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const renderChart = () => {
    if (!chartData) {
      return <p>No data available</p>;
    }

    const seriesData = chartData['LBNL/71T/A/cree_light/light level'].value.map(([timestamp, value]) => ({
      x: new Date(timestamp),
      y: value,
    }));

    const options = {
      series: [{
        type: 'line',
        data: seriesData,
      }],
      title: {
        text: 'Light Level',
      },
      // Add more chart configuration options as needed
    };

    return <AgChartsReact options={options} />;
  };

  return (
    <div>
      <button onClick={fetchData}>Fetch Data</button>
      {renderChart()}
    </div>
  );
};

export default LightLevelChartComponent;
*/
