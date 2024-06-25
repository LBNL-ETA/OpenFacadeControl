import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from "./pages";
import OFCTimeseries from './pages/ofcTimeseries';
import OFCDeviceConfigs from './pages/ofcDeviceConfigs';
import OFCDeviceRegisterConfigs from './pages/ofcDeviceRegisterConfigs';
import OFCAreaControllerConfigs from './pages/ofcAreaControllerConfigs';
import OFCGenericEditPage from './pages/ofcGenericEdit';
//import Navbar from "./components/Navbar";
import Layout from "./pages/Layout";
import NoPage from "./pages/NoPage";

const App = () => {
  return (
    <Router>
      <div>
        <nav>
          <ul>
            <li>
              <Link to="/ofc_ui/ofc_charts">Graphs</Link>
            </li>
            <li>
              <Link to="/ofc_ui/ofc_device_configs">Device Config Files</Link>
            </li>
            <li>
              <Link to="/ofc_ui/ofc_device_register_configs">Device Register Config Files</Link>
            </li>
            <li>
              <Link to="/ofc_ui/ofc_area_controller_configs">Area Controller Config Files</Link>
            </li>
          </ul>
        </nav>
        <Routes>
          <Route path="/ofc_ui/ofc_charts" element={<OFCTimeseries />} />
          <Route path="/ofc_ui/ofc_device_configs" element={<OFCDeviceConfigs />} />
          <Route path="/ofc_ui/ofc_device_register_configs" element={<OFCDeviceRegisterConfigs />} />          
          <Route path="/ofc_ui/ofc_area_controller_configs" element={<OFCAreaControllerConfigs />} />
          <Route path="/ofc_ui/ofc_generic_edit" element={<OFCGenericEditPage />} />                    
        </Routes>
      </div>
    </Router>
  );
};

export default App;
