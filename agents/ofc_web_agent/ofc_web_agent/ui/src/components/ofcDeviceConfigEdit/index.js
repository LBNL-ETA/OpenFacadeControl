import React, { useState, useEffect } from 'react';
import Form from "react-jsonschema-form"

const OFCDeviceConfigEditor = () => {
  const [schema, setSchema] = useState({});
  const [formData, setFormData] = useState({});
  const [dropdownData, setDropdownData] = useState([]);
  const [selectedOption, setSelectedOption] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch JSON schema from my_endpoint_1
    const fetchSchema = async () => {
      try {
        console.log('/ofc/api/v1/schemas?id=ofc_component_schema.json');
        const response = await fetch('/ofc/api/v1/schemas?id=ofc_component_schema.json');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const jsonSchema = await response.json();
        console.log(jsonSchema);
        setSchema(jsonSchema);
      } catch (error) {
        setError('Error fetching JSON schema:', error.message);
      }
    };
    
    const fetchOptions = async () => {
      try {
        console.log('/ofc/api/v1/config_files');
        const response = await fetch('/ofc/api/v1/config_files');        
        console.log(response);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        
        const result = await response.json();
        console.log(result);
        const configFileList = result.result;
        console.log(configFileList);
        setDropdownData(configFileList);
      } catch (error) {
        setError('Error fetching options for listbox:', error.message);
      }
    };

    // Fetch initial schema
    fetchSchema();
    fetchOptions();
  }, []);


  const onSubmit = ({ formData }) => {
    // Handle form submission
    console.log('Form data submitted:', formData);
  };

  const handleListboxChange = (event) => {
    console.log('handleListboxChange');
    console.log(event);
    setSelectedOption(event.target.value);

    // Fetch data based on the selected option from my_endpoint_2
    const fetchData = async () => {
      try {
        console.log(event.target.value);
        const lastSegment = event.target.value.split('/').pop();
        console.log(lastSegment);
      	const url = '/ofc/api/v1/config_files?id=' + lastSegment;
      	console.log(url);
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const jsonData = await response.json();
        console.log(jsonData);
        setFormData(jsonData);
      } catch (error) {
        setError('Error fetching data for form:', error.message);
      }
    };

    // Fetch data based on the selected option
    fetchData();
  };

/*
  return (
    <div>
      {error && <p>{error}</p>}
      {Object.keys(schema).length > 0 && (
        <>
          <label>Select an option:</label>
          <select value={selectedOption} onChange={handleListboxChange}>
            {options.map((option, index) => (
              <option key={index} value={option}>
                {option}
              </option>
            ))}
          </select>
          <Form schema={schema} formData={formData} onSubmit={onSubmit} />
        </>
      )}
    </div>
  );
  */
  
    return (
    <div>
      <select value={selectedOption} onChange={handleListboxChange}>
        {dropdownData.map((item, index) => (
          <option key={index} value={item}>
            {item}
          </option>
        ))}
      </select>
      <Form schema={schema} formData={formData} onSubmit={onSubmit} />
    </div>
  );
};

export default OFCDeviceConfigEditor;

