#!/bin/bash
# Install Strategist Agent launchd jobs
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCHD_DIR="$SCRIPT_DIR/scripts/launchd"
TARGET_DIR="$HOME/Library/LaunchAgents"

# Настройка: IWE_WORKSPACE — корневая директория IWE (можно переопределить через env)
IWE_WORKSPACE="${IWE_WORKSPACE:-$HOME/Documents/IWE}"

echo "Installing Strategist Agent launchd jobs..."
echo "  IWE_WORKSPACE: $IWE_WORKSPACE"

# Unload old agents if present
launchctl unload "$TARGET_DIR/com.strategist.morning.plist" 2>/dev/null || true
launchctl unload "$TARGET_DIR/com.strategist.weekreview.plist" 2>/dev/null || true
launchctl bootout gui/$(id -u)/com.strategist.update-reminder 2>/dev/null || true

# Copy plist files with path substitution (__IWE_WORKSPACE__ → actual path)
for plist in com.strategist.morning.plist com.strategist.weekreview.plist com.strategist.update-reminder.plist; do
    sed "s|__IWE_WORKSPACE__|$IWE_WORKSPACE|g; s|__USER_HOME__|$HOME|g" \
        "$LAUNCHD_DIR/$plist" > "$TARGET_DIR/$plist"
done

# Make script executable
chmod +x "$SCRIPT_DIR/scripts/strategist.sh"
chmod +x "$HOME/bin/update-reminder.sh" 2>/dev/null || true

# Load agents
launchctl load "$TARGET_DIR/com.strategist.morning.plist"
launchctl load "$TARGET_DIR/com.strategist.weekreview.plist"
launchctl bootstrap gui/$(id -u) "$TARGET_DIR/com.strategist.update-reminder.plist"

echo "Done. Agents loaded:"
launchctl list | grep strategist
