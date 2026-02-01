const TimeTracker = require('../src/tracker');
const fs = require('fs');
const path = require('path');

const testDataDir = path.join(__dirname, '../data/test');

function runTests() {
  console.log('🧪 Running Time Tracker Tests...\n');
  
  let passedTests = 0;
  let failedTests = 0;

  function test(name, fn) {
    try {
      fn();
      console.log(`✅ ${name}`);
      passedTests++;
    } catch (error) {
      console.log(`❌ ${name}`);
      console.log(`   Error: ${error.message}`);
      failedTests++;
    }
  }

  function assert(condition, message) {
    if (!condition) {
      throw new Error(message || 'Assertion failed');
    }
  }

  // Clean up test data directory before tests
  if (fs.existsSync(testDataDir)) {
    fs.rmSync(testDataDir, { recursive: true });
  }

  // Test 1: Tracker initialization
  test('Tracker should initialize correctly', () => {
    const tracker = new TimeTracker(testDataDir);
    assert(fs.existsSync(testDataDir), 'Data directory should be created');
    assert(fs.existsSync(path.join(testDataDir, 'activities.json')), 'Data file should be created');
  });

  // Test 2: Start tracking
  test('Should start tracking session', () => {
    const tracker = new TimeTracker(testDataDir);
    const result = tracker.start();
    assert(result.success === true, 'Start should return success');
    assert(result.sessionId, 'Should return session ID');
    tracker.stop();
  });

  // Test 3: Prevent double start
  test('Should not allow starting twice', () => {
    const tracker = new TimeTracker(testDataDir);
    tracker.start();
    const result = tracker.start();
    assert(result.success === false, 'Second start should fail');
    tracker.stop();
  });

  // Test 4: Status when active
  test('Should show active status when tracking', () => {
    const tracker = new TimeTracker(testDataDir);
    tracker.start();
    const status = tracker.status();
    assert(status.active === true, 'Status should be active');
    assert(status.sessionId, 'Should have session ID');
    tracker.stop();
  });

  // Test 5: Status when inactive
  test('Should show inactive status when not tracking', () => {
    const tracker = new TimeTracker(testDataDir);
    const status = tracker.status();
    assert(status.active === false, 'Status should be inactive');
  });

  // Test 6: Stop tracking
  test('Should stop tracking session', () => {
    const tracker = new TimeTracker(testDataDir);
    tracker.start();
    const result = tracker.stop();
    assert(result.success === true, 'Stop should return success');
    assert(result.sessionId, 'Should return session ID');
  });

  // Test 7: Categorization
  test('Should categorize applications correctly', () => {
    const tracker = new TimeTracker(testDataDir);
    assert(tracker.categorizeActivity('Slack') === 'Communication', 'Slack should be Communication');
    assert(tracker.categorizeActivity('Visual Studio Code') === 'Development', 'VS Code should be Development');
    assert(tracker.categorizeActivity('Chrome') === 'Browser', 'Chrome should be Browser');
    assert(tracker.categorizeActivity('Unknown App') === 'Other', 'Unknown should be Other');
  });

  // Test 8: Data persistence
  test('Should persist session data', () => {
    const tracker = new TimeTracker(testDataDir);
    tracker.start();
    tracker.stop();
    const data = tracker.loadData();
    assert(data.sessions.length > 0, 'Should have saved sessions');
  });

  // Test 9: Report generation
  test('Should generate reports', () => {
    const tracker = new TimeTracker(testDataDir);
    const report = tracker.generateReport('all');
    assert(report !== null, 'Report should not be null');
    assert(report.categories !== undefined, 'Report should have categories');
    assert(report.topApplications !== undefined, 'Report should have top applications');
  });

  // Test 10: Export data as JSON
  test('Should export data as JSON', () => {
    const tracker = new TimeTracker(testDataDir);
    const json = tracker.exportData('json');
    assert(json !== null, 'JSON export should not be null');
    const parsed = JSON.parse(json);
    assert(parsed.sessions !== undefined, 'JSON should have sessions');
  });

  // Test 11: Export data as CSV
  test('Should export data as CSV', () => {
    const tracker = new TimeTracker(testDataDir);
    const csv = tracker.exportData('csv');
    assert(csv !== null, 'CSV export should not be null');
    assert(csv.includes('Timestamp'), 'CSV should have header');
  });

  // Test 12: Clear data
  test('Should clear all data', () => {
    const tracker = new TimeTracker(testDataDir);
    const result = tracker.clearData();
    assert(result.success === true, 'Clear should return success');
    const data = tracker.loadData();
    assert(data.sessions.length === 0, 'Sessions should be empty');
    assert(data.activities.length === 0, 'Activities should be empty');
  });

  // Summary
  console.log('\n' + '═'.repeat(50));
  console.log(`Tests completed: ${passedTests + failedTests}`);
  console.log(`✅ Passed: ${passedTests}`);
  console.log(`❌ Failed: ${failedTests}`);
  
  // Clean up test data directory after tests
  if (fs.existsSync(testDataDir)) {
    fs.rmSync(testDataDir, { recursive: true });
  }

  return failedTests === 0;
}

const success = runTests();
process.exit(success ? 0 : 1);
