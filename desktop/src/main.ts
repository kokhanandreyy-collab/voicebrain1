import { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, ipcMain, screen } from 'electron';
import * as path from 'path';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
const APP_URL = 'http://localhost:5173'; // Dev execution

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        show: false, // Don't show until ready
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    mainWindow.loadURL(APP_URL);

    mainWindow.on('ready-to-show', () => {
        mainWindow?.show();
    });

    // Minimize to tray logic
    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow?.hide();
        }
        return false;
    });
}

const toggleWindow = () => {
    if (mainWindow?.isVisible()) {
        mainWindow.hide();
    } else {
        mainWindow?.show();
        mainWindow?.focus();
    }
};

const triggerRecording = () => {
    if (!mainWindow) return;
    mainWindow.show();
    mainWindow.focus();
    // Send IPC to renderer
    mainWindow.webContents.send('start-recording');
};

app.whenReady().then(() => {
    createWindow();

    // Tray Icon
    // Placeholder icon usage
    const iconPath = path.join(__dirname, '../../web/public/vite.svg'); // Try to grab from web? Or generate? 
    // For now we might fail on icon path, so maybe skip icon or use empty
    try {
        tray = new Tray(iconPath);
        const contextMenu = Menu.buildFromTemplate([
            { label: 'Show/Hide', click: toggleWindow },
            { label: 'Record New Note', click: triggerRecording },
            {
                label: 'Quit', click: () => {
                    app.isQuitting = true;
                    app.quit();
                }
            }
        ]);
        tray.setToolTip('VoiceBrain');
        tray.setContextMenu(contextMenu);

        tray.on('click', toggleWindow);
    } catch (e) {
        console.log("Tray icon failed load (expected if files missing)", e);
        // Fallback tray text?
    }

    // Global Shortcut
    const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
        console.log('CommandOrControl+Shift+Space is pressed');
        triggerRecording();
    });

    if (!ret) {
        console.log('registration failed');
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Flag/Property to check quitting
// Extending 'app' object in TS might need interface augmentation, or just simple property assignment
// Here we cast to any or use a global var?
// Let's use a property on app instance if TS allows, else global var.
(app as any).isQuitting = false;
