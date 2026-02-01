const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

const CHECK_INTERVAL_MS = 60000; // Check every minute

class TimeTracker {
  constructor(dataDir = path.join(__dirname, '../data')) {
    this.dataDir = dataDir;
    this.dataFile = path.join(dataDir, 'activities.json');
    this.currentSession = null;
    this.checkInterval = null;
    
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    
    if (!fs.existsSync(this.dataFile)) {
      fs.writeFileSync(this.dataFile, JSON.stringify({ sessions: [], activities: [] }, null, 2));
    }
  }

  loadData() {
    const data = fs.readFileSync(this.dataFile, 'utf8');
    return JSON.parse(data);
  }

  saveData(data) {
    fs.writeFileSync(this.dataFile, JSON.stringify(data, null, 2));
  }

  async detectActiveApplication() {
    try {
      const platform = process.platform;
      let command;
      
      if (platform === 'darwin') {
        command = 'osascript -e \'tell application "System Events" to get name of first application process whose frontmost is true\'';
      } else if (platform === 'linux') {
        command = 'xdotool getwindowfocus getwindowname 2>/dev/null || echo "Unknown"';
      } else if (platform === 'win32') {
        command = 'powershell "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -First 1 MainWindowTitle | Format-Table -HideTableHeaders"';
      } else {
        return 'Unknown';
      }
      
      const { stdout } = await execAsync(command);
      return stdout.trim() || 'Unknown';
    } catch (error) {
      return 'Unknown';
    }
  }

  categorizeActivity(appName) {
    const categories = {
      'Communication': ['Slack', 'Microsoft Teams', 'Discord', 'Zoom', 'Skype', 'WhatsApp', 'Telegram', 'Meet', 'Webex'],
      'Email': ['Mail', 'Outlook', 'Gmail', 'Thunderbird'],
      'Development': ['Code', 'Visual Studio', 'IntelliJ', 'Eclipse', 'Xcode', 'Terminal', 'iTerm', 'Vim', 'Emacs'],
      'Browser': ['Chrome', 'Firefox', 'Safari', 'Edge', 'Brave'],
      'Documentation': ['Word', 'Docs', 'Notion', 'Confluence', 'Evernote']
    };

    for (const [category, apps] of Object.entries(categories)) {
      if (apps.some(app => appName.toLowerCase().includes(app.toLowerCase()))) {
        return category;
      }
    }
    
    return 'Other';
  }

  start() {
    if (this.currentSession) {
      return { success: false, message: 'Tracking already active' };
    }

    this.currentSession = {
      id: Date.now().toString(),
      startTime: new Date().toISOString(),
      activities: []
    };

    this.checkInterval = setInterval(async () => {
      const appName = await this.detectActiveApplication();
      const category = this.categorizeActivity(appName);
      const timestamp = new Date().toISOString();
      
      const activity = {
        timestamp,
        application: appName,
        category
      };
      
      this.currentSession.activities.push(activity);
    }, CHECK_INTERVAL_MS);

    return { success: true, message: 'Time tracking started', sessionId: this.currentSession.id };
  }

  stop() {
    if (!this.currentSession) {
      return { success: false, message: 'No active tracking session' };
    }

    clearInterval(this.checkInterval);
    this.checkInterval = null;

    this.currentSession.endTime = new Date().toISOString();
    
    const data = this.loadData();
    data.sessions.push(this.currentSession);
    
    this.currentSession.activities.forEach(activity => {
      data.activities.push(activity);
    });
    
    this.saveData(data);

    const sessionId = this.currentSession.id;
    const duration = new Date(this.currentSession.endTime) - new Date(this.currentSession.startTime);
    this.currentSession = null;

    return { 
      success: true, 
      message: 'Tracking stopped', 
      sessionId,
      duration: Math.round(duration / 1000 / 60) // minutes
    };
  }

  status() {
    if (!this.currentSession) {
      return { 
        active: false, 
        message: 'No active tracking session' 
      };
    }

    const duration = Date.now() - new Date(this.currentSession.startTime).getTime();
    const minutes = Math.round(duration / 1000 / 60);
    
    return {
      active: true,
      sessionId: this.currentSession.id,
      startTime: this.currentSession.startTime,
      duration: minutes,
      activitiesLogged: this.currentSession.activities.length
    };
  }

  generateReport(period = 'today') {
    const data = this.loadData();
    const now = new Date();
    let startDate;

    switch(period) {
      case 'today':
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'week':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'month':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      default:
        startDate = new Date(0);
    }

    const filteredActivities = data.activities.filter(activity => {
      const activityDate = new Date(activity.timestamp);
      return activityDate >= startDate;
    });

    const categoryStats = {};
    const appStats = {};

    filteredActivities.forEach(activity => {
      categoryStats[activity.category] = (categoryStats[activity.category] || 0) + 1;
      appStats[activity.application] = (appStats[activity.application] || 0) + 1;
    });

    const sortedCategories = Object.entries(categoryStats)
      .sort((a, b) => b[1] - a[1])
      .map(([category, count]) => ({ category, minutes: count }));

    const sortedApps = Object.entries(appStats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([app, count]) => ({ application: app, minutes: count }));

    return {
      period,
      totalMinutes: filteredActivities.length,
      categories: sortedCategories,
      topApplications: sortedApps,
      sessionsCount: data.sessions.filter(s => {
        const sessionDate = new Date(s.startTime);
        return sessionDate >= startDate;
      }).length
    };
  }

  exportData(format = 'json') {
    const data = this.loadData();
    
    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }
    
    if (format === 'csv') {
      let csv = 'Timestamp,Application,Category\n';
      data.activities.forEach(activity => {
        csv += `${activity.timestamp},${activity.application},${activity.category}\n`;
      });
      return csv;
    }
    
    return null;
  }

  clearData() {
    this.saveData({ sessions: [], activities: [] });
    return { success: true, message: 'All data cleared' };
  }
}

module.exports = TimeTracker;
