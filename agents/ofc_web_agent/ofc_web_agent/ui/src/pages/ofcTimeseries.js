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
