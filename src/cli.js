#!/usr/bin/env node

const TimeTracker = require('./tracker');
const path = require('path');

const tracker = new TimeTracker();

function printHelp() {
  console.log(`
Time Visibility Tracker - Make invisible work time visible

Usage:
  tvt start              Start tracking time
  tvt stop               Stop tracking time
  tvt status             Show current tracking status
  tvt report [period]    Generate report (today|week|month|all)
  tvt export [format]    Export data (json|csv)
  tvt clear              Clear all tracking data
  tvt help               Show this help message

Examples:
  tvt start              # Start tracking your activity
  tvt status             # Check if tracking is active
  tvt report week        # See your activity for the past week
  tvt export csv         # Export all data as CSV
  `);
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  }
  return `${mins}m`;
}

function printReport(report) {
  console.log(`\n📊 Time Visibility Report - ${report.period.toUpperCase()}`);
  console.log('═'.repeat(50));
  console.log(`Total tracked time: ${formatDuration(report.totalMinutes)}`);
  console.log(`Sessions: ${report.sessionsCount}\n`);
  
  if (report.categories.length > 0) {
    console.log('⏱️  Time by Category:');
    report.categories.forEach(({ category, minutes }) => {
      const percentage = ((minutes / report.totalMinutes) * 100).toFixed(1);
      const bar = '█'.repeat(Math.round(percentage / 2));
      console.log(`  ${category.padEnd(20)} ${formatDuration(minutes).padEnd(10)} ${bar} ${percentage}%`);
    });
  }
  
  if (report.topApplications.length > 0) {
    console.log('\n🔝 Top Applications:');
    report.topApplications.forEach(({ application, minutes }, index) => {
      console.log(`  ${(index + 1).toString().padStart(2)}. ${application.padEnd(30)} ${formatDuration(minutes)}`);
    });
  }
  
  console.log('');
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'help';

  switch (command) {
    case 'start':
      const startResult = tracker.start();
      if (startResult.success) {
        console.log('✅ ' + startResult.message);
        console.log(`Session ID: ${startResult.sessionId}`);
        console.log('Activity will be checked every minute.');
      } else {
        console.log('❌ ' + startResult.message);
      }
      break;

    case 'stop':
      const stopResult = tracker.stop();
      if (stopResult.success) {
        console.log('✅ ' + stopResult.message);
        console.log(`Session ID: ${stopResult.sessionId}`);
        console.log(`Duration: ${formatDuration(stopResult.duration)}`);
      } else {
        console.log('❌ ' + stopResult.message);
      }
      break;

    case 'status':
      const status = tracker.status();
      if (status.active) {
        console.log('✅ Tracking is ACTIVE');
        console.log(`Session ID: ${status.sessionId}`);
        console.log(`Started: ${new Date(status.startTime).toLocaleString()}`);
        console.log(`Duration: ${formatDuration(status.duration)}`);
        console.log(`Activities logged: ${status.activitiesLogged}`);
      } else {
        console.log('⏸️  Tracking is NOT active');
        console.log('Run "tvt start" to begin tracking.');
      }
      break;

    case 'report':
      const period = args[1] || 'today';
      const report = tracker.generateReport(period);
      printReport(report);
      break;

    case 'export':
      const format = args[1] || 'json';
      const data = tracker.exportData(format);
      if (data) {
        const filename = `time-tracker-export-${Date.now()}.${format}`;
        const fs = require('fs');
        const exportPath = path.join(process.cwd(), filename);
        fs.writeFileSync(exportPath, data);
        console.log(`✅ Data exported to: ${exportPath}`);
      } else {
        console.log('❌ Invalid export format. Use: json or csv');
      }
      break;

    case 'clear':
      const clearResult = tracker.clearData();
      console.log('✅ ' + clearResult.message);
      break;

    case 'help':
    default:
      printHelp();
      break;
  }
}

main().catch(error => {
  console.error('Error:', error.message);
  process.exit(1);
});
