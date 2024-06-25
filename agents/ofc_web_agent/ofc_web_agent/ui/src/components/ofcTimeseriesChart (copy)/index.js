import React, { useState, useEffect } from 'react';
import { AgChartsReact } from 'ag-charts-react';
import OFCTopicsComponent from '../ofcTopics';

function getTopicUrl(topic) {
  const topicUrl = '/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/' + topic + '?count=20&order=LAST_TO_FIRST';
  topicUrl = encodeURIComponent(topicUrl);
  return topicUrl;
};

const LightLevelChartComponent = ({selectedTopic}) => {
  
  const [chartOptions, setChartOptions] = useState({
    series: [],
  });
  
  const [topicData, setTopicData] = useState(null);
  
  // Function to fetch data from the REST endpoint
  const fetchData = async () => {
    try {
      const encodedTopic = encodeURIComponent(selectedTopic);
      const topicUrl = '/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/' + encodedTopic + '?count=50&order=LAST_TO_FIRST';
      console.log(topicUrl);
      const response = await fetch(topicUrl);
      if (!response.ok) {
         throw new Error('Network response was not ok');
      }

      const jsonData = await response.json();
      const obj = jsonData[selectedTopic];      
      console.log(obj);
      const seriesData = obj.value.reverse().map(([timestamp, value]) => ({
        x: new Date(timestamp),
        y: value,
        }));
      console.log(seriesData);
      const yAxisLabel = obj.metadata.units;
      console.log(yAxisLabel);
//      const newChartData = {'data': seriesData, 'yaxisLabel': yAxisLabel, 'xaxisLabel': 'Time' };
//      console.log(newChartData);
//      setChartData(newChartData);
      
      /*
      setChartOptions({
          data: chartData,
          xAxis: { title: { text: 'Timestamp' } },
          xAxis: { title: { text: yaxisLabel } },
        });
        */
        /*
        setChartOptions({
          data: seriesData,
          xAxis: { title: { text: 'Timestamp' } },
          series: [{ xKey: 'x', yKey: 'y', type: 'line' }],
        });
        */
        setChartOptions({
          series: [
            {
              type: 'line',
              xKey: 'x',
              yKey: 'y',
              title: yAxisLabel,
            },
          ],
          data: seriesData,
          xAxis: {
            type: 'timestamp',
            title: {
              text: 'Timestamp',
            },
          },
          width:800,
          height:600
        });
    } 
    catch (error) {
      console.error('Error fetching data:', error);
    }
  };
    
  /*
  useEffect(() => {    

    // Fetch data initially
    fetchData();

    // Set up interval to fetch data every 5 seconds (adjust as needed)
    const intervalId = setInterval(fetchData, 5000);

    // Cleanup function to clear the interval on component unmount
    return () => clearInterval(intervalId);
  }, []); // Empty dependency array ensures useEffect runs only once on mount
*/

/*
  const fetchData = async () => {
    try {
      console.log({selectedTopic});
      //const response = await axios.get('https://your-api-base-url/my_endpoint');
      const response = await fetch('/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/LBNL/71T/A/cree_light/light%20level?count=20&order=LAST_TO_FIRST');  
      setChartData(response.data);
      renderChart();
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };
*/
/*
  const renderChart = () => {
    if (!chartData) {
      return <p>No data available</p>;
    }

    const options = {
      series: [{
        type: 'line',
        data: {chartData['data']},
      }],
      title: {
        text: {selectedTopic},
      },
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
                format: '#{.2f} {chartData['xaxisLabel']}',
            },
        },
      ]     
    };

    return <AgChartsReact options={options} />;
  };
*/

  return (
    <div>
      <h2>Graph Component</h2>
      {selectedTopic && (
        <div>
          <button onClick={fetchData}>Update Graph</button>
          <AgChartsReact options={chartOptions} theme="ag-default-dark" />
        </div>
      )}
    </div>
  );
};

export default LightLevelChartComponent;
