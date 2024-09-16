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
import { AgChartsReact } from 'ag-charts-react';


const TimeseriesChartComponent = ({selectedTopic}) => {
  console.log("TimeseriesChartComponent Start");
  const [chartOptions, setChartOptions] = useState({
    series: [],
  });
  
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  
  const [topicData, setTopicData] = useState(null);
  
    // Function to fetch data from the REST endpoint
  const fetchData = async () => {
    try {      
      console.log("Trying to graph topic: " + selectedTopic);
      const cleanedTopic = selectedTopic.startsWith('/') ? selectedTopic.slice(1) : selectedTopic;
      console.log("cleanedTopic: " + cleanedTopic);
      const encodedTopic = encodeURIComponent(cleanedTopic);
      console.log("Encoded topic: " + encodedTopic);
      const params = new URLSearchParams();
      params.append("order", "LAST_TO_FIRST");
      params.append("count", "50");
      if (startTime) params.append('start', startTime);
      if (endTime) params.append('end', endTime);
      
      
      const topicUrl = '/vui/platforms/volttron1/historians/platform.historian/topics/' + encodedTopic;
      console.log(topicUrl);
      const topicUrlComplete = topicUrl + "?" + params.toString();

      console.log("topicUrlComplete: " + topicUrlComplete);
      const response = await fetch(topicUrlComplete);
      console.log("res[pmse: " + JSON.stringify(response));
      if (!response.ok) {
         throw new Error('Network response was not ok');
      }

      const jsonData = await response.json();
      console.log("jsonData: " + jsonData);
      const apiData = jsonData[cleanedTopic];      
      console.log("apiData: " + apiData);
      const seriesData = apiData.value.reverse().map(([timestamp, value]) => ({
        timestamp: new Date(timestamp),
        value,
        }));
      console.log("seriesData: " + seriesData);
      
      const titleFields = apiData.route.split('/');
      const titleText = titleFields[titleFields.length - 1];
      
      setChartOptions({
                data: seriesData,
                title: {
                    text: titleText,
                    fontSize: 18, // Example title font size, adjust as needed
                    color: '#FFFFFF', // Title color
                },
                series: [
                    {
                        xKey: 'timestamp',
                        yKey: 'value',
                        type: 'line',
                        stroke: '#1E88E5', // Line color, adjust as needed
                        marker: {
                            fill: '#1E88E5', // Marker color, adjust as needed
                            stroke: '#1E88E5', // Marker outline color, adjust as needed
                        },
                    },
                ],
                axes: [
                    {
                        type: 'time',
                        position: 'bottom',
                        //tick: { count: agCharts.time.second.every(10) },
                        title: { text: 'Time', color: '#FFFFFF' }, // Axis title color
                        label: { color: '#FFFFFF' }, // Axis label color
                    },
                    {
                        type: 'number',
                        position: 'left',
                        title: { text: apiData.metadata.units, color: '#FFFFFF' }, // Axis title color
                        label: { color: '#FFFFFF' }, // Axis label color
                    },
                ],
                background: {
                    fill: '#0A0A0A', // Chart background color
                },
                legend: {
                    enabled: false, // Disable legend or set to true if you need it
                },
            });      
    } 
    catch (error) {
      console.error('Error fetching data:', error);
    }
  };
  
  fetchData();
    
  return (
    <div style={{ flex: 1, padding: '20px', height: '80vh', backgroundColor: '#0A0A0A' }}>
      {selectedTopic && (
        <div style={{ height: '100%' }}>
          <form onSubmit={e => {
                e.preventDefault();
                fetchData();
            }}>
                <label>
                    Start Time:
                    <input
                        type="datetime-local"
                        value={startTime}
                        onChange={e => setStartTime(e.target.value)}
                        style={{
                            backgroundColor: '#2C2C2C',
                            color: '#FFFFFF',
                            border: 'none',
                            padding: '5px',
                            borderRadius: '4px',
                            // ...other styles
                          }}
                    />
                </label>
                <label>
                    End Time:
                    <input
                        type="datetime-local"
                        value={endTime}
                        onChange={e => setEndTime(e.target.value)}
                    />
                </label>
                <button 
                  type="submit"
                  style={{
                      backgroundColor: '#1E88E5',
                      color: '#FFFFFF',
                      border: 'none',
                      padding: '5px 10px',
                      borderRadius: '4px',
                      // ...other styles
                    }}
                  >
                  Load Data
                </button>
            </form>
          <AgChartsReact options={chartOptions} theme="ag-default-dark" />
        </div>
      )}
    </div>
  );
};

export default TimeseriesChartComponent;
