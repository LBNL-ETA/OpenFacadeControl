import React, { useState } from 'react';

function App() {
  const [responseText, setResponseText] = useState('');
/*
  const [requestData, setRequestData] = useState({
    jsonrpc: '2.0',
    method: 'some_method', // Replace 'some_method' with the actual method name
    params: {}, // Replace {} with the actual parameters object if needed
    id: 1 // Request ID (can be any unique value)
  });
*/
  const fetchData = () => {
    // Retrieve the JWT token from cookies
    const token = getCookie('Bearer');
    console.log("token");
    console.log(token);

    // Make the GET request with the JWT token as a Bearer token
    fetch('/vui/platforms/volttron1/agents/simple_web_agent_id_1/rpc/say_hello', {
      method: 'POST',
      headers: {
       'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({})
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }
        return response.json();
      })
      .then(data => {
        setResponseText(JSON.stringify(data, null, 2));
      })
      .catch(error => {
        console.error('Error fetching data:', error);
        setResponseText('Error fetching data. Please check the console.');
      });
  };

  const getCookie = (name) => {
    const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return cookieValue ? cookieValue.pop() : '';
  };

  return (
    <div>
      <h1>React App with JWT Authentication</h1>
      <button onClick={fetchData}>Fetch Data with JWT</button>
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

export default App;

