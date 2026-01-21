import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
import { join } from 'path'
import * as fs from 'fs'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { spawn, ChildProcessWithoutNullStreams } from 'child_process'
import icon from '../../resources/icon.png?asset'
// 引入 server 模块
import { startServer, setReviewDir, setMainWindow } from './server' // 新增 setMainWindow

// === 配置区 ===
const CONFIG_PATH = is.dev
  ? join(__dirname, '../../config.json') 
  : join(process.resourcesPath, 'config.json')

let PYTHON_PATH = 'python' // 默认值，万一没配置文件就用系统默认的
  
try {
  if (fs.existsSync(CONFIG_PATH)) {
    const rawData = fs.readFileSync(CONFIG_PATH, 'utf-8')
    const config = JSON.parse(rawData)
    // 如果配置文件里写了 pythonPath，就用它；否则保持默认
    if (config.pythonPath) {
      PYTHON_PATH = config.pythonPath
      console.log(`[Config] Loaded Python path: ${PYTHON_PATH}`)
    }
  } else {
    console.warn(`[Config] Warning: config.json not found at ${CONFIG_PATH}, using default 'python'`)
  }
} catch (error) {
  console.error('[Config] Error reading config.json:', error)
}

const PYTHON_SCRIPT = join(__dirname, '../../api.py')

let pythonProcess: ChildProcessWithoutNullStreams | null = null
let mainWindow: BrowserWindow | null = null

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 850,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#0f172a',
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true
    }
  })

  setMainWindow(mainWindow)

  mainWindow.on('ready-to-show', () => {
    if (mainWindow) mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function startPythonBackend(): void {
  console.log('Starting Python backend...')
  try {
    pythonProcess = spawn(PYTHON_PATH, [PYTHON_SCRIPT, '-u'])

    if (pythonProcess.stdout) {
      pythonProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n')
        lines.forEach((line: string) => {
          if (line.trim()) {
            try {
              const jsonMsg = JSON.parse(line)
              if (mainWindow) mainWindow.webContents.send('python-log', jsonMsg)
            } catch (e) {
              console.log('Raw Python Output:', line)
            }
          }
        })
      })
    }

    if (pythonProcess.stderr) {
      pythonProcess.stderr.on('data', (data) => {
        const errMsg = data.toString()
        console.error(`Python Error: ${errMsg}`)
        if (mainWindow) mainWindow.webContents.send('python-log', { type: 'err', msg: errMsg })
      })
    }
  } catch (e) {
    console.error('Spawn Error:', e)
  }
}

// === App 生命周期管理 ===
// 确保 app 被正确使用
app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.electron')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  createWindow()
  startPythonBackend()

  // 1. 启动本地 Web 服务器 (Analytics)
  startServer()

  // --- IPC 监听 ---
  // IPC: 打开外部链接 (用于更新)
  // @ts-ignore
  ipcMain.handle('shell:openExternal', async (_, url) => {
    await shell.openExternal(url)
  })

  // IPC: 选择文件夹
  ipcMain.handle('dialog:openDirectory', async () => {
    if (!mainWindow) return null
    const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory']
    })
    if (canceled) return null
    return filePaths[0]
  })

  // IPC: 打开文件夹
  ipcMain.handle('shell:openPath', async (_, path) => {
    await shell.openPath(path)
  })

  // IPC: 打开 Analytics
  // @ts-ignore
  ipcMain.on('open-analytics', (event, outputDir) => {
    setReviewDir(outputDir)
    // 假设本地服务器运行在 3333 端口
    shell.openExternal('http://localhost:3333')
  })

  // IPC: 通用 Python 指令
  ipcMain.on('run-python-command', (event, args) => {
    if (pythonProcess && pythonProcess.stdin) {
      const command = JSON.stringify(args) + '\n'
      pythonProcess.stdin.write(command)
    }
  })

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
