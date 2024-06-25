function getData() {
    return {
        "LBNL/71T/A/cree_light": 
        {
            "value": [
                ["2023-10-26T21:48:50.002172+00:00", 0.14723411487508964],
                ["2023-10-26T21:49:00.001522+00:00", 0.14723411487508964],
                ["2023-10-26T21:49:10.002022+00:00", 0.14723411487508964],
                ["2023-10-26T21:49:20.001373+00:00", 0.5576705599270217],
                ["2023-10-26T21:49:30.005696+00:00", 0.5576705599270217],
                ["2023-10-26T21:49:40.004001+00:00", 0.5576705599270217],
                ["2023-10-26T21:49:50.003601+00:00", 0.5286022722313601],
                ["2023-10-26T21:50:00.008166+00:00", 0.5286022722313601]
            ],
            "metadata": {
                "units": "%", 
                "type": "float", 
                "tz": "US/Pacific"
            }
        }
    };
};

export function getVOLTTRONData() {
// make GET request
    const response = fetch('/vui/platforms/volttron1/historians/sqlhistorianagent-4.0.0_1/topics/LBNL/71T/A/cree_light/light%20level?count=20&order=LAST_TO_FIRST');  
    console.log(response);
    const json = response.json();
    console.log(json);
    const formatted = formatVOLTTRONData(json);
}

export function formatVOLTTRONData(data) {
    //data = getData();
    const lightData = data["LBNL/71T/A/cree_light/light level"]["value"];
    console.log(lightData);
    return lightData.map(item => {
      return {
        timestamp: new Date(item[0]),
        value: parseFloat(item[1])
      };
    });
  }
  
