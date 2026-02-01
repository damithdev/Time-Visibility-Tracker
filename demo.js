#!/usr/bin/env node

// Demo script to show Time Visibility Tracker in action
const TimeTracker = require('./src/tracker');
const fs = require('fs');
const path = require('path');

const demoDataDir = path.join(__dirname, 'data/demo');
const tracker = new TimeTracker(demoDataDir);

console.log('🎬 Time Visibility Tracker Demo\n');
console.log('═'.repeat(60));

// Create sample data to demonstrate the tool
console.log('\n📝 Creating sample tracking data...\n');

const now = new Date();
const sampleActivities = [];
const sampleSessions = [];

// Create 3 sample sessions over the past week
for (let day = 6; day >= 0; day--) {
  const sessionDate = new Date(now.getTime() - day * 24 * 60 * 60 * 1000);
  sessionDate.setHours(9, 0, 0, 0);
  
  const session = {
    id: `demo-${day}`,
    startTime: sessionDate.toISOString(),
    endTime: new Date(sessionDate.getTime() + 8 * 60 * 60 * 1000).toISOString(),
    activities: []
  };
  
  // Add activities for this session
  const apps = [
    { name: 'Visual Studio Code', category: 'Development', weight: 40 },
    { name: 'Slack', category: 'Communication', weight: 20 },
    { name: 'Chrome', category: 'Browser', weight: 15 },
    { name: 'Microsoft Teams', category: 'Communication', weight: 10 },
    { name: 'Terminal', category: 'Development', weight: 10 },
    { name: 'Notion', category: 'Documentation', weight: 5 }
  ];
  
  // Generate activities (one per minute for 8 hours)
  for (let minute = 0; minute < 480; minute++) {
    const activityTime = new Date(sessionDate.getTime() + minute * 60 * 1000);
    
    // Pick an app based on weights
    const rand = Math.random() * 100;
    let cumulative = 0;
    let selectedApp = apps[0];
    
    for (const app of apps) {
      cumulative += app.weight;
      if (rand < cumulative) {
        selectedApp = app;
        break;
      }
    }
    
    const activity = {
      timestamp: activityTime.toISOString(),
      application: selectedApp.name,
      category: selectedApp.category
    };
    
    sampleActivities.push(activity);
    session.activities.push(activity);
  }
  
  sampleSessions.push(session);
}

// Save sample data
const data = {
  sessions: sampleSessions,
  activities: sampleActivities
};

if (!fs.existsSync(demoDataDir)) {
  fs.mkdirSync(demoDataDir, { recursive: true });
}

fs.writeFileSync(
  path.join(demoDataDir, 'activities.json'),
  JSON.stringify(data, null, 2)
);

console.log(`✅ Created ${sampleSessions.length} sample sessions`);
console.log(`✅ Generated ${sampleActivities.length} sample activities\n`);

// Demonstrate status (not tracking)
console.log('═'.repeat(60));
console.log('\n📊 Command: tvt status (when not tracking)\n');
const status1 = tracker.status();
if (status1.active) {
  console.log('✅ Tracking is ACTIVE');
} else {
  console.log('⏸️  Tracking is NOT active');
  console.log('Run "tvt start" to begin tracking.');
}

// Demonstrate weekly report
console.log('\n═'.repeat(60));
console.log('\n📊 Command: tvt report week\n');
const report = tracker.generateReport('week');

console.log(`📊 Time Visibility Report - ${report.period.toUpperCase()}`);
console.log('═'.repeat(60));
console.log(`Total tracked time: ${Math.floor(report.totalMinutes / 60)}h ${report.totalMinutes % 60}m`);
console.log(`Sessions: ${report.sessionsCount}\n`);

if (report.categories.length > 0) {
  console.log('⏱️  Time by Category:');
  report.categories.forEach(({ category, minutes }) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    const percentage = ((minutes / report.totalMinutes) * 100).toFixed(1);
    const bar = '█'.repeat(Math.round(percentage / 2));
    console.log(`  ${category.padEnd(20)} ${timeStr.padEnd(10)} ${bar} ${percentage}%`);
  });
}

if (report.topApplications.length > 0) {
  console.log('\n🔝 Top Applications:');
  report.topApplications.forEach(({ application, minutes }, index) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    console.log(`  ${(index + 1).toString().padStart(2)}. ${application.padEnd(30)} ${timeStr}`);
  });
}

console.log('\n═'.repeat(60));
console.log('\n✅ Demo completed! The tool is ready to use.\n');

// Clean up demo data
if (fs.existsSync(demoDataDir)) {
  fs.rmSync(demoDataDir, { recursive: true });
  console.log('🧹 Demo data cleaned up.\n');
}
