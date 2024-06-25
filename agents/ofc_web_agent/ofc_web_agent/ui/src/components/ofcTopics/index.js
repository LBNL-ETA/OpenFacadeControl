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
