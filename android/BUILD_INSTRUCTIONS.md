# AttendanceApp - Android Build Instructions

## Prerequisites

- Android Studio (latest version recommended)
- JDK 17+
- Android SDK (API 34)

## Setup

### 1. Configure Server URL

Open `app/src/main/java/com/attendanceapp/MainActivity.java` and change:

```java
private static final String APP_URL = "http://YOUR_SERVER_IP:80";
```

Replace `YOUR_SERVER_IP` with your Flask server's IP address. Examples:
- Local testing: `http://10.0.2.2:80` (Android emulator → host machine)
- LAN: `http://192.168.1.100:80` (your server's LAN IP)
- Production: `http://your-domain.com` (your deployed server)

### 2. Build APK

#### Option A: Android Studio
1. Open the `android/` folder in Android Studio
2. Wait for Gradle sync to complete
3. Go to **Build → Build Bundle(s) / APK(s) → Build APK(s)**
4. APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

#### Option B: Command Line
```bash
cd android
chmod +x gradlew
./gradlew assembleDebug
```
APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

#### Option C: Signed Release APK
```bash
cd android
./gradlew assembleRelease
```
Note: For release, you need to configure signing in `app/build.gradle`.

### 3. Install on Device

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or transfer the APK to your phone and install it.

## Features

- WebView loads the Flask attendance app
- Gradient progress bar while loading
- Error screen with retry button when offline
- Back button navigates WebView history
- Fullscreen with themed status bar
- Splash screen with gradient background
- Custom app icon (clock design)

## Troubleshooting

- **Can't connect to server**: Make sure `usesCleartextTraffic="true"` is in AndroidManifest.xml (already included) for HTTP connections
- **Emulator can't reach host**: Use `10.0.2.2` instead of `localhost` or `127.0.0.1`
- **White screen**: Check that the Flask server is running and accessible from your device's network
