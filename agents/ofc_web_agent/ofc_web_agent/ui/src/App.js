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

import 'bootstrap/dist/css/bootstrap.min.css';
import 'ag-grid-community/styles/ag-grid.css'; // Core grid CSS, provides basic styling
import 'ag-grid-community/styles/ag-theme-alpine.css'; // Optional theme CSS


import React, { useState, useEffect } from 'react';
import Form from '@rjsf/bootstrap-4';
import { RJSFSchema } from '@rjsf/utils';
import validator from '@rjsf/validator-ajv8';
import TimeseriesChartComponent from './components/ofcTimeseriesChart';
import AnalysisLogGridComponent from './components/ofcAnalysisLogGrid';
import { parseToTree, TreeNode } from './components/ofcTree';


import './main.css';


const sectionUrls = {
  'Devices': '/vui/platforms/volttron1/agents/ofc_web_agent_id_1/rpc/topics_endpoint',
  'Configuration Files': '/vui/platforms/volttron1/agents/ofc_web_agent_id_1/rpc/config_files',
  'Areas': '/vui/platforms/volttron1/agents/ofc_web_agent_id_1/rpc/areas',
  'Control Algorithms': '/vui/platforms/volttron1/agents/ofc_web_agent_id_1/rpc/control_algorithms',
  'Analysis Log': '/vui/platforms/volttron1/agents/ofc_web_agent_id_1/rpc/algorithm_output_topics_endpoint',
};


const App = () => {
  const [expandedSection, setExpandedSection] = useState({});
  const [sectionData, setSectionData] = useState({});
  const [selectedItem, setSelectedItem] = useState('');
  const [configData, setConfigData] = useState({});
  const [display, setDisplay] = useState('');
  const [schema, setSchema] = useState(null);
  const [volttronConfig, setVolttronConfig] = useState(null);
  const [analysisLogData, setAnalysisLogData] = useState([]);
  
  const getCookie = (name) => {
    const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return cookieValue ? cookieValue.pop() : '';
  };
  
  const doVOLTTRONPostRequest = async (url, body={}) => {
    const token = getCookie('Bearer');
    console.log("Making POST request to:", url);
    console.log("body:", body);
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    if (response.status === 401) {
        alert("Login Required");  // Show an alert if the response is 401 Unauthorized
        throw new Error("401 Unauthorized - Login Required");
    }
    const data = await response.json();
    console.log("VOLTTRON returned:", data);
    return data;
  };

  
  const toggleSection = (section) => {
    setExpandedSection(prev => ({ ...prev, [section]: !prev[section] }));
    if (!sectionData[section]) {
      fetchSectionData(section); // Implement this based on your existing logic
    }
  };
    
  const fetchSectionData = async (section) => {
    if (sectionData[section]) {
      // If data already exists, don't refetch
      return;
    }
    const apiUrl = sectionUrls[section];
    const data = await doVOLTTRONPostRequest(apiUrl);
    const tree = parseToTree(data); // Assuming `data` is suitable for tree parsing for all sections
    setSectionData((prevData) => ({ ...prevData, [section]: tree }));
  };

  const handleItemClick = async (fullPath, section) => {
    try {
      console.log("Item clicked:", fullPath + " section: " + section);
      setSelectedItem(fullPath);
      console.log("calling setDisplay");
      setDisplay(section);
      console.log("finished setDisplay");
      const token = getCookie('Bearer');
      const url = sectionUrls[section];
      
      if (section === 'Analysis Log') {
        console.log("section === Analysis Log");
        const data = await doVOLTTRONPostRequest(url, { "path": fullPath });
        console.log("Calling setAnalysisLogData with ", setAnalysisLogData);
        setAnalysisLogData(data);
   
      } else if (section === 'Configuration Files') {
        const schemaData = await doVOLTTRONPostRequest(url, { "path": "schema" });
        console.log("calling setSchema with:", schemaData);
        setSchema(schemaData);
      
        const data = await doVOLTTRONPostRequest(url, { "path": fullPath });
        console.log("Calling setVolttronConfig with:", data);
        await setVolttronConfig(data);
      }
    } catch (error) {
        console.error("error in handleItemClick:", error);
    }
    
  };
  
    
  const handleSubmit = async (e, formData) => {
    e.preventDefault();
    console.log('Form data submitted:', formData);
    const url = sectionUrls[display];
    const body = {"path": selectedItem, "contents": formData};
    console.log('body:', formData);
    const data = await doVOLTTRONPostRequest(url, body);    
  };
  
    const section_name_clicked = (sectionName) => {
    console.log(`${sectionName} name was clicked`);
    // Add any additional logic for when a section name is clicked
  };


  const renderAnalysisLog = () => {
     const gridStyle = {
        flexGrow: 1, // This will make the chart expand to the available space
        // ... any other style properties you need
      };
    return (
      <div style={gridStyle}>
        <AnalysisLogGridComponent analysisRowData={analysisLogData} />
      </div>
    );
  };
  
  const renderContent = () => {
    console.log("renderContent called");
    if (display === 'Devices' && selectedItem) {
      console.log("display === Devices && selectedItem called");
      const chartStyle = {
        flexGrow: 1, // This will make the chart expand to the available space        
      };

      return (        
        <div style={chartStyle}>
          <TimeseriesChartComponent selectedTopic={selectedItem} />
        </div>
        );
    } else if (display === 'Analysis Log' && selectedItem) {
      console.log("display === Analysis Log && selectedItem called");    
      return renderAnalysisLog();
    } else if (selectedItem && sectionUrls[display] && schema) {
      console.log("selectedItem && sectionUrls[display] && schema");
      console.log("sectionUrls[display]:", sectionUrls[display] );              
      console.log("schema", schema);
      console.log("volttronConfig", volttronConfig);
      console.log("validator", validator);      
      // Assuming configData is the data needed for the ConfigForm
      return (
        <Form 
          schema={ schema } 
          validator={ validator }
          formData={ volttronConfig }          
        />
      );
    } else {
      console.log("renderContent else branch taken");
      return <div>Select an item to view details</div>;
    }
  };
  
  return (
    <div>
      {/* Title of the Application */}
      <header style={{ backgroundColor: '#0A0A0A', color: '#FFFFFF', padding: '10px 20px', fontFamily: 'Arial, sans-serif', fontSize: '24px' }}>
        OpenFaçadeControl
      </header>
    <div style={{ display: 'flex', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ width: '250px', background: '#0A0A0A', padding: '20px', color: '#FFFFFF' }}>
        {Object.keys(sectionUrls).map((section) => (
          <div key={section} style={{ marginBottom: '20px' }}>
            <div
              onClick={() => toggleSection(section)}
              style={{ cursor: 'pointer', fontWeight: 'bold', fontSize: '18px' }}
            >
              {section}
            </div>
            {expandedSection[section] && sectionData[section] && (
              <TreeNode
                node={sectionData[section]}
                name=""
                section={section} // Add this prop to pass the section name
                onNodeClick={handleItemClick}
                isExpanded={expandedSection[section]}
                isSelected={selectedItem.includes(section)}
              />
            )}
          </div>
        ))}
      </div>
      <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column'}}>
        {renderContent()}
      </div>
    </div>
  </div>
  );
};

export default App;

