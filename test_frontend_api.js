/**
 * Test script to simulate frontend CSV upload
 */
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const fetch = require('node-fetch');

async function testCSVUpload() {
  console.log('Starting frontend simulation test');
  
  // Path to test CSV file
  const csvFilePath = path.join(__dirname, 'backend', 'test_data.csv');
  
  // Check if file exists
  if (!fs.existsSync(csvFilePath)) {
    console.error(`Test file not found: ${csvFilePath}`);
    return;
  }
  
  console.log(`Using test file: ${csvFilePath}`);
  console.log(`File size: ${fs.statSync(csvFilePath).size} bytes`);
  
  // Create form data similar to frontend upload
  const form = new FormData();
  form.append('file', fs.createReadStream(csvFilePath));
  
  try {
    console.log('Sending upload request...');
    const response = await fetch('http://localhost:8001/api/transformer-sentiment/upload', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Origin': 'http://localhost:5173'
      },
      body: form,
    });
    
    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }
    
    console.log('Upload successful!');
    console.log(`Response status: ${response.status}`);
    
    const data = await response.json();
    console.log('\nAnalysis Results:');
    console.log(`Total rows: ${data.total_rows}`);
    console.log(`Analyzed column: ${data.analyzed_column}`);
    console.log(`Results count: ${data.results.length}`);
    
    // Print individual results
    console.log('\nSentiment Analysis Results:');
    data.results.forEach((result, index) => {
      console.log(`Row ${index + 1}: ${result.sentiment} (${result.score}%)`);
    });
    
    // Print summary
    console.log('\nSummary:');
    console.log(`Positive: ${data.summary.positive}`);
    console.log(`Negative: ${data.summary.negative}`);
    console.log(`Neutral: ${data.summary.neutral}`);
    console.log(`Total: ${data.summary.total}`);
    
    console.log('\nTest completed successfully!');
  } catch (error) {
    console.error('Error during test:', error.message);
  }
}

testCSVUpload().catch(console.error); 