// fetching data from csv file
async function fetchData(csvPath) {
  try {
    const response = await fetch(csvPath);
    if (!response.ok) {
      throw new Error(`Failed to fetch data (status ${response.status})`);
    }
    return response.text();
  } catch (error) {
    console.error("Error fetching data: ", error);
    throw error;
  }
}

async function parseCSV(csvPath) {
  try  {
    const text = await fetchData(csvPath);
    console.log(text);
    return Papa.parse(text, {skipEmptyLines: true});
  } catch (error) {
    console.error("Error parsing CSV: ", error);
    throw error;
  }
}

async function processData(csvPath) {
  try {
    const response = await fetchData(csvPath);
    const data = await parseCSV(csvPath);
    let xData = data.data.map(row => row[0]);
    let yData = data.data.map(row => row[1]);
    return { xData, yData};
  } catch (error) {
    console.error("Error processing data: ", error);
    throw error;
  }
}

async function createChart(csvPath) {
  try {
    const { xData, yData} = await processData(csvPath);

    const data = [{
      x: xData,
      y: yData,
      type: "scatter",
      mode: "lines",
      name: "Data"
    }];
    
    const layout = {
      title: "Pico Onboard Temperature",
      xaxis: {
        title: "Date Time"
      },
      yaxis: {
        title: "Onbaord Temp"
      }
    };

    Plotly.newPlot("chart-container", data, layout)
  } catch (error) {
    console.error("Error creating chart: ", error);
  }
}

const csvPath = "../data/measurements.csv"
createChart(csvPath)
