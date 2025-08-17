// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'KALI-Speed-Engine',
      script: 'main_speed_engine.py',
      args: 'multi', // Use 'multi' to launch all listeners (raydium, pump, virtuals)
      interpreter: 'python3',
      restart_delay: 5000, // Wait 5 seconds before restarting on crash
      autorestart: true,
      max_restarts: 10, // Attempt to restart 10 times
    },
    {
      name: 'KALI-Position-Tracker',
      script: 'position_tracker_v2.py',
      interpreter: 'python3',
      restart_delay: 5000,
      autorestart: true,
      max_restarts: 10,
    },
  ],
};