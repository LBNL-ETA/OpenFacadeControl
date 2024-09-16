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
