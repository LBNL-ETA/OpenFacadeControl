
import React, { useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';

const AnalysisLogGridComponent = ({
  analysisRowData
}) => {
  console.log("AnalysisLogGridComponent called with ", AnalysisLogGridComponent);
      
  const formatDate = (params) => {
    if (!params.value) return '';
    // Example format: '2024-04-19 12:27:53'
    return new Date(params.value).toLocaleString();
  };
  
  const [columnDefs] = useState([
    { headerName: "Timestamp", field: "timestamp", sortable: true, filter: true, valueFormatter: formatDate, sort: 'desc', sortIndex: 0  },
    { headerName: "Action", field: "action", sortable: true, filter: true },
    { headerName: "Reason", field: "reason", sortable: true, filter: true }
  ]); // Column definitions
  
  const onGridReady = params => {
    // Use the column API to auto-size all columns
    params.api.autoSizeAllColumns();
  };
  
  return (
    <>
      <style>
        {`
          .ag-theme-alpine-dark .ag-cell {
              color: #ffffff; /* Bright white text for better readability */
          }
        `}
      </style>
      <div className="ag-theme-alpine-dark" style={{ height: '100%', width: '100%', fontFamily: 'Arial, sans-serif', fontWeight: 'bold', fontSize: '18px'}}>
        <AgGridReact
          rowData={analysisRowData}
          columnDefs={columnDefs}
          domLayout='autoHeight'
          onGridReady={onGridReady}
          onFirstDataRendered={onGridReady}
        />
      </div>
    </>
  );
}

export default AnalysisLogGridComponent;
