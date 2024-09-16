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

const OFCTopicsComponent = ({ onSelectionChange }) => {
  const [dropdownData, setDropdownData] = useState([]);
  const [selectedOption, setSelectedOption] = useState('');

  useEffect(() => {
    // Fetch data when the component mounts
    fetchData();
  }, []); // The empty dependency array ensures the effect runs only once on mount

  const fetchData = async () => {
    try {
      const response = await fetch('/ofc/api/v1/historian_topics');
      console.log(response);
      const result = await response.json();
      console.log(result);
      const topicList = result.result;
      console.log(topicList);
      setDropdownData(topicList);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleDropdownChange = (event) => {
    // Update the selected option when the dropdown value changes
    setSelectedOption(event.target.value);
    onSelectionChange(event.target.value);
  };

  return (
    <div>
      <button onClick={fetchData}>Refresh Topics</button>
      <select value={selectedOption} onChange={handleDropdownChange}>
        {dropdownData.map((item, index) => (
          <option key={index} value={item}>
            {item}
          </option>
        ))}
      </select>
    </div>
  );
};

export default OFCTopicsComponent;
