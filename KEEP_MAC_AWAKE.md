# Keep MacBook Awake During Development

Multiple options to prevent your Mac from sleeping while running the API server.

---

## Option 1: caffeinate (Recommended) ☕

Built-in macOS command, no installation needed.

### Quick Start

```bash
# Use the pre-configured script (keeps Mac awake automatically)
./scripts/start_api_server_awake.sh
```

### Manual Usage

```bash
# Keep Mac awake while API runs
caffeinate ./scripts/start_api_server.sh

# Keep Mac awake with tmux setup
caffeinate ./start-mobile-test-tmux.sh

# Keep Mac awake indefinitely (Ctrl+C to stop)
caffeinate

# Keep Mac awake for 2 hours
caffeinate -t 7200
```

### caffeinate Flags

```bash
-i    Prevent idle sleep (recommended for servers)
-d    Prevent display sleep
-m    Prevent disk sleep
-s    Prevent system sleep (AC power only)
-t N  Timeout after N seconds
```

### Example with Flags

```bash
# Prevent idle sleep while API runs (recommended)
caffeinate -i ./scripts/start_api_server.sh

# Keep display and system awake
caffeinate -d -i python3 -m uvicorn src.api_server:app
```

**Pros:**
- ✅ Built-in to macOS
- ✅ No installation needed
- ✅ Stops automatically when process ends
- ✅ Command-line friendly

**Cons:**
- ⚠️ Must be started from terminal
- ⚠️ No GUI controls

---

## Option 2: System Settings

Adjust macOS power settings directly.

### Steps

1. Open **System Settings** > **Displays**
2. Click **Advanced...** button
3. Uncheck **"Prevent automatic sleeping on power adapter when the display is off"**

OR

1. Open **System Settings** > **Lock Screen**
2. Set "Turn display off on battery when inactive" to **Never**
3. Set "Turn display off on power adapter when inactive" to **Never**

**Important:** Remember to re-enable sleep settings when done!

**Pros:**
- ✅ No terminal commands needed
- ✅ Works system-wide

**Cons:**
- ❌ Easy to forget to re-enable
- ❌ Affects battery life
- ❌ Not automated

---

## Option 3: Amphetamine (Free Mac App)

Professional app for keeping Mac awake.

### Installation

```bash
# Install via Homebrew
brew install --cask amphetamine

# Or download from Mac App Store (free)
# https://apps.apple.com/us/app/amphetamine/id937984704
```

### Features

- 🎛️ Menu bar controls
- ⏰ Timer-based sessions
- 🔧 Trigger-based automation
- 🎨 Customizable settings
- 📊 Session history

**Pros:**
- ✅ User-friendly GUI
- ✅ Flexible controls
- ✅ Can trigger based on specific apps
- ✅ Timer and schedule support

**Cons:**
- ⚠️ Requires installation
- ⚠️ Manual start/stop (unless configured)

---

## Option 4: KeepingYouAwake (Open Source)

Lightweight alternative to Amphetamine.

### Installation

```bash
# Install via Homebrew
brew install --cask keepingyouawake
```

### Usage

- Click coffee icon in menu bar to activate
- Click again to deactivate
- Simple on/off toggle

**Pros:**
- ✅ Very simple
- ✅ Open source
- ✅ Lightweight

**Cons:**
- ⚠️ Less features than Amphetamine
- ⚠️ Manual control only

---

## Comparison Table

| Method | Installation | Automation | Ease of Use | Battery Impact |
|--------|-------------|------------|-------------|----------------|
| caffeinate | None (built-in) | ✅ Auto-stops | Terminal only | Low (tied to process) |
| System Settings | None | ❌ Manual | Easy | High (always on) |
| Amphetamine | Required | ✅ Configurable | Very Easy | Medium (controllable) |
| KeepingYouAwake | Required | ❌ Manual | Easy | Medium (on/off) |

---

## Recommended Workflow

### For Development (Recommended)

Use `caffeinate` with our scripts:

```bash
# Option 1: Use pre-configured script
./scripts/start_api_server_awake.sh

# Option 2: Add caffeinate to tmux
caffeinate ./start-mobile-test-tmux.sh
```

### For Long-Running Server

Install Amphetamine and configure triggers:

1. Install Amphetamine
2. Add trigger: "Keep awake when API server is running"
3. Set to activate when `python` process is detected on port 8000

### For Quick Testing

Use simple caffeinate command:

```bash
# In one terminal
caffeinate

# In another terminal
./scripts/start_api_server.sh
```

Press Ctrl+C in caffeinate terminal when done.

---

## Scripts in This Project

### With caffeinate (Keeps Mac Awake)

```bash
./scripts/start_api_server_awake.sh
```

### Without caffeinate (Standard)

```bash
./scripts/start_api_server.sh
```

### Tmux Setup (Add caffeinate manually)

```bash
# Without keep-awake
./start-mobile-test-tmux.sh

# With keep-awake
caffeinate ./start-mobile-test-tmux.sh
```

---

## How to Check if Mac is Prevented from Sleeping

```bash
# Check caffeinate processes
ps aux | grep caffeinate

# Check power assertions
pmset -g assertions | grep -i "PreventUserIdleSystemSleep\|PreventSystemSleep"
```

You should see output like:
```
PreventUserIdleSystemSleep    1
```

---

## Battery Considerations

**When on Battery:**
- caffeinate `-s` flag won't work (system sleep only works on AC)
- Use `-i` flag instead (prevents idle sleep)
- Close MacBook lid = sleep (can't prevent without third-party apps)

**When on AC Power:**
- All methods work
- caffeinate can use `-s` flag
- Display can sleep, system stays awake

---

## Troubleshooting

### Mac Still Sleeps

**Problem:** Mac sleeps despite caffeinate
**Solution:** Use `-i` flag explicitly:
```bash
caffeinate -i ./scripts/start_api_server.sh
```

### Process Killed

**Problem:** caffeinate process killed unexpectedly
**Solution:** Check if battery saver mode is active:
```bash
pmset -g batt
```

### Display Keeps Sleeping

**Problem:** Display sleeps but system stays awake
**Solution:** This is normal with `-i` flag. To keep display awake:
```bash
caffeinate -d -i ./scripts/start_api_server.sh
```

---

## Best Practices

1. ✅ **Use caffeinate for development** - automatic and safe
2. ✅ **Keep display sleep enabled** - saves energy, doesn't affect server
3. ✅ **Use tmux with caffeinate** - best of both worlds
4. ❌ **Don't disable system sleep globally** - wastes battery
5. ✅ **Re-enable sleep when done** - good battery management

---

## Quick Reference

| Task | Command |
|------|---------|
| Keep awake during API run | `caffeinate -i ./scripts/start_api_server.sh` |
| Keep awake for 1 hour | `caffeinate -t 3600` |
| Keep awake indefinitely | `caffeinate` |
| Keep display awake too | `caffeinate -d -i ./scripts/start_api_server.sh` |
| Check if active | `pmset -g assertions \| grep -i prevent` |
| Kill caffeinate | `pkill caffeinate` |

---

## Additional Resources

- [caffeinate man page](https://ss64.com/osx/caffeinate.html)
- [Amphetamine](https://apps.apple.com/us/app/amphetamine/id937984704)
- [KeepingYouAwake](https://keepingyouawake.app/)
- [pmset documentation](https://ss64.com/osx/pmset.html)
