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
