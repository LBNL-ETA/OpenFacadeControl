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

import React, { useState } from 'react';

function OFCGenericEdit() {
  const [responseText, setResponseText] = useState('');

  const fetchData = () => {
    fetch('https://openfacadecontrol-22:8443/vui/platforms/volttron1/agents/simple_web_agent_id_1/rpc/say_hello', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    })
      .then(response => response.json())
      .then(data => {
        // Set the response text to display in the text box
        setResponseText(JSON.stringify(data, null, 2));
      })
      .catch(error => {
        console.error('Error fetching data:', error);
        setResponseText('Error fetching data. Please check the console.');
      });
  };

  return (
    <div>
      <h1>React POST Request Example</h1>
      <button onClick={fetchData}>Fetch Data</button>
      <br />
      <textarea
        rows={10}
        cols={50}
        value={responseText}
        readOnly
        style={{ marginTop: '10px' }}
      />
    </div>
  );
}

export default OFCGenericEdit;
