import { useState } from 'react';
import ReactDOM from 'react-dom/client';
import { AgChartsReact } from 'ag-charts-react';
import { time } from 'ag-charts-community';

import { formatVOLTTRONData, getVOLTTRONData } from './data.js';

function App() {

  const [data, setData] = useState({});

  const handleGet = async () => {
    // make GET request
    const response = await fetch('/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/LBNL/71T/A/cree_light/light%20level?count=20&order=LAST_TO_FIRST');  
    console.log(response);
    const json = await response.json();
    console.log(json);
    const formatted = await formatVOLTTRONData(json);
    setData(formatted);
  }

  const handleSubmit = async () => {
    // make POST request
    const response = await fetch('/my_endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'  
      },
      body: JSON.stringify(data)
    });
  }
  
  // Chart Component
  const ChartExample = () => {
    // Chart Options: Control & configure the chart
    const [chartOptions, setChartOptions] = useState({
      // Data: Data to be displayed in the chart
      data: data,
      // Series: Defines which chart type and data to use
      series: [{ type: 'line', xKey: 'timestamp', yKey: 'value' }],
      axes: [
        {
            type: 'time',
            position: 'bottom',
            nice: false,
            tick: {
                interval: time.second.every(60*2),
            },
            label: {
                format: '%H:%M:%S',
            },
        },
        {
            type: 'number',
            position: 'left',
            label: {
                format: '#{.2f} Lumen',
            },
        },
    ],
    title: {
        text: 'Light Level',
    }
    });

    return (
      // AgCharsReact component with options passed as prop
      <AgChartsReact options={chartOptions} />
    );
  }

  return (
    <div>
      <button onClick={handleGet}>Get Data</button>
      <button onClick={handleSubmit}>Submit</button>

      <form>
        {Object.keys(data).map(key => {
          return (
            <div key={key}>
              <label>{key}</label>
              <input 
                type="text"
                value={data[key]}
                onChange={e => setData({...data, [key]: e.target.value})} 
              />
            </div>
          )
        })}
      </form>
      <ChartExample />
    </div>
  );
}

export default App;
